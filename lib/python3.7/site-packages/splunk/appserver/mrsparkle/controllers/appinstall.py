"""
App installation/upgrade controller
lives at /manager/appinstall

ahebert 10/12/2016: The app installation flow is not using this controller anymore. It's all using backbone modals.

"""

import cherrypy
import os.path 
import shutil 
import tempfile 
from future.moves.urllib import parse as urllib_parse
import logging
import xml.etree.cElementTree as et 

import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import cached
from splunk.appserver.mrsparkle.lib import module
from splunk.appserver.mrsparkle.lib.capabilities import Capabilities
from splunk.appserver.mrsparkle.lib.memoizedviews import memoizedViews
from splunk.appserver.mrsparkle.lib.msg_pool import MsgPoolMgr, UI_MSG_POOL
from splunk.appserver.mrsparkle.lib.statedict import StateDict
from splunk.appserver.mrsparkle.lib.util import parse_breadcrumbs_string
from splunk.appserver.mrsparkle.lib.util import reset_app_build
from splunk.appserver.mrsparkle.lib.util import isLite
from splunk.appserver.mrsparkle.lib.util import isCloud
import splunk.rest as rest
import splunk.entity as en
import splunk
import splunk.util

APP_INSTALL_TIMEOUT = 600

logger = logging.getLogger('splunk.appserver.controllers.appinstall')


class SBLoginException(Exception): pass
class SBInvalidLoginException(SBLoginException): pass
class SBNotConnectedException(SBLoginException): pass
class SBFileUploadException(Exception): pass


