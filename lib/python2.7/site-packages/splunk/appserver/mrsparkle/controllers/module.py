from builtins import object
import cherrypy
import re
import sys
import splunk.appserver.mrsparkle # bulk edit
from  splunk.appserver.mrsparkle import MIME_HTML
from  splunk.appserver.mrsparkle import SYSTEM_NAMESPACE
import splunk.search
import logging
import traceback
import xml.sax.saxutils as su
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
import splunk.appserver.mrsparkle.lib.util as util

import splunk
import splunk.rest as rest

logger = logging.getLogger('splunk.appserver.controllers.module')

class ModuleController(BaseController):
    """/module"""

    @route('/:host_app/:module/:action=render')
    @expose_page(methods='GET')
    def renderModule(self, host_app, module, action, **args):
        '''
        Provides generic module content rendering endpoint.

        The base module JS dispatcher will always append a 'client_app' param
        that contains the app context from which this request was made.  It is
        entirely different from the host_app where this module resides.
        '''

        # strip out the cache defeater
        args.pop('_', None)

        if not self._isModuleClassInApp(module, host_app):
            logger.warn('Could not load module "%s" in host app "%s"' % (module, host_app))
            return _('Could not find module "%(module)s" in the following host app "%(host_app)s"') % {'module':su.escape(module), 'host_app':su.escape(host_app)}

        args['host_app'] = host_app

        # put in default client_app if incoming request did not have one
        args.setdefault('client_app', splunk.getDefault('namespace'))

        # TODO: change me when the modules are registered under a module
        try:
            module_name = module.split('.').pop()
            handler = getattr(sys.modules[__name__], module_name)
        except Exception as e:
            logger.exception(e)
            traceback.print_exc(e)
            return _('Splunk could not find a controller to import for the following module: "%s".') % su.escape(module)

        # get module content
        cherrypy.request.headers['content-type'] = MIME_HTML
        instance = handler(self)

        try:
            pageContent = instance.generateResults(**args)
        except Exception as e:
            logger.exception(e)
            traceback.print_exc(e)
            errorString = _("[%(module_name)s module] %(error_msg)s") % {'module_name':module_name, 'error_msg':e}
            pageContent = instance.generateErrorMessage(errorString)

        if cherrypy.response.headers.get('Cache-Control') == None:
            return util.set_cache_level('etag', pageContent)
        return pageContent


    @route('/:host_app/:module/:action=statusMessage')
    @expose_page(methods='GET')
    @set_cache_level('etag')
    def renderJobStatusMessage(self, **kwargs):

        # get module content
        cherrypy.request.headers['content-type'] = MIME_HTML
        instance = ModuleHandler(self)

        try:
            pageContent = instance.generateStatusMessage(**kwargs)
        except Exception as e:
            logger.exception(e)
            pageContent = instance.generateErrorMessage(e)

        return pageContent


    def _isModuleClassInApp(self, moduleClass, host_app):
        '''
        Determines if requested moduleClass has been defined in host_app.
        NOTE: This method will only return true if requests are made from
        the host app of 'system', as we are not supporting modules that
        exist in other apps (though they can be packaged as so).
        '''

        return host_app == SYSTEM_NAMESPACE


class ModuleHandler(object):

    def __init__(self, controller):
        self.controller = controller


    def getTemplatePath(self, modulePath):
        return '../../modules/%s' % modulePath.strip(' /')

    def generateResults(self, **args):
        '''
        Generates module HTML content.

        Override this method to provide module-specific content information.
        The 'args' dict is a mapping of all the URI querystring params that
        may be passed from the UI.
        '''

        return _('This module does not have a registered renderer.')

    def generateErrorMessage(self, errorString):
        '''
        Generates module error message HTML.

        Override the basic behavior if any custom error rendering is needed.
        '''

        return '<p class="moduleException">%s</p>' % su.escape(errorString)

    def getConfig(self, viewId=None):
        '''
        Returns configuration information for a module.

        Override this method to provide module-specific configuration information.
        '''

        return _('This module does not have registered configuration information.')


    def generateStatusMessage(self, entity_name, msg, sid, **kwargs):
        '''
        Generate the status message to display in search results containers.

        msg:
            waiting: UI is waiting for first results to return
            nodata: search has completed and no data is available
        '''

        output = '<p class="resultStatusMessage empty_results">'

        if msg == 'nodata':
            if entity_name == 'events':
                submsg = _('No matching events found.')
            else:
                submsg = _('No results found.')

            output += '%s <span class="resultStatusHelp"><a href="#" onclick=%s class="resultStatusHelpLink">%s</a></span>' % (
                submsg,
                su.quoteattr("Splunk.window.openJobInspector('%s');return false;" % sid.replace("'", "")),
                _('Inspect ...')
            )

        elif msg == 'waiting':
            output += _('Waiting for data...')
        elif msg == 'queued':
            output += _('Waiting for search to start: job is queued.')
        elif msg == 'parsing':
            output += _('Waiting for search to start: evaluating subsearches.')
        elif msg == 'preparing':
            output += _('Waiting for search to start: job is preparing.')
        else:
            logger.error('generateStatusMessage - got unexpected message request=%s' % msg)
            output += _('(unknown search state: %s)' % su.escape(msg))

        return output + '</p>'

    def render_json(self, response_data, set_mime='text/json'):
        return BaseController().render_json(response_data, set_mime=set_mime)
