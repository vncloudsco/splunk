# coding=UTF-8
from __future__ import division

from builtins import map
from builtins import object
from builtins import range

import sys

import lxml.etree as et
import logging
import time, datetime, copy, decimal

import splunk
import splunk.auth as auth
import splunk.rest as rest
import splunk.util as util
import splunk.rest.format
import splunk.entity as entity
import json

logger = logging.getLogger('splunk.search')

# define the block size of events to fetch per request
ITER_BUFFER_SIZE = 100

# define the number of times to retry the event fetching if the returned event
# count is less than expected count; retry interval is in seconds
FETCH_RETRY_COUNT = 10
FETCH_RETRY_INTERVAL = .5

# define parameters around retry requesting search job data if splunkd reports
# that it's not ready yet (HTTP 204); all times are in seconds
STATUS_FETCH_TIMEOUT = 300
STATUS_FETCH_MIN_INTERVAL = .05
STATUS_FETCH_MAX_INTERVAL = 1
STATUS_FETCH_EASING_DURATION = 5

# define number of tries to obtain the 'dispatchState' job value; needed to
# support older APIs that do not output this key
MAX_DISPATCH_STATE_RETRY_COUNT = 2

# define standard namespace map for use with etree
NS_MAP = {
    'atom': splunk.rest.format.ATOM_NS,
    'splunk': splunk.rest.format.SPLUNK_NS
}

# define list of field names returned by summary that should be cast as
# numeric, for use with the SummaryContainer object
KNOWN_NUMERIC_FIELD_ATTR = ['min', 'max', 'mean', 'stdev']

# define the dispatch() args that map to the REST endpoint params
DISPATCH_ARG_MAP = {
    'callerData':'caller_data',
    'earliestTime': 'earliest_time',
    'enableEventTypes': 'enable_eventtypes',
    'label':'label',
    'latestTime': 'latest_time',
    'maxEvents': 'max_count',
    'remoteServerList': 'remote_server_list',
    'statusBucketCount': 'status_buckets',
    'timeFormat': 'time_format',
    'ttl': 'timeout'
}

# define argument used in retrieving events and results from SearchJob
RESULT_ARG_MAP = {
    'callerData':'caller_data',
    'count': 'count',
    'earliestTime': 'earliest_time',
    'fieldList': 'field_list',
    'latestTime': 'latest_time',
    'maxLines': 'max_lines',
    'offset': 'offset',
    'outputMode': 'output_mode',
    'search': 'search',
    'segmentationMode': 'segmentation',
    'timeFormat': 'time_format',
    'truncationMode': 'truncation_mode',
    'showEmptyFields': 'show_empty_fields'
}

# define default set of parameters when requesting events/results
DEFAULT_RESULT_ARG_MAP = {
    'earliestTime': None,
    'latestTime': None,
    'fieldList': [],
    'maxLines': 100,
    'timeFormat': util.ISO_8601_STRFTIME,
    'outputMode': 'json',
    'showEmptyFields': True
}

# define job dispatch state; job state will transition in a forward direction
# only; once DONE is reached, no other changes will occur; job will never
# transition from DONE to FAILED
DISPATCH_STATE_MAP = {
    'QUEUED': 1,
    'PARSING': 2,
    'RUNNING': 3,
    'FINALIZING': 4,
    'DONE': 5,
    'FAILED': 99
}

# define the mimimum state from which the SDK can reliably operate
PASSABLE_DISPATCH_ENUM = DISPATCH_STATE_MAP['RUNNING']

# define list of job properties that can change over life of search
DYNAMIC_JOB_PROPERTIES = [
    'chunkEarliestTime',
    'chunkLatestTime',
    'cursorTime',
    'dispatchState',
    'doneProgress',
    'eventAvailableCount',
    'eventCount',
    'isDone',
    'isFailed',
    'isFinalized',
    'isPaused',
    'isSaved',
    'isZombie',
    'messages',
    'priority',
    'resultCount',
    'resultPreviewCount',
    'runDuration',
    'scanCount',
    'ttl'
]

# list of job properties that can change even after a job is morked isDone
ALWAYS_DYNAMIC_JOB_PROPERTIES = [
    'isSaved',
    'ttl'
]

# define list of job properties to be cast to boolean
BOOLEAN_JOB_PROPERTIES = [
    'eventIsStreaming',
    'eventIsTruncated',
    'isDone',
    'isFailed',
    'isFinalized',
    'isPaused',
    'isPreviewEnabled',
    'isBatchModeSearch',
    'isRealTimeSearch',
    'isRemoteTimeline',
    'isSaved',
    'isSavedSearch',
    'isZombie',
    'resultIsStreaming'

]

# define list of job properties to be cast to int
INTEGER_JOB_PROPERTIES = [
    'eventAvailableCount',
    'eventCount',
    'eventFieldCount',
    'priority',
    'resultCount',
    'resultPreviewCount',
    'scanCount',
    'statusBuckets',
    'ttl'
]

# define list of job properties to be cast to float
FLOAT_JOB_PROPERTIES = [
    'runDuration',
    'doneProgress'
]

# Used to normalize values of a job's ttl that may indicate it's expired
JOB_TTL_EXPIRED_VALUES = [
    '-1',
    -1,
    'expired',
    '0'
]

JOBS_ENDPOINT_ENTITY_PATH = 'search/jobs'


# /////////////////////////////////////////////////////////////////////////////
#  SearchJob factory methods
# /////////////////////////////////////////////////////////////////////////////

def dispatch(search, hostPath=None, sessionKey=None, namespace=None, owner=None, waitForRunning=True, **kwargs):
    '''
    Initiates a search job against a splunk server, and returns a SearchJob
    object.

    dispatch() can take time arguments in the following formats:

        string: an arbitrary time format, that must be accompanied by a
            time_format parameter

        time.struct_time: a native python time structure, in local time

        int/float: a unix epoch timestamp

        NOTE: dispatch will return a TypeError if you mix time formats between
            earliest_time and latest_time.

    dispatch() recognizes the following options (options not on this list will
        be passed, but will trigger an INFO log message):

        label=None,
        hostPath=None,
        earliestTime=None,
        latestTime=None,
        savedSearch=None,
        timeFormat=None,
        statusBucketCount=None,
        enableEventTypes=False,
        maxEvents=None,
        ttl=None,
        remoteServerList=[],
        sessionKey=None
    '''

    if not sessionKey and 'sessionKey' in kwargs: sessionKey = kwargs['sessionKey']

    if not hostPath and 'hostPath' in kwargs: hostPath = kwargs['hostPath']

    if not namespace and 'namespace' in kwargs: namespace = kwargs['namespace']

    if not owner and 'owner' in kwargs: owner = kwargs['owner']

    # assemble params
    uri = entity.buildEndpoint('search', 'jobs', namespace, owner)

    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri

    args = {
        'search': search.strip()
    }

    # convert the python keyword arg names to known HTTP param names
    for key in kwargs:
        if key in DISPATCH_ARG_MAP:
            args[DISPATCH_ARG_MAP[key]] = kwargs[key]
        else:
            args[key] = kwargs[key]


    # auto flatten lists
    for key in args:
        if isinstance(args[key], list):
            args[key] = util.fieldListToString(args[key])

    # check the time terms and do convenience casting
    hasUnixTime = False
    if 'time_format' not in args:
        for param in ['earliest_time', 'latest_time']:
            if param in args:
                if isinstance(args[param], float) or isinstance(args[param], int):
                    hasUnixTime = True
                    args['time_format'] = '%s'
                elif isinstance(args[param], time.struct_time):
                    args['time_format'] = util.ISO_8601_STRFTIME
                    args[param] = util.getISOTime(args[param])

        # if one of the args is unixtime, then both must be; otherwise time_format breaks
        if (args.get('earliest_time') != None and args.get('latest_time') != None) \
            and (not isinstance(args['earliest_time'], type(args['latest_time']))):
            raise TypeError('Time arguments are mismatched.  "earliest_time" and "latest_time" must be of the same type.')

    serverResponse, serverContent = rest.simpleRequest(uri, postargs=args, sessionKey=sessionKey, rawResult=True)

    rootXml = None
    rootJson = None
    try:
        if serverContent.startswith(b'<?xml'):
            rootXml = et.fromstring(serverContent)
        else:
            rootJson = json.loads(serverContent)
    except Exception as e:
        logger.error("Unable to parse server response. Exception: %s" % e)
        raise splunk.SearchException('Unable to parse server response')

    # catch quota overage; TODO: do something nicer
    if serverResponse.status == 503:
        if rootXml is not None:
            extractedMessages = rest.extractMessages(rootXml)
        else:
            extractedMessages = rest.extractJsonMessages(rootJson)

        for msg in extractedMessages:
            raise splunk.QuotaExceededException(msg['text'])

    # normal messages from splunkd are propogated via SplunkdException;
    if 400 <= serverResponse.status < 600:
        if rootXml is not None:
            extractedMessages = rest.extractMessages(rootXml)
        else:
            extractedMessages = rest.extractJsonMessages(rootJson)

        #SPL-53234 if extractedMessages is empty the msg['text'] throws an exception
        if extractedMessages is not None:
            for msg in extractedMessages:
                raise splunk.SearchException(msg['text'])
        else:
            raise splunk.SearchException('Failed to get response msg from server')

    if rootXml is not None:
        # get the search ID
        sid = rootXml.findtext('sid').strip()
    else:
        sid = rootJson['sid']

    # instantiate result object
    result = SearchJob(sid, hostPath, sessionKey, namespace, owner, dispatchArgs=args, waitForRunning=waitForRunning)

    return result

def listJobs(hostPath=None, sessionKey=None, normalizeValues=False, ignoreExpired=False, namespace=None, owner=None, **kw):
    '''
    Returns a list of search jobs present on the server
    '''
    uri = entity.buildEndpoint(JOBS_ENDPOINT_ENTITY_PATH, '', namespace, owner)

    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri
    serverResponse, serverContent = rest.simpleRequest(uri, sessionKey, getargs=kw)
    atomFeed = splunk.rest.format.parseFeedDocument(serverContent)

    def entryMapper(entry):

        # get available properties from the api
        prim = entry.toPrimitive()

        if ignoreExpired and not util.normalizeBoolean(prim['isSaved']) and prim['ttl'] in JOB_TTL_EXPIRED_VALUES:
            return None

        prim['search'] = entry.title
        prim['createTime'] = entry.published.isoformat()
        prim['modifiedTime'] = entry.updated.isoformat()
        prim['user'] = entry.author

        # scaffold the expected values for float and int properties; the API
        # sometimes is lazy about setting them
        for k in FLOAT_JOB_PROPERTIES: prim.setdefault(k, 0.0)
        for k in INTEGER_JOB_PROPERTIES: prim.setdefault(k, 0)

        # This does not normalize the new request parameter in jobs.
        if normalizeValues:
            for k, v in prim.items():
                prim[k] = normalizeJobPropertyValue(k, v)
        return prim

    return [job for job in map(entryMapper, atomFeed) if not job == None]


def getJob(sid, hostPath=None, sessionKey=None, message_level=None, status_fetch_timeout=STATUS_FETCH_TIMEOUT, waitForRunning=True):
    '''Returns a SearchJob object for a specific job.'''
    return SearchJob(sid, hostPath, sessionKey, message_level=message_level, status_fetch_timeout=status_fetch_timeout, waitForRunning=waitForRunning)



# /////////////////////////////////////////////////////////////////////////////
#  search convenience methods
# /////////////////////////////////////////////////////////////////////////////

def searchAll(search, **kwargs):
    '''
    Returns all results for a search. CAUTION: output can be the entire
    dataset.  Synchronous.  Not compatible with real-time search.
    '''

    searchjob = dispatch(search, **kwargs)
    waitForJob(searchjob)
    output = list(searchjob)
    searchjob.cancel()
    return output


def searchOne(search, **kwargs):
    '''
    Returns the first item from the search, or none if empty results.  Synchronous.
    Not compatible with real-time search.
    '''

    searchjob = dispatch(search, **kwargs)
    waitForJob(searchjob)
    for item in searchjob:
        searchjob.cancel()
        return item


def searchCount(search, **kwargs):
    '''
    Returns the number of events that match a search.  Synchronous.
    Not compatible with real-time search.
    '''

    searchjob = dispatch(search, **kwargs)
    waitForJob(searchjob)
    output = searchjob.count
    searchjob.cancel()
    return output


def waitForJob(searchjob, maxtime=-1):
    """
    Wait up to maxtime seconds for searchjob to finish.  If maxtime is
    negative (default), waits forever.  Returns true, if job finished.
    All real-time searches will return immediately.
    """

    pause = 0.2
    lapsed = 0.0
    while not searchjob.isDone:
        if searchjob.isRealTimeSearch:
            break
        time.sleep(pause)
        lapsed += pause
        if maxtime >= 0 and lapsed > maxtime:
            break
    return searchjob.isDone


# /////////////////////////////////////////////////////////////////////////////
#  Search objects
# /////////////////////////////////////////////////////////////////////////////

