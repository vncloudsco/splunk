#   Version 4.0
import sys, glob, tempfile, os
import string
import getpass
import time
import math

import splunk
import splunk.auth
import splunk.search
import splunk.util
import splunk.clilib.bundle_paths as bundle_paths

app = None
ssname_list = []
ssname_map = {}
owner = 'nobody'
et = None
lt = None
user = None
password = None
trigger = True
sleep = 5
maxjobs = 1
indexarg = None
dedup = False
reverseorder = False
sched_start_time = None
sched_end_time = None
timefield = 'search_now'
namefield = 'source'

dedupsearch = 'search splunk_server=local index=$index$ $namefield$="$name$" | stats count by $timefield$'
distdedupsearch = 'search index=$index$ $namefield$="$name$" | stats count by $timefield$'
showprogress = False

def printError(msg, code=1):
  print(msg)
  sys.exit(code)

def printUsage():
  print('''
  Description:
    This python script is designed to backfill summary indexes that are
    populated by saved searches by executing those saved searches as they
    would have been executed at their regularly scheduled times in a given
    time range.
    
    You can provide the application context to use and either a specify a list
    of saved searches from that app or choose to backfill all relevant (enabled,
    scheduled, has summary indexing action) saved searches in that app.

    You must also provide a timerange for the backfilling where the times can
    either by UTC epoch numbers or relative time specifiers (e.g. -3d@d for
    3 days ago at midnight).  The script will automatically compute the
    scheduled times that the specified saved searches would have been executed
    during the given time range.  If requested, this script can automatically
    examine the summary index to find existing data so that only scheduled
    times corresponding to missing data are executed.
    
    You must also provide the necessary authentication (i.e. splunk username
    and password). If the a valid splunk session key is known at invocation 
    time it can be passed in via -sk option.    

    Any required information not specified in the command line will be
    prompted for interactively.  This includes the saved search name(s),
    the authentication information, and the time range.


  Examples:

    splunk cmd python fill_summary_index.py -app splunkdotcom -name "*" -et -mon@mon -lt @mon -dedup true -auth admin:changeme

       Backfills all summary index saved searches for the previous month for
       the splunkdotcom app and skips any searches that already has data in
       the summary index

    splunk cmd python fill_summary_index.py -app search -name my_daily_search -et -y -lt now -j 8 -auth admin:changeme

       Executes the "my_daily_search" saved search from a year ago to now,
       running at most 8 searches at a time.  Does *not* skip searches that
       already have data in the summary index.

  
  Usage: splunk cmd python fill_summary_index.py [OPTIONS]
  
    ***Note: <boolean> options accept the values "1", "t", "true", or "yes" for true
                                            and "0", "f", "false", or "no" for false

    -et <string>            Earliest time (required).  Either a UTC time (integer since unix epoch) 
                                            or a Splunk search relative time string [1].

    -lt <string>            Latest time (required).  Either a UTC time (integer since unix epoch) 
                                            or a Splunk search relative time string [1].
    
    -app <string>           The application context to use (defaults to None)

    -name <string>          Specify a single saved search name.  Can specify
                            multiple times to provide multiple names.
                            "*" specifies all enabled, scheduled saved searches
                            that have a summary index action.

    -names <string>         Specify a comma seperated list of saved search names

    -namefile <file>        Specify a file with a list of saved search names,
                            one per line.  Anything after a # each line of the
                            file is a considered a comment and ignored.

    -owner <string>         The user context to use (defaults to None)

    -index <string>         The index that the saved search summary indexes to.
                            If not provided, will try to determine automatically.
                            If auto index detection fails, defaults to "summary".
                            
    -auth <string>          The authentication string expects either <username> or
                            <username>:<password>.  If only a username is provided,
                            the password will be requested interactively.
                            
    -sleep <float>          Number of seconds to sleep between each search
                            Default is 5 seconds
    
    -j <int>                Maximum number of concurrent searches to run
                            (default is 1)

    -sched_start_time <int> Time to start running the backfill searches.
                            Specified in military time (e.g. 1230 is 12:30pm).
                            By default, it starts immediately.

    -sched_end_time <int>   Time to stop and suspend the backfill searches.
                            Specified in military time (e.g. 1230 is 12:30pm).
                            By default, it does not pause the searches.

    -dedup <boolean>        If true, do not run a saved search for a scheduled
                            time if data already exists in the summary index
                            Default is false
                            
    -reverseorder <boolean> If true, backfill from most recent time period to
                            oldest timeperiod.
                            Default is false

    -showprogress <boolean> If true, will periodically show the done progress
                            for each currently running search that we spawn.
                            Default is false

    *** Advanced options: these should not need to be used in almost all cases
    
      -trigger <boolean>    If false, will run each search but will not trigger
                            the alert actions. (summary indexing action is always triggered).
                            Default is true.
                            
      -dedupsearch <string> The search to be used to determine if data
                            corresponding to a particular saved search at a
                            specific scheduled times is present

      -namefield <string>   The field in summary index data that contains the
                            name of the saved search that generated that data

      -timefield <string>   The field in summary index data that contains the
                            scheduled time of the saved search that generated
                            that data
    
  1 - For a full description of Splunk relative time strings, see:
      http://docs.splunk.com/Documentation/Splunk/latest/User/ChangeTheTimeRangeOfYourSearch#Syntax_for_relative_time_modifiers
  ''')
  sys.exit(0)
  
