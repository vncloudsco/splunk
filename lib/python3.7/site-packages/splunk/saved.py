# coding=UTF-8

from __future__ import absolute_import

from builtins import range
import splunk
from splunk import auth, entity, rest, util

from future.moves.urllib import parse as urllib_parse

import splunk.search   # we cant import it more simply as 'search' because it collides with several 'search' arguments in these functions.
import lxml.etree as et
import logging
import splunk.util
logger = logging.getLogger('splunk.saved')


# Saved Search constants
SAVED_SEARCHES_ENDPOINT_ENTITY_PATH = 'saved/searches'
SAVED_SEARCHES_HISTORY_ENTITY_PATH = 'saved/searches/%s/history'
SAVED_SEARCH_ESCAPE_CHR = u'"'

SAVED_SEARCH_DISPATCH_ARG_MAP = {
    'ttl': 'dispatch.ttl',
    'buckets': 'dispatch.buckets',
    'maxCount': 'dispatch.max_count',
    'maxTime': 'dispatch.max_time',
    'lookups': 'dispatch.lookups',
    'spawnProcess': 'dispatch.spawn_process',
    'timeFormat': 'dispatch.time_format',
    'earliestTime': 'dispatch.earliest_time',
    'latestTime': 'dispatch.latest_time'
}


# ////////////////////////////////////////////////////////////////////////////
#  Saved Search functions
# ////////////////////////////////////////////////////////////////////////////


def dispatchSavedSearch(savedSearchName, sessionKey=None, namespace=None, owner=None, hostPath=None, now=0, triggerActions=0, **kwargs):
    """Initiates a new job based on a saved search."""

    uri = entity.buildEndpoint(['saved', 'searches', savedSearchName, 'dispatch'], namespace=namespace, owner=owner)
    if hostPath:
        uri = splunk.mergeHostPath(hostPath) + uri
        
    args = {
        'now': now,
        'trigger_actions' : triggerActions
    }
    
    for key, val in kwargs.items():
        if key in SAVED_SEARCH_DISPATCH_ARG_MAP:
            args[SAVED_SEARCH_DISPATCH_ARG_MAP[key]] = val
        # Pass through for dispatch.* formated kwargs
        elif key.startswith('dispatch.'):
            args[key] = val

    serverResponse, serverContent = rest.simpleRequest(uri, postargs=args, sessionKey=sessionKey)
    root = et.fromstring(serverContent)

    # normal messages from splunkd are propogated via SplunkdException;
    if not 201 == serverResponse.status:

        extractedMessages = rest.extractMessages(root)
        for msg in extractedMessages:
            raise splunk.SearchException(msg['text'])
    
    # get the search ID
    sid = root.findtext('sid').strip()

    # instantiate result object
    return splunk.search.SearchJob(sid, hostPath, sessionKey, namespace, owner)


def createSavedSearch(search, label, sessionKey=None, namespace=None, owner=None, earliestTime=None, latestTime=None, hostPath=None):
    '''Save a search given a search string and a search label.'''

    output = entity.Entity(SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, label, namespace=namespace, owner=owner)
    
    # Manually set the properties...
    output['search'] = search
    output['name'] = label
    output['dispatch.earliest_time'] = earliestTime
    output['dispatch.latest_time'] = latestTime
    if hostPath:
        output.hostPath = hostPath
    entity.setEntity(output, sessionKey=sessionKey)
    return output


def getSavedSearchWithTimes(label, et, lt, namespace=None, sessionKey=None, owner=None, hostPath=None):
    '''Retrieve a list of UTC times that a saved searches was schedule to run.'''
    return entity.getEntity(SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, label, uri="/servicesNS/"+owner+"/"+namespace+"/saved/searches/"+urllib_parse.quote_plus(label)+"/scheduled_times", earliest_time=et, latest_time=lt, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)

def listSavedSearches(namespace=None, sessionKey=None, owner=None, hostPath=None, count=None):
    '''Retrieve a list of saved searches.'''
    return entity.getEntities(SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath, count=count)