class SearchJob(object):
    '''
    Represents a dispatched search job that currently exists on the splunkd
    server.

    Usage:

        key = splunk.auth.getSessionKey('admin', 'changeme')

        # start the search
        job = dispatch('search *', sessionKey=key)

        # iterate over the raw events; stop at 10
        for idx, event in enumerate(job.events):
            print(event)
            if idx > 10: break

        # do direct selection of events 2 to 3:
        print(job.events[2:3])

        # check the job status
        if job.isDone: print("The search job=%s is finished" % job.id)

        # get the raw XML output for first 5 events
        print(job.getFeed(mode='events', count=5))

        # clean up
        job.cancel()

    '''

    # define all the sub-endpoints that are expected to be listed in the
    # Atom entry <link> section

    # defines the data endpoints, i.e. /search/jobs/1234/events
    ASSET_LINKS = ['events', 'results', 'summary', 'timeline']

    # defines the meta endpoints, i.e. /search/jobs/control
    META_LINKS = ['alternate', 'control']


    def __init__(self, searchId, hostPath, sessionKey=None, namespace=None, owner=None, message_level=None, dispatchArgs={}, status_fetch_timeout=STATUS_FETCH_TIMEOUT, waitForRunning=True):

        # init container for the fetch operation options
        # set defaults here
        self.dispatchArgs = dispatchArgs
        self.clearFetchOptions()

        # write once
        self.id = searchId
        self.username = None
        self.createTime = None
        self.modifiedTime = None
        self.hostPath = splunk.mergeHostPath(hostPath)
        self.serverList = []
        self.sessionKey = sessionKey
        self.isStreaming = False
        self.keywords = []
        self.links = {}
        self.namespace = namespace
        self.owner = owner
        self.message_level = message_level
        self.messages = {}
        self._propertyPrimitives = None
        self.resourceLinks = []
        self.waitForRunning = waitForRunning

        # scaffold job properties that we expect to be there from the start
        # of the job; sometimes the job endpoint is lazy
        self._cachedProps = {
            'doneProgress': 0,
            'eventCount': 0,
            'resultCount': 0,
            'scanCount': 0,
            'isFinalized': False,
            'isDone': False,
            'cursorTime': None,
            'search': None,
            'runDuration': 0
        }

        # init the results containers
        self.events = ResultSet(self, 'events')
        self.results = ResultSet(self, 'results')
        self.results_preview = ResultSet(self, 'results_preview')
        self._status_fetch_timeout = status_fetch_timeout

        self._getStatus(True)



    # ------------------------------------------------------------------------
    # properties
    #
    # the explicitly called out props here are only for those that change
    # during the lifetime of a dispatched job.  static props are fetched once
    # at getStatus() time
    # ------------------------------------------------------------------------

    def _getLogicalCount(self, getUpdate=True):

        if getUpdate:
            if self.eventIsStreaming: return self.eventCount
            else: return self.resultCount
        else:
            if self.eventIsStreaming: return self._cachedProps['eventCount']
            else: return self._cachedProps['resultCount']


    def __len__(self):
        return self._getLogicalCount()

    def __getattr__(self, key):

        if key == 'search':
            return self._cachedProps[key]

        elif key == 'count':
            return self._getLogicalCount()

        elif key in ALWAYS_DYNAMIC_JOB_PROPERTIES:
            self._getStatus(force=True)
            return self._cachedProps[key]

        elif key not in DYNAMIC_JOB_PROPERTIES:
            # return None instead of AttributeError for the case when attribute isnt provided by splunkd
            if key == 'latestTime' or key == 'earliestTime': return None
            raise AttributeError(key)

        self._getStatus()
        return self._cachedProps[key]

    def __bool__(self):
        '''
        The Boolean test for this object is strictly for cases when you want
        to test for the successful construction of the job, i.e.:

            job = dispatch('search foo')
            if not job:
                print('unable to dispatch job')
        '''
        return (self.id != None)

    #
    # define getters for timeline and summary; these are loaded on demand
    #
    def _getTimelineProperty(self):
        self._getStatus()
        self.pushValidation()
        if ('_timeline' not in self.__dict__) or (not self._cachedProps['isDone']):
            self._getTimeline()
        return self._timeline

    def _getSummaryProperty(self):
        self._getStatus()
        self.pushValidation()
        if ('_summary' not in self.__dict__) or (not self._cachedProps['isDone']):
            self._getSummary()
        return self._summary

    timeline    = property(_getTimelineProperty)
    summary     = property(_getSummaryProperty)


    def __repr__(self):
        return '<splunk.search.SearchJob: id=%s search="%s" isDone=%s>' % \
            (self.id, self._cachedProps['search'], self._cachedProps['isDone'])

    def __getitem__(self, index):
        if self.isStreaming:
            return self.events.__getitem__(index)
        else:
            return self.results.__getitem__(index)

    def __contains__(self, index):
        if self.isStreaming:
            return self.events.__contains__(index)
        else:
            return self.results.__contains__(index)

    def __iter__(self):
        mode = self.getAutoAssetType()
        return getattr(self, mode).__iter__()

    def __str__(self):
        self.refresh()
        output = []
        data = self.toJsonable()
        for k in sorted(data):
            output.append('%s %s' % (k.ljust(20), data[k]))
        return '\n'.join(output)

    # ------------------------------------------------------------------------
    #  state control
    # ------------------------------------------------------------------------

    def isExpired(self):
        '''Returns a boolean about whether the job is truly expired or not.'''
        if self.ttl in JOB_TTL_EXPIRED_VALUES and not self.isSaved:
            return True
        return False


    def pushValidation(self):
        '''
        Raises an exception if the current job has fatal errors and must not
        be processed any further.
        '''

        fatality = None

        if self._cachedProps['isFailed']:
            fatality = 'Cannot access search data; job %s has been marked as failed' % self.id
        elif self._cachedProps['isZombie']:
            fatality = 'Cannot access search data; job %s is a zombie and is no longer with us' % self.id
        else:
            return

        fatality = self.messages.get('fatal', [fatality])[0]
        raise splunk.SearchException(fatality)


    def getAutoAssetType(self):
        '''
        Determines the most likely search job asset type to use based on the
        known properties of the job.  Chooses between one of the following:
        -- events
        -- results
        -- results_preview
        '''

        # if job is done, only the results matter
        if self.isDone:
            return 'results'

        # otherwise, try to select the most appropriate asset type
        if self.isRealTimeSearch:
            return 'results_preview'

        if self.reportSearch:
            return 'results'

        return 'events'


    # ------------------------------------------------------------------------
    #  job control
    # ------------------------------------------------------------------------

    def refresh(self):
        '''
        Refreshes the current job status properties
        '''

        self._getStatus()


    def _execControl(self, action, kwargs=None):
        '''
        Executes a control action on the job
        '''

        logger.debug('Executing action=%s on job id=%s' % (action, self.id))

        try:
            uri = self.links['control']
        except KeyError:
            raise AssertionError('Splunkd did not provide URI to job control endpoint')

        if self.hostPath:
            uri = self.hostPath + uri

        postargs = {'action': action}
        if kwargs:
            postargs.update(kwargs)

        serverResponse, serverContent = rest.simpleRequest(uri, postargs=postargs, sessionKey=self.sessionKey)

        if serverResponse.status != 200:
            logger.warn('job control request for action=%s id=%s return statusCode=%s' % \
                (action, self.id, serverResponse.status))
            rest.extractMessages(et.fromstring(serverContent))
            return False

        return True


    def cancel(self):
        '''Cancels the search and deletes if from the system'''
        return self._execControl('cancel')

    def pause(self):
        '''Pauses the search'''
        return self._execControl('pause')

    def unpause(self):
        '''Unpauses the search'''
        return self._execControl('unpause')

    def enablepreview(self):
        '''Enables previews of the search'''
        return self._execControl('enablepreview')

    def disablepreview(self):
        '''Disables previews of search'''
        return self._execControl('disablepreview')

    def finalize(self):
        '''Finalizes the search'''
        return self._execControl('finalize')

    def touch(self):
        '''Touches the job to reset the TTL'''
        return self._execControl('touch')

    def save(self):
        '''Saves the job so that it will not be removed from the system'''
        return self._execControl('save')

    def unsave(self):
        '''undoes a previous 'save' action. The job will now be removed from the system when its TTL expires'''
        return self._execControl('unsave')


    def setTTL(self, TTL):
        '''Changes the TTL value for the job (in seconds). The resulting live TTL
        is always calculated from the last touch timestamp.  To reset the TTL
        to its full value, call SearchJob.touch() afterwards.'''

        try:
            int(TTL)
        except:
            raise ValueError('TTL must be an integer, representing seconds')

        if TTL == 0:
            logger.info('SearchJob.cancel() should be used instead of SearchJob.setTTL(0)')

        if TTL < 0:
            raise ValueError('TTL must be a positive integer')

        return self._execControl('setttl', {'ttl': TTL})


    def setpriority(self, priority):
        '''Changes the OS-level priority for the job. Valid values are 0-10.
        NOTE: certain OSes will prohibit the increase of priority.'''

        try:
            int(priority)
        except:
            raise ValueError('priority must be an integer from 0-10')

        if priority < 0 or priority > 10:
            raise ValueError('priority must be an integer from 0-10')

        return self._execControl('setpriority', {'priority': priority})


    # ------------------------------------------------------------------------
    #  data access methods
    # ------------------------------------------------------------------------

    def _getStatus(self, isInitial=False, force=False):
        '''
        Makes status request to server and updates local properties
        '''

        if self._cachedProps['isDone'] and not force: return True

        if not self.id:
            raise Exception("No job id passed")

        uri = entity.buildEndpoint(JOBS_ENDPOINT_ENTITY_PATH, self.id)
        if self.hostPath:
            uri = self.hostPath + uri

        args = {}
        if self.message_level is not None:
            args['message_level'] = self.message_level

        # a HTTP 204 means that splunkd isn't quite ready yet; retry for a bit
        loopStartTime = time.time()
        stateRetryCount = 0
        firstTime = True
        while firstTime or ((time.time() - loopStartTime) < self._status_fetch_timeout):
            serverResponse, serverContent = rest.simpleRequest(uri, getargs=args, sessionKey=self.sessionKey, raiseAllErrors=True)
            firstTime = False

            # determine polling interval easing
            elapsedTime = time.time() - loopStartTime
            nextRetry = getRetryInterval(
                elapsedTime,
                STATUS_FETCH_MIN_INTERVAL,
                STATUS_FETCH_MAX_INTERVAL,
                STATUS_FETCH_EASING_DURATION
            )
            logger.debug('getStatus - elapsed=%s nextRetry=%s' % (elapsedTime, nextRetry))

            # splunkd has no info yet
            if serverResponse.status == 204:

                if elapsedTime < self._status_fetch_timeout:
                    time.sleep(nextRetry)
                    continue
                else:
                    raise splunk.SplunkdException('Timed out waiting for status to become available on job=%s' % self.id)

            # job is created and can be polled
            elif serverResponse.status == 200:

                root = et.fromstring(serverContent)

                # check that the dispatch state is sufficient
                dispatchState = root.findtext('{%(atom)s}content/{%(splunk)s}dict/{%(splunk)s}key[@name="dispatchState"]' % NS_MAP)

                if dispatchState == None:
                    if stateRetryCount >= MAX_DISPATCH_STATE_RETRY_COUNT:
                        logger.warn('did not find job dispatch state in %s tries; assuming older API and bypassing check' % MAX_DISPATCH_STATE_RETRY_COUNT)
                        break
                    logger.debug('did not find job dispatch state key; retrying')
                    stateRetryCount += 1
                    time.sleep(nextRetry)
                    continue

                dispatchEnum = DISPATCH_STATE_MAP.get(dispatchState.upper())
                if dispatchEnum == None:
                    logger.warn('received unknown job dispatch state value (%s); retrying' % dispatchState)
                    time.sleep(nextRetry)
                    continue

                if self.waitForRunning and dispatchEnum < PASSABLE_DISPATCH_ENUM:
                    logger.debug('job dispatch state not sufficient (%s); retrying' % dispatchState)
                    time.sleep(nextRetry)
                    continue

                # everything is OK
                break


            else:
                raise splunk.SplunkdException('_getStatus - unexpected response while getting job status; status=%s content=%s'\
                        % (serverResponse.status, serverContent))

        else:
            raise splunk.SplunkdException('Timed out waiting for status to become available on job=%s' % self.id)



        # iterate over every key returned in the job property data
        keyNodes = root.findall('{%(atom)s}content/{%(splunk)s}dict/{%(splunk)s}key' % NS_MAP)
        for node in keyNodes:

            key = node.get('name')

            # try to auto-cast values
            if key in BOOLEAN_JOB_PROPERTIES:
                value = util.normalizeBoolean(node.text)
            elif key in INTEGER_JOB_PROPERTIES:
                try:
                    value = int(node.text)
                except:
                    logger.warn('Unable to cast job property "%s" to integer; got: "%s"' % (key, node.text))
                    value = -1
            elif key in FLOAT_JOB_PROPERTIES:
                try:
                    value = float(node.text)
                except:
                    logger.warn('Unable to cast job property %s to float; got: %s' % (key, node.text))
                    value = -1
            elif key.endswith('Time'):
                try:
                    value = util.parseISO(node.text)
                except:
                    logger.warn('Unable to cast job property "%s" to a datetime object; got: "%s"' % (key, node.text))
                    value = util.parseISO('')

            else:
                value = node.text

            # properties that always change get dropped into a dict
            if key in DYNAMIC_JOB_PROPERTIES:

                # process the runtime messages; raise if it's bad
                if key == 'messages':
                    if len(node) > 0:
                        self.messages = rest.format.nodeToPrimitive(node[0])
                        #logger.debug('    >>> %s' % self.messages)

                # otherwise just drop in value
                else:
                    self._cachedProps[key] = value

            # otherwise, static values are assumed to be present at init time
            # and will only be pulled in during the initial request
            else:

                # pick off the request key
                if key == 'request':
                    self.request = {}
                    for subnode in node.findall('{%(splunk)s}dict/{%(splunk)s}key' % NS_MAP):
                        self.request[subnode.get('name')] = subnode.text

                # process the eai:acl key
                elif key == 'eai:acl':
                    self.eaiacl = {}
                    for subnode in node.findall('{%(splunk)s}dict/{%(splunk)s}key' % NS_MAP):
                        self.eaiacl[subnode.get('name')] = subnode.text

                    perms = node.find('{%(splunk)s}dict/{%(splunk)s}key[@name="perms"]' % NS_MAP)
                    self.eaiacl['perms'] = {}
                    if len(perms):
                        for subnode in perms.findall('{%(splunk)s}dict/{%(splunk)s}key' % NS_MAP):
                            self.eaiacl['perms'][subnode.get('name')] = [ item.text for item in subnode.findall('{%(splunk)s}list/{%(splunk)s}item' % NS_MAP) ]

                elif key == 'resource_links':
                    self.resourceLinks = []
                    linkDicts = node.findall('{%(splunk)s}list/{%(splunk)s}item/{%(splunk)s}dict' % NS_MAP)
                    if linkDicts is not None and len(linkDicts):
                        for linkDict in linkDicts:
                            self.resourceLinks.append({
                                'name': linkDict.findtext('{%(splunk)s}key[@name="name"]' % NS_MAP),
                                'url': linkDict.findtext('{%(splunk)s}key[@name="url"]' % NS_MAP)
                            })
                else:
                    try:
                        getattr(set, key)
                        logger.warn('_getStatus - trying to set existing property on SearchJob object: %s' % key)
                    except AttributeError as e:
                        setattr(self, key, value)

                    #
                    # TODO: remove me and refactor into eventIsStreaming
                    #
                    if key == 'eventIsStreaming':
                        self.isStreaming = value


        # get the remaining static values from the standard Atom feed elements
        # at init time
        if isInitial:

            # get atom feed props
            self.createTime = root.findtext('{%(atom)s}published' % NS_MAP)
            self.modifiedTime = root.findtext('{%(atom)s}updated' % NS_MAP)
            self._cachedProps['search'] = root.findtext('{%(atom)s}title' % NS_MAP)

            # import all the <link> URIs; verify that server is sending
            # expected rels over
            for node in root.findall('{%(atom)s}link' % NS_MAP):
                if node.get('href'):
                    self.links[node.get('rel')] = node.get('href')
            for name in (self.ASSET_LINKS + self.META_LINKS):
                if name not in self.links:
                    logger.warn('SearchJob._getStatus - did not find expected "%s" <link> tag' % name)


        # create primitive container for property serialization, and pulling in
        # from the Atom wrapper
        self._propertyPrimitives = rest.format.nodeToPrimitive(
            root.find('{%(atom)s}content/{%(splunk)s}dict' % NS_MAP)
        )
        # setting createTime from XML
        # isInitial, self._cachedProps['isDone'] and not force leave self.createTime empty
        self._propertyPrimitives['createTime'] = root.findtext('{%(atom)s}published' % NS_MAP)
        self._propertyPrimitives['modifiedTime'] = self.modifiedTime
        self._propertyPrimitives['search'] = self._cachedProps['search']



    def _getTimeline(self):
        '''
        Parses the timeline feed and creates the proper 'timeline' property on
        the SearchJob object
        '''

        try:
            uri = self.links['timeline']
        except KeyError:
            raise AssertionError('Splunkd did not provide URI to job timeline endpoint')

        if self.hostPath:
            uri = self.hostPath + uri

        serverResponse, serverContent = rest.simpleRequest(uri, self.sessionKey, raiseAllErrors=True)

        if serverResponse.status != 200:
            logger.error('_getTimeline - error while getting timeline for job=%s; error=%s' % (self.id, serverContent))

        root = et.fromstring(serverContent)

        #
        # parse the timeline XML
        #
        self._timeline = TimeContainer(cursorTime=root.get('cursor'))
        self._timeline.itemCount = root.get('c')

        isAllDone = True

        for child in root:

            # extract data from XML
            itemCount = child.get('c')
            itemAvailableCount = child.get('a')
            earliestTime = child.get('t')
            duration = child.get('d')
            isComplete = util.normalizeBoolean(child.get('f'))

            # extract timezone
            timeOffset = child.get('ltz', 0) // 60 # data returned in seconds
            tzinfo = util.TZInfo(timeOffset)

            # create container
            bucket = TimeContainer(earliestTime=earliestTime, duration=duration, tzinfo=tzinfo)
            bucket.itemCount = int(itemCount)
            bucket.itemAvailableCount = int(itemAvailableCount)
            bucket.isComplete = isComplete
            self._timeline.buckets.append(bucket)

            # if we encounter any unfinished buckets, then mark
            # the parent container
            if not isComplete: isAllDone = False

        self._timeline.isComplete = isAllDone



    def _getSummary(self):

        uri = self.links['summary']

        if self.hostPath:
            uri = self.hostPath + uri

        getargs = self.getFetchOptions(nestedKey='summary')

        try:
            serverResponse, serverContent = rest.simpleRequest(uri, self.sessionKey, getargs=getargs)
        except KeyError:
            raise AssertionError('Splunkd did not provide URI to job summary endpoint')


        if (serverResponse.status != 200) and (serverResponse.status != 204):
            logger.error('_getSummary - error while getting summary for job=%s; error=%s' % (self.id, serverContent))

        # setup summary object
        summary = SummaryContainer()
        summary.fields = {}
        summary.count = 0

        if serverContent:
            root = et.fromstring(serverContent)
            summary.count = int(root.get('c', 0))
            # loop over all the fields
            for fieldNode in root.findall('field'):

                fieldName = fieldNode.get('k')
                fieldInfo = {
                    'count': int(fieldNode.get('c', 0)),
                    'distinctCount': int(fieldNode.get('dc', 0)),
                    'numericCount': int(fieldNode.get('nc', 0)),
                    'isExact': util.normalizeBoolean(fieldNode.get('exact'))
                }

                # handle the properties; modes is slightly different
                for childNode in fieldNode:
                    if childNode.tag == 'modes':
                        modes = []
                        for mode in childNode.findall('value'):
                            modes.append({
                                'count': int(mode.get('c', 0)),
                                'isExact': util.normalizeBoolean(mode.get('exact')),
                                'value': mode.findtext('text')
                            })
                        fieldInfo['modes'] = modes
                    else:
                        fieldInfo[childNode.tag] = childNode.text
                        if childNode.tag in KNOWN_NUMERIC_FIELD_ATTR:
                            try:
                                fieldInfo[childNode.tag] = float(childNode.text)
                            except:
                                pass

                summary.fields[fieldName] = fieldInfo

        self._summary = summary



    def _getResultRange(self, mode='events', http_method='GET', **kwargs):
        '''
        Private.  Retrieves a chunk of data from splunkd job data endpoint.

        http_method is used when the expected request args are larger than the 8KB
        limit on GET URI.  Set to 'POST' if the server is returning HTTP 414.
        '''

        if mode not in self.links:
            raise AssertionError('Splunkd did not provide link to job "%s" endpoint for sid=%s' % (mode, self.id))

        uri = self.links[mode]

        if self.hostPath:
            uri = self.hostPath + uri

        getargs = self.getFetchOptions()
        getargs.update(self._normalizeFetchOptions(kwargs))

        # auto-flatten list params
        for k in getargs:
            if isinstance(getargs[k], list):
                getargs[k] = util.fieldListToString(getargs[k])

        if http_method == 'POST':
            serverResponse, serverContent = rest.simpleRequest(uri, postargs=getargs, sessionKey=self.sessionKey)
        else:
            serverResponse, serverContent = rest.simpleRequest(uri, getargs=getargs, sessionKey=self.sessionKey)

        if serverResponse.status == 404:
            raise splunk.ResourceNotFound('Splunkd reported that the "%s" endpoint does not exist for sid=%s.  Either the job expired, or dispatch system is broken' % (mode, self.id))
        if serverResponse.status not in [200, 204]:
            logger.error('_getResultRange - error while getting data; status=%s content=%s'\
                % (serverResponse.status, serverContent))
            # TODO: handle messaging
            raise Exception('Server reported HTTP status=%s while getting mode=%s\n%s' % (serverResponse.status, mode, serverContent))

        return serverContent.strip()



    def getFeed(self, mode='events', **kwargs):
        '''
        Retrieves the raw data feed for a search job.  Specify the 'mode' option
        to choose between events, results, timeline, summary.  This method will
        use the current options set by setFetchOption().  Each endpoint only
        supports a few of the parameters listed in RESULT_ARG_MAP.  See docs for
        full info.
        '''

        return self._getResultRange(mode=mode.lower(), **kwargs)



    def setFetchOption(self, **kwargs):
        '''
        Sets data retrieval options used by all the data fetching operations on
        the current SearchJob.  Call getFetchOptions() to see the current
        settings.  Option aliases listed in RESULT_ARG_MAP are always
        translated to the splunkd API spec
        '''

        normalized = self._normalizeFetchOptions(kwargs)
        self._fetchOptions.update(normalized)
    setFetchOptions = setFetchOption

    def getFetchOptions(self, nestedKey=None):
        '''
        Returns the current fetch options set on this SearchJob. The default
        settings are listed in RESULT_ARG_MAP.
        '''
        if nestedKey:
            items = self._fetchOptions[nestedKey].items() if nestedKey in self._fetchOptions else []
        else:
            items = self._fetchOptions.items()
        return dict([(k, v) for (k, v) in items if v != None and not isinstance(v, dict) ])

    def removeFetchOption(self, key):
        '''
        Remove a fetch option set on this SearchJob. This is most useful for
        removing a default value that for some reason the caller can't use
        '''
        self._fetchOptions.pop(key)

    def _normalizeFetchOptions(self, options):
        '''
        Returns the current fetch options, with the additionalArgs merged in,
        duplicates normalized
        '''

        output = {}
        for k in options:
            if k in RESULT_ARG_MAP:
                output[RESULT_ARG_MAP[k]] = options[k]
            else:
                output[k] = options[k]

        return output


    def clearFetchOptions(self):
        '''
        Clears the current fetch options
        '''

        self._fetchOptions = self._normalizeFetchOptions(DEFAULT_RESULT_ARG_MAP)


    def toJsonable(self, timeFormat=None):
        '''
        Returns a primitive dict of the job property data feed from splunkd

        timeFormat: {unix} Tries to convert all timestamps to unix epoch time
        '''

        if self._propertyPrimitives == None:
            raise Exception('SearchJob object is in inconsistent state; cannot retrieve properties')

        output = copy.deepcopy(self._propertyPrimitives)

        # try to auto-cast values
        for k, v in output.items():
            if k in BOOLEAN_JOB_PROPERTIES:
                output[k] = util.normalizeBoolean(v)
            elif k in INTEGER_JOB_PROPERTIES:
                try:
                    output[k] = int(v)
                except:
                    pass
            elif k in FLOAT_JOB_PROPERTIES:
                try:
                    output[k] = float(v)
                except:
                    pass

            elif timeFormat and k.endswith('Time'):
                if timeFormat == 'unix':
                    if isinstance(v, util.string_type):
                        try:
                            output[k] = str(util.dt2epoch(util.parseISO(v, True)))
                        except:
                            pass
                else:
                    raise ValueError('Invalid timeFormat param: %s' % timeFormat)

        if len(self.resourceLinks):
            output['resource_links'] = self.resourceLinks

        return output


