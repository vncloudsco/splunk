from builtins import object
import splunk.search
import splunk.pdf.pdfgen_utils as utils

from splunk import QuotaExceededException, SearchException

logger = utils.getLogger()


class BaseSearchManager(object):
    def __init__(self, namespace, owner, sessionKey):
        self.job = None
        self.namespace = namespace
        self.owner = owner
        self.sessionKey = sessionKey
        self.realtime = None
        self.deps = 0

    def dispatch_internal(self, **kwargs):
        # Implemented by subclasses
        raise Exception("Not implemented")

    def dispatch(self, **kwargs):
        if self.job is None:
            try:
                self.setJob(self.dispatch_internal(**kwargs), force=True)
            except QuotaExceededException as e:
                logger.error("dispatchSearch exception dispatching search, " + str(self) + ": " + str(e))
        return self.job

    def feed(self, **kwargs):
        mode = 'results_preview' if self.isRealtime() else 'results'
        return self.job.getFeed(mode=mode, **kwargs)

    def events(self):
        return getattr(self.job, 'results_preview' if self.isRealtime() else 'events')

    def results(self):
        return getattr(self.job, 'results_preview' if self.isRealtime() else 'results')

    def touch(self):
        if self.job and (self.job.eaiacl is None or self.job.eaiacl.get('can_write') != '0'):
            self.job.touch()

    def cancel(self):
        if self.job is not None:
            self.job.cancel()
            self.job = None

    def resolve(self):
        pass

    def earliest(self):
        pass

    def latest(self):
        pass

    def isComplete(self):
        return self.job is not None and self.job.isDone

    def isRealtime(self):
        if self.realtime is not None:
            return self.realtime
        else:
            return utils.isTimerangeRealtime(self.earliest(), self.latest())

    def validateJob(self, job):
        if job.isExpired():
            logger.warn("Job sid=%s has already expired", job.id)
            return False
        return True

    def setJob(self, job, force=False):
        if self.job is None:
            if job is None:
                logger.debug("setJob() called with None")
            elif self.validateJob(job) or force:
                logger.debug("Using search job sid=%s", job.id)
                self.job = job
            else:
                logger.warn("Rejecting invalid job sid=%s", job.id)
        else:
            logger.warn('Search Manager already has a job')


def forceHistoricTimerange(earliestTime, latestTime):
    return dict(
        earliestTime=utils.stripRealtime(earliestTime),
        latestTime=utils.stripRealtime(latestTime)
    )


class InlineSearchManager(BaseSearchManager):
    type = "inline"

    def __init__(self, searchCommand, earliestTime, latestTime, namespace, owner, sessionKey, sampleRatio=None):
        BaseSearchManager.__init__(self, namespace, owner, sessionKey)
        self.searchCommand = searchCommand
        self.earliestTime = earliestTime
        self.latestTime = latestTime
        self.sampleRatio = sampleRatio

    def dispatch_internal(self, **kwargs):
        search = self.searchCommand
        options = forceHistoricTimerange(self.earliestTime, self.latestTime)
        self.realtime = False
        if 'overrideNowTime' in kwargs:
            options['now'] = int(kwargs['overrideNowTime'])
        if 'maxRowsPerTable' in kwargs:
            options['maxEvents'] = kwargs['maxRowsPerTable']
        if 'stripLeadingSearchCommand' in kwargs and kwargs['stripLeadingSearchCommand']:
            search = utils.stripLeadingSearchCommand(search)
        if self.sampleRatio is not None:
            options['sample_ratio'] = self.sampleRatio
        search = utils.unEscapeTokenInSearchCommand(search)             
        query = utils.prepareInlineSearchCommand(search)
        logger.debug('Dispatching inline search=%s options: %s', query, repr(options))
        job = splunk.search.dispatch(query, namespace=self.namespace, owner=self.owner, sessionKey=self.sessionKey, **options)
        return job

    def resolve(self):
        return self.searchCommand

    def earliest(self):
        return self.earliestTime

    def latest(self):
        return self.latestTime

    def validateJob(self, job):
        if not BaseSearchManager.validateJob(self, job):
            return False
        req = job.request
        expectedSearch = utils.stripLeadingSearchCommand(self.resolve())
        actualSearch = utils.stripLeadingSearchCommand(req.get('search', None))
        if expectedSearch != actualSearch:
            # Only warn here at the moment, don't reject the job
            logger.warning("Job sid=%s does not match search query"
                        "\n\texpected query=%s\n\tdetected query=%s", job.id, expectedSearch, actualSearch)
        et, lt = utils.stripRealtime(self.earliestTime), utils.stripRealtime(self.latestTime)
        if not utils.compareTimerange(req.get('earliest_time', None), req.get('latest_time', None), et, lt):
            # Only warn here at the moment, don't reject the job
            logger.warning("Job sid=%s has a different timerange than the given search (saw: et=%s, lt=%s, expected: et=%s, lt=%s)", job.id,
                        req['earliest_time'], req['latest_time'],
                        et, lt)
        return True

    def __str__(self):
        return "Search(type=inline, searchCommand=%s)" % self.searchCommand