def getSavedSearch(label, namespace=None, sessionKey=None, owner=None, hostPath=None, uri=None):
    '''Retrieve a single saved search.'''
    return entity.getEntity(SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, label, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath, uri=uri)


def getSavedSearchHistory(label, namespace=None, sessionKey=None, ignoreExpired=True, owner=None, sortKey=None, sortDir='desc', ignoreRunning=False, search=None, hostPath=None, uri=None):
    '''
    Retrieve the history of a saved search.

    ignoreExpired: {True|False} When True only return saved searches that have a TTL > 0 or they have been saved by the user.
                                When False return everything, including searches with a TTL >= 0 regardless of the job's saved status.
    '''
    #SPL-35662 done RT searches are alert artifacts which should be of no use to UI,  
    #          dashboards should always reference running rt searches
    search   = (search if search != None else '') + " NOT (isRealTimeSearch=1 AND isDone=1)" 
    entities = entity.getEntities(['saved', 'searches', label, 'history'], namespace=namespace, owner=owner, sessionKey=sessionKey, search=search, hostPath=hostPath, count=0, uri=uri)

    if ignoreExpired or ignoreRunning: 
        for sid, job in entities.items():
            if ignoreExpired \
            and splunk.search.normalizeJobPropertyValue('ttl', job.get('ttl')) <= 0 \
            and not splunk.search.normalizeJobPropertyValue('isSaved', job.get('isSaved')):
                del entities[sid]
                continue
            # real time searches are never done so no need to ignore running
            isRTSearch = splunk.search.normalizeJobPropertyValue('isRealTimeSearch', job.get('isRealTimeSearch'))
            isDone     = splunk.search.normalizeJobPropertyValue('isDone', job.get('isDone'))
            if ignoreRunning and not isDone and not isRTSearch:
                del entities[sid]

    if sortKey:
        reverse = True
        if sortDir == 'asc':
            reverse = False
        try:
            entities = sorted(entities.items(), key=lambda x: x[1].__dict__[sortKey], reverse=reverse)
        except KeyError as e:
            logger.warn("Attempted to sort on a key (%s) from a saved search's history that doesn't exist" % sortKey)
    
    return util.OrderedDict(entities)

def getSavedSearchJobs(label, namespace=None, owner=None, ignoreExpired=True, ignoreRunning=False, sortKey='createTime', sortDir='desc', sessionKey=None, hostPath=None, **kw):
    '''Retrieve the saved search's history as search.SearchJob objects.'''

    jobs = []
    history = getSavedSearchHistory(label, namespace=namespace, owner=owner, ignoreExpired=ignoreExpired, ignoreRunning=ignoreRunning, sortKey=sortKey, sortDir=sortDir, sessionKey=sessionKey, hostPath=hostPath)
    for sid in history:
        jobs.append(splunk.search.getJob(sid, hostPath=hostPath, sessionKey=sessionKey))
    return jobs
    