# /////////////////////////////////////////////////////////////////////////////
#  Search result object
# /////////////////////////////////////////////////////////////////////////////


class ResultSet(object):


    def __init__(self, parentJob, mode):
        self.mode = mode
        self.job = parentJob
        self._fieldOrder = None


    def _getFieldOrder(self):
        '''
        Returns the result set field ordering by inspecting the first returned
        output from the results.

        The fields returned are as follows:

            If show_empty_fields == True (default), then all fields, including
            fields that are requested but don't exist in the data, are
            returned.

            If show_empty_fields == False, then only the intersection of
            fields in the dataset and fields listed in 'field_list' are
            returned.  Except if 'field_list' is empty, all fields in the
            result set are returned.
        '''

        if self.mode == 'events' and self.job.isRealTimeSearch:
            offset = -1
        else:
            offset = 0

        response = self.job._getResultRange(
            mode=self.mode,
            offset=offset,
            count=1,
            outputMode='xml'
        )

        try:
            root = et.fromstring(response)
        except Exception as e:
            logger.warn('ResultSet._getFieldOrder - unable to parse field order info: %s' % e)
            return []

        self._fieldOrder = []

        # if request does not want empty fields listed, then fetch the summary
        # feed and pull out empty fields
        options = self.job.getFetchOptions()
        showEmptyFields = util.normalizeBoolean(options['show_empty_fields'])

        # when requesting events, get list of known fields in dataset; otherwise
        # don't populate available fields to allow results to get all fields;
        # /summary doesn't seem to provide _ fields, so we make sure that
        # both _time and _raw are marked as available in events
        availableFields = []
        if showEmptyFields == False and self.mode == 'events':
            for field in self.job.summary.fields:
                availableFields.append(field)
            if len(availableFields) > 0:
                availableFields.extend(['_time', '_raw'])

        for field in root.findall('meta/fieldOrder/field'):
            field = field.text.strip()
            if (showEmptyFields == True) or \
                    (showEmptyFields == False and len(availableFields) == 0) or \
                    (showEmptyFields == False and (field in availableFields)):
                self._fieldOrder.append(field)

        return self._fieldOrder

    fieldOrder = property(_getFieldOrder)

    # ResultSet is indexed by an integer or slice, not a map-like abstraction so, __contains__ isn't required there

    def __getitem__(self, index):
        '''
        Retrieves items from the result set; supports slicing

        NOTE: slicing like [-5:1] where start < 0 while start > 0 will
              effectively ignore the stop and be equivalent to [-5:]
        '''

        self.job._getStatus()
        self.job.pushValidation()

        isSlice = False

        if self.mode == 'events':
            L = self.job._cachedProps['eventCount']
        elif self.mode == 'results':
            L = self.job._cachedProps['resultCount']
        elif self.mode == 'results_preview':
            L = self.job._cachedProps['resultPreviewCount']
        else:
            L = self.job._getLogicalCount(False)

        # handle slice requests
        if isinstance(index, slice):

            # valid start: 0 < i < L; handle negative starts
            if index.start >= L: return []
            elif not index.start: start = 0
            else: start = index.start

            # valid stop: i < j <= L; handle negative stops
            if (not index.stop) or (index.stop > L):
                stop = L
            else:
                stop = index.stop

            # catch empty set conditions:
            #   [-1:-2]
            #   [0:-99999999]
            if not self.job.isRealTimeSearch: ##fixes SPL-45516
                if (start != 0 and stop != 0 and start > stop) \
                or (stop < 0 and L + stop < 0) \
                or (stop > L):
                    return []

            # [:-45]
            if start == 0 and stop < 0:
                count = L + stop
            # [-45:-23]
            elif start < 0 and stop < 0:
                count = stop - start
            # [-45:]
            elif start < 0:
                count = -1
            else:
                count = stop - start

            isSlice = True

            # this is necessary because splunkd interprets count=0 as 'ALL'
            if count == 0:
                return []

            # single-unbounded needs to be translated, i.e. [-45:]
            if count == -1:
                count = 0

        # handle single item index requests
        else:
            count = 1
            start = index

            if start >= L or (start < 0 and -start > L):
                raise IndexError

        response = self.job._getResultRange(
            mode=self.mode,
            offset=start,
            count=count,
            outputMode='xml'
            )

        # parse results from server; slice requests always return list
        incomingObject = self._parseResultSet(response)

        output = []
        for item in incomingObject:
            if not isSlice:
                return Result(item)
            output.append(Result(item))

        return output


    def _parseResultSet(self, xmlString):
        '''
        Returns a list of results stored in an OrderedDict
        '''

        if not xmlString:
            logger.debug('_parseResultSet - got empty string; exiting')
            return []

        try:
            root = et.fromstring(xmlString)
        except Exception as e:
            logger.exception(e)
            raise Exception('Unable to parse the result xml.  Verify the character encoding of the results is correct.')

        # get the actual results
        results = []
        for result in root.findall('result'):
            row = util.OrderedDict()

            # get the offset
            offset = result.get('offset', 'null')
            if offset == 'null':
                row['__splunk_offset'] = -1
            else:
                row['__splunk_offset'] = int(offset)

            for field in result.findall('field'):
                key = field.get('k')
                if key == '_raw':
                    raw = RawEvent()
                    raw.fromXml(field.find('v'))
                    row[key] = raw

                else:
                    values = field.findall('value')

                    for value in values:
                           text_value = value.find('text')
                           tags_value = value.findall('tag')

                           text_value_data = ''
                           tags_data = []

                           isHighlighted = True if value.get("h", "") is "1" else False

                           if text_value.text:
                              text_value_data = text_value.text
                           if tags_value:
                              tags_data = [y.text for y in tags_value]

                           if key in row:
                              row[key].addVal(ResultFieldValue(isHighlighted, value=text_value_data, tags=tags_data))
                           else:
                              row[key] = ResultField(fieldValues=[ResultFieldValue(isHighlighted, value=text_value_data, tags=tags_data)])

            results.append(row)

        return results


    def __iter__(self):
        '''
        Returns the streaming iterator for all results in the result set
        '''

        self.job.pushValidation()

        __iteridx = 0
        __iterbuffer = []
        __iterbufferBounds = (0, -1)

        allDataFetched = False
        localCount = 0

        # optimize events to use the streaming event count; otherwise fallback
        # to safer resultCount property that usually is 0 while isDone=0
        if self.mode == 'events':
            jobCountProperty = 'eventAvailableCount'
        elif self.mode == 'results_preview':
            jobCountProperty = 'resultPreviewCount'
        else:
            jobCountProperty = 'resultCount'

        # if data has not all been retrieved, then keep polling for data
        loopStartTime = time.time()
        while not allDataFetched:

            self.job._getStatus()

            # while job is still running, first check that the server is event
            # returning streaming data; if not, just sleep until job is done
            if not self.job._cachedProps['isDone']:
                if (self.mode == 'events' and not self.job.eventIsStreaming and not self.job.isRealTimeSearch) \
                or (self.mode == 'results' and not self.job.resultIsStreaming):
                    logger.debug('ResultSet.__iter__ -- waiting on completion of non-streaming results...')
                    time.sleep(1)
                    continue

            # seed the count once here
            localCount = self.job._cachedProps[jobCountProperty]

            # if request is within available data bounds
            while __iteridx < localCount:

                localCount = self.job._cachedProps[jobCountProperty]

                # if data is in buffer, then yield
                if __iterbufferBounds[0] <= __iteridx < __iterbufferBounds[1]:
                    yield __iterbuffer[__iteridx - __iterbufferBounds[0]]
                    __iteridx = __iteridx + 1

                # otherwise, request new buffer
                else:
                    stop = min(__iteridx + ITER_BUFFER_SIZE, localCount)
                    logger.debug('ResultSet.__iter__ -- need to get data for range: %s-%s' % (__iteridx, stop))

                    # loop is for protecting against incomplete data; see SPL-12146;
                    # loop is not applicable when fetching results, so flush the buffer
                    # if it's non-empty
                    for i in range(FETCH_RETRY_COUNT):
                        __iterbuffer = self[__iteridx:stop]
                        if len(__iterbuffer) >= (stop - __iteridx):
                            break
                        if self.mode != 'events':
                            if len(__iterbuffer) > 0:
                                for item in __iterbuffer:
                                    yield item
                            if sys.version_info >= (3, 0): return # Python 3 no longer respects StopIteration
                            raise StopIteration

                        logger.debug('ResultSet.__iter__ -- waiting on complete events...')
                        time.sleep(FETCH_RETRY_INTERVAL)
                    else:
                        raise Exception('ResultSet.__iter__ -- timed out while waiting on data; expected %s events, only got %s; count=%s' % \
                            ((stop - __iteridx), len(__iterbuffer), localCount))

                    __iterbufferBounds = (__iteridx, stop)

            # stop loop when job is done; also stop when in preview mode because
            # preview is expected to return partial data
            if self.job._cachedProps['isDone'] or self.mode == 'results_preview':
                logger.debug('ResultSet.__iter__ -- DONE')
                allDataFetched = True
            else:
                elapsedTime = time.time() - loopStartTime
                nextRetry = getRetryInterval(elapsedTime, .1, .5, 2)
                logger.debug('ResultSet.__iter__ -- sleeping for %s' % nextRetry)
                time.sleep(nextRetry)

        if sys.version_info >= (3, 0): return # Python 3 no longer respects StopIteration
        raise StopIteration