def combineSearchCommands(*searches):
    stripChars = ' \r\n\t|'
    result = []
    first = True
    for part in searches:
        if first:
            result.append(part.rstrip(stripChars))
            first = False
        else:
            result.append(part.strip(stripChars))
    return " | ".join(result)


class PostProcessSearchJob(splunk.search.SearchJob):
    def __init__(self, postprocess, *args, **kwargs):
        self._postprocess = postprocess
        super(PostProcessSearchJob, self).__init__(*args, **kwargs)
        self.setFetchOption()

    def setFetchOption(self, **kwargs):
        newargs = dict()
        newargs.update(kwargs)
        if 'search' in kwargs:
            newargs['search'] = combineSearchCommands(self._postprocess, kwargs['search'])
        else:
            newargs['search'] = self._postprocess
        logger.debug("Applying post-process fetch options %s (override of %s)", newargs, kwargs)
        super(PostProcessSearchJob, self).setFetchOption(**newargs)

    def setFetchOptions(self, **kwargs):
        self.setFetchOption(**kwargs)


def createPostProcessJob(job, postprocessSearch):
    jobArgs = dict(
        hostPath=job.hostPath,
        sessionKey=job.sessionKey,
        namespace=job.namespace,
        owner=job.owner,
        message_level=job.message_level,
        dispatchArgs=job.dispatchArgs,
        status_fetch_timeout=job._status_fetch_timeout,
        waitForRunning=job.waitForRunning
    )
    return PostProcessSearchJob(postprocess=postprocessSearch, searchId=job.id, **jobArgs)


class PostProcessSearchManager(BaseSearchManager):
    type = "postprocess"

    def __init__(self, postSearch, parentManager, namespace, owner, sessionKey):
        BaseSearchManager.__init__(self, namespace, owner, sessionKey)
        self.parent = parentManager
        self.parent.deps += 1
        self.postSearch = postSearch

    def resolve(self):
        return combineSearchCommands(self.parent.resolve(), self.postSearch)

    def resolvePostprocess(self):
        if isinstance(self.parent, PostProcessSearchManager):
            return combineSearchCommands(self.parent.resolvePostprocess(), self.postSearch)
        else:
            return self.postSearch

    def earliest(self):
        return self.parent.earliest()

    def latest(self):
        return self.parent.latest()

    def toInline(self):
        return InlineSearchManager(self.resolve(), self.earliest(), self.latest(), self.namespace, self.owner,
                                   self.sessionKey)

    def dispatch(self, **kwargs):
        job = self.parent.dispatch(**kwargs)
        if job is not None:
            job = createPostProcessJob(job, self.resolvePostprocess())
            self.job = job
            return job

    def cancel(self):
        if self.job is not None:
            self.parent.deps -= 1
            if self.parent.deps <= 0:
                self.parent.cancel()
            self.job = None

    def isRealtime(self):
        return self.parent.isRealtime()
    
    def setJob(self, job, force=False):
        self.parent.setJob(job, force=force)

    def __str__(self):
        return "Search(type=postprocess, searchCommand=%s)" % self.postSearch


class SavedSearchManager(BaseSearchManager):
    type = "saved"

    def __init__(self, name, earliestTime=None, latestTime=None, namespace=None, owner=None, sessionKey=None):
        self.searchName = name
        self.earliestTime = earliestTime
        self.latestTime = latestTime
        self.savedSearchModel = None
        self.ownDispatch = None
        BaseSearchManager.__init__(self, namespace, owner, sessionKey)

    def dispatch_internal(self, overrideNowTime=None, **kwargs):
        dispatchArgs = dict(
            namespace=self.namespace,
            owner=self.owner,
            sessionKey=self.sessionKey,
            forceHistoricSearch=True,
            overrideNowTime=overrideNowTime,
            earliestTime=self.earliestTime,
            latestTime=self.latestTime
        )
        logger.debug("Dispatching %s with args %s", self, dispatchArgs)
        job, self.ownDispatch = utils.dispatchSavedSearch(self.searchName, savedSearchModel=self.model(), **dispatchArgs)
        return job

    def model(self):
        if self.savedSearchModel is None:
            self.savedSearchModel = utils.getSavedSearch(self.searchName, self.namespace, self.owner, self.sessionKey)
        return self.savedSearchModel

    def resolve(self):
        return self.model().search

    def earliest(self):
        return self.model().dispatch.earliest_time if self.earliestTime is None else self.earliestTime

    def latest(self):
        return self.model().dispatch.latest_time if self.latestTime is None else self.latestTime

    def isRealtime(self):
        self.model().is_realtime()

    def cancel(self):
        # Only cancel the job if we dispatched it ourselves (ie. not if we're reusing a scheduled artifact)
        if self.ownDispatch is True:
            BaseSearchManager.cancel(self)

    def validateJob(self, job):
        if job.isRealTimeSearch:
            logger.info("Rejecting real-time search job sid=%s", job.id)
            return False
        return BaseSearchManager.validateJob(self, job)

    def __str__(self):
        return "Search(type=saved, name=%s)" % self.searchName
