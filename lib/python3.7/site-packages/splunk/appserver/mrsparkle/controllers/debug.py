from __future__ import absolute_import
import sys
import cherrypy
import splunk
from  splunk.appserver.mrsparkle import MIME_HTML
from  splunk.appserver.mrsparkle import MIME_TEXT

from splunk.appserver.mrsparkle.controllers.config import ConfigController
from splunk.appserver.mrsparkle.lib.module import moduleMapper
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import DEFAULT_REMOTE_USER_HEADER
from splunk.appserver.mrsparkle.lib.decorators import SPLUNKWEB_SSO_MODE_CFG
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import filechain
import logging
import splunk.util
import os
import splunk.rest
import splunk.entity as en
import splunk.search as se
import splunk.auth as au
import __main__

from splunk.appserver.mrsparkle.controllers import view

logger = logging.getLogger('splunk.appserver.controllers.debug')

class DebugController(BaseController):
    
    def web_debug_conf_check(self):
        if cherrypy.config.get('enableWebDebug') is not True:
            self.raise_403_error()

    """/debug"""

    #@route('/:p=status')
    # @expose_page(methods='GET')
    def status(self, **args):
        '''
        Provides a debug output page for appserver config
        '''
        hasReadPerms = self._hasReadPerms()

        # get overview items
        general = splunk.util.OrderedDict()
        general['Appserver boot path'] = getattr(__main__, '__file__', '<N/A>')
        general['Splunkd URI'] = splunk.mergeHostPath()
        general['Debug Mode'] = __debug__

        # get various dicts
        configController = ConfigController()
        uiConfig = configController.index(asDict=True)

        mm = moduleMapper
        moduleMap = mm.getInstalledModules()

        uiPanels = splunk.util.OrderedDict()
        uiPanels['config'] = uiConfig
        uiPanels['views'] = en.getEntities(view.VIEW_ENTITY_CLASS, namespace=splunk.getDefault('namespace'))
        uiPanels['modules'] = moduleMap
        uiPanels['cherrypy'] = cherrypy.config
        uiPanels['request'] = args
        uiPanels['wsgi'] = cherrypy.request.wsgi_environ

        splunkdPanels = splunk.util.OrderedDict()

        #code to display splunkd debug information as well
        try:
            serverResponse, serverContent = splunk.rest.simpleRequest('/services/debug/status')
            atomFeed = splunk.rest.format.parseFeedDocument(serverContent)
            atomFeed_prim = atomFeed.toPrimitive()
            general['Splunkd time'] = splunk.util.getISOTime(atomFeed.updated)
            general['Splunkd home'] = atomFeed_prim.get('SPLUNK_HOME', '&lt;unknown&gt;')

            for key in atomFeed_prim:
                splunkdPanels[key] = atomFeed_prim[key]

        except splunk.AuthenticationFailed as e:
            splunkdPanels['errors'] = 'The appserver is not authenticated with splunkd; retry login'

        except splunk.SplunkdConnectionException as e:
            splunkdPanels['errors'] = 'The appserver could not connect to the splunkd instance at: %s' % splunk.mergeHostPath()

        except Exception as e:
            splunkdPanels['errors'] = 'Unhandled exception: %s' % str(e)


        cherrypy.response.headers['content-type'] = MIME_HTML

        return self.render_template('debug/status.html', {
            'uiPanels': uiPanels,
            'splunkdPanels': splunkdPanels,
            'appserverTime': splunk.util.getISOTime(),
            'general': general,
            'hasReadPerms': hasReadPerms
        })


    def _hasReadPerms(self):
        '''
        Use services/server/settings as a proxy for read permissions.
        '''

        # NOTE:Due SPL-21113 BETA: unify ACL actions to read/write we cannot use the settings endpoint defer to user admin for now.
        return True if 'admin' == au.getCurrentUser()['name'] else False

        entity = None
        try:
            entity = en.getEntity('/server/', 'settings', namespace=splunk.getDefault('namespace'))
        except Exception as e:
            return False
        if not entity['eai:acl']:
            return False
        if not entity['eai:acl']['perms']:
            return False
        if au.getCurrentUser()['name'] in entity['eai:acl']['perms'].get('read', []):
            return True
        else:
            return False

    @route('/:p=reset')
    def reset(self, **kwargs):
        '''
        Resets the user space to a clean state; usually used for testingm
        '''
        self.web_debug_capability_check()
        has_perms = True if 'admin'==au.getCurrentUser()['name'] else False
        jobs_cancelled = []
        if has_perms and cherrypy.request.method=='POST':
            jobs = se.listJobs()
            for job in jobs:
                try:
                    j = se.getJob(job['sid'])
                    j.cancel()
                    jobs_cancelled.append(job['sid'])
                except splunk.ResourceNotFound:
                    continue
        return self.render_template('debug/reset.html', {
            'has_perms': has_perms,
            'method': cherrypy.request.method,
            'jobs_cancelled': jobs_cancelled
        })

    @expose_page(must_login=False, methods=['GET', 'POST'])
    def echo(self, **kw):
        '''echos incoming params'''
        self.web_debug_conf_check()
        output = {
            'headers': cherrypy.request.headers,
            'params': cherrypy.request.params
        }

        return self.render_template('debug/echo.html', output)


    @expose_page()
    def refresh(self, entity=None, **kwargs):
        '''
        Forces a refresh on splunkd resources

        This method calls a splunkd refresh on all registered EAI handlers that
        advertise a reload function.  Alternate entities can be specified by appending
        them via URI parameters.  For example,

            http://localhost:8000/debug/refresh?entity=admin/conf-times&entity=data/ui/manager

        will request a refresh on only 'admin/conf-times' and 'data/ui/manager'.

        1) not all splunkd endpoints support refreshing.
        2) auth-services is excluded from the default set, as refreshing that system will
           logout the current user; use the 'entity' param to force it
        3) remote_index endpoint is configured for CLI use as it requires APP Name and APP Location to be passed to it as arguments
        '''
        # added this endpointExclusionList for SPL-147061 
        endpointExclusionList = ['admin/remote_indexes', 'admin/fshpasswords']

        method = cherrypy.request.method
        if method == 'GET':
            return """<html><body>
            <form method="post">
            <input type="hidden" name="splunk_form_key" value="%s">
            <input type="submit" value="Refresh">
            </form></body></html>""" % util.getFormKey()
        elif method == 'POST':
            # get auto-list of refreshable EAI endpoints
            self.web_debug_capability_check()
            allEndpoints = en.getEntities('admin', namespace="search")
            eligibleEndpoints = {}

            for name in allEndpoints:
                for link in allEndpoints[name].links:
                    if link[0] == '_reload':
                        logger.debug('FOUND reload for %s' % name)
                        eligibleEndpoints[name] = allEndpoints[name]
                        break

            if isinstance(entity, list):
                entityPaths = entity
            elif isinstance(entity, splunk.util.string_type):
                entityPaths = [entity]
            else:
                # seed manual endpoints
                entityPaths = [
                    'admin/conf-times',
                    'data/ui/manager',
                    'data/ui/nav',
                    'data/ui/views'
                ]

                # add capable endpoints
                for name in sorted(eligibleEndpoints):
                    if name in ['auth-services']: # refreshing auth causes logout
                        continue
                    if sys.platform == 'win32' and name == 'fifo':
                        # splunkd never loads FIFO on windows, but advertises it anyway
                        continue
                    entityPaths.append('%s/%s' % (allEndpoints[name].path, allEndpoints[name].name))


            cherrypy.response.headers['content-type'] = MIME_TEXT

            output = ['Entity refresh control page']
            output.append('=' * len(output[0]))
            output.append("'''")
            output.append(self.refresh.__doc__.strip())
            output.append("'''")
            output.append('')

            # call refresh on each
            for path in entityPaths:
                try:
                    if path not in endpointExclusionList:
                        en.refreshEntities(path, namespace='search', owner='nobody')
                        output.append(('Refreshing %s' % path).ljust(40, ' ') + 'OK')
                except Exception as e:
                    logger.exception(e)
                    msg = e
                    if hasattr(e, 'extendedMessages') and e.extendedMessages:
                        msg = e.extendedMessages[0]['text']
                    output.append(('Refreshing %s' % path).ljust(43, ' ') + e.__class__.__name__ + ' '
                                  + splunk.util.unicode(msg))

            output.append('DONE')
            return '\n'.join(output)

    @expose_page()
    def clear_cache(self, **unused):
        self.web_debug_capability_check()
        if cherrypy.request.method == 'POST':
            filechain.clear_cache()
            return 'Cache clear requested.'

        return '''
            <html><form method="POST">
            <input type="hidden" name="splunk_form_key" value="%s"/>
            <button type="submit">Clear minification cache</button>
            </form></html>
        ''' % util.getFormKey()