class Result(object):
    '''
    Represents a single result contained in a ResultSet.  Typically, this is an
    event generated by Splunk.

    For events:

        result.time     # the event time, as specified via output_time_format
        result.raw      # the original event text
        result.fields   # the dictionary of event field values (metadata)
        result[field]   # a convenience key accessor to the result.fields dict

        The default __iter__ iterates over the field names contained in the
        'fields' property
    '''


    def __init__(self, fields):

        self.time = None
        self.offset = -1

        if '__splunk_offset' in fields:
            self.offset = fields['__splunk_offset']
            del fields['__splunk_offset']

        if '_raw' in fields:
            self.raw = fields['_raw']
        else:
            self.raw = RawEvent()

        if '_time' in fields:
            self.time = fields['_time'][0].value

        self.fields = fields

    def __str__(self):
        raw = self.raw.getRaw()
        if raw:
            return raw
        output = []
        for k in self.fields:
            output.append('%s=%s' % (k, self.fields[k]))
        return '\t'.join(output)

    def __getitem__(self, key):
        return self.fields.__getitem__(key)

    def __contains__(self, key):
        return self.fields.__contains__(key)

    def __iter__(self):
        return self.fields.__iter__()

    def __len__(self):
        return self.fields.__len__()

    def get(self, key, default=None):
        return self.fields.get(key, default)

    def values(self):
        return self.fields.values()

    def keys(self):
        return self.fields.keys()


    def toDateTime(self):
        '''
        Returns a datetime.datetime object that represents the event's timestamp.
        This method only works with ISO-8601 timeformats, or epoch time.  NOTE:
        if given epoch time, then the return value will take on the local server's
        timezone.
        '''

        if not self.time:
            return self.time

        # first try to interpret as ISO-8601
        try:
            return util.parseISO(self.time, strict=True)

        # then try as epoch time
        except ValueError:
            try:
                t = self.toEpochTime()
            except ValueError:
                raise ValueError('Cannot parse time field "%s"; this method only supports ISO-8601 or epoch time formats' % self.time)

            return datetime.datetime.fromtimestamp(t, util.TZInfo())


    def toEpochTime(self):
        '''
        Returns a decimal.Decimal object that represents the event's timestamp
        '''

        if not self.time:
            return self.time

        # first try to interpret as epoch time
        try:
            return decimal.Decimal(self.time)

        # then try ISO-8601
        except decimal.InvalidOperation:
            try:
                t = util.parseISO(self.time, strict=True)
            except ValueError:
                raise ValueError('Cannot parse time field "%s"; this method only supports ISO-8601 or epoch time formats' % self.time)

            return util.dt2epoch(t)



class RawEvent(object):
    '''
    Represents an event, marked with segmentation information and highlighted
    terms
    '''

    def __init__(self, plainString=''):
        self._value = plainString
        self._xmlNode = None
        self.isTruncated = False

    def setRaw(self, plainString):
        self._value = plainString

    def getRaw(self):
        return self._value

    def _getTransform(self, xslt):
        '''
        xslt: A string respresentation of the xslt document.

        Returns an lxml xslt transform object see: http://codespeak.net/lxml/xpathxslt.html#xslt
        '''
        xsltTree = et.XML(xslt)
        transform = et.XSLT(xsltTree)
        return transform(self._xmlNode)

    def toXml(self, xslt=None):
        '''
        xslt: An optional string representation of an xslt transform to apply.

        Returns a string respresentation of the xml or a transformed result based on the
        optional xslt param. XSLT transformed results encoding is specified via the
        <xsl:output encoding="utf-8" /> setting. If no raw xml markup exists a None value is returned.
        '''
        if self._xmlNode is None:
            return None
        elif xslt is None:
            # Specify encoding otherwise lxml will mutate results.
            return et.tostring(self._xmlNode, encoding='utf-8')
        else:
            transform = self._getTransform(xslt)
            # As opposed to normal ElementTree objects, an XSLTransform object is converted to a string
            # by applying the str() function. The result is encoded as requested by the xsl:output element
            # See: http://codespeak.net/lxml/xpathxslt.html#xslt
            return  str(transform).rstrip('\n\r')

    def fromXml(self, lxmlNode):
        '''
        lxmlNode: The raw field xml to serialize following the structure:
        <v xml:space="preserve" trunc="0">...<sg h="0">lang</sg>...<sg h="1">...</sg></v>
        '''
        self._xmlNode = lxmlNode
        truncation = lxmlNode.get("trunc", None)
        if truncation is not None:
            self.isTruncated = util.normalizeBoolean(truncation)
        self.setRaw(lxmlNode.xpath("string()"))

    #
    # TODO: these should be a generic pass through to string object
    #

    def __str__(self):
        return self.getRaw()

    def __repr__(self):
        return self.getRaw()

    def __getitem__(self, idx):
        return self.getRaw().__getitem__(idx)

    def __contains__(self, idx):
        return self.getRaw().__contains__(idx)

    def __iter__(self):
        return self.getRaw().__iter__()

    def __len__(self):
        return self.getRaw().__len__()

    def decode(self, codepage):
        return self.getRaw().decode(codepage)

    def encode(self, codepage):
        return self.getRaw().encode(codepage)

    def split(self, splitter):
        return self.getRaw().split(splitter)



class TimeContainer(object):
    '''
    Represents a generic container for holding a time-bounded entity.
    '''

    def __init__(self, earliestTime=0, latestTime=0, duration=0, cursorTime=0, tzinfo=util.utc):
        '''
        Creates a new time container object.

        earliestTime unix_timestamp: The timestamp of the earliest time boundary (inclusive)
        latestTime unix_timestamp: The timestamp of the latest time boundary (exclusive)
        cursorTime unix_timestamp: The timestamp of the cursor location
        duration unix_timestamp: The duration, in seconds, of the time between earliestTime and latestTime
        tzinfo tzinfo: The timezone object

        If earliestTime, latestTime, and duration are specified, duration is computed
        by diffing latestTime with earliestTime; the passed duration is ignored.
        '''

        self.buckets = []
        self.itemCount = 0
        self.itemAvailableCount = 0
        self.isComplete = True
        self.earliestTime = None
        self.latestTime = None
        self.cursorTime = None
        self.duration = None
        self.tzinfo = tzinfo

        earliestTime = float(earliestTime)
        latestTime = float(latestTime)
        cursorTime = float(cursorTime)
        duration = float(duration)

        if earliestTime:
            self.earliestTime = datetime.datetime.fromtimestamp(earliestTime, tzinfo)
        if latestTime:
            self.latestTime = datetime.datetime.fromtimestamp(latestTime, tzinfo)
        if cursorTime:
            self.cursorTime = datetime.datetime.fromtimestamp(cursorTime, tzinfo)

        # do auto completion on time data
        if earliestTime and not latestTime and duration:
            self.latestTime = datetime.datetime.fromtimestamp(earliestTime + duration, tzinfo)

        elif not earliestTime and latestTime and duration:
            self.earliestTime = datetime.datetime.fromtimestamp(latestTime - duration, tzinfo)

        if self.latestTime and self.earliestTime:
            self.duration = self.latestTime - self.earliestTime


    def __len__(self):
        return self.buckets.__len__()

    def __getitem__(self, index):
        return self.buckets.__getitem__(index)

    def __contains__(self, index):
        return self.buckets.__contains__(index)

    def __setitem__(self, index, value):
        return self.buckets.__setitem__(index, value)

    def __iter__(self):
        return self.buckets.__iter__()



class SummaryContainer(object):
    '''
    Represents summary information about a search job
    '''

    earliestTime = None
    latestTime = None
    fields = None
    count = None