def getJobForSavedSearch(label, useHistory=None, namespace=None, sessionKey=None, ignoreExpired=True, owner=None, ignoreRunning=True, sortKey='createTime', sortDir='desc', search=None, hostPath=None, **kw):
    '''
    Retrieve the last job run for a saved search.

    == WARNING ==
    This is meant to be a convenience method for accessing jobs from saved searches that
    are typically run by the splunkd scheduler.  As such dispatching a job from a saved search
    and then attempting to immediately call getJobForSavedSearch with the param
    ignoreRunning == True will result in a second job being dispatched.
    == / WARNING ==

    useHistory dictates how getJobForSavedSearch attempts to fetch a job.
    useHistory=None implies that if the saved search has a history of jobs relevant to
        the saved search, it will return the last run saved search. If no jobs can be
        found a new one will be dispatched and returned.
    useHistory=True implies that the last run job for the saved search will be returned.
        If no jobs exist None will be returned instead.
    useHistory=False is effectively the same as calling dispatchSavedSearch(label) in that
        it does not check for a previously run job, and instead forces a new job to be
        created and returned.  This option is left for convenience.
    '''
    job = None
    useHistory = util.normalizeBoolean(useHistory)
    if isinstance(useHistory, splunk.util.string_type):
        #verified while fixing SPL-47422
        #pylint: disable=E1103
        if useHistory.lower() in ('none', 'auto'):
            useHistory = None
        else:
            raise ValueError('Invalid option passed for useHistory: %s' % useHistory)

    logger.debug('getJobForSavedSearch - label=%s namespace=%s owner=%s' % (label, namespace, owner))
    
    # Attempt to get the saved search history
    if useHistory == None or useHistory == True:
        history = getSavedSearchHistory(label, namespace=namespace, sessionKey=sessionKey, ignoreExpired=ignoreExpired, owner=owner, ignoreRunning=ignoreRunning, sortKey=sortKey, sortDir=sortDir, search=search, hostPath=hostPath, uri=kw.get('historyURI'))
        if len(history) > 0:
            job = splunk.search.getJob(list(history.keys())[0], hostPath=hostPath, sessionKey=sessionKey)
            logger.debug('getJobForSavedSearch - found job artifact sid=%s' % job.id)

    # Dispatch a new search if there is no history for the search
    if (useHistory == False) or (useHistory == None and job == None):
        logger.debug('getJobForSavedSearch - no artifact found; dispatching new job')
        job = dispatchSavedSearch(label, sessionKey=sessionKey, namespace=namespace, owner=owner, hostPath=hostPath, **kw)

    # If the user specified useHistory = yes and no history was found, this may return None
    return job


def deleteSavedSearch(label, namespace=None, sessionKey=None, owner=None, hostPath=None):
    '''Delete a saved search.'''
    return entity.deleteEntity(SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, label, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)


def getSavedSearchFromSID(sid, sessionKey=None, hostPath=None):
    '''
    Takes a search job id and attempts to find the associated saved search
    object, if set.  Returns a splunk.entity.Entity() object if found, None
    otherwise.
    '''

    job = splunk.search.getJob(sid, sessionKey=sessionKey, hostPath=hostPath)
    
    # the eai key contains a : which makes python accessors unhappy; use alt means
    jobProps = job.toJsonable()
    namespace = jobProps['eai:acl']['app']
    owner = jobProps['eai:acl']['owner']
    
    if job.isSavedSearch and len(job.label) > 0:
        
        # first try to fetch saved search from explicit user container
        try:
            return getSavedSearch(job.label, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)
        except:
            pass
            
        # if fail, try from shared context
        try:
            return getSavedSearch(job.label, namespace=namespace, owner=entity.EMPTY_OWNER_NAME, sessionKey=sessionKey, hostPath=hostPath)
        except splunk.ResourceNotFound:
            pass
        # else raise any other exception

    return None

def savedSearchJSONIsAlert(savedSearchJSON):
    content = savedSearchJSON['entry'][0]['content']
    is_scheduled = util.normalizeBoolean(content['is_scheduled'])
    alert_type   = content['alert_type']
    alert_track  = util.normalizeBoolean(content['alert.track'])
    actions      = util.normalizeBoolean(content.get('actions'))
    isRealtime   = content['dispatch.earliest_time'].startswith('rt') and content['dispatch.latest_time'].startswith('rt')

    return is_scheduled and ((alert_type != 'always') or alert_track or (isRealtime and actions))