class AppInstallController(BaseController, Capabilities):

    def getLocalApp(self, appid, app_name=None, flush_cache=True):
        """
        Fetch details on a locally installed app, optionally ensuring the cache is flushed first
        """
        local_apps = cached.getEntities('apps/local', count=-1, __memoized_flush_cache=flush_cache)
        for id, app in local_apps.items(): # local_apps is not an instance of dictionary
            if self.getSbAppId(app).lower() == appid.lower() or app.get('label', appid) == app_name:               #if id.lower() == appid or app.get('label', appid) == app_name:
                return app
        if appid in local_apps:
            # if we haven't found a match yet, then the app doesn't have packageid - fall back to treating the appid as local
            return local_apps[appid]
        return None

    def splunkbaseLogin(self, username, password):
        try:
            response, content = rest.simpleRequest('/apps/remote/login', postargs={'username' : username, 'password' : password})
        except splunk.SplunkdConnectionException as e:
            logger.error("Splunkd connection error: %s" % e)
            raise SBNotConnectedException()
        except splunk.AuthorizationFailed as e:
            logger.warn("Invalid credentials: %s" % e)
            raise SBInvalidLoginException()

        if response.status == 400:
            logger.warn("Invalid Splunkbase credentials")
            raise SBInvalidLoginException()

        if response.status not in [200, 201]:
            return None
            
        root = et.fromstring(content)
        sbKey = cherrypy.session['sbSessionKey'] = root.findtext('sessionKey')

        return sbKey

    def supports_blacklist_validation(self):
        """
        Overridden this method from BaseController!
        """
        return True

    def getSBSessionKey(self):
        """
        Fetch the user's logged in splunkbase session key
        """
        return cherrypy.session.get('sbSessionKey')

    def getRemoteAppEntry(self, sbAppId):
        """
        Used to determine whether the app is available on Splunkbase and whether splunkd can even talk to Splunkbase.
        Unfortunately, this end point doesn't return the object type ('app' or 'addon'), so every object will be called app.
        """
        return en.getEntity('/apps/remote/entriesbyid', sbAppId)

    def isRestartRequired(self):
        """Query the messages endpoint to determine whether a restart is currently required"""
        try:
            rest.simpleRequest('/messages/restart_required')
            return True
        except splunk.ResourceNotFound:
            return False

    def appNeedsSetup(self, app):
        """Returns true if the passed in app needs to be setup to continue"""
        return app.getLink('setup') and app['configured'] == '0'

    def appUpgradeAvailable(self, app):
        """Returns true if the passed in app has an upgrade available for install from Splunkbase"""
        return app.getLink('update')

    def appIsDisabled(self, app):
        """Returns true if the app is disabled"""
        return app['disabled'] == '1'

    def getSetupURL(self, appid, state):
        """Build the URL to an app's setup page, setting the return url to be this controller's checkstatus page"""
        return self.make_url(['manager', appid, 'apps', 'local', appid, 'setup'], _qs={
            'action': 'edit',
            'redirect_override': self.make_url(['manager', 'appinstall', appid, 'checkstatus'], translate=False, _qs={
                'state': state.serialize()
                })
            })

    def getSbAppId(self, entity):
        sbAppId = ''
        if 'details' in entity and ('/' in entity['details']):
            sbAppId = entity['details'][entity['details'].rfind('/')+1:]
        return sbAppId

    def processAppUpload(self, f, force):
        """
        Process a file uploaded from the upload page
        """
        if not (isinstance(f, cherrypy._cpreqbody.Part) and f.file):
            raise SBFileUploadException(_("No file was uploaded."))

        # Copy uploaded data to a named temporary file
        fd, tmpPath = tempfile.mkstemp()
        tfile = os.fdopen(fd, "wb+")
        shutil.copyfileobj(f.file, tfile)
        tfile.flush() # leave the file open, but flush so it's all committed to disk

        try:
            args = { 'name': tmpPath, 'filename' : 1 }
            if force: 
                args['update'] = 1
            response, content = rest.simpleRequest('apps/local', postargs=args)
            uploadFailure = "There was an error processing the upload."

            if response.status in (200, 201):
                atomFeed = rest.format.parseFeedDocument(content)
                content = atomFeed[0].toPrimitive()
                sbAppId = content['name']
                if 'details' in content:
                    details = content['details']
                    sbAppId = details[details.rfind('/')+1:]
                return sbAppId
            elif response.status == 409:
                raise SBFileUploadException(_("App with this name already exists. Select upgrade app to overwrite the existing app."))
            elif response.messages and len(response.messages) > 0 and 'text' in response.messages[0]:
                raise SBFileUploadException(_(uploadFailure + response.messages[0]['text']))
            else:
                raise SBFileUploadException(_(uploadFailure))
        except splunk.AuthorizationFailed:
            raise SBFileUploadException(_("Client is not authorized to upload apps."))
        finally:
            shutil.rmtree(tmpPath, True)



    def render_admin_template(self, *a, **kw):
        # use the AdminController's render_admin_template method for now
        # this won't be required once we remove modules from manager

        # get the manager controller
        manager = cherrypy.request.app.root.manager
        return manager.render_admin_template(*a, **kw)


    @route('/:appid')
    @expose_page(must_login=True)
    def start(self, appid, app_name=None, return_to=None, return_to_success=None, breadcrumbs=None, implicit_id_required=None, error=None, state=None, **kw):
        """
        The main entry point upgrading an app
        params:
        appid - splunkbase app id
        app_name - label of the app
        return_to - optional return address on completion
        return_to_success - optional return address used in favour or return_to if the app install is succesful
        breadcrumbs - pipe separated list of name|url tuples.  tuples themselves are joined by tabs.
        error - internally used error message
        state - internally used StateDict object
        """

        current_app = self.getLocalApp(appid, app_name)

        # state is a dict sublcass for storing things like the return_to url
        # that can be serialized to a URL-safe string by calling .serialize() on it
        # and restored by passing the raw data to StateDict.unserialize()
        if state:
            state = StateDict.unserialize(state)
            breadcrumbs = state['breadcrumbs']
        else:
            breadcrumbs = parse_breadcrumbs_string(breadcrumbs)
            installBreadcrumbText = _('Update app')
            breadcrumbs.append([installBreadcrumbText, None])
            if isLite():
                breadcrumbs[-2] = ['apps local', self.make_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], translate=False)]
            state = StateDict({
                'app_name': app_name,
                'return_to': return_to if splunk.util.isRedirectSafe(return_to) else self.make_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], translate=False),
                'return_to_success': return_to_success,
                'breadcrumbs': breadcrumbs,
                'implicit_id_required': implicit_id_required
                })

        if current_app:
            # check whether a newer version is available
            if self.appUpgradeAvailable(current_app):
                state['implicit_id_required'] = current_app.get('update.implicit_id_required', None)
                remote_app = self.getRemoteAppEntry(appid);
                return self.render_admin_template('/admin/appinstall/upgrade-available.html', {
                    'app': current_app,
                    'appid': appid,
                    'appname': app_name,
                    'breadcrumbs': breadcrumbs,
                    'error': error,
                    'state': state,
                    'app_license': remote_app['license'],
                    'app_license_url': remote_app['licenseUrl']
                })

            if self.isRestartRequired() or self.appNeedsSetup(current_app):
                # app is installed but hasn't been setup, or a restart is required
                return self.redirect_to_url(['/manager/appinstall', appid, 'checkstatus'], {
                    'state': state.serialize()
                    })

            # else the app is already installed and no upgrades are available
            return self.render_admin_template('/admin/appinstall/already-installed.html', {
                'app': current_app,
                'visible': current_app.get('visible'),
                'disabled': current_app.get('disabled'),
                'appid': appid,
                'state': state,
                'breadcrumbs': breadcrumbs
            })
        else:
            # 6.3 onwards new backbone based install flow is used, but upgrade flow still goes through
            # this python controller, regardless of flavor.
            if isLite() or isCloud():
                self.deny_access('AppInstall:start endpoint not supported in this environment.')
                
        # see whether the app exists on Splunkbase (and thus whether Splunkbase is even reachable)
        try:
            remote_app = self.getRemoteAppEntry(appid)
        except splunk.ResourceNotFound:
            # app doesn't exist on splunkbase; allow for manual upload
            return self.render_admin_template('/admin/appinstall/app-not-found.html', {
                'appid': appid,
                'breadcrumbs': breadcrumbs,
                'state': state
            })
        except splunk.RESTException as e:
            if e.statusCode == 503:
                # splunkd will return 503 if it's configured not to contact splunkbase
                error = None
            else:
                # else something else went wrong
                error = str(e)
            return self.render_admin_template('/admin/appinstall/no-internet.html', {
                'appid': appid,
                'breadcrumbs': breadcrumbs,
                'state': state,
                'error': error
            })

        sbKey = self.getSBSessionKey()
        if sbKey:
            # user is already logged in, ready to go
            # display a template confirming that they really want to do the install
            return self.render_admin_template('/admin/appinstall/ready-to-install.html', {
                'appid': appid, 
                'appname': remote_app['appName'],
                'breadcrumbs': breadcrumbs,
                'error': error,
                'install_url': self.make_url(['/manager/appinstall', appid, 'install'], _qs={'state': state.serialize()}),
                'state': state,
                'app_license': remote_app['license'],
                'app_license_url': remote_app['licenseUrl']
            })

        # login required
        return self.render_admin_template('/admin/appinstall/sb-login.html', {
            'appid': appid,
            'breadcrumbs': breadcrumbs,
            'error': error,
            'state': state,
            'next': 'install',
            'app_license': remote_app['license'],
            'app_license_url': remote_app['licenseUrl']
        })

                
    @route('/:appid=_upload', methods=['GET', 'POST'])
    @expose_page(must_login=True)
    def upload(self, appid, return_to=None, breadcrumbs=None, state=None, appfile=None, force=None, **kw):
        """
        Present a form for direct upload of an app
        """
        
        if not self.can_create_entity('apps/local'):
            self.deny_access()
        
        # display upload form; Do not show in cloud (404)
        if isCloud():
            raise cherrypy.HTTPError(404, _('Page cannot be found.'))
        else:
            if state:
                state = StateDict.unserialize(state)
                breadcrumbs = state.get('breadcrumbs')
            else:
                breadcrumbs = parse_breadcrumbs_string(breadcrumbs)
                breadcrumbs.append([_('Upload app'), None])
                state = StateDict({
                    'return_to': return_to if splunk.util.isRedirectSafe(return_to) else self.make_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], translate=False),
                    'breadcrumbs': breadcrumbs
                    })
            error = None
            if appfile is not None and cherrypy.request.method == 'POST':
                try:
                    force = (force == '1')
                    sbAppId = self.processAppUpload(appfile, force)
                    module.moduleMapper.resetInstalledModules()
                    memoizedViews.clearCachedViews()
                    return self.checkstatus(sbAppId, state=state)
                except SBFileUploadException as e:
                    error = e.args[0]
                except splunk.RESTException as e:
                    error = e.get_extended_message_text()
                except cherrypy.HTTPRedirect as e:
                    raise e
                except Exception as e:
                    error = e.args[0]

            return self.render_admin_template('/admin/appinstall/upload-app.html', {
                'appid': appid,
                'breadcrumbs': state.get('breadcrumbs'),
                'error': error,
                'state': state
            })


    @route('/:appid/:login=login', methods='POST')
    @expose_page(must_login=True)
    def login(self, appid, login, sbuser, sbpass, next, state, **kw):
        """
        Receive the Splunkbase login credentials from the login form and start the install
        """

        remote_app = self.getRemoteAppEntry(appid)

        state = StateDict.unserialize(state)
        try:
            error = None
            sbSessionKey = None        
            sbSessionKey = self.splunkbaseLogin(sbuser, sbpass)
        except SBInvalidLoginException:
            error = _("Invalid username/password")
        except SBNotConnectedException:
            # let the user know that Splunkd either can't see the Internet or
            # has been configured not to talk to Splunkbase
            return self.render_admin_template('/admin/appinstall/no-internet.html', {
                'appid': appid,
                'breadcrumbs': state['breadcrumbs'],
                'state': state
            })

        if not sbSessionKey:
            return self.render_admin_template('/admin/appinstall/sb-login.html', {
                'appid': appid,
                'breadcrumbs': state['breadcrumbs'],
                'error': error,
                'state': state,
                'next': next,
                'app_license': remote_app['license'],
                'app_license_url': remote_app['licenseUrl']
            })

        if next == 'install':
            # display a template confirming that they really want to do the install
            return self.render_admin_template('/admin/appinstall/ready-to-install.html', {
                'appid': appid, 
                'appname': remote_app['appName'],
                'breadcrumbs': state['breadcrumbs'],
                'error': error,
                'install_url': self.make_url(['/manager/appinstall', appid, 'install'], _qs={'state': state.serialize()}),
                'state': state,
                'app_license': remote_app['license'],
                'app_license_url': remote_app['licenseUrl']
            })
        return self.update(appid, state=state)


    @route('/:appid/:install=install', methods='POST')
    @expose_page(must_login=True)
    def install(self, appid, state, install=None, **kw):
        """
        Start the app download and installation processs
        """

        remote_app = self.getRemoteAppEntry(appid)

        if not isinstance(state, StateDict):
            state = StateDict.unserialize(state)
        sbSessionKey = self.getSBSessionKey()
        if not sbSessionKey:
            logger.warn("Attempted install of app '%s' with sbSessionKey unset" % appid)
            return self.redirect_to_url(['/manager/appinstall/', appid], _qs={'error': _('Splunkbase login failed'), 'state': state.serialize()}) 

        # don't hold the session lock through network I/O
        cherrypy.session.release_lock()

        # attempt to actually install the app
        url = 'apps/remote/entriesbyid/%s' % appid
        requestArgs = {'action': 'install', 'auth': urllib_parse.quote(sbSessionKey)}
        try:
            logger.info("Installing app %s" % appid)
            response, content = rest.simpleRequest(url, postargs=requestArgs, timeout=APP_INSTALL_TIMEOUT)
        except splunk.AuthenticationFailed:
            # login expired
            return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('Splunkbase login timed out'), 'state': state.serialize()})
        except Exception as e:
            logger.exception(e)
            if e.statusCode == 403:
                return self.render_admin_template('/admin/appinstall/sb-login.html', {
                    'appid': appid,
                    'breadcrumbs': state['breadcrumbs'],
                    'error': _('Splunkbase login timed out'),
                    'state': state,
                    'next': install,
                    'app_license': remote_app['license'],
                    'app_license_url': remote_app['licenseUrl']
                })
            else:
                return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('An error occurred while downloading the app: %s') % str(e), 'state': state.serialize()})

        if response.status not in [200, 201]:
            return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('An error occurred while installing the app: %s - %s') % (str(response.status), content), 'state': state.serialize()})

        module.moduleMapper.resetInstalledModules()
        memoizedViews.clearCachedViews()
        logger.info("App %s installed" % appid)
        return self.checkstatus(appid, state=state)


    @route('/:appid/:update=update', methods='POST')
    @expose_page(must_login=True)
    def update(self, appid, state, update=None, **kw):
        """
        Attempt to download and install an app update from Splunkbase
        """

        remote_app = self.getRemoteAppEntry(appid)
        local_app = self.getLocalApp(appid)

        if not isinstance(state, StateDict):
            state = StateDict.unserialize(state)
        sbSessionKey = self.getSBSessionKey()
        if not sbSessionKey:
            # login required
            return self.render_admin_template('/admin/appinstall/sb-login.html', {
                'appid': appid,
                'breadcrumbs': state['breadcrumbs'],
                'state': state,
                'next': 'update',
                'app_license': remote_app['license'],
                'app_license_url': remote_app['licenseUrl']
            })
        url = 'apps/local/%s/update' % local_app.name
        requestArgs = {
            'auth': urllib_parse.quote(sbSessionKey),
            'implicit_id_required' : state.get('implicit_id_required')
        }
        try:
            logger.info("Updating app %s" % appid)
            response, content = rest.simpleRequest(url, postargs=requestArgs)
        except splunk.AuthenticationFailed:
            # login expired
            return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('Splunkbase login timed out'), 'state': state.serialize()})
        except Exception as e:
            if e.statusCode == 403:
                logger.exception(e)
                return self.render_admin_template('/admin/appinstall/sb-login.html', {
                    'appid': appid,
                    'breadcrumbs': state['breadcrumbs'],
                    'error': _('Splunkbase login timed out'),
                    'state': state,
                    'next': update
                })
            else:
                return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('An error occurred while downloading the app: %s') % str(e), 'state': state.serialize()})

        if response.status not in [200, 201]:
            return self.redirect_to_url(['/manager/appinstall', appid], _qs={'error': _('An error occurred while installing the app: %s') % str(response.status,), 'state': state.serialize()})

        reset_app_build(appid)
        module.moduleMapper.resetInstalledModules()
        memoizedViews.clearCachedViews()
        logger.info("App %s installed" % appid)
        return self.checkstatus(appid, state=state)

    @route('/:appid/:enable=enable', methods='POST')
    @expose_page(must_login=True)
    def enable(self, appid, state=None, app_name=None, return_to=None, breadcrumbs=None, enable=None, **kw):
        """Enable a disabled app"""
        if state:
            state = StateDict.unserialize(state)
            breadcrumbs = state.get('breadcrumbs')
        else:
            state = StateDict({
                'app_name': app_name,
                'return_to': return_to if splunk.util.isRedirectSafe(return_to) else self.make_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], translate=False),
                'breadcrumbs': breadcrumbs
                })
        entityURI = '/apps/local/'+appid+'/enable'
        en.controlEntity('enable', entityURI)
        logger.info("App %s enabled" % appid)
        return self.checkstatus(appid, state=state)


    @route('/:appid/:checkstatus=checkstatus', methods=['POST', 'GET'])
    @expose_page(must_login=True)
    def checkstatus(self, appid, state=None, app_name=None, return_to=None, checkstatus=None, **kw):
        """
        appid - splunkbase app id
        Check the status of the installed app
        Is the app enabled?  If not prompt for that
        Is a restart required? If so prompt for that
        Does the app need to be setup? If so prompt for that
        Else set a message and bounce the user back to the return_url
        """
        if state:
            if not isinstance(state, StateDict):
                state = StateDict.unserialize(state)
        else:
            state = StateDict({
                'app_name': app_name,
                'return_to': return_to if splunk.util.isRedirectSafe(return_to) else self.make_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], translate=False),
                })
        app = self.getLocalApp(appid, state.get('app_name'))
        if not app:
            logger.warn("Attempted to access appinstall/checkstatus point for non-installed app %s" % appid)
            return self.redirect_to_url(['/manager/appinstall', appid], _qs={'state': state.serialize()})

        if self.isRestartRequired():
            # check the user has restart privileges
            serverControls = en.getEntities("server/control")
            displayRestartButton = any(filter((lambda x: x[0] == 'restart'), serverControls.links))
            is_cloud = cherrypy.config['instance_type'] == 'cloud'
            return self.render_admin_template('/admin/appinstall/restart-required.html', {
                'displayRestartButton': displayRestartButton,
                'restart_target_url': self.make_url(['/manager/appinstall', appid, 'checkstatus'], _qs={'state': state.serialize()}),
                'breadcrumbs': state.get('breadcrumbs', []),
                'appid': appid,
                'state': state,
                'isCloud': is_cloud
            })
            
        # app is installed, does it need configuring?
        if self.appNeedsSetup(app):
            return self.render_admin_template('/admin/appinstall/setup-required.html', {
                'app': app,
                'state': state,
                'breadcrumbs': state.get('breadcrumbs', []),
                'setup_url': self.getSetupURL(appid, state)
            })

        if self.appIsDisabled(app):
            return self.render_admin_template('/admin/appinstall/enable-required.html', {
                'app': app,
                'appid': appid,
                'state': state,
                'breadcrumbs': state.get('breadcrumbs', [])
            })
            
        # else it's installed OK!
        try:
            msgid = MsgPoolMgr.get_poolmgr_instance()[UI_MSG_POOL].push('info', _('"%(appname)s" was installed successfully') % {'appname': app.get('label', appid)})
        except KeyError:
            msgid = ''
        return_to = state.get('return_to')
        return_to_success = state.get('return_to_success')
        if return_to_success:
            # an explicit success-page url was supplied
            return_to_success = return_to_success.replace('__appid__', splunk.util.safeURLQuote(appid))
            return self.redirect_to_url(return_to_success, _qs={'msgid': msgid})

        if return_to:
            # else use the default return to
            return self.redirect_to_url(return_to, _qs={'msgid': msgid})

        return self.redirect_to_url(['manager', splunk.getDefault('namespace'), 'apps', 'local'], _qs={'msgid': msgid})