class ResultField(object):
   '''
   Represents a result field
   This is a container class that will comprise of several ResultFieldValue objects

   NOTE: Owing to this new class a parsed dict from _parseResultSet can now contain two types of objects:

   1. RawEvent
   2. ResultField (which is a container for ResultFieldValue objects)
   '''

   def __init__(self, fieldValues=[]):
      self._fieldValue = fieldValues

   def __str__(self):
      '''
      String representation of the obj
      '''
      return ','.join([x.value for x in self._fieldValue])

   def __repr__(self):
      '''
      repr representation for the obj
      '''
      return self.__str__()

   def __getitem__(self, key):
      '''
      so we can do things like  self[key]
      '''
      return self._fieldValue[key]

   def __contains__(self, key):
      '''
      returns bool if key available
      '''
      return key in self._fieldValue

   def __len__(self):
      '''
      returns the len of the contained list
      '''
      return len(self._fieldValue)

   def __iter__(self):
      '''
      iterates over the contained list
      '''
      return self._fieldValue.__iter__()

   def addVal(self, obj):
      '''
      helper function to add a value to the contained list
      '''
      self._fieldValue.append(obj)

class ResultFieldValue(object):
   '''
   Class to represent individual field values
   '''

   def __init__(self, isHighlighted, value='', tags=[]):
     self._value = value
     self._tags = tags
     self._isHighlighted = isHighlighted

   def __str__(self):
      return self.value

   def getValue(self):
      return self._value

   def setValue(self, value):
      self._value = value

   def getTags(self):
      return self._tags

   def setTags(self, tags=[]):
      self._tags = tags

   def getIsHighlighted(self):
       return self._isHighlighted

   def __len__(self):
      raise Exception('len method not supported for ResultFieldValue objects')

   def __iter__(self):
      raise TypeError('ResultFieldValue object is not iterable.')

   value = property(getValue, setValue, None, 'value of this field value object')
   tags = property(getTags, setTags, None, 'tags for this field value object')
   isHighlighted = property(getIsHighlighted, None, None, 'highlighted state for the field value object')

class ResultsLite(object):
    def __init__(self, text):
        import lxml.etree as et

        self._isPreview = True
        self._fieldOrder = []
        self._unstrippedFieldOrder = []
        self._results = []

        if text == None:
            return

        try:
            root = et.fromstring(text)
        except Exception as e:
            self._isPreview = False
            logger.exception(e)
            return

        self._isPreview  = splunk.util.normalizeBoolean(root.get('preview', False))
        self._fieldOrder = self._parseFieldOrder(root)
        self._unstrippedFieldOrder = self._parseUnstrippedFieldOrder(root)
        self._results    = self._parseResults(root)

    def _parseFieldOrder(self, root):
        fieldOrder = []

        for field in root.findall('meta/fieldOrder/field'):
            fieldOrder.append(field.text.strip())

        return fieldOrder

    def _parseUnstrippedFieldOrder(self, root):
        fieldOrder = []

        for field in root.findall('meta/fieldOrder/field'):
            fieldOrder.append(field.text)

        return fieldOrder

    def _parseResults(self, root):
        results = []

        for result in root.findall('result'):
            row = splunk.util.OrderedDict()

            # get the offset
            offset = result.get('offset', 'null')
            if offset == 'null':
                row['__splunk_offset'] = -1
            else:
                row['__splunk_offset'] = int(offset)

            for field in result.findall('field'):
                key = field.get('k')
                if key == '_raw':
                    raw = RawEvent()
                    raw.fromXml(field.find('v'))
                    row[key] = raw
                else:
                    values = field.findall('value')

                    for value in values:
                           text_value = value.find('text')
                           tags_value = value.findall('tag')

                           text_value_data = ''
                           tags_data = []

                           isHighlighted = True if value.get("h", "") is "1" else False

                           if text_value.text:
                              text_value_data = text_value.text
                           if tags_value:
                              tags_data = [y.text for y in tags_value]

                           if key in row:
                              row[key].addVal(ResultFieldValue(isHighlighted, value=text_value_data, tags=tags_data))
                           else:
                              row[key] = ResultField(fieldValues=[ResultFieldValue(isHighlighted, value=text_value_data, tags=tags_data)])

            results.append(Result(row))

        return results

    def isPreview(self):
        return self._isPreview

    def fieldOrder(self):
        return self._fieldOrder

    def results(self):
        return self._results

    def unstrippedFieldOrder(self):
        return self._unstrippedFieldOrder

class JobLite(object):
    def __init__(self, sid):
        self.sid = sid
        self.fetchOptions = {}

    def setFetchOption(self, **kwargs):
        for (option, value) in kwargs.items():
            self.fetchOptions[RESULT_ARG_MAP.get(option, option)] = value

    def get(self, asset):
        import splunk.rest

        #SPL-50513 sid can contain space. Please escape
        sid = self.sid.replace(' ', '%20')
        uri = '/services/search/jobs/%s/%s' % (sid, asset)

        serverResponse, serverContent = splunk.rest.simpleRequest(uri, getargs=self.fetchOptions)

        if serverResponse.status == 404:
            raise splunk.ResourceNotFound('Splunkd reported that the "%s" endpoint does not exist for sid=%s.  Either the job expired, or dispatch system is broken' % (uri, self.sid))
        if serverResponse.status not in [200, 204]:
            raise Exception('Server reported HTTP status=%s while getting uri=%s\n%s' % (serverResponse.status, uri, serverContent))

        return serverContent.strip()

    def getResults(self, asset, offset=None, count=None):
        import splunk.rest

        #SPL-50513 sid can contain space. Please escape
        sid = self.sid.replace(' ', '%20')
        uri = '/services/search/jobs/%s/%s' % (sid, asset)

        getargs = copy.copy(self.fetchOptions)

        getargs['output_mode'] = "xml"

        if offset:
            getargs['offset'] = offset

        if count:
            getargs['count'] = count

        serverResponse, serverContent = splunk.rest.simpleRequest(uri, getargs=getargs)

        if serverResponse.status == 204:
            return ResultsLite(None)

        if serverResponse.status != 200 or len(serverContent) == 0:
            return None

        return ResultsLite(serverContent)



# ////////////////////////////////////////////////////////////////////////////
# Supplemental methods
# ////////////////////////////////////////////////////////////////////////////

def getRetryInterval(elapsed_time, min_interval, max_interval, clamp_time):
    '''
    Returns a wait time (sec) based on the current time elapsed, as mapped
    onto a cubic easing function.

    elapsed_time: number of seconds that have elapsed since the first
        call to getRetryInterval()

    min_interval: minimum return value of this method; also the interval
        returned when elapsed_time = 0

    max_interval: maximum return value of this method; also the interval
        returned when elapsed_time >= clamp_time

    clamp_time: total duration over which to calculate a wait time; while
        elapsed_time < clamp_time, the return value will be less than
        max_interval; when elapsed_time >= clamp_time, the return value will
        always be max_interval
    '''

    if elapsed_time >= clamp_time: return float(max_interval)
    return min(max_interval * pow(elapsed_time/float(clamp_time), 3) + min_interval, max_interval)


def normalizeJobPropertyValue(key, value):
    if key in BOOLEAN_JOB_PROPERTIES:
        return util.normalizeBoolean(value)
    elif key in INTEGER_JOB_PROPERTIES:
        try:
            return int(value)
        except:
            logger.warn('Unable to cast job property "%s" to integer; got: "%s"' % (key, value))
            return -1
    elif key in FLOAT_JOB_PROPERTIES:
        try:
            return float(value)
        except:
            logger.warn('Unable to cast job property %s to float; got: %s' % (key, value))
            return -1
    elif key.endswith('Time'):
        try:
            return util.parseISO(value)
        except:
            logger.warn('Unable to cast job property "%s" to a datetime object; got: "%s"' % (key, value))
            return util.parseISO('')
    else:
        return value



# ////////////////////////////////////////////////////////////////////////////
# legacy saved search method mapping
#
# all of the methods defined in this section used to be in this file;
# relocating all of the saved search methods into a separate file: saved.py
#
# old method call:
#       splunk.search.listSavedSearches()
#
# new call:
#       splunk.saved.listSavedSearches()
# ////////////////////////////////////////////////////////////////////////////

class _savedMethodFactory(object):
    '''
    This class defers the import of splunk.saved to provide legacy method
    mapping.
    '''

    def __init__(self, methodName):
        self.methodName = methodName

    def __call__(self, *args, **kwargs):
        try:
            _savedModuleInstance
        except:
            import splunk.saved as _savedModuleInstance

        return getattr(_savedModuleInstance, self.methodName)(*args, **kwargs)

# route specific legacy saved search method calls to the proxy
for methodName in [
    'dispatchSavedSearch',
    'createSavedSearch',
    'getSavedSearchWithTimes',
    'listSavedSearches',
    'getSavedSearch',
    'getSavedSearchHistory',
    'getSavedSearchJobs',
    'getJobForSavedSearch',
    'deleteSavedSearch']:
        setattr(sys.modules[__name__], methodName, _savedMethodFactory(methodName))



