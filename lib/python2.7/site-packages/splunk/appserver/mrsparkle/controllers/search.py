
import defusedxml.lxml as safe_lxml
import json
import logging
import logging.handlers
import lxml.etree as et
import sys
import os
import re
from future.moves.urllib import parse as urllib_parse

import cherrypy

import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle import MIME_HTML
from splunk.appserver.mrsparkle import MIME_TEXT
from splunk.appserver.mrsparkle import MIME_CSV
from splunk.appserver.mrsparkle import MIME_XML
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import ONLY_API
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.appserver.mrsparkle.lib.util as util

import splunk.appserver.mrsparkle.lib.i18n as i18n
from splunk.appserver.mrsparkle.lib.jsonresponse import JsonResponse
import splunk.appserver.mrsparkle.lib.module as module
import splunk.auth
import splunk.clilib.bundle_paths as bundle_paths
import splunk.entity as en
import splunk.rest as rest
import splunk.search
import splunk.util

logger = logging.getLogger('splunk.appserver.controllers.search')

EXPORT_HARDLIMIT = 10000
ASSET_EVENTS = 'events'
ASSET_RESULTS = 'results'
ASSET_TIMELINE = 'timeline'
ASSET_SUMMARY = 'summary'
JOB_ACTIONS = ['cancel', 'pause', 'unpause', 'finalize', 'save', 'touch', 'ttl']
REQUIRED_DISPATCH_ARGUMENTS = ['search', 'status_buckets', 'earliest_time', 'latest_time']