def getBoolArg(opt, val):
  try:
    return splunk.util.normalizeBoolean(val, enableStrictMode=True)
  except ValueError:
    printError("Invalid boolean value '%s' for %s option" % (val, opt))
    
def missingArgValue(opt):
  printError("Missing value for option '%s'" % opt)

def updateJobList(job_list, showprogress = False, trigger = True):
  newjobs = []
  for cj in job_list:
    try:
      if cj.isDone:
        if not trigger:
          print(" ... job '%s' finished (not triggering actions)" % cj.id)
        else:
          print(" ... job '%s' finished" % cj.id)
      else:
        newjobs.append(cj)
        if showprogress:
          print(" ... job '%s' progress: %.1f%%" % (cj.id, (cj.doneProgress * 100)))
    except:
      print(" ... job '%s' FAILED: %s" % (cj.id, sys.exc_info()[0]))
  return newjobs

# process all command line arguments first
if (len(sys.argv) == 2 and (sys.argv[1] == '-h' or sys.argv[1] == '-help' or sys.argv[1] == 'help')):
  printUsage()

sk = None
i  = 1
while i<len(sys.argv):
  # arguments should be (<option> <value>)+
  opt = sys.argv[i]
  if (i + 1 >= len(sys.argv)):
    missingArgValue(opt)
  val = sys.argv[i+1]
  i = i + 2
  
  if (opt == '-app'):
    app = val
  elif (opt == '-name'):
    ssname_list.append(val)
  elif (opt == '-names'):
    ssname_list.extend(val.split(','))
  elif (opt == '-namefile'):
    # read list of names from a plain txt file
    with open(val) as f:
      for line in f:
        line = (line.split('#',1))[0].strip() # assume everything after # is a comment
        if len(line) > 0:
          ssname_list.append(line)
  elif (opt == '-owner'):
    owner = val
  elif (opt == '-et'):
    et = val
  elif (opt == '-lt'):
    lt = val
  elif (opt == '-index'): # the index that this schedule search writes to
    indexarg = val
  elif (opt == '-sk'):
    sk = val
  elif (opt == '-auth'):
    tmp = val.split(':',1)
    if len(tmp) < 2:
      printError("Invalid '-auth' value")
    user=tmp[0]
    password=tmp[1]
  elif (opt == '-trigger'):
    trigger = getBoolArg(opt, val)
  elif (opt == '-sleep'):
    sleep = float(val)
  elif (opt == '-dedup'):
    dedup = getBoolArg(opt, val)
  elif (opt == '-reverseorder'):
    reverseorder = getBoolArg(opt, val)
  elif (opt == '-sched_start_time'):
    sched_start_time = int(val)
    if int(sched_start_time/100) > 23:
      printError("\nhours > 23. Use military time format for sched_start_time.")
    if int(sched_start_time%100) > 60:
      printError("\nminutes > 60. Use military time format for sched_start_time.")
  elif (opt == '-sched_end_time'):
    sched_end_time = int(val)
    if int(sched_end_time/100) > 23:
      printError("\nhours > 23. Use military time format for sched_end_time.")
    if int(sched_end_time%100) > 60:
      printError("\nminutes > 60. Use military time format for sched_end_time.")
  elif (opt == '-showprogress'):
    showprogress = getBoolArg(opt, val)
  elif (opt == '-dedupsearch'):
    dedupsearch = val
  elif (opt == '-namefield'):
    namefield = val
  elif (opt == '-timefield'):
    timefield = val
  elif (opt == '-nolocal'):
    dedupsearch = distdedupsearch
  elif (opt == '-j'):
    try:
      maxjobs = int(val)
    except ValueError:
      printError("Invalid value '%s' for -j option.  Integer between 1 and 16 required." % val)
    if (maxjobs < 1 or maxjobs > 16):
      printError("Maximum number of parallel jobs (-j) must be >=1 and <=16")

  else:
    printError("Invalid option '%s'" % opt)

if sys.version_info >= (3, 0):
    get_input = input
else:
    get_input = raw_input