# ////////////////////////////////////////////////////////////////////////////
# Test routines
# ////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':

    import unittest
    import splunk.rest as rest

    TEST_NAMESPACE = splunk.getDefault('namespace')
    TEST_OWNER = 'admin'

    class JobControlTests(unittest.TestCase):
        '''Tests covering splunkd response to job control requests'''

        TEST_NAMESPACE = splunk.getDefault('namespace')
        TEST_OWNER = 'admin'

        def testJobTouch(self):
            '''Test touching a job updates its TTL.'''
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('search non foo bar empty', sessionKey=sessionKey)
            waitForJob(job)

            start_ttl = job.ttl

            # Stall the ttl for 2 seconds
            time.sleep(2)

            aged_ttl = job.ttl
            self.assert_(aged_ttl <= start_ttl)

            job.touch()
            refreshed_ttl = job.ttl

            self.assert_(refreshed_ttl >= aged_ttl)
            job.cancel()

        def testJobSave(self):
            '''Test saving a job marks it as isSaved.'''
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('search non foo bar empty', sessionKey=sessionKey)
            waitForJob(job)

            job.save()
            self.assert_(job.isSaved)

            # test with namespace/owner
            # NOTE: The save and the touch methods depend on the _execControl method which derives the uri from the atom feed itself
            # test here is to ensure that the atom feed has the correct url.
            job = dispatch('search non foo bar empty', sessionKey=sessionKey, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            waitForJob(job)

            job.save()
            self.assert_(job.isSaved)

        def testRequestPassing(self):

            job = dispatch('search NOTHING HERE1111', required_field_list='A,B,C,D', some_random_key='I LIEK PIE', earliest_time='-23d')

            self.assertEquals(job.request['search'], 'search NOTHING HERE1111')
            self.assertEquals(job.request['required_field_list'], 'A,B,C,D')
            self.assertEquals(job.request['some_random_key'], 'I LIEK PIE')
            self.assertEquals(job.request['earliest_time'], '-23d')

            job.cancel()


        def testTTLChange(self):

            job = dispatch('search NOTHING balba da sdfq234faf')
            waitForJob(job, 20)

            ttl = 54321
            job.setTTL(ttl)
            job.refresh()
            self.assert_(job.ttl <= ttl and job.ttl > ttl-10, 'Job TTL does not validate: actual=%s expected=%s' % (job.ttl, ttl))

            self.assertRaises(ValueError, job.setTTL, None)
            self.assertRaises(ValueError, job.setTTL, -1)
            self.assertRaises(ValueError, job.setTTL, 'eofk3n')

            job.cancel()


        def testPriorityChange(self):

            # assume that default priority is 5
            new_priority = 3

            job = dispatch('search index=_*', earliest_time='rt-30s', latest_time='rt')
            time.sleep(1)

            original_priority = job.priority
            job.setpriority(new_priority)

            if original_priority == new_priority:
                job.cancel()
                self.fail('the new job priority is the same as the old; cannot test')

            # wait for 30 seconds for priority to change values
            for i in range(30):
                job.refresh()
                if job.priority != original_priority:
                    break
                time.sleep(1)


            try:
                self.assertEquals(job.priority, new_priority)

                self.assertRaises(ValueError, job.setpriority, None)
                self.assertRaises(ValueError, job.setpriority, -1)
                self.assertRaises(ValueError, job.setpriority, 11)
                self.assertRaises(ValueError, job.setpriority, 'eofk3n')

            finally:
                job.cancel()


    class SearchObjectTests(unittest.TestCase):
        '''Tests covering behavior of splunk.search object properties and methods.'''

        xslt = '''<?xml version="1.0" encoding="UTF-8"?>
        <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
            <xsl:strip-space elements="*" />
            <xsl:preserve-space elements="v" />
            <xsl:output method="html" indent="no" encoding="utf-8" />
            <xsl:template match="/">
                <xsl:apply-templates select="v" />
            </xsl:template>
            <xsl:template match="v">
                <xsl:apply-templates />
            </xsl:template>
            <xsl:template match="sg">
                <em>
                    <xsl:attribute name="class">
                        <xsl:text>t</xsl:text>
                        <xsl:if test="@h">
                            <xsl:text> a</xsl:text>
                        </xsl:if>
                    </xsl:attribute>
                    <xsl:apply-templates />
                </em>
            </xsl:template>
        </xsl:stylesheet>
        '''

        def testAaRawEvent(self):
            '''
            test the parsing in raw XML
            '''

            xml = '''<v xml:space="preserve" trunc="0">2008/09/24 19:28:27  changelist=42331 filePath=//splunk/cm/winbuild.pl <sg>added=0</sg> deleted=0 <sg h="1">changed=8</sg> user=kim@kim-laptop revision=40 changetype=edit isTruncated=False</v>'''

            rawtext = '2008/09/24 19:28:27  changelist=42331 filePath=//splunk/cm/winbuild.pl added=0 deleted=0 changed=8 user=kim@kim-laptop revision=40 changetype=edit isTruncated=False'

            xmltransform = '''2008/09/24 19:28:27  changelist=42331 filePath=//splunk/cm/winbuild.pl <em class="t">added=0</em> deleted=0 <em class="t a">changed=8</em> user=kim@kim-laptop revision=40 changetype=edit isTruncated=False'''

            node = et.fromstring(xml)
            r = RawEvent()
            r.fromXml(node)
            self.assertEqual(str(r), rawtext)
            self.assertEqual(len(r), len(rawtext))
            self.assertEqual(r[0], rawtext[0])
            self.assertEqual(r[5:10], rawtext[5:10])
            self.assertEqual(r.toXml(xslt=self.xslt), xmltransform)
            self.assertEqual(r.isTruncated, False)


        def testNoRawEvent(self):
            '''
            test handling cases when _raw is absent
            '''
            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = dispatch('| windbag | head 10 | fields - _raw', sessionKey=sessionKey)

            waitForJob(job)

            r = job.results[0]

            self.assertEquals(r.raw.getRaw(), '')
            self.assertEquals(r.raw.getRaw().__len__(), 0)

        def testSearchRaw(self):

            expectedRaw = u'''2008-10-20T14:29:22 POSITION 0 lang=Albanian sample="Unë mund të ha qelq dhe nuk më gjen gjë." constant="double quotes" \'single quotes\' \\slashes\\ `~!@#$%^&*()-_=+{}|;:<>,./? [brackets] <script>alert("raw event unescaped!")</script>'''

            expectedXml = u'''<v xml:space="preserve" trunc="0">2008-10-20T14:29:22 POSITION 0 <sg h="1">lang</sg>=Albanian sample="Unë mund të ha qelq dhe nuk më gjen gjë." constant="double quotes" 'single quotes' \slashes\ `~!@#$%^&amp;*()-_=+{}|;:&lt;&gt;,./? [<sg h="1">brackets</sg>] &lt;script&gt;alert("raw event unescaped!")&lt;/script&gt;</v>'''

            expectedXMLTransform = u'''2008-10-20T14:29:22 POSITION 0 <em class="t a">lang</em>=Albanian sample="Unë mund të ha qelq dhe nuk më gjen gjë." constant="double quotes" 'single quotes' \slashes\ `~!@#$%^&amp;*()-_=+{}|;:&lt;&gt;,./? [<em class="t a">brackets</em>] &lt;script&gt;alert("raw event unescaped!")&lt;/script&gt;'''

            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = dispatch('windbag rowcount=5 basetime=1224538162 | search lang OR brackets', sessionKey=sessionKey)

            waitForJob(job)

            r = job.results[0]

            self.assertEquals(r.raw.getRaw(), expectedRaw)
            self.assertEquals(str(r), expectedRaw)
            self.assertEquals(r.raw.decode('utf-8'), expectedRaw)
            self.assertEquals(r.raw.toXml(), expectedXml)
            self.assertEquals(r.raw.toXml(xslt=self.xslt), expectedXMLTransform)
            self.assertEquals(r.raw.isTruncated, False)


        def testResultSlicing(self):
            '''
            Test the dispatcher's ability to merge results from split data files;
            see SPL-12146
            '''

            rowCount = 500

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag rowcount=%s' % rowCount, sessionKey=sessionKey, status_buckets=1)

            waitForJob(job)

            self.assertEqual(job.count, rowCount)

            s = job.events[0:100]
            self.assertEqual(len(s), 100)

            s = job.events[0:rowCount]
            self.assertEqual(len(s), rowCount)

            s = job.events[0:12342]
            self.assertEqual(len(s), rowCount)

            s = job.events[0:50]
            self.assertEqual(len(s), 50)

            s = job.events[12:76]
            self.assertEqual(len(s), 64)

            s = job.events[76:12]
            self.assertEqual(len(s), 0)

            s = job.events[52:52]
            self.assertEqual(len(s), 0)

            s = job.events[0:]
            self.assertEqual(len(s), rowCount)

            s = job.events[:]
            self.assertEqual(len(s), rowCount)

            s = job.events[:-73]
            self.assertEqual(len(s), 427)

            s = job.events[:-600]
            self.assertEqual(len(s), 0, 'failed on [:-600]')


            s = job.events[-1:]
            self.assertEqual(len(s), 1)

            s = job.events[-499:]
            self.assertEqual(len(s), 499)

            s = job.events[-500:]
            self.assertEqual(len(s), 500)

            s = job.events[-501:]
            self.assertEqual(len(s), 500)

            s = job.events[-1:-2]
            self.assertEqual(len(s), 0)

            s = job.events[-2:-1]
            self.assertEqual(len(s), 1)

            s = job.events[-1:-1]
            self.assertEqual(len(s), 0)

            s = job.events[-345:-234]
            self.assertEqual(len(s), 111)

            s = job.events[-9999:-9999]
            self.assertEqual(len(s), 0)


            s = job.events[-1]
            self.assertEqual(int(str(s['position'])), 499, 'failed on [-1]')

            s = job.events[0]
            self.assertEqual(int(str(s['position'])), 0, 'failed on [0]')

            s = job.events[1]
            self.assertEqual(int(str(s['position'])), 1, 'failed on [1]')

            s = job.events[499]
            self.assertEqual(int(str(s['position'])), 499, 'failed on [499]')

            self.assertRaises(IndexError, job.__getitem__, 500)

            job.cancel()

        def testWaitForRunning(self):
             # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag', sessionKey=sessionKey)
            self.assertTrue(job.waitForRunning, True)
            self.assertEqual(job.dispatchState, 'RUNNING')

            job = getJob(job.sid, sessionKey=sessionKey)
            self.assertTrue(job.waitForRunning, True)
            self.assertEqual(job.dispatchState, 'RUNNING')

            # can't appropriately test waitForRunning==False mode in a unit test infrastructure

        def testTimelineObject(self):

            # test default population of latestTime, given a start and duration
            t = TimeContainer(earliestTime=1199145600, duration=62)
            self.assertEquals(t.latestTime, datetime.datetime(2008, 1, 1, 0, 1, 2, 0, util.utc))
            self.assertEquals(t.duration, datetime.timedelta(seconds=62))

            # test default population of earliestTime, given a end and duration
            t = TimeContainer(latestTime=1199145662, duration=62)
            self.assertEquals(t.earliestTime, datetime.datetime(2008, 1, 1, 0, 0, 0, 0, util.utc))

            # test default population of duration, given a start and end
            t = TimeContainer(earliestTime=1199145600, latestTime=1199145675)
            self.assertEquals(t.duration, datetime.timedelta(seconds=75))

            # test default population of duration, given a start and end and extra duration
            t = TimeContainer(earliestTime=1199145600, latestTime=1199145675, duration=12)
            self.assertEquals(t.duration, datetime.timedelta(seconds=75))


        def testResultProperties(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag', sessionKey=sessionKey)

            waitForJob(job)

            for i, v in enumerate(job.events):
                self.assertEquals(v.raw, v['_raw'])
                self.assertEquals(v.time, v['_time'][0].value)
                self.assertEquals(v.offset, i)

                for k in v.fields:
                    self.assertEquals(v[k], v.fields[k])

            job.cancel()


        def testEventOptions(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # handle QuotaExceededException by waiting
            j = 10
            while j > -1:
               j -= 1
               try:
                  job = dispatch('windbag', sessionKey=sessionKey)
               except splunk.QuotaExceededException as e:
                  time.sleep(5) # wait for some searches to complete
                  if j == 0:
                     raise e
                  else:
                     pass

            waitForJob(job)

            # check that fieldList accepts both list() and string()
            job.setFetchOptions(fieldList='A,B,C')
            self.assertEquals(job.getFetchOptions()['field_list'], 'A,B,C')
            job.setFetchOptions(fieldList=['A', 'B', 'C'])
            self.assertEquals(job.getFetchOptions()['field_list'], ['A', 'B', 'C'])

            # restrict fields to 1 field
            job.setFetchOption(fieldList=['position'])
            for i, x in enumerate(job.events):
                self.assertEquals(len(x.fields), 1)
                self.assertEquals(str(x['position']), str(i))

            # restrict fields to 3 fields
            job.setFetchOption(fieldList=['_time', 'position', '_raw'])
            for i, x in enumerate(job.events):
                self.assertEquals(len(x.fields), 3)
                self.assertEquals(str(x['position']), str(i))

            job.cancel()

        def testHostPath(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag', hostPath=splunk.mergeHostPath())

            job.cancel()


        def testDispatchTimeHandling(self):

            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('search non foo bar empty')
            self.assertEqual(job.dispatchArgs.get('earliest_time'), None)
            self.assertEqual(job.dispatchArgs.get('latest_time'), None)
            job.cancel()

            job = dispatch('search non foo bar empty', earliestTime=time.struct_time((2008, 9, 26, 21, 49, 50, 4, 270, 0)))
            self.assertEqual(job.dispatchArgs.get('earliest_time'), '2008-09-26T21:49:50-0700')
            self.assertEqual(job.dispatchArgs.get('latest_time'), None)
            self.assertEqual(job.dispatchArgs.get('time_format'), util.ISO_8601_STRFTIME)
            job.cancel()

            job = dispatch('search non foo bar empty', earliestTime=1222470138.127239)
            self.assertEqual(job.dispatchArgs.get('earliest_time'), 1222470138.127239)
            self.assertEqual(job.dispatchArgs.get('time_format'), '%s')
            job.cancel()

            job = dispatch('search non foo bar empty', latestTime=1222470138.127239)
            self.assertEqual(job.dispatchArgs.get('latest_time'), 1222470138.127239)
            self.assertEqual(job.dispatchArgs.get('time_format'), '%s')
            job.cancel()

            job = dispatch('search non foo bar empty', earliestTime=1222470138.127239, latestTime=1222472317.413522)
            self.assertEqual(job.dispatchArgs.get('earliest_time'), 1222470138.127239)
            self.assertEqual(job.dispatchArgs.get('latest_time'), 1222472317.413522)
            self.assertEqual(job.dispatchArgs.get('time_format'), '%s')
            job.cancel()

            self.assertRaises(TypeError,
                dispatch,
                'search non foo bar empty',
                earliestTime=1222470138.127239,
                latestTime=time.struct_time((2008, 9, 26, 21, 49, 50, 4, 270, 0))
            )


        def testDispatchArgAsList(self):
            '''
            Test the ability for the dispatch method to auto-handle arguments
            passed in as a list; all lists are normalized by fieldListToString
            '''

            sessionKey = auth.getSessionKey('admin', 'changeme')

            s = 'search 23faef2f3 dfae9fa'
            job = dispatch(s, required_field_list=['A', 'B', 'C'], sessionKey=sessionKey)
            self.assertEquals(job.search, s)
            job.cancel()

            job = dispatch(s, required_field_list='X,Y,Z', sessionKey=sessionKey)
            self.assertEquals(job.search, s)
            job.cancel()


        def testDispatchArgNormalization(self):
            '''
            Tests the normalization of property aliases, to prevent overlap
            '''

            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = dispatch('windbag', sessionKey=sessionKey)

            # first try to set every aliased option and check that they are mapped
            job.setFetchOptions(**DEFAULT_RESULT_ARG_MAP)
            setOptions = job.getFetchOptions()
            for k in DEFAULT_RESULT_ARG_MAP:
                self.assert_(k not in setOptions)

            # now try double assigment
            job.setFetchOptions(field_list='directWay')
            job.setFetchOptions(fieldList='aliasWay')
            setOptions = job.getFetchOptions()
            self.assert_('fieldList' not in setOptions)
            self.assertEquals(setOptions['field_list'], 'aliasWay')

            # and the other way
            job.setFetchOptions(fieldList='aliasWay')
            job.setFetchOptions(field_list='directWay')
            setOptions = job.getFetchOptions()
            self.assert_('fieldList' not in setOptions)
            self.assertEquals(setOptions['field_list'], 'directWay')

            job.cancel()

        def testToJsonable(self):
            '''
            Tests the primitive serializer
            '''

            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = dispatch('windbag', sessionKey=sessionKey)
            waitForJob(job)

            # try with default time handling

            prim = job.toJsonable()
            self.assertEquals(prim['eventSearch'].strip(), 'windbag')
            self.assertEquals(prim['isDone'], True)
            self.assertEquals(prim['reportSearch'], None)

            try:
                import json
                json.dumps(prim)
            except ImportError:
                pass

            # try with unix time format

            prim = job.toJsonable(timeFormat='unix')
            self.assertEquals(prim['eventSearch'].strip(), 'windbag')
            self.assertEquals(prim['isDone'], True)
            self.assertEquals(prim['reportSearch'], None)

            try:
                import json
                json.dumps(prim)
            except ImportError:
                pass



        def testToJsonableLongRunning(self):
            '''
            Tests the primitive serializer while the job is still running
            '''

            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = dispatch('search *', sessionKey=sessionKey)

            for i in range(5):
                prim = job.toJsonable()
                self.assertNotEquals(prim['sid'], None)
                time.sleep(2)

            job.cancel()


    class SearchResultTests(unittest.TestCase):
        '''Tests covering splunkd responses to dispatch requests'''


        def testAWindbag(self):
            '''
            Generate known dummy data to check for consistency
            '''

            rowCount = 18

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag rowcount=%s' % rowCount, sessionKey=sessionKey)

            self.assert_(job.isStreaming, 'job is expected to be streaming; marked as non-streaming')
            self.assert_(not job.isFinalized, 'job is expected to not be finalized')

            for i, event in enumerate(job.events):
                self.assertEqual(int(str(event['position'])), i)
                for field in event:
                    self.assertNotEqual(event[field], None)

            self.assertEqual(job.count, rowCount)

            job.cancel()


        def testSearchInitialSetupDelay(self):
            '''
            Upon first executing a search, any of the result endpoints must return
            an HTTP 204 while it is still preparing results;  the SearchJob should
            block on access while this is still occuring and not blow up.
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('search *', sessionKey=sessionKey)

            self.assert_(job.createTime)

            events = None
            runaway = 0
            while not events and runaway < 20:
                events = job[1:5]
                if job.isDone: break
                time.sleep(.5)
                runaway += 1

            job.cancel()


        def testSearchSpanningFiles(self):
            '''
            Test the dispatcher's ability to merge results from split data files;
            see SPL-12146
            '''

            rowCount = 2000

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag rowcount=%s' % rowCount, sessionKey=sessionKey)

            for i, event in enumerate(job.events):
                self.assertEqual(int(str(event['position'])), i)

            self.assertEqual(job.count, rowCount)

            job.cancel()


        def xxtestNonStreamingBlocking(self):
            '''
            DISABLED: need to do convert windbag to streaming
            Test the iterator on non-streaming results
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag delay=3 | timechart count', sessionKey=sessionKey)

            # check that access to result row is blocked while search is still prepping
            self.assertRaises(IndexError, job.__getitem__, 1)

            # check that search is not allowing access to result item
            # before job is done; raw event access should be okay though
            while job.count < 2:
                time.sleep(.5)
            self.assertRaises(splunk.SplunkdException, job.__getitem__, 1)
            self.assert_(job.events[0])

            # check that convenience accessor on job object points to 'results'
            waitForJob(job)
            self.assertEqual(job[0]['count'], job.results[0]['count'], 'SearchJob index getter is pointed to wrong event set')

            job.cancel()



        def testTimelinePopulation(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            basetime = 1120201200.0
            interval = 1
            expectedBucketCount = 100
            localtz = util.TZInfo(-7*60, '')


            job = dispatch('windbag basetime=%s interval=%s' % (basetime, interval), sessionKey=sessionKey, status_buckets=250)

            waitForJob(job)

            self.assertEqual(len(job.timeline), len(job.timeline.buckets))
            self.assertEqual(len(job.timeline), expectedBucketCount)

            # check that the last bucket time is the same as the interval
            # specified in the search string
            self.assertEqual(
                datetime.datetime.fromtimestamp(basetime, localtz),
                job.timeline[-1].earliestTime)

            # TODO: resolve the timezone info
            firstBucketTime = datetime.datetime.fromtimestamp(basetime - interval * (expectedBucketCount - 1), localtz)
            self.assert_(job.timeline.cursorTime < firstBucketTime, 'cursorTime is not earlier than first bucket time')

            for i, x in enumerate(job.timeline):
                self.assertEqual(
                    x.earliestTime,
                    datetime.datetime.fromtimestamp(basetime - interval * (expectedBucketCount - (i + 1)), localtz))
                self.assertEquals(x.itemCount, 1)
                self.assertEquals(x.duration, datetime.timedelta(seconds=1))
                self.assertTrue(x.isComplete, 'bucket is not finalized')


            self.assertEqual(job.timeline.isComplete, True)

            job.cancel()


        def testSummary(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            basetime = 1205967600
            job = dispatch('windbag basetime=%s interval=1' % basetime, sessionKey=sessionKey, status_buckets=1)

            waitForJob(job)

            self.assertEqual(job.summary.latestTime, None)
            self.assertEqual(job.summary.earliestTime, None)
            self.assertEqual(job.summary.count, 100)

            for fieldName in job.summary.fields:
                self.assertEqual(job.summary.fields[fieldName]['isExact'], True)

            f = job.summary.fields

            self.assertEquals(f['position']['count'], 100)
            self.assertEquals(f['position']['distinctCount'], 100)
            self.assertEquals(f['position']['numericCount'], 100)
            self.assertEquals(f['position']['min'], 0)
            self.assertEquals(f['position']['max'], 99)

            self.assertEquals(f['source']['modes'][0]['value'], 'SpaceOdyssey')
            self.assertEquals(f['source']['modes'][0]['count'], 100)
            self.assertEquals(f['source']['modes'][0]['isExact'], True)

            job.cancel()

            # summary fetch options
            job = dispatch('windbag', sessionKey=sessionKey, status_buckets=1)
            waitForJob(job)
            job.setFetchOption(summary=dict(search="fancy"))
            self.assertEquals(len(job.summary.fields), 1)
            job.cancel()

            job = dispatch('windbag', sessionKey=sessionKey, status_buckets=1, required_field_list='*')
            waitForJob(job)
            job.setFetchOption(summary=dict(min_freq=".99"))
            self.assertEquals(len(job.summary.fields), 10)
            job.cancel()

            job = dispatch('windbag', sessionKey=sessionKey, status_buckets=1, required_field_list='*')
            waitForJob(job)
            job.setFetchOption(summary=dict(min_freq=".5", search="source"))
            self.assertEquals(len(job.summary.fields), 2)
            job.cancel()

            job = dispatch('windbag', sessionKey=sessionKey, status_buckets=0, required_field_list='*')
            waitForJob(job)
            job.setFetchOption(summary=dict(min_freq=".5", search="source"))
            self.assertEquals(len(job.summary.fields), 0)
            job.cancel()



        def XXtestMaxLines(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            job = dispatch('windbag multiline=true fieldcount=100', sessionKey=sessionKey)

            waitForJob(job)

            job.setFetchOption(maxLines=12)

            # the windbag operator has a bunch of default fields that exist; we pad by 4
            self.assertEquals(job.events[0].raw.strip().count('\n') + 1, 16)

            job.cancel()


        def testFeedEvent(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            rowcount = 200

            job = dispatch('| windbag rowcount=%s | fields *' % rowcount, sessionKey=sessionKey, status_buckets=1)

            waitForJob(job)

            # check that XML is valid
            feed = job.getFeed('events', outputMode='xml')
            et.fromstring(feed)

            # now get JSON format so we can do quick parse
            feed = job.getFeed(mode='events', outputMode='json', count=rowcount)
            feed = json.loads(feed)
            feedResults = feed['results']

            self.assertEquals(len(feedResults), rowcount)

            for i, x in enumerate(feedResults):
                self.assertEquals(int(str(x['position'])), i)

            #
            # check that passed params are recognized
            #
            offset = 12
            count = 5
            job.setFetchOption(count=count, offset=offset)
            feed = job.getFeed(mode='events', outputMode='json')
            feed = json.loads(feed)
            feedResults = feed['results']

            self.assertEquals(len(feedResults), count)

            for i in range(offset, offset + count - 1):
                self.assertEquals(int(feedResults[i - offset]['position']), i)

            #
            # check that event and results feeds are the same
            #
            job.setFetchOption(count=5, offset=0, outputMode='xml')
            self.assertEqual(job.getFeed('events'), job.getFeed('results'))

            job.cancel()


        def testFeedCount(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            rowcount = 228

            job = dispatch('windbag rowcount=%s' % rowcount, sessionKey=sessionKey)

            waitForJob(job)

            job.setFetchOption(outputMode='json')

            # check that the default count=100
            feed = job.getFeed('results')
            feed = json.loads(feed)
            feedResults = feed['results']
            self.assertEquals(len(feedResults), 100)

            # check that count is respected
            job.setFetchOption(count=124)
            feed = job.getFeed('results')
            feed = json.loads(feed)
            feedResults = feed['results']
            self.assertEquals(len(feedResults), 124)

            # check that count=0 returns all
            job.setFetchOption(count=0)
            feed = job.getFeed('results')
            feed = json.loads(feed)
            feedResults = feed['results']
            self.assertEquals(len(feedResults), rowcount)

            job.cancel()

        def testSearchAll(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            data = searchAll('windbag rowcount=100', status_buckets=1)

            for i, x in enumerate(data):
                self.assertEquals(int(str(x['position'])), i)


        def testSearchOne(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            data = searchOne('windbag rowcount=100', status_buckets=1)
            self.assert_(isinstance(data, Result))

            #self.assertEqual(str(data), expectedResult)


        def testSearchCount(self):

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            rowcount = 321
            data = searchCount('windbag rowcount=%s' % rowcount)

            self.assertEqual(data, rowcount)


        def XXXtestShowEmptyFields(self):
            '''
            disabling this test: the empty field request behavior that is
            expected in this test has not been true for a while, as the backend
            will only display fields that exist somewhere in the dataset;
            am unable to find the SPL trail
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # first check if empty fields is on (by default)
            job = dispatch('windbag rowcount=10', sessionKey=sessionKey, status_buckets=1, required_field_list='*')

            waitForJob(job)

            # check that non-existent requested fields show up
            job.setFetchOption(field_list=['host', 'source', 'sourcetype', 'cola'])
            self.assert_(job.getFetchOptions()['show_empty_fields'])
            self.assert_('host' in job.events.fieldOrder, 'host field is missing in field order')
            self.assert_('source' in job.events.fieldOrder, 'source field is missing in field order')
            self.assert_('sourcetype' in job.events.fieldOrder, 'sourcetype field is missing in field order')
            self.assert_('cola' in job.events.fieldOrder, 'cola field is missing in field order')
            self.assert_('lolcat' not in job.events.fieldOrder, 'unexpected lolcat field is present in field order')

            # now check that the restriction applies
            job.setFetchOption(show_empty_fields=False)
            self.assert_(not job.getFetchOptions()['show_empty_fields'])

            job.setFetchOption(field_list=['host'])
            self.assert_('host' in job.events.fieldOrder, 'host field is missing in field order')
            self.assert_('source' not in job.events.fieldOrder, 'source field is errantly in field order')
            self.assert_('sourcetype' not in job.events.fieldOrder, 'sourcetype field is errantly in field order')
            self.assert_('cola' not in job.events.fieldOrder, 'cola field is missing in field order')

            # check that non-event feeds always parrot back what was passed in,
            # regardless of what summary says
            job.setFetchOption(field_list=['host', 'blue', 'red', 'green'], show_empty_fields=False)
            self.assert_('host' in job.results.fieldOrder, 'host field is missing in field order')
            self.assert_('blue' in job.results.fieldOrder, 'blue field is missing in field order')
            self.assert_('red' in job.results.fieldOrder, 'red field is missing in field order')
            self.assert_('green' in job.results.fieldOrder, 'green field is missing in field order')


            job.cancel()


        def testResultTimeEpoch(self):
            '''
            Check that the Result() object time property and methods work
            properly when output_time_format=%s.%Q
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # first check if empty fields is on (by default)
            job = dispatch('windbag rowcount=100 interval=2220', sessionKey=sessionKey)

            waitForJob(job)

            job.setFetchOption(output_time_format='%s.%Q')

            for result in job.events:

                self.assertEquals(
                    result.time,
                    result.fields['_time'][0].value,
                    'check that time property is identical to raw time field')

                self.assertEquals(
                    result.time,
                    str(result.toEpochTime()),
                    'check that toEpochTime() is idempotent')

                self.assertEquals(
                    datetime.datetime.fromtimestamp(float(result.time), util.TZInfo()),
                    result.toDateTime(),
                    'check that toDateTime() matches expected datetime object casting (into local TZ)'
                )

            job.cancel()


        def testResultTimeDatetime(self):
            '''
            Check that the Result() object time property and methods work
            properly when output_time_format=ISO-8601
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # first check if empty fields is on (by default)
            job = dispatch('windbag rowcount=100 interval=2220', sessionKey=sessionKey)

            waitForJob(job)

            job.setFetchOption(output_time_format=util.ISO_8601_STRFTIME)

            for result in job.events:

                self.assertEquals(
                    result.time,
                    result.fields['_time'][0].value,
                    'check that time property is identical to raw time field')

                self.assertEquals(
                    util.parseISO(result.time),
                    result.toDateTime(),
                    'check that toDateTime() returns expected datetime object'
                )

                self.assertEquals(
                    util.dt2epoch(util.parseISO(result.time)),
                    result.toEpochTime(),
                    'check that toEpochTime() returns expected decimal.Decimal object'
                )

                self.assertEquals(
                    result.time,
                    util.getISOTime(result.toDateTime()),
                    'check that ISO time string survives round trip'
                )

            job.cancel()


        def testResultTimeNegative(self):
            '''
            Check that the Result() object time property and methods work
            properly when output_time_format is not recognized as either
            ISO or epoch
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # first check if empty fields is on (by default)
            job = dispatch('windbag rowcount=5 interval=2220', sessionKey=sessionKey)
            waitForJob(job)
            job.setFetchOption(output_time_format='%m-%y-%d')

            for result in job.events:

                self.assertEquals(
                    result.time,
                    result.fields['_time'][0].value,
                    'check that time property is identical to raw time field')

                self.assertRaises(ValueError, result.toEpochTime)
                self.assertRaises(ValueError, result.toDateTime)

            job.cancel()


        def testResultTimeNull(self):
            '''
            Check that the Result() object time property and methods return
            None if there is no time
            '''

            # get session key
            sessionKey = auth.getSessionKey('admin', 'changeme')

            # first check if empty fields is on (by default)
            job = dispatch('windbag rowcount=5 interval=2220 | fields - _time', sessionKey=sessionKey)
            waitForJob(job)
            job.setFetchOption(output_time_format='%m-%y-%d')

            for result in job.events:

                self.assertEquals(result.time, None, 'check that time property is null')
                self.assertEquals(result.toEpochTime(), None, 'check that toEpochTime returns nothing')
                self.assertEquals(result.toDateTime(), None, 'check that toDateTime returns nothing')

            job.cancel()


    # ----------------------------------
    class TagTests(unittest.TestCase):

        def setUp(self):

           self.xmlString = """<results>
                                  <meta><fieldOrder><field>xyz</field></fieldOrder></meta>
                                  <result offset="0">
                                     <field k="key1">
                                        <value h="1">
                                           <text>some test data</text>
                                        </value>
                                     </field>
                                     <field k="key2">
                                        <value>
                                           <text>DB2</text>
                                           <tag>tag1</tag>
                                           <tag>tag2</tag>
                                           <tag>tag3</tag>
                                        </value>
                                     </field>
                                     <field k="key3">
                                        <value h="1">
                                           <text>test data3</text>
                                           <tag>tag4</tag>
                                           <tag>tag5</tag>
                                        </value>

                                         <value>
                                            <text>test data4</text>
                                            <tag>tag6</tag>
                                            <tag>tag7</tag>
                                         </value>
                                      </field>
                                     <field k="_raw">
                                        <v xml:space="preserve" trunc="0">
                                            2008-12-22-14.08.15.320000-420 I27561H327         LEVEL: Event
                                            PID     : 2120                 TID  : 4760        PROC : db2fmp.exe
                                            INSTANCE: DB2                  NODE : 000
                                            FUNCTION: DB2 UDB, Automatic Table Maintenance, db2HmonEvalStats, probe:100
                                            START   : Automatic Runstats: evaluation has started on database TRADEDB
                                        </v>
                                     </field>
                                     <field k="_time">
                                        <value>
                                           <text>2008-12-22T14:08:15.320-08:00</text>
                                        </value>
                                     </field>
                                   </result>
                                </results>"""

           #No need of making rest calls etc here. Create a dummy ResultSet obj in order to get the parsed result
           #These tests are only related to tags etc so we want to test if our population of the data structures happened correctly
           self._dummyResultSetObj = ResultSet('', '')._parseResultSet(self.xmlString)[0]

    # ------------------------------------
    class Tags_SingleValNoTag(TagTests):

        def setUp(self):
           super(Tags_SingleValNoTag, self).setUp()
           self.result_field_key1 = self._dummyResultSetObj['key1']

        #######################################
        # tests related to ResultField object #
        #######################################

        def testResultField_key1(self):
           self.assertTrue(isinstance(self.result_field_key1, ResultField), 'ResultField object did not evaluate correctly (key1)')

        def testResultFieldAsString_key1(self):
           self.assertEqual(str(self.result_field_key1), 'some test data', 'string evaluation of ResultField object failed (key1)')

        def testResultFieldLength_key1(self):
           self.assertEqual(len(self.result_field_key1), 1, 'len of ResultField object did not evaluate correctly (key1)')

        ############################################
        # tests related to ResultFieldValue object #
        ############################################

        def testResultFieldValue_key1(self):
           self.assertTrue(isinstance(self.result_field_key1[0], ResultFieldValue), 'ResultFieldValue object did not evaluate correctly (key1)')
           self.assertTrue(self.result_field_key1[0].isHighlighted, 'ResultFieldValue isHighlighted attribute did not evaluate correctly')

        def testResultFieldValueText_key1(self):
           self.assertEqual(self.result_field_key1[0].value, 'some test data', 'attribute "value" of ResultFieldValue object did not evaluate correctly (key1)')

        def testResultFieldValueAsString_key1(self):
           self.assertEqual(str(self.result_field_key1[0]), 'some test data', 'string evaluation of ResultFieldValue object failed (key1)')

        def testResultFieldValueTags_key1(self):
           self.assertEqual(self.result_field_key1[0].tags, [], 'attribute "tags" of ResultFieldValue object did not evaluate correctly (key1)')

        def testResultFieldValueTagsLength_key1(self):
           self.assertEqual(len(self.result_field_key1[0].tags), 0, 'len of ResultField object tags did not evaluate correctly (key1)')

        def testResultFieldValueLength_key1(self):
           self.assertRaises(Exception, len, self.result_field_key1[0])


    # -------------------------------------
    class Tags_SingleValWithTag(TagTests):

        def setUp(self):
           super(Tags_SingleValWithTag, self).setUp()
           self.result_field_key2 = self._dummyResultSetObj['key2']

        #######################################
        # tests related to ResultField object #
        #######################################

        def testResultField_key2(self):
           self.assertTrue(isinstance(self.result_field_key2, ResultField), 'ResultField object did not evaluate correctly (key2)')

        def testResultFieldAsString_key2(self):
           self.assertEqual(str(self.result_field_key2), 'DB2', 'string evaluation of ResultField object failed (key2)')

        def testResultFieldLength_key2(self):
           self.assertEqual(len(self.result_field_key2), 1, 'len of ResultField object did not evaluate correctly (key2)')

        ############################################
        # tests related to ResultFieldValue object #
        ############################################

        def testResultFieldValue_key2(self):
           self.assertTrue(isinstance(self.result_field_key2[0], ResultFieldValue), 'ResultFieldValue object did not evaluate correctly (key2)')
           self.assertFalse(self.result_field_key2[0].isHighlighted, 'ResultFieldValue isHighlighted attribute did not evaluate correctly')

        def testResultFieldValueText_key2(self):
           self.assertEqual(self.result_field_key2[0].value, 'DB2', 'attribute "value" of ResultFieldValue object did not evaluate correctly (key2)')

        def testResultFieldValueAsString_key2(self):
           self.assertEqual(str(self.result_field_key2[0]), 'DB2', 'string evaluation of ResultFieldValue object failed (key2)')

        def testResultFieldValueTags_key2(self):
           self.assertEqual(self.result_field_key2[0].tags, ['tag1', 'tag2', 'tag3'], 'attribute "tags" of ResultFieldValue object did not evaluate correctly (key2)')

        def testResultFieldValueTagsLength_key2(self):
           self.assertEqual(len(self.result_field_key2[0].tags), 3, 'len of ResultField object tags did not evaluate correctly (key2)')

        def testResultFieldValueLength_key2(self):
           self.assertRaises(Exception, len, self.result_field_key2[0])

    # ------------------------------------
    class Tags_MultiValWithTag(TagTests):

        def setUp(self):
           super(Tags_MultiValWithTag, self).setUp()
           self.result_field_key3 = self._dummyResultSetObj['key3']

        #######################################
        # tests related to ResultField object #
        #######################################

        def testResultField_key3(self):
           self.assertTrue(isinstance(self.result_field_key3, ResultField), 'ResultField object did not evaluate correctly (key3)')

        def testResultFieldAsString_key3(self):
           self.assertEqual(str(self.result_field_key3), 'test data3,test data4', 'string evaluation of ResultField object failed (key3)')

        def testResultFieldLength_key3(self):
           self.assertEqual(len(self.result_field_key3), 2, 'len of ResultField object did not evaluate correctly (key3)')

        ############################################
        # tests related to ResultFieldValue object #
        ############################################

        def testResultFieldValue_key3(self):
           self.assertTrue(isinstance(self.result_field_key3[0], ResultFieldValue), 'ResultFieldValue object did not evaluate correctly (key3)')
           self.assertTrue(self.result_field_key3[0].isHighlighted, 'ResultFieldValue isHighlighted attribute did not evaluate correctly')

        def testResultFieldValueText_key3(self):
           self.assertEqual(self.result_field_key3[0].value, 'test data3', 'attribute "value" of ResultFieldValue object did not evaluate correctly (key3)')

        def testResultFieldValueAsString_key3(self):
           self.assertEqual(str(self.result_field_key3[0]), 'test data3', 'string evaluation of ResultFieldValue object failed (key3)')

        def testResultFieldValueTags_key3(self):
           self.assertEqual(self.result_field_key3[0].tags, ['tag4', 'tag5'], 'attribute "tags" of ResultFieldValue object did not evaluate correctly (key3)')

        def testResultFieldValueTagsLength_key3(self):
           self.assertEqual(len(self.result_field_key3[0].tags), 2, 'len of ResultField object tags did not evaluate correctly (key3)')

        def testResultFieldValueLength_key3(self):
           self.assertRaises(Exception, len, self.result_field_key3[0])

        def testResultFieldValueItem2_key3(self):
           self.assertTrue(isinstance(self.result_field_key3[1], ResultFieldValue), 'ResultFieldValue object did not evaluate correctly (key3 item2)')
           self.assertFalse(self.result_field_key3[1].isHighlighted, 'ResultFieldValue isHighlighted attribute did not evaluate correctly')

        def testResultFieldValueTextItem2_key3(self):
           self.assertEqual(self.result_field_key3[1].value, 'test data4', 'attribute "value" of ResultFieldValue object did not evaluate correctly (key3 item2)')

        def testResultFieldValueAsStringItem2_key3(self):
           self.assertEqual(str(self.result_field_key3[1]), 'test data4', 'string evaluation of ResultFieldValue object failed (key3 item2)')

        def testResultFieldValueTagsItem2_key3(self):
           self.assertEqual(self.result_field_key3[1].tags, ['tag6', 'tag7'], 'attribute "tags" of ResultFieldValue object did not evaluate correctly (key3 item2)')

        def testResultFieldValueTagsLengthItem2_key3(self):
           self.assertEqual(len(self.result_field_key3[1].tags), 2, 'len of ResultField object tags did not evaluate correctly (key3 item2)')




    class SearchMessaging(unittest.TestCase):
        '''
        Tests the job messaging services
        '''

        def setUp(self):
            self.sessionKey = auth.getSessionKey('admin', 'changeme')


        def testInvalidArgument(self):
            '''
            Execs a search that has events, but followed by a command that has invalid args
            '''

            j = dispatch('windbag | timechart bad_arg', sessionKey=self.sessionKey)
            waitForJob(j)
            self.assertEquals(j.isFailed, True)

            # job object should raise immediately if data iterator is requested
            try:
                for event in j:
                    self.fail('SearchJob.__iter__ did not raise exception')
                    break
            except:
                self.assert_(True, 'SearchJob.__iter__ this assert should never fail')

            # also check slice accesses
            try:
                j[0]
                self.fail('SearchJob.__getitem__ did not raise exception')
            except:
                self.assert_(True, 'SearchJob.__getitem__ this assert should never fail')

            # also check slice accesses
            try:
                j.results[0]
                self.fail('SearchJob.__getitem__ did not raise exception')
            except:
                self.assert_(True, 'SearchJob.__getitem__ this assert should never fail')


        def testInvalidArgumentWithSummaryTimeline(self):
            '''
            Execs a search that has events, but followed by a command that has invalid args;
            tests the timeline and summary objects
            '''

            j = dispatch('windbag | timechart bad_arg', sessionKey=self.sessionKey)
            waitForJob(j)
            self.assertEquals(j.isFailed, True)

            try:
                j.timeline
                self.fail('SearchJob.timeline did not raise exception')
            except:
                self.assert_(True, 'SearchJob.timeline this assert should never fail')

            try:
                j.summary
                self.fail('SearchJob.summary did not raise exception')
            except:
                self.assert_(True, 'SearchJob.summary this assert should never fail')



    class SearchJobIterator(unittest.TestCase):
        '''
        Tests the automatic and explicit iterator behavior around:
        -- historical events
        -- historical transforming
        -- realtime events
        -- realtime transforming
        '''

        def setUp(self):
            self.sessionKey = auth.getSessionKey('admin', 'changeme')
            self.j = None

        def tearDown(self):
            try:
                self.j.cancel()
            except:
                pass

        def xxAutoEventSelectionRunning(self):
            '''
            disable this test -- succeeds or fails based on speed of job execution
            getAutoAssetType() will return 'events' or 'results' for this search depending on whether or not the
            job is done when the assert is executed
            '''
            self.j = dispatch('search index=_internal', status_buckets=500, rf='*')

            # wait for up to 30 seconds for data to start flowing
            for i in range(30):
                if self.j.eventCount > 0:
                    self.assertEquals(self.j.getAutoAssetType(), 'events')
                    break
                time.sleep(.2)

        def testAutoResultSelectionDone(self):
            self.j = dispatch('search index=_internal | head 10', status_buckets=1)
            waitForJob(self.j)
            self.assertEquals(self.j.getAutoAssetType(), 'results')

        def testAutoResultSelectionRunning(self):
            self.j = dispatch('search index=_internal | timechart count', status_buckets=1)
            time.sleep(2)
            self.assertEquals(self.j.getAutoAssetType(), 'results')

        def testAutoTransformingResultSelectionDone(self):
            self.j = dispatch('search index=_internal | head 100 | timechart count', status_buckets=1)
            waitForJob(self.j)
            self.assertEquals(self.j.getAutoAssetType(), 'results')

        def testAutoResultSelectionRealtimeEvents(self):
            self.j = dispatch('search index=_internal', status_buckets=1, earliest_time='rt-1m', latest_time='rt')
            time.sleep(2)
            self.assertEquals(self.j.getAutoAssetType(), 'results_preview')

        def testAutoResultSelectionRealtimeReport(self):
            self.j = dispatch('search index=_internal | timechart count', status_buckets=1, earliest_time='rt-1m', latest_time='rt')
            time.sleep(2)
            self.assertEquals(self.j.getAutoAssetType(), 'results_preview')

        def XXtestIteratorStreaming(self):
            '''
            TODO:

            This test is current disabled because it fails constantly in the
            test automation framework.  Proper fix is to introduce a search
            command that props open a search job for a predetermined time
            interval.
            '''
            self.j = dispatch('search index=_*', status_buckets=300)

            time.sleep(.2)
            self.assertEquals(self.j.eventIsStreaming, True)

            # check that the iterator returns while job is still running
            for i, row in enumerate(self.j.events):
                if self.j.isDone:
                    self.fail('job completed before we could even get one event; search is running too fast')
                else:
                    break
            else:
                self.fail('SearchJob iterator failed to return streaming results; got=%s' % i)

        def testIteratorNonStreaming(self):
            self.j = dispatch('search index=_internal | sort + _time', status_buckets=1)

            time.sleep(1)
            self.j.refresh()
            self.assertEquals(self.j.eventIsStreaming, False)

            # TODO: check that the iterator is blocked until job is done



    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(SearchObjectTests))
    suites.append(loader.loadTestsFromTestCase(JobControlTests))
    suites.append(loader.loadTestsFromTestCase(SearchResultTests))
    suites.append(loader.loadTestsFromTestCase(Tags_SingleValNoTag))
    suites.append(loader.loadTestsFromTestCase(Tags_SingleValWithTag))
    suites.append(loader.loadTestsFromTestCase(Tags_MultiValWithTag))
    suites.append(loader.loadTestsFromTestCase(SearchMessaging))
    suites.append(loader.loadTestsFromTestCase(SearchJobIterator))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