class JobsController(BaseController):
    """
    /search/jobs
    
    Manages job control.
    
    Endpoints return a standard json envelope:
    { messages: [{type: 'ERROR', 'text': 'Abe ate the job.'}],
      data: None,
      success: True }
    """

    def __init__(self):
        super(JobsController, self).__init__()

        mm = module.moduleMapper
        self.moduleRoster = mm.getInstalledModules()

    #
    # handles job listing and dispatch
    #

    def streamJobExport(self, job, assetType, **kwargs):
        """
        Stream exported job results to the client (does not buffer the whole result in memory)
        """
        ns = job.eaiacl['app']
        sid = job.sid
        owner = job.eaiacl['owner']
        request = {}
        request['output_mode'] = kwargs['outputMode']
        # SPL-79832 when exporting xml splunkd requires additional request argument
        # to generate valid xml
        if request['output_mode'] == "xml":
            request['export_xml_with_wrapper'] = 1


        request['f'] = kwargs['field_list']
        
        if 'output_time_format' in kwargs:
            request['output_time_format'] = kwargs['output_time_format']
        else:
            request['output_time_format'] = i18n.ISO8609_MICROTIME

        try:
            count = int(kwargs.get('count'))
            if count>0:
                request['count'] = count
        except ValueError:
            logger.warn("Failed to parse count field for export count=%s" % count)
            pass

        # We're not going to read/write further from the user's session at this point
        # and streaming may take a while, so release the session read lock
        cherrypy.session.release_lock()

        # Don't buffer the (potentially sizeable) result in memory
        cherrypy.response.stream = True

        postargs = getargs = None
        if job.reportSearch is None and ((job.eventIsTruncated and (count == 0 or count > job.eventAvailableCount)) or not job.isDone):
            logger.debug('re-run the search to get the complete results')
            uri = en.buildEndpoint('search/jobs/export', namespace=ns, owner=owner)

            # SPL-164106 Do not overwrite earliest_time if it already exists
            if job.earliestTime is not None and 'earliest_time' not in job.request:
                job.request['earliest_time'] = str(splunk.util.mktimegm(job.earliestTime.utctimetuple()))
                logger.debug('Rerunning search with original earliestTime')

            if job.latestTime is None and 'createTime' in job._propertyPrimitives and job._propertyPrimitives['createTime'] is not None:
                job.request['latest_time'] = str(splunk.util.mktimegm(splunk.util.parseISO(job._propertyPrimitives['createTime']).utctimetuple()))
                logger.debug('Rerunning search with original createTime')
            # SPL-164106 Do not overwrite latest_time if it already exists
            elif 'latest_time' not in job.request:
                job.request['latest_time'] = str(splunk.util.mktimegm(job.latestTime.utctimetuple()))
                logger.debug('Rerunning search with original latestTime')

            request.update(job.request)
            if 'search' not in request:
                request['search'] = job.eventSearch

            if count > 0:
                request['search'] += '|head %s' % count
            postargs = request

            # if re-running the search for exporting events, 
            # ensure we do not run the search with following arguments
            ignoreArgs = ['auto_cancel', 'max_count']
            for iarg in ignoreArgs:
                if iarg in postargs:
                    logger.debug("Dropping argument %s from postargs" % iarg)
                    del postargs[iarg]

        elif assetType == 'event': 
            logger.debug('No re-run non-reporting search assetType==event')
            uri = en.buildEndpoint('search/jobs/%s/events/export' % job.sid, namespace=ns, owner=owner)
            getargs = request
        else:
            logger.debug('No re-run reporting search')
            uri = en.buildEndpoint('search/jobs/%s/results/export' % job.sid, namespace=ns, owner=owner)
            getargs = request
        
        export_timeout =  cherrypy.config.get('export_timeout')
        
        logger.debug('Export timeout =%s' % export_timeout)

        if (export_timeout != None) :
            export_timeout = int(export_timeout)

        stream = rest.streamingRequest(uri, getargs=getargs, postargs=postargs, timeout=export_timeout)
        return stream.readall() # returns a generator
        

    @route('/', methods='GET')
    @expose_page(handle_api=ONLY_API)
    def listJobs(self, restrictToSession=True, nocache=False, s=None, cachebuster=None, wait=True):
        '''
        Returns a listing of jobs that the client needs to be aware of;
        listing is restricted by user session, and optionally filtered by
        a whitelist provided by the client
        '''

        resp = JsonResponse()
        
        # dump out if no jobs are specified
        if not s:
            resp.data = []
            return self.render_json(resp)

        if 0:
            uri = en.buildEndpoint('search/jobs', '')
            logger.error("uri: %s" % uri)
            serverResponse, serverContent = rest.simpleRequest(uri, getargs={'id':s, 'output_mode':'json'})
            
            return serverContent
            
        # normalize a single string into a list
        if isinstance(s, splunk.util.string_type): s = [s]
        
        # bypass the legacy sdk blocking for RUNNING state
        wait = splunk.util.normalizeBoolean(wait)
        
        # loop over all all requested jobs and ask server for status
        listing = []
        for requestSID in s:
            try:
                job = splunk.search.getJob(requestSID, waitForRunning=wait)
                listing.append(job.toJsonable())
                
            except splunk.ResourceNotFound:
                listing.append({'sid': requestSID, '__notfound__': True})
                nocache = True # ensure we always bust the cache otherwise, multiple requests may not find out that the job doesn't exist
                resp.addError(_('Splunk could not find a job with sid=%s.') % requestSID)
                
            except Exception as e:
                logger.exception(e)
                resp.success = False
                resp.addError(str(e))
                return self.render_json(resp)
        
        # normalize the key data
        for item in listing:
            if not item.get('__notfound__'):
                for key in ('eventCount', 'resultCount', 'scanCount'):
                    if key in item:
                        item[key] = int(item[key]) 
                for key in ('isDone', 'eventIsStreaming', 'isFinalized', 'isPaused', 'isSaved', 'isSavedSearch'):
                    if key in item:
                        item[key] = splunk.util.normalizeBoolean(item[key]) 
        
        # do caching on hash
        if not splunk.util.normalizeBoolean(nocache):
        
            # generate a copy of the listing without job TTL information; 
            # this is so we can hash contents to send a 304
            staticlisting = listing[:]
            for x in staticlisting:
                if not item.get('__notfound__'):
                    del x['ttl']
                
            staticoutput = json.dumps(staticlisting)
        
            if util.set_cache_level('etag', staticoutput) == None:
                return None

        resp.data = listing
        return self.render_json(resp)


    @route('/', methods='POST')
    @expose_page(handle_api=ONLY_API)
    def dispatchJob(self, wait=True, **kwargs):
        '''
        Dispatches a new job
        '''
        if not set(kwargs.keys()) >= set(REQUIRED_DISPATCH_ARGUMENTS):
            raise cherrypy.HTTPError(status=400, message="Missing one or more of the required arguments: 'search', 'statusBucketCount', 'earliestTime', 'latestTime'.")

        # setup the dispatch args
        options = kwargs.copy()
        q = options['search']
        del options['search']

        if 'maxEvents' not in options:
            options['maxEvents'] = EXPORT_HARDLIMIT
        
        # ensure that owner and namespace contexts are passed
        if 'owner' not in options:
            options['owner'] = cherrypy.session['user'].get('name')
        if 'namespace' not in options:
            options['namespace'] = splunk.getDefault('namespace')
            logger.warn('search was dispatched without a namespace specified; defaulting to "%s"' % options['namespace'])

        # Add the default time format
        options['time_format'] = cherrypy.config.get('DISPATCH_TIME_FORMAT')
        
        # bypass the legacy sdk blocking for RUNNING state
        wait = splunk.util.normalizeBoolean(wait)
        options["waitForRunning"] = wait
     
        resp = JsonResponse()

        try:
            logger.debug('q=%s' % q)
            logger.debug('options=%s' % options)

            # We're not going to read/write further from the user's session at this point...if we do, acquire the lock`
            # This can take significant time when there is a subsearch
            cherrypy.session.release_lock()

            job = splunk.search.dispatch(q, **options)
            resp.data = job.id
        except splunk.SplunkdConnectionException as e:
            logger.exception(e)
            resp.success = False
            resp.addFatal(str(e))
        except Exception as e:
            logger.exception(e)
            resp.success = False
            resp.addError(str(e))
            
        logger.debug('dispatch returned %s' % resp)
        return self.render_json(resp)

        
    # It might be worth revisiting this endpoint since it returns a myriad
    # list of response types.  In its current configuration it can even
    # return JSON in two formats, one from the JsonResponse obj and another
    # directly from splunkd
    @route('/:sid/:asset', methods='GET')
    @expose_page(handle_api=ONLY_API)
    @set_cache_level("never")
    def getJobAsset(self, sid, asset, compat_mode=True, **kwargs):
        '''
        Returns specific asset for a given job

        compat_mode: When enabled results in JSON transformed to 4.X variant for 
        results, events and results_preview asset types.
        '''
        
        compat_mode = splunk.util.normalizeBoolean(compat_mode)
         
        job_lite = splunk.search.JobLite(sid)

        # set response type; default to XML output
        if 'outputMode' not in kwargs:
            kwargs['outputMode'] = 'xml'

        outputMode = kwargs['outputMode']
        if outputMode == 'json': ct = splunk.appserver.mrsparkle.MIME_JSON
        elif outputMode == 'raw': ct = MIME_TEXT
        elif outputMode == 'csv': ct = MIME_CSV
        else: 
            outputMode = 'xml'
            ct = MIME_XML

        cherrypy.response.headers['content-type'] = ct
        
        # if we're exporting, set the correct headers, to get the browser to show a download
        # dialog. also hardlimit the export cap to 10,000 events.
        if 'isDownload' in kwargs:
            if outputMode == 'raw':
                extension = 'txt'
            else:
                extension = outputMode

            if 'filename' in kwargs and len(kwargs["filename"]) > 0:
                if kwargs['filename'].find('.') > -1:
                    filename = kwargs['filename']
                else:
                    filename = "%s.%s" % ( kwargs['filename'], extension)
            else:
                filename = "%s.%s" % ( sid.replace('.', '_'), extension)

            # sanitize filenames
            if sys.version_info < (3, 0):
                filename = filename.encode('utf-8')
            clean_filename = re.split(r'[\r\n;"\']+', filename)[0]
            clean_filename = clean_filename[:255]
            clean_filename = clean_filename.replace(' ', '_')

            cherrypy.response.headers['content-type'] = 'application/force-download'
            # adding filename* to support non-ascii characters (https://tools.ietf.org/html/rfc6266#section-5)
            cherrypy.response.headers['content-disposition'] = "filename*=UTF-8''%s" % urllib_parse.quote(clean_filename)

            rs = job_lite.getResults('results_preview', 0, 1)
            
            # by default, exclude underscore fields except time and raw
            if 'field_list' not in kwargs:
                if not rs:
                    resp = JsonResponse()
                    cherrypy.response.status = 404
                    resp.success = False
                    resp.addError("job sid=%s not found" % sid)
                    return self.render_json(resp)

                kwargs['field_list'] = [x for x in rs.unstrippedFieldOrder() if (not x.startswith('_') or x == '_time' or x == '_raw')]
            
            job = splunk.search.getJob(sid)
            return self.streamJobExport(job, asset, **kwargs)

        # set default time format
        if 'time_format' not in kwargs and 'timeFormat' not in kwargs:
            kwargs['time_format'] = cherrypy.config.get('DISPATCH_TIME_FORMAT')

        # SPL-34380, if the url will be too long, remove the field_list value.
        # This is just a bandaid for now, a better solution involves splunkd 
        # patching.
        url_len = len(urllib_parse.urlencode(kwargs))
        if url_len > 8192: # Max url length
            logger.warn('field_list argument removed in REST call to shorten URL')
            kwargs.pop('field_list', None)
            kwargs.pop('f', None)
            
        # pass through the search options
        job_lite.setFetchOption(**kwargs)

        try:
            output = job_lite.get(asset)
        except:
            resp = JsonResponse()
            cherrypy.response.status = 404
            resp.success = False
            resp.addError("job sid=%s not found" % sid)
            return self.render_json(resp)
                

        # TODO:
        # handle server-side XSL transforms
        enableSearchJobXslt = splunk.util.normalizeBoolean(cherrypy.config.get('enableSearchJobXslt'))
        moduleName = cherrypy.request.headers.get('X-Splunk-Module', None)
        if 'moduleName' in kwargs:
            moduleName = kwargs.get('moduleName')
        if outputMode == 'json' and output and compat_mode and asset in ['results_preview', 'results', 'events']:
            # transform json to pre-5.0 format for backwards compliance
            try:
                data = json.loads(output)
            except:
                pass
            else:
                output = json.dumps(data.get('results', []))
        
        elif moduleName and ('xsl' in kwargs) and output and enableSearchJobXslt:
            
            #logger.debug('search api got xsl request: %s' % moduleName)
            
            # get XSL file
            xslFilePath = os.path.abspath(bundle_paths.expandvars(os.path.join(self.moduleRoster[moduleName]['path'], kwargs['xsl'])))
            splunkHomePath = bundle_paths.expandvars('$SPLUNK_HOME')
            
            if (xslFilePath.startswith(splunkHomePath)):
                try:
                    f = open(xslFilePath, 'r')
                    xslt_doc = safe_lxml.parse(f)
                    f.close()
                
                    # generate transformer
                    transform = et.XSLT(xslt_doc)
                
                    # transform the XML
                    xmlDoc = safe_lxml.fromstring(output)
                    transformedOutput = transform(xmlDoc)
                
                    cherrypy.response.headers['content-type'] = MIME_HTML
    
                    html = et.tostring(transformedOutput)
                    if not html:
                        output = 'Loading...'
                    else:
                        output = html
                except Exception as e:
                    cherrypy.response.headers['content-type'] = MIME_HTML
                    logger.warn('Exception occurred while transforming xml results -')
                    output = 'Error occurred while performing xslt transform on results. Please check the logs for errors.'

            else:
                cherrypy.response.headers['content-type'] = MIME_HTML
                logger.warn('File xsl="%s" is out of $SPLUNK_HOME="%s"' % (xslFilePath, splunkHomePath))
                output = 'The file you are trying to access is not under the $SPLUNK_HOME directory'
        
        # This handles the edge case when output returns no results but
        # a content-type of html is still expected, say by jQuery's $.ajax
        # method.  This could be avoided if the response returned a valid
        # xml document while maintaining a content-type of xml.  Currently
        # empty results are rendered as content-length 0 which jQuery fails
        # on parsing, as it expects xml.
        elif moduleName and ('xsl' in kwargs) and not output:
            if enableSearchJobXslt:
                logger.debug('Search api got xsl request, but api is not enabled to accept xsl. '+
                             'Setting content-type to html anyway')
            else:
                logger.debug('Search api got xsl request, but no search results '+
                             'were returned. Setting content-type to html anyway')
            cherrypy.response.headers['content-type'] = MIME_HTML

            output = 'Loading...'

        # otherwise, return raw contents
        if util.apply_etag(output):
            return None
        else:
            return output

    
    @route('/:ctl=control', methods='POST')
    @expose_page(handle_api=ONLY_API)
    def batchControl(self, ctl, sid=None, action=None, ttl=None, **kw):
        
        resp = JsonResponse()
        
        if sid == None or action == None or not action in JOB_ACTIONS:
            cherrypy.response.status = 400
            resp.success = False
            resp.addError(_('You must provide a job id(s) and a valid action.'))
            return self.render_json(resp)
        
        if not isinstance(sid, list):
            sid = [sid]
        
        resp.data = []
        action = action.lower()
        
        for searchId in sid:
            try:
                job = splunk.search.getJob(searchId, sessionKey=cherrypy.session['sessionKey'])
                if action=='ttl':
                    response = job.setTTL(ttl)
                else:
                    actionMethod = getattr(job, action)
                    response = actionMethod()
            except splunk.ResourceNotFound as e:
                resp.addError(_('Splunk could not find a job with a job id of %s.') % searchId, sid=searchId, status=404)
                response = False
            resp.data.append({'sid': searchId, 'action':action, 'response': response})                
        return self.render_json(resp)


class SearchController(BaseController):
    """
    /search
    """

    # delegate results and jobs to sub-controllres
    jobs = JobsController()

    @expose_page(handle_api=ONLY_API)
    def index(self, **kwargs):
        
        if cherrypy.request.is_api:

            return 'you got api access'
            serverResponse, serverContent = rest.simpleRequest(
                cherrypy.request.path, 
                cherrypy.session['sessionKey'], 
                #getargs=, 
                #postargs=postargs,
                method=cherrypy.request.method
            )

            for header in serverResponse : 
                cherrypy.response.headers[header] = serverResponse[header]

            return serverContent

        else:
            
            return 'This is the search endpoint'