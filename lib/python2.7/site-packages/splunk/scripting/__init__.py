from __future__ import print_function
from builtins import object
import sys, re, platform, os, csv

import splunk
import splunk.search
import splunk.util as sutil
import splunk.Intersplunk
import logging
from threading import Thread
import time
from splunk.clilib.bundle_paths import make_splunkhome_path

def setup_logging():
    logger = logging.getLogger('splunk.script')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    # define logging configuration. taken from python-site/splunk/appserver/mrsparkle/root.py
    LOGGING_DEFAULT_CONFIG_FILE = make_splunkhome_path(['etc', 'log.cfg'])
    LOGGING_LOCAL_CONFIG_FILE = make_splunkhome_path(['etc', 'log-local.cfg'])
    LOGGING_STANZA_NAME = 'python'
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, 'search_script.log'), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

logger = setup_logging()


###########################################################
############ GOALS
###########################################################
## remove need for many subsearches
## post-processing results into many charts (need to output many jobs + chartspec?)
## getting events near other events
## comparing results
## integrating outside data
## complex alerting conditions / actions
## post-processing BY clause
## unify with a new api for python search commands
##
## have 'templates' of scripts to handle most common use cases (e.g. diffing two searches), and have them drop down from a selection box at the top. this would be the greatest educational tool.
## template could just be a script that's heavily commented and has placeholders for real values. or better is a class and user is writing 'run_user' method, while class handles dispatching error handling, logging in, converting user's code to debuggable (e.g. foo(); bar(); --> try: foo(); profilestep(); bar(); profilestep(); except ...)
## allowing uses to add their own templates as well. templates/scripts could be shared on answers.splunk.com and possibly splunkbase.
## consider security issues. undefining eval, exec, file io,
## consider timeout issues (e.g. setting for max script run time?)
## need to help debug execution of each statement on at a time. (e.g. next button and value of "_" in python and known variables. pretty easy)
## consider auto importing (e.g. math.sin(foo) --> if math undefined, attempt to import math)
## api
##
## it should be as intuitive, clear, and minimal as possible.
## we know we're in the splunk world, so the user doesn't need to think about, or specify, sessionkeys, users, passwords, namespaces, etc. (he can set those if he wants to somehow refer to other apps, I suppose)
## make convenient classes for various usecases. perhaps something like a 'resultsDiffer', for example.
## have iterators deal with all the set up of the search and canceling
## for performance reasons, perhaps complex searches can be assembled behind the user's back (possibly buggy red flags here). for example, a diff command that took two searches, might run them as one search
## some ideas inspired by sql stored modules
##
## (http://kb.askmonty.org/v/persistent-stored-modules)
## app has named Scripts, with names being unique
## script can have parameters passed in
## output-status of success or failure
## scripts have acl
## scripts have authorization info (e.g. sessionkey, module, owner) passed in
## scripts can run other scripts
## parallel statements? defaults to serial obviously. sql has 'atomic'
## iterators similar to cursors
## common handling of errors (e.g. script template class might have standard way to error and user can overwrite) sql has handlers
## somewhat sandboxed in that it cannot do disk or screen I/O
## sql optimizer -> search optimizer to optimize search or multisearches???
## reporting where time is going (profiling that includes searchjob stats)



####################################################################################################################################
########### SCRIPT CLASSES TO RUN A SCRIPT
####################################################################################################################################

class ScriptException(Exception):
    """
    Represents Exceptions while processing or running a script
    """
    pass

