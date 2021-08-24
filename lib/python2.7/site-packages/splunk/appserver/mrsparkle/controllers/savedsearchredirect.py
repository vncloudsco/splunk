# coding=UTF-8
import json
import string

import cherrypy
import logging

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.rest import simpleRequest
from splunk.saved import savedSearchJSONIsAlert

logger = logging.getLogger('splunk.appserver.controllers.savedsearchredirect')

class SavedSearchRedirectController(BaseController):
    
    @route('/')
    @expose_page(must_login=True, methods='GET')
    def index(self, **params):
        ssId = params.get('s')

        #no ssId
        if not ssId:
            raise cherrypy.HTTPError(400, _('Must specify a savedsearch id.'))

        #fetch saved search
        responseHeaders, responseBody = simpleRequest(ssId, method='GET', getargs={'output_mode':'json'})
        savedSearchJSON = json.loads(responseBody)
        app = savedSearchJSON['entry'][0]['content'].get("request.ui_dispatch_app") or\
            savedSearchJSON['entry'][0]['acl'].get("app") or 'search'

        #scheduled view
        if '_ScheduledView__' in ssId:
            #redirect to dashboard page
            name = savedSearchJSON['entry'][0]['name']
            name = string.replace(name, '_ScheduledView__', '', 1)
            self.redirect_to_url(['app', app, name], _qs={'dialog': 'schedulePDF'})

        if savedSearchJSONIsAlert(savedSearchJSON):
            #if alert route to  :app/alert?s=ssId
            self.redirect_to_url(['app', app, 'alert'], _qs={'s': ssId, 'dialog': 'actions'})
        #report - :app/report?s=ssId
        self.redirect_to_url(['app', app, 'report'], _qs={'s': ssId, 'dialog': 'schedule'})
        return

    