# ////////////////////////////////////////////////////////////////////////////
# Test routines        
# ////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':

    import unittest
    import time

    TEST_NAMESPACE = splunk.getDefault('namespace')
    TEST_OWNER = 'admin'


    class SavedSearchTests(unittest.TestCase):

        def assertGreaterThan(self, greaterThan, lessThan):
            self.assert_(greaterThan > lessThan)


        def assertLessThan(self, lessThan, greaterThan):
            self.assert_(greaterThan > lessThan)


        def setupSavedSearchTest(self):
            sessionKey = auth.getSessionKey('admin', 'changeme')
            label = '12349876 foobar'
            searchString = 'error sourcetype="something" host="nothing"'
            # Ensure that saved search 'label' doesn't already exist
            try:
                newSavedSearch = createSavedSearch(searchString, label, namespace=splunk.getDefault('namespace'), sessionKey=sessionKey)
                history = getSavedSearchHistory(label)
                for job_id in history:
                    splunk.search.getJob(job_id).cancel()
            except splunk.RESTException as e:
                deleteSavedSearch(label, namespace=splunk.getDefault('namespace'))
                newSavedSearch = createSavedSearch(searchString, label, namespace=splunk.getDefault('namespace'), sessionKey=sessionKey)

            return (sessionKey, label, searchString, newSavedSearch)


        def setupSavedSearchWithNamespaceOwnerTest(self, savedSearchName=None, earliestTime=None, latestTime=None, searchString=None):
            sessionKey = auth.getSessionKey('admin', 'changeme')

            time.sleep(1)

            label = u'%s %s foobar'
            if savedSearchName == None or not isinstance(savedSearchName, splunk.util.string_type):
                label = label % (TEST_NAMESPACE, TEST_OWNER)
            else:
                label = savedSearchName

            searchString = searchString or 'error sourcetype="something" host="nothing"'

            def gen_savedSearch():
                return createSavedSearch(searchString, label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, sessionKey=sessionKey, earliestTime=earliestTime, latestTime=latestTime)

            # Ensure that saved search 'label' doesn't already exist
            try:
                newSavedSearch = gen_savedSearch()
                history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
                for job_id in history:
                    splunk.search.getJob(job_id).cancel()
            except splunk.RESTException as e:
                deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
                newSavedSearch = gen_savedSearch()

            return (sessionKey, label, searchString, newSavedSearch)

        
        def XXtestSavedSearchHistoryIgnoreRunning(self):
            '''
            TODO:

            Disabling because test fails constantly in test automation.  Proper
            solution is to write search command to prop open a running search
            for a specified period.
            
            Tests ignoreRunning option of the getSavedSearchHistory method.
            '''
            search_str = 'search index=_*'
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest(
                searchString=search_str
            )
            
            # Dispatch a long running search
            job = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            job.pause()

            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=True)
            self.assertEquals(len(history), 0, 'failed to have 0 jobs when ignoreRunning=true for savedsearch=%s; assumed that job is long-running' % label)
        
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=False)
            self.assert_(len(history) > 0, 'failed to find any running search jobs for savedsearch=%s' % label)
        
            job.cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        def testsavedSearchJSONIsAlert(self):
            savedSearchJSON = {
                'entry': [
                    {
                        'content': {                
                            'is_scheduled': '0',
                            'alert_type': 'always',
                            'alert.track': '0',
                            'actions': '',
                            'dispatch.earliest_time': '',
                            'dispatch.latest_time': ''
                        }
                    }
                ]
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '0',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(not savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'always',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '0',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': '',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': 'rt',
                'dispatch.latest_time': ''
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))
            savedSearchJSON['entry'][0]['content']={
                'is_scheduled': '1',
                'alert_type': 'foo',
                'alert.track': '1',
                'actions': 'email',
                'dispatch.earliest_time': '',
                'dispatch.latest_time': 'rt'
            }
            self.assert_(savedSearchJSONIsAlert(savedSearchJSON))

        def testSavedSearchHistorySorting(self):
            '''Tests sorting of the saved search history endpoint results.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            
            for i in range(5):
                dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
                time.sleep(1)
        
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, sortKey='createTime')
            items = list(history.items())
        
            # Default sort is 'desc'
            self.assertGreaterThan(items[0][1].createTime, items[2][1].createTime)
        
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, sortKey='createTime', sortDir='asc')
            items = list(history.items())
        
            self.assertLessThan(items[0][1].createTime, items[2][1].createTime)
        
            for key, val in items:
                splunk.search.getJob(key).cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testGeneralSavedSearchMethodsWithHighByteCharacters(self):
            '''Tests saved search methods with high byte characters.'''
        
            name = splunk.util.unicode('"ABCDEFGHIJKLMNOPQRSTUVWXYZ "Å" Ä Ö (å ä ö)')
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest(savedSearchName=name)
        
            # Did it create the saved search?
            self.assert_(isinstance(newSavedSearch, entity.Entity))
        
            # Can it dispatch jobs?
            job = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(isinstance(job, splunk.search.SearchJob))
            job.save()
        
            # Is there a valid history?
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(len(history) > 0)
        
            # Get the most recent job?
            last_job = getJobForSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=False)
            self.assertEquals(last_job.sid, job.sid)
        
            job.cancel()
            # Delete the saved search?
            self.assert_(deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER))
        
        
        def testGetSavedSearchHistoryObeysIgnoreExpired(self):
            '''Test that ignore expired correctly filters old results.'''

            name = 'testSavedSearchHistory'
            namespace = TEST_NAMESPACE
            owner = TEST_OWNER
        
            sessionKey, label, searchString, newSavedSearch = \
                self.setupSavedSearchWithNamespaceOwnerTest(savedSearchName=name)
        
            # there is a thread that checks for expired jobs. 
            # but it only checks every 10 seconds. 
            # and there's some additional delta that can make even a X+10 sleep not long enough
            # so here i just wait for X+20 seconds.   Only way i can get the test to pass 
            # 100% of the time.
            testTTL = 2
            jobExpirationPollingInterval = 10
            job = dispatchSavedSearch(label, ttl=testTTL, namespace=namespace, owner=owner)
        
            self.assert_(job.ttl <= testTTL, 
                'Job TTL does not validate: actual=%s expected=%s' % (job.ttl, testTTL))
        
            # Job should be there at first
            fresh = getSavedSearchHistory(name, namespace=namespace, owner=owner)
            self.assert_(job.sid in fresh)
        
            # we wait for the TTL, plus twice whatever the period is of the job reaping thread.
            time.sleep(testTTL + 2*jobExpirationPollingInterval)
        
            # the TTL will have expired and then the reaping thread will have run at least once. 
            # thus the job should be expired.
            fresh = getSavedSearchHistory(name, namespace=namespace, owner=owner)
            self.assert_(job.sid not in fresh)
        
            # Clean up
            try:
                job.cancel()
            except splunk.ResourceNotFound:
                # splunkd might have already cleaned this up, since it has expired.
                pass

            deleteSavedSearch(name, namespace=namespace, owner=owner)
        
        
        def testCreateSavedSearchIncludesTimeArgs(self):
            '''Assert that including an earlist / latest time includes them in the saved search object.'''
            e = '-3d'
            l = '-1d'
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest(earliestTime=e, latestTime=l)
            savedSearch = getSavedSearch(label)
            self.assert_(savedSearch['dispatch.earliest_time'] == e)
            self.assert_(savedSearch['dispatch.latest_time'] == l)
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testCreateSavedSearchWOTimeArgs(self):
            '''Assert that not providing the earliest / latest times does not define a default earliest / latest time.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            savedSearch = getSavedSearch(label)
            
            # At some point splunkd used to set default dispatch.latest_time to 'now'. 
            # at alater point there was a comment here saying that it started defaulting 
            # to not setting anything, including a dispatch.latest_time key.
            # and at the current time, it appears to set the value to a literal None value.

            #FAILS.
            #self.assertRaises(KeyError, savedSearch.__getitem__, 'dispatch.earliest_time')
            #self.assertRaises(KeyError, savedSearch.__getitem__, 'dispatch.latest_time')
            #PASSES.  cause it now returns none. 
            self.assert_(savedSearch['dispatch.earliest_time'] == None)
            

            
            
            self.assert_(savedSearch['dispatch.latest_time'] == None)
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testCreateSavedSearch(self):
            '''Test creating a saved search with/without namespace/owner.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            self.assert_(isinstance(newSavedSearch, entity.Entity))
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testDispatchSavedSearch(self):
            '''Test dispatching a saved search with/without namespace/owner.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            job = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(isinstance(job, splunk.search.SearchJob))
            job.cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testListSavedSearches(self):
            '''Test listing saved searches with/without namespace/owner.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            ss = listSavedSearches(namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(label in ss)
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testListSavedSearchHistory(self):
            '''Test lists saved search history with/without namespace/owner.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            self.assertEquals(len(getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)), 0)
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testDeleteSavedSearch(self):
            '''Test deleting a saved search with/without namespace/owner.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            self.assert_(deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER))
        
        
        def testFindLastRunSavedSearchUseHistoryAuto(self):
            '''Test returns a search job given a saved search name, or creates a new job if there is none in the history.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(len(history), 0)
        
            job_no = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(isinstance(job_no, splunk.search.SearchJob))
        
            # Test that calling findLastJobFromSavedSearch returns the same sid as 'job'
            job2_no = getJobForSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=False)
            self.assertEquals(job_no.sid, job2_no.sid)
        
            job2_no.cancel() # should clean up both
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testFindLastRunSavedSearchUseHistoryYes(self):
            '''Test returns a search job only from the search history given a saved search name.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(len(history), 0)
        
            # Test that a new job is created when saved search
            job = getJobForSavedSearch(label, useHistory=True, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(job, None)
        
            # Test that calling findLastJobFromSavedSearch returns the same sid as 'job'
            job2 = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            job2_clone = getJobForSavedSearch(label, useHistory=True, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=False)
            self.assertEquals(job2.sid, job2_clone.sid)
        
            job2.cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
        
        
        def testFindLastRunSavedSearchUseHistoryNo(self):
            '''Test returns a new search job given a saved search name with use_history=False.'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(len(history), 0)
        
            # Test that a new job is created when saved search
            job = getJobForSavedSearch(label, useHistory=False, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assert_(isinstance(job, splunk.search.SearchJob))
        
            time.sleep(1)
        
            # Test that calling getJobForSavedSearch does not return the same sid as 'job'
            job2 = getJobForSavedSearch(label, useHistory=False, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertNotEquals(job.sid, job2.sid)
        
            job.cancel()
            job2.cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)


        def testAAGetSavedSearchFromSID(self):
            '''Verify getSavedSearchFromSID()'''
            sessionKey, label, searchString, newSavedSearch = self.setupSavedSearchWithNamespaceOwnerTest()
            history = getSavedSearchHistory(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(len(history), 0)

            # Test that a new job is created when saved search
            job = getJobForSavedSearch(label, useHistory=True, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            self.assertEquals(job, None)

            # Test that calling findLastJobFromSavedSearch returns the same sid as 'job'
            job2 = dispatchSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)
            job2_clone = getJobForSavedSearch(label, useHistory=True, namespace=TEST_NAMESPACE, owner=TEST_OWNER, ignoreRunning=False)
            self.assertEquals(job2.sid, job2_clone.sid)
            
            # check that lookup via SID works
            challengeSavedSearch = getSavedSearchFromSID(job2.id, sessionKey=sessionKey)
            self.assert_(isinstance(challengeSavedSearch, entity.Entity), 'check that entity.Entity object returned; got %s' % type(challengeSavedSearch))
            self.assertEquals(challengeSavedSearch.name, label, 'check that saved search name matches')
            self.assertEquals(challengeSavedSearch['search'], newSavedSearch['search'], 'check that saved search string matches')

            job2.cancel()
            deleteSavedSearch(label, namespace=TEST_NAMESPACE, owner=TEST_OWNER)




    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(SavedSearchTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