class Script(object):
    """
    Represents a Splunk Search Script, which allows custom, multistep processing.
    """

    def __init__(self, sessionKey, owner, namespace, name=None, path=None, script=None, prerunfix=True, settings=None, outputstream=sys.stdout):
        """
        Script initialization
        @type  sessionKey: string
        @param sessionKey: the authentication value needed to run commands against the Splunk API.
        @type  owner: string
        @param owner: user running the script.
        @type  namespace: string
        @param namespace: app that script should be run in.
        @type  name: string
        @param name: name of the script. In no value given, the filename is used.
        @type  path: string
        @param path: if supplied the script is read in from this value.
        @type  script: string
        @param script: if path is not supplied, the text of the script.
        @type  prerunfix: bool
        @param prerunfix: if True, scripts are pre-run to fix import problems and find syntax errors
        @type  settings: dictionary
        @param settings: unused
        @rtype: None
        @return: nothing
        """

        self.sessionKey = sessionKey
        self.owner = owner
        self.namespace = namespace
        self._script = None
        if name == None:
            name = "script"
            if path != None: # name = windows, given path of '~/foo/bar/windows.py'
                name = path[path.rfind(os.sep)+1:].replace('.py', '')

        self.name = name
        self.successful = False
        self.settings = settings
        self.outputstream = outputstream
        self.outputRows = 0
        self.prerunfix = prerunfix
        self.testmode = False
        if path != None:
            script = self._load_script(path)
        self.set_script(script)

    def _load_script(self, path):
        f = None
        code = None
        try:
            f = open(path, 'r')
            code = ''.join(f.readlines())
        except Exception as e:
            raise ScriptException(e)
        finally:
             if f: f.close()
        return code

    def onError(self, e):
        raise e

    def preRun(self):
        """
        Future use: code to be run before the script runs.
        """
        pass

    def set_script(self, script):
        """
        Sets the script text, possibly cleaning up import problems, and testing the code for errors
        @type  script: string
        @param script: the text of the script.
        @rtype: None
        @return: nothing
        """
        if script == self._script:
            return False
        cleaned_code = self._clean_code(script)
        self._script = cleaned_code


    def postRun(self):
        """
        Future use: code to be run after the script runs.
        """
        pass

    def isSuccessful(self):
        """
        @rtype: bool
        @return: True, if script was successfully run.
        """
        return self.successful

    def run(self):
        """
        Run the script.
        @rtype: dictionary
        @return: variables/values that have changed/created by running the script
        """
        self.preRun()
        output = self._run()
        self.postRun()
        return output

    def _run(self):
        """
        Internal Run Function that executes the script.  Aliases
        public Script methods to local variables accessible to
        scripts (e.g. search = self.search).  Does basic sanity
        checking on dangerous operations performed.

        @rtype: dictionary
        @return: variables/values that have changed/created by running the script
        """

        mylocals = dict(self._aliased_locals())
        initlocals = dict(locals())
        code = self._script
        cache = _stow_away_dangerous()
        try:
            exec(code, globals(), mylocals)
        except:
            logger.error('type="Script Problem" name="%s"' % self.name)
            raise
        _restore_danger(cache)

        # remove any values that haven't changed or is an imported module
        for var, val in mylocals.items():
            if( var in initlocals and initlocals[var] == val) or val.__class__.__name__ == 'module':
                mylocals.pop(var)
        return mylocals #???

    def _aliased_locals(self):
        """
        Aliases public Script methods to local variables accessible to scripts.
        @rtype: dictionary
        @return: mappings such as d['search'] = self.search
        """
        # returns locals variables + search=self.search etc...
        loc = dict(locals())
        for cmd in Script.API_COMMANDS:
            exec('loc["%s"] = self.%s' % (cmd, cmd))
        return loc

    def _clean_code(self, code):
        """
        Checks code is safe and automatically imports referenced packages
        @type  code: string
        @param code: code to check
        @rtype: string
        @return: modified code
        """

        _unsafeCheck(code)
        # modify code to have 'self' parameter in front of each command
        #newcode = re.sub("(?<![a-zA-Z])(%s)[(]" % "|".join(Script.API_COMMANDS), "self.\\1(", code)

        newcode = code
        oldErr = None
        while True:
            try:
                compile(newcode, "", "exec")
                if self.prerunfix:
                    self.testmode = True
                    exec(newcode, globals(), self._aliased_locals())
                    self.testmode = False
                break
            except NameError as ne:
                ms = re.findall("name '(\S+)' is not defined", str(ne))
                if ne == oldErr or len(ms) != 1 or ms[0] == 'this':
                    raise ne
                else:
                    newcode = 'import %s\n%s' % (ms[0], newcode)
                    oldErr = ne
            except Exception as e:
                logger.error('type="Script Problem" name="%s"' % self.name)
                logger.error("-"*100)
                logger.error(newcode)
                logger.error("-"*100)
                raise
        return newcode



    ####################################################################################################################################
    ########### PUBLIC FUNCTIONS USED BY SCRIPTS (i.e. the api)
    ####################################################################################################################################

    API_COMMANDS = ['search', 'post', 'diff', 'near', 'output', 'join']
    """script calls to functions in this list are modified to include the script variable as the first arg"""


    # # define time ranges to run multiple copies of the search, along with attr=val that gets added to events (e.g., mylabel=yesterday)
    # myranges = [{earliest:'-30d@d', 'mylabel':'lastmonth'}, {earliest='-1d@d', 'mylabel':'yesterday'}]
    # # run search over time ranges with post_search to get stats
    # results = search('*foo* | calc some stats over these results (baseline)', times=myranges, post_search='stats count by mylabel')

    def search(self, q, earliest=None, latest=None, max_count=None, times=None):
        """
        Kicks off a search, returning immediately.

        @type  q: string
        @param q: the search to kick off
        @type  earliest: number (seconds offset) or time-offset (e.g. '-9d')
        @param earliest: earliest time from which to consider events.
        @type  latest: number (seconds offset) or time-offset (e.g. '-9d')
        @param latest: latest time from which to consider events.
        @type  max_count: integer
        @param max_count: maximum number of results for search to return
        @type  times: list of dictionaries containing 'label' and 'earliest' and/or 'latest'.
        @param times: list time ranges to run search over, settings 'label' to the value of the time change in question on the results.
        @rtype: ScriptJob
        @return: job from which to manage search and retrieve results.
        """

        logger.debug('command=search search="%s" max_count="%s"' % (q, max_count))

        # if we're only execing the code for syntax errors and testing, run the fastest search possible
        if self.testmode == True:
            q = '| stats count as _raw | eval _raw="test"'
        else:
            q = _fix_search(q)
        sjob = splunk.search.searchAll(q, sessionKey=self.sessionKey, namespace=self.namespace, owner=self.owner, max_count=None, earliest_time=earliest, latest_time=latest)


        return ScriptJob(sjob)


    def post(self, input_job, q, preview=True, postfunc=None, max_count=None):
        """
        Kicks off a post-process search, returning immediately.

        @type  input_job: ScriptJob
        @param input_job: results to post process
        @type  q: string
        @param q: search to post-process results from input_job.
        @type  preview: bool
        @param preview: if True, output_preview will regularly be called with intermediate results.
        @type  postfunc: python function
        @param postfunc: if specified, this function is called on each result before returned, in preview and not. The function takes a ScriptResult and must return one
        @type  max_count: integer
        @param max_count: maximum number of results for search to return
        @rtype: PostScriptJob
        @return: job from which to manage search and retrieve results.
        """
        logger.debug('command=post q="%s"' % q)
        postjob = PostScriptJob(self, input_job, q, preview=preview, postfunc=postfunc, max_count=max_count)
        postjob.start()
        return postjob


    # come common convenient diff function?
    # we need to define what a diff looks like (including diff in values, diff is position (was #4 now is #2).
    # how to 'diff' stats, vs timechart, vs chart, etc
    def diff(self, results1, results2, by=None):
        """
        Calculates the difference of results.  Currently unclear what that should mean for sets of results (e.g. timecharts, events, etc)

        @type  results1: ScriptJob
        @param results1: first results to compare
        @type  results2: ScriptJob
        @param results2: second results to compare
        @type  by: None, string, or list.  None means all features; a single feature, diff by that feature; a list of features, diff by all those features
        @param by: determines how the difference is determined.
        @rtype: ScriptJob
        @return: the difference between results1 and results2.
        """
        logger.debug('command=diff by="%s"' % by)

    # out = join(z, 'rip', y.to_string('rip, src_mac')
    # by_fields can be list or string
    def join(self, input_job, by_fields, q, max_count=None):
        """
        Convenience function.  Probably unnecessary.
        join(input_job, by, q) is the same as post(input_job, "|join %s [%s]" % (",".join(by), q))

        @type  input_job: ScriptJob
        @param input_job: results to join
        @type  by: string or list of strings
        @param by: determines by which attributes the events are joined.
        @type  q: string
        @param q: search to run and join with input_job.
        @type  max_count: integer
        @param max_count: maximum number of results for search to return.
        @rtype: PostScriptJob
        @return: job from which to manage search and retrieve results.
        """
        logger.debug('command=diff by="%s"' % by_fields)
        return self.post(input_job, "|join %s [%s]" % (",".join(by_fields), q))

    # errorsOut = near('login', 'error', '+0m', '+5m')
    def near(self, q1, q2, min_time_diff, max_time_diff):
        """
        Returns results from q2 that are within a time window of results from q1.
        For example, find errors that are within 5 minutes of a root login.

        @type  q1: string
        @param q1: search query to determine time boundaries.
        @type  q2: string
        @param q2: search query to return results within time boundaries.
        @type  min_time_diff: number (seconds offset) or time-offset (e.g. '-9d')
        @param min_time_diff: Minimum time difference between results from q1 and q2 (e.g. "0")
        @type  max_time_diff: number (seconds offset) or time-offset (e.g. '-9d')
        @param max_time_diff: Maximum time difference between results from q1 and q2 (e.g. "60" or "+5m")
        @rtype: PostScriptJob
        @return: job from which to manage search and retrieve results.
        """
        logger.debug('command=after_search q1="%s" q2="%s" time_diff="%s-%s"' % (q1, q2, min_time_diff, max_time_diff))
        return []

    def log(self, msg):
        ''' log to a script log for real_time(?) retrieval for debugging.  allows user to log values debugging in their script.'''
        """
        Allows script to log messages that assist in debugging.
        @type  msg: string
        @param msg: message to log
        @rtype: None
        @return: nothing
        """
        logger.debug('command=log msg="%s"' % msg)

    # outputs a single result or a list of results
    def output(self, thing):
        """
        Outputs results from the script
        @type  thing: a single result, a list of results, or an entire ScriptJob.
        @param thing: object to output
        @rtype: None
        @return: nothing
        """
        logger.debug('command=output %s' % _prettyID(thing))

        if thing == None:
            return # do nothing
        if self.testmode:
            return # do nothing. no output on testing

        writer = csv.writer(self.outputstream)

        # !!! HACKHACK.  ASSUMES FIRST RESULTS WILL HAVE ALL KEYS OF ALL RESULTS.  NEED TO CLEAN UP.
        # WHAT IF USER OUTPUTS RESULTS THEN ADDS FIELDS?!
        if isinstance(thing, ScriptJob) or isinstance(thing, list):
            for i, r in enumerate(thing):
                if i == 0:
                    writer.writerow(r.keys())
                self.outputRows += 1
                writer.writerow(r.values()) #! order is a problem.   make results be ordered not dict.
        elif isinstance(thing, ScriptResult):
            if self.outputRows == 0:
                writer.writerow(thing.keys())
            writer.writerow(thing.values())
            self.outputRows += 1
        else:
            raise ScriptException("output() can only be passed a searchjob, result, or a list of results.  Not a '%s'." % thing.__class__.__name__)


# as opposed to interactive script.  this would handle scheduled scripts, not run with an interactive ui.
class BatchScript(Script):
    """
    TODO.  Needs work. Class to use when calling scripts non-interactively, so errors are logged, rather than raised, etc.
    """
    def __init__(self):
        super(BatchScript, self).__init__()

    def onError(self, e):
        logger.error(e)


####################################################################################################################################
########### JOBS AND RESULTS
####################################################################################################################################

class ScriptJob(object):
    """Wrapper around JV's splunk.search.SearchJob, for more convenience. Results are dicts, _time is epoch not ISO, and results are automatically processed by user defined callbacks, lazily called."""

    def __init__(self, job):
        logger.debug('command=create_script_job %s' % _prettyID(job))
        self._job = job
        self._callback = None

    def __del__(self):
        try:
            if self.getJob() == None: return
            logger.debug('command=delete_script_job %s' % _prettyID(self._job))
            self._job.cancel()
        except:
            pass

    def hasJob(self):
        return self._job != None

    def getJob(self):
        if self.hasJob():
            return self._job
        return None

    def __len__(self):
        if not self.hasJob(): return 0
        return self.getJob().__len__()
    def __getattr__(self, key):
        if not self.hasJob(): return None
        return self.getJob().__getattr__(key)
    def __getitem__(self, index):
        if not self.hasJob(): return None
        return self.getJob().__getitem__(index)
    def __contains__(self, index):
        return self.hasJob() and self.getJob().__contains__(index)

    # overwrite __iter__ and next to return a dict
    def __iter__(self):
        if not self.hasJob(): return None
        self.i = self.getJob().__iter__()
        return self

    def __next__(self):
        if not self.hasJob(): return None
        obj = next(self.i)
        return self._makeInstance(obj)

    def _makeInstance(self, obj):
        '''convert jv result to dict. jv result is not editable. also has _time in iso format.'''
        result = ScriptResult()
        for a in obj:
            v = obj.get(a)
            # if this is a multivalued field, return list of strings. (for some reason the python api is returning
            # _raw with a length of the string, rather than number of mv-values as for every other field.)
            if a != '_raw' and len(v) > 1:
                val = [str(x) for x in v]
            else: # otherwise just a string
                val = str(obj.get(a))
            try:
                if a == '_time':
                    val = sutil.dt2epoch(sutil.parseISO(val))
                else:
                    val = float(val) if '.' in val else int(val)
            except:
                pass
            result[a] = val
        if self._callback != None:
            # run callback.  callback takes a result and returns a result.
            result = self._callback(*result)
        return result

    def callback(self, func):
        self._callback = func


    def to_string(self, return_format, max_rows=1):
        """
        Returns a string, the same as the 'return' command, for use in another search string.
        @type  return_format: string
        @param return_format: determines how results are formatted (e.g. "mac_addr=src_mac, src_ip=ip")
        @type  max_rows: integer
        @param max_rows: number of results to use in generating the output
        """
        return "NOT IMPLEMENTED"




