from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle import MIME_HTML

from splunk.appserver.mrsparkle.lib import i18n
from splunk.appserver.mrsparkle.lib import jsonresponse
import cherrypy
import logging
import splunk.util
import splunk.input
import splunk.search

logger = logging.getLogger('splunk.appserver.controllers.twink')

class TwinkController(BaseController):
    """/twink"""
    
    @route('/:service/:action')
    @expose_page()
    def dispatcher(self, service, action=None, **kwargs):
        '''
        This is the main dispatcher that provides compatibility with the
        Twitter API.  The URI structure of Twitter's API is not as clean as the
        routes system expects; we route everything through here first.
        '''

        # parse the URI
        serviceParts = service.split('.', 2)
        handler = serviceParts[0]
        actionParts = action.split('.', 2)
        action = actionParts[0]
        
        outputMode = 'html'
        if len(serviceParts) > 1:
            outputMode = serviceParts[-1]
        elif len(actionParts) > 1:
            outputMode = actionParts[-1]

        data = None
        
        
        if handler == 'statuses':
            
            if action == 'public_timeline': 
                searchString = 'search index=twink | head 100'
                data = self.executeSearch(searchString)

            elif action == 'user_timeline':
                 searchString = 'search index=twink source="%s" | head 100' % kwargs.get('screen_name', cherrypy.session['user'].get('name'))
                 data = self.executeSearch(searchString)

            elif action == 'mentions':
                pass

            elif action == 'show':
                pass

            elif action == 'update':
                self.addTweet(kwargs['status'])
                raise cherrypy.HTTPRedirect('public_timeline')
                
            else:
                raise cherrypy.HTTPError(404, 'statuses does not recognize action: %s' % action)


        elif handler == 'search':
            searchString = 'search index=twink | head 100'
            

        elif handler == 'saved_searches':
            if action == 'show':
                pass
            else:
                pass


        else:
            raise cherrypy.HTTPError(404, 'handler not found: %s' % handler)
           
           
            
        if outputMode == 'html':
            cherrypy.response.headers['content-type'] = MIME_HTML
            return self.render_template('/twink:/templates/public_timeline.html', {'stream': data})
            
        elif outputMode == 'json':
            output = jsonresponse.JsonResponse()
            output.data = data
            return self.render_json(output)

        else:
            raise cherrypy.HTTPError(500, 'something is wrong')
        
        

    # /////////////////////////////////////////////////////////////////////////
    #  helper methods
    # /////////////////////////////////////////////////////////////////////////
        
    def executeSearch(self, q, **kwargs):
        job = splunk.search.dispatch(q)
        splunk.search.waitForJob(job)

        output = []
        for event in job.results[0:50]:
            output.append({
                'status': splunk.util.unicode(event.raw),
                'time': i18n.format_datetime_microseconds(event['_time'], 'short'),
                'screen_name': splunk.util.unicode(event['source']),
                'host': splunk.util.unicode(event['host']),
                'source': splunk.util.unicode(event['sourcetype'])
            })
        return output
        
        
    def addTweet(self, status):
        stream = splunk.input.open(
            source=('/' + cherrypy.session['user'].get('name')),
            sourcetype='web',
            hostname=cherrypy.request.remote.ip,
            index='twink')
        stream.write(status)
        stream.close()