if app is None:
    app = get_input('Please enter the app that contains the search(es): ')

app_dir = bundle_paths.make_bundle_install_path(app)
if not os.path.exists(app_dir):
    printError("Cannot locate directory for app, %s does not exist." % app_dir)

# simple way to make sure only one backfilling summary index is working on this app 
# NOTE: there is a (short)  race condition here, between glob and temp file creation
logs_dir = os.path.join(app_dir, "log")
if not os.path.exists(logs_dir):
   os.mkdir(logs_dir)

if len(glob.glob(os.path.join(logs_dir, "fsidx*lock"))) > 0:
    printError("An instance of fill_summary_index is already running for app=%s" % app)

tmp_file =  tempfile.NamedTemporaryFile(prefix="fsidx", suffix=".lock", dir=logs_dir) 

# some values are required
if len(ssname_list) == 0:
  while True:
    n = get_input("Please enter the name of saved search #%d (empty value to stop entering): " % (len(ssname_list)+1))
    if len(n) == 0:
      break
    ssname_list.append(n)
    
if sk is None and  user is None:
  user = get_input('Please enter your splunk username: ')
if sk is None and password is None:
  password = getpass.getpass('Please enter your splunk password: ')
if et is None:
  et = get_input('Please enter the earliest time (UTC or relative): ')
if lt is None:
  lt = get_input('Please enter the latest time (UTC or relative): ')

# get the splunk session key

if sk is None:
   try:
      sk = splunk.auth.getSessionKey(user, password)
   except splunk.AuthenticationFailed:
      printError("Invalid username/password")

# if our list includes '*', get all searches that have a schedule and action contains 'summary_index'
if '*' in ssname_list:
  print("\nGetting list of all saved searches for selected app=%s and owner=%s" % (app,owner))
  # count=-1 means please return all, not the first 30
  ss = splunk.search.listSavedSearches(namespace=app, sessionKey=sk, owner=owner, count=-1)
  print(" ... found %s saved searches" % len(ss))
  added = 0
  for name in ss:
    if 'disabled' in ss[name] and ss[name]['disabled'] == '0':
      if 'is_scheduled' in ss[name] and ss[name]['is_scheduled'] == '1':
        if 'actions' in ss[name] and ss[name]['actions'] is not None and ss[name]['actions'].find('summary_index') >= 0:
          added = added + 1
          ssname_list.append(name)
  print(" ... of those, %s will be added to list (those that are enabled, scheduled, and has summary_index action)" % added)

# first get list of all searches and all the times they have to be executed for
st_list = []
donemap = {}    
for ssname in ssname_list:
    if ssname == '*':
      continue

    if ssname in donemap:
      print("\n!!! Warning: saved search specific multiple times: '%s'" % ssname)
      continue

    donemap[ssname] = 1
    
    print("\n*** For saved search '%s' ***" % ssname)
    cur_st_list = []
    index = indexarg
    try:
      ent = splunk.search.getSavedSearchWithTimes(ssname, et, lt, namespace=app, sessionKey=sk, owner=owner)
      if 'scheduled_times' in ent:
        for st in ent['scheduled_times']:
          cur_st_list.append((ssname, st))
      if index is None and 'action.summary_index._name' in ent:
        index = ent['action.summary_index._name']
    except splunk.RESTException as e:
      print("Failed to get list of scheduled times for saved search '%s' (app = '%s', error = '%s' " % (ssname, app, str(e)))
      continue

    if len(cur_st_list) < 1:
      print("No scheduled times for your time range.")
      continue

    if index is None:
      index = 'summary' # set to default as last resort

    if dedup:
      # try to find for what scheduled times the summary index has already been populated so we only fill in gaps
      # do this by dispatching a job

      # first replace placeholders in the dedupsearch
      cdsearch = dedupsearch.replace("$namefield$", namefield)
      cdsearch = cdsearch.replace("$timefield$", timefield)  
      cdsearch = cdsearch.replace("$index$", index)
      cdsearch = cdsearch.replace("$name$", ssname)
      cdsearch = cdsearch.replace("$et$", et)
      cdsearch = cdsearch.replace("$lt$", lt)

      print("Executing search to find existing data: '%s'" % cdsearch)
      # note: we can't limit search by et and lt because et and lt are just the bounds of the scheduled times,
      # not the bounds for the indexed time of the events that those searches would produce
      try:
        cdjob = splunk.search.dispatch(cdsearch, sessionKey=sk, namespace=app, owner=owner)
      except splunk.SearchException as msg:
        printError(msg) # fatal error, just exits

      sys.stdout.write("  waiting for job sid = '%s' " % cdjob.id)
      sys.stdout.flush()
      while not cdjob.isDone:
        time.sleep(sleep)
        if showprogress:
          sys.stdout.write(" ... %.lf%%" % (cdjob.doneProgress * 100))
          sys.stdout.flush()
      print(" ... finished")
      existmap = {}
      for r in cdjob.results:
        if timefield in r:
          existmap[str(math.trunc(float(str(r[timefield]))))] = 1
      
      new_list = []
      for (ssname,st) in cur_st_list:
        if str(math.trunc(float(st))) not in existmap:
          new_list.append((ssname,st))
      if (len(new_list) < len(cur_st_list)):
        print("Out of %d scheduled times, %d will be skipped because they already exist." % (len(cur_st_list), (len(cur_st_list) - len(new_list))))
        cur_st_list = new_list
      else:
        print("All scheduled times will be executed.")
    
    st_list.extend(cur_st_list) # add to overall list of jobs to do

if reverseorder:
  st_list.reverse()

if trigger:
  triggerStr = '1'
else:
  triggerStr = '0'

if len(st_list) == 0:
  printError("\nNo searches to run", code=0)

print("\n*** Spawning a total of %d searches (max %d concurrent) ***" % (len(st_list),maxjobs))

if (maxjobs == 1):
  for (ssname,st) in st_list:
    # calculate sleep time if schedule start and/or end times are specified: 
    if sched_start_time is not None: 
      timenow=time.localtime()
      timenow_min=(int(time.strftime("%H", timenow))*60)+int(time.strftime("%M", timenow))
      sched_start_min = 60*int(sched_start_time/100)+int(sched_start_time%100)
      sleepsecs = 0
      if sched_end_time is not None:
        sched_end_min = 60*int(sched_end_time/100)+int(sched_end_time%100)
      else:  
        sched_end_min = sched_end_time
  
      if (sched_start_min > timenow_min):
        if ((sched_end_min > sched_start_min) or ((sched_end_min < sched_start_min) and (timenow_min > sched_end_min)) or (sched_end_min is none)):
          sleepsecs=60*(sched_start_min-timenow_min)
      elif (sched_start_min < timenow_min):
        if (sched_end_min > sched_start_min):
          sleepsecs=60*((24*60)-timenow_min+sched_start_min)
      time.sleep(sleepsecs)
  
    print("\nExecuting %s for UTC = %s (%s)" % (ssname, st, time.ctime(int(st))))
    job = splunk.search.dispatchSavedSearch(ssname, sessionKey=sk, namespace=app,
                                            owner=owner, triggerActions=triggerStr, now=st)
  
    print("  waiting for job sid = '%s' " % job.id)
    sys.stdout.write(" ")
    while not job.isDone:
      time.sleep(sleep)
      if showprogress:
        sys.stdout.write(" ... %.1f%%" % (job.doneProgress * 100))
        sys.stdout.flush()
    if not trigger:  
      print(" ... Finished (not triggering actions)")
    else:
      print(" ... Finished")
else:
  # handle doing parallel jobs
  curjobs = [] # list of currently executing jobs
  for (ssname,st) in st_list:
   
    # calculate sleep time if schedule start and/or end times are specified: 
    if sched_start_time is not None: 
      timenow=time.localtime()
      timenow_min=(int(time.strftime("%H", timenow))*60)+int(time.strftime("%M", timenow))
      sched_start_min = 60*int(sched_start_time/100)+int(sched_start_time%100)
      sleepsecs = 0
      if sched_end_time is not None:
        sched_end_min = 60*int(sched_end_time/100)+int(sched_end_time%100)
      else:  
        sched_end_min = sched_end_time

      if (sched_start_min > timenow_min):
        if ((sched_end_min > sched_start_min) or ((sched_end_min < sched_start_min) and (timenow_min > sched_end_min)) or (sched_end_min is none)):
          sleepsecs=60*(sched_start_min-timenow_min)
      elif (sched_start_min < timenow_min):
        if (sched_end_min > sched_start_min):
          sleepsecs=60*((24*60)-timenow_min+sched_start_min)
      time.sleep(sleepsecs)

    while (len(curjobs) >= maxjobs):
      time.sleep(sleep)
      curjobs = updateJobList(curjobs, showprogress=showprogress, trigger=trigger)

    # now we can spawn a new job
    job = splunk.search.dispatchSavedSearch(ssname, sessionKey=sk, namespace=app,
                                            owner=owner, triggerActions=triggerStr, now=st)
    curjobs.append(job)
    print("Started job '%s' for saved search '%s', UTC = %s (%s)" % (job.id, ssname, st, time.ctime(int(st))))

  # still have jobs not done?
  while (len(curjobs) > 0):
    time.sleep(sleep)
    curjobs = updateJobList(curjobs, showprogress=showprogress, trigger=trigger)