# 1.0 = sleep between previews the same time as each preview takes.
DEFAULT_PREVIEW_SLEEP_MULTIPLIER = 1.0

class PostScriptJob(ScriptJob, Thread):
    """Subclass of ScriptJob (our wrapper around splunk.search.SearchJob) and Thread.  Created by calls to post().  Runs in a separate thread, so previews can be output as they are available."""

    def __init__(self, scriptobj, input_job, q, max_count=None, preview=True, postfunc=None, maxWaitTime=-1):
        logger.debug('command=create_post_script_job %s' % _prettyID(input_job))
        ScriptJob.__init__(self, None)
        Thread.__init__(self)

        self._job = None
        self._script = scriptobj
        self._max_count = max_count
        self._preview = preview
        self._postfunc = postfunc
        self._maxWaitTime = maxWaitTime
        self._input_job = input_job
        self._out = None
        self._wait_multiplier = DEFAULT_PREVIEW_SLEEP_MULTIPLIER

        base_dir = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'script')

        try:
            os.mkdir(base_dir)
        except:
            pass

        # use memory address of script obj as unique filename for tmp csv
        self._tmp_file = os.path.join(base_dir, str(id(scriptobj)) + '.csv')

        q = _fix_search(q)
        if q.startswith('|'): q = q[1:]
        self._q = '|inputcsv "%s" | %s' % (self._tmp_file, q)

    def __del__(self):
        logger.debug('command=delete_post_script_job %s' % _prettyID(self._input_job))
        super(PostScriptJob, self).__del__()
        if os.path.exists(self._tmp_file):
            try:
                os.remove(self._tmp_file)
            except Exception as e:
                logger.warn('Unable to delete temp file (file="%s") because: %s' % (self._tmp_file, e))

    # ??? can | inputcsv handle file output by Intersplunk.outputResults?? if not have to write custom version
    # ??? outputResults, iterating over results might block for results, rather than the current events we have
    # ??? probably need to redo
    def dumpcsv(self):
        try:
            logger.debug('command=dump_csv %s' % _prettyID(self._input_job))
            saveout = sys.stdout
            sys.stdout = f = open(self._tmp_file, 'w')
            splunk.Intersplunk.outputResults(self._input_job)
            sys.stdout = saveout
            f.close()
        finally:
             if f: f.close()

    def output_preview(self, preview_job):
        """TODO: output preview results"""
        print("previewing with %u results" % len(preview_job))

    def getResults(self):
        return self._out

    def start(self):
        pass

    def generateResults(self):
        """Generates results, from input results we have so far.  Will be called many times for preview functionality"""
        logger.debug('command=post_script_job_run %s' % _prettyID(self._input_job))
        # output input job results to csv. prototype hack.
        self.dumpcsv()
        # get results from running search on input results
        self._job = splunk.search.searchAll(self._q, max_count=self._max_count, sessionKey=self.sessionKey, namespace=self.namespace, owner=self.owner)
        # sort of weird.  if we have a post func, self._out is a list of results processed, otherwise it's job.
        # either way, it's an iterable object to get results, so it should be ok
        if self._postfunc != None:
            self._out = self._postfunc(*self._job)
        else:
            self._out = self._job

    def run(self):
        """Called when thread is started.  If preview=True, results are passed to output_preview() every so often."""
        if self._preview:
            logger.debug('command=post_script_job_run %s' % _prettyID(self._input_job))
            waittime = 0
            # while job not done
            while not self._input_job.isDone:
                time.sleep(waittime) # sleep an appropriate amount of time
                starttime = time.time()
                # call post search and output preview results
                self.generateResults()
                self.output_preview(self._out)
                waittime = (time.time() - starttime) * self._wait_multiplier
        splunk.search.waitForJob(self._inpout_job, self._maxWaitTime)
        self.generateResults()



class ScriptResult(dict):
    """Represents Search Results.  For now just a dict"""

    def __getattr__(self, key):
        return self.get(key, None)

    def __setattr__(self, key, value):
        self[key] = value

####################################################################################################################################
########### SCRIPT SECURITY
####################################################################################################################################
def _unsafeCheck(code):
    for banned in ["open", "write", "read" ]: # for now "import"
        if banned in code: #overly strict right now. fix
            raise ScriptException("'%s' not allowed in script" % banned)

class PermissionRestricted(object):
    pass

_DANGEROUS = ['__builtins__.open', '__builtins__.file', '__builtins__.execfile']
# undefine some basic unsafe packages/functions
def _stow_away_dangerous():
    pr = PermissionRestricted()
    cache = {}

    for d in _DANGEROUS:
        try:
            exec("cache['%s']=%s" % (d, d))  # cache away dangerous function
            exec("%s=None" % d)              # null-out public pointer to function
        except Exception as e:
            logger.warn(e)
    return cache

# undefine some basic unsafe packages/functions
def _restore_danger(cache):
    for name in cache:
        exec("%s=cache['%s']" % (name, name)) # restore public pointer to function

def _fix_search(q):
    q = q.strip()
    if not q.startswith('|') and not q.startswith('search'):
        q = 'search ' + q
    return q

def _prettyID(obj):
    if isinstance(obj, object):
        return 'class=%s id=%s' % (obj.__class__.__name__, id(obj))
    return 'type="%s" id=%s' % (str(obj)[:100], id(obj))


def ANY(joblist):
    """
    Used to return the results from many jobs as they become available.
    example: "for result in ANY([x, y, z]): my_processing(result)"
    where x, y, z are ResultSets and ANY() just returns the results from x, y, and z as they come.
    @rtype: generator iterator
    @return: iterator over the results in the joblist.  First available, first served.
    """

    # initialize could of results (how we'll know if there are new results)
    currentCounts = [0] * len(joblist)
    # list of iterators for each job
    iterators = [job.__iter__ for job in joblist]

    # while there are more results
    while not _isDone(joblist):
        # for each job
        for i, job in enumerate(joblist):
            newCount = job.eventAvailableCount
            # if new results
            if newCount != currentCounts[i]:
                currentCounts[i] = newCount
                # yield next()
                yield next(iterators[i])
        # don't be an ahole
        time.sleep(0.1)

def _isDone(joblist):
    """
    @return: True, if any job in list isn't done.
    @rtype: bool
    """

    for job in joblist:
        if not job.isDone:
            return False
    return True



def test():
    """Runs a script, or if 'test' then runs all scripts in scripts subdirectory"""
    sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
    owner      = "admin"
    namespace  = "search"

    if len(sys.argv) == 2:
        args = sys.argv[1:]
        filename = args[0]
        if filename == 'test':
            import glob
            files = glob.glob('scripts/*ss')
        else:
            files = [filename]
        for f in files:
            print("FILE: " + f)
            script = Script(sessionKey, owner, namespace, path=f, prerunfix=True)
            results = script.run()
            print("results: " + str(results))
    else:
        print("Usage: <ss file>")




if __name__ == "__main__":
    test()
