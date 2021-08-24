from __future__ import absolute_import
from splunk.util import cmp

import cherrypy
import os
from cherrypy import expose
import splunk.appserver.mrsparkle # bulk edit

from splunk.appserver.mrsparkle.lib import i18n

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level

from splunk.appserver.mrsparkle.lib import util

import splunk.auth
import logging

import splunk.entity as en

from splunk.appserver.mrsparkle.lib.decorators import expose_page

# pull in active controllers
from splunk.appserver.mrsparkle.controllers.account import AccountController

from splunk.appserver.mrsparkle.controllers.admin import AdminController
from splunk.appserver.mrsparkle.controllers.alerts import AlertsController
from splunk.appserver.mrsparkle.controllers.alertswizard import AlertsWizardController
from splunk.appserver.mrsparkle.controllers.alertswizardv2 import AlertsWizardV2Controller
from splunk.appserver.mrsparkle.controllers.appnav import AppNavController
from splunk.appserver.mrsparkle.controllers.config import ConfigController
from splunk.appserver.mrsparkle.controllers.dashboardshare import DashboardShareController
from splunk.appserver.mrsparkle.controllers.dashboardwizard import DashboardWizardController
from splunk.appserver.mrsparkle.controllers.debug import DebugController
from splunk.appserver.mrsparkle.controllers.embed import EmbedController
from splunk.appserver.mrsparkle.controllers.field import FieldController
from splunk.appserver.mrsparkle.controllers.lists import ListsController
from splunk.appserver.mrsparkle.controllers.messages import MessagesController
from splunk.appserver.mrsparkle.controllers.module import ModuleController
from splunk.appserver.mrsparkle.controllers.parser import ParserController
from splunk.appserver.mrsparkle.controllers.paneleditor import PanelEditorController
from splunk.appserver.mrsparkle.controllers.prototype import PrototypeController
from splunk.appserver.mrsparkle.controllers.proxy import ProxyController
from splunk.appserver.mrsparkle.controllers.search import SearchController
from splunk.appserver.mrsparkle.controllers.tags import TagsController
from splunk.appserver.mrsparkle.controllers.utility import UtilityController
from splunk.appserver.mrsparkle.controllers.view import ViewController
from splunk.appserver.mrsparkle.controllers.savedsearchredirect import SavedSearchRedirectController
from splunk.appserver.mrsparkle.controllers.savesearchwizard import SaveSearchWizardController
from splunk.appserver.mrsparkle.controllers.searchhelper import SearchHelperController
from splunk.appserver.mrsparkle.controllers.ifx import IFXController
from splunk.appserver.mrsparkle.controllers.etb import ETBController
from splunk.appserver.mrsparkle.controllers.viewmaster import ViewmasterController
from splunk.appserver.mrsparkle.controllers.scheduledigestwizard import ScheduleDigestWizardController
from splunk.appserver.mrsparkle.controllers.tree import TreeController
from splunk.appserver.mrsparkle.controllers.custom import CustomController
from splunk.appserver.mrsparkle.controllers.scheduledviews import ScheduledViewController
from splunk.appserver.mrsparkle.controllers.i18n_catalog import I18NCatalogController
from splunk.appserver.mrsparkle.controllers.error import ErrorController



# this must be imported after the controllers.
from splunk.appserver.mrsparkle.lib.module import moduleMapper

logger = logging.getLogger('splunk.appserver.controllers.top')

class APIController(BaseController):
    pass

class TopController(BaseController):
    # set base endpoint controllers
    account = AccountController()
    # this change was for the URL structure. file is still admin.py
    manager = AdminController()
    api = APIController()
    app = ViewController()
    alerts = AlertsController()
    alertswizard = AlertsWizardController()
    alertswizardv2 = AlertsWizardV2Controller()
    config = ConfigController()
    appnav = AppNavController()
    dashboardshare = DashboardShareController()
    dashboardwizard = DashboardWizardController()
    debug = DebugController()
    embed = EmbedController()
    field = FieldController()
    lists = ListsController()
    messages = MessagesController()
    module = ModuleController()
    parser = ParserController()
    paneleditor = PanelEditorController()
    prototype = PrototypeController()
    search = SearchController()
    tags = TagsController()
    splunkd = ProxyController()
    util = UtilityController()
    savesearchwizard = SaveSearchWizardController()
    savedsearchredirect = SavedSearchRedirectController()
    scheduledigestwizard = ScheduleDigestWizardController()
    shelper = SearchHelperController()
    ifx = IFXController()
    etb = ETBController()
    viewmaster = ViewmasterController()
    tree = TreeController()
    custom = CustomController()
    scheduledview = ScheduledViewController()
    i18ncatalog = I18NCatalogController()
    error = ErrorController()

    @expose_page(must_login=False)
    def admin(self):
        '''
        redirect to manager in case old admin url is hit.
        '''
        self.redirect_to_url('/manager')

    @expose_page()
    def index(self):
        '''
        Serves the root of the webserver
        '''
        # If the license is expired, redirect to the licensing endpoint.
        # Since we have no way of determining if the user has permissions to change
        # licenses, there is still the chance that a basic user could hit the root
        # endpoint and get redirected to licensing by hitting "/" with an expired license.
        if cherrypy.config['license_state'] == 'EXPIRED':
           return self.redirect_to_url('/licensing', _qs={'return_to': cherrypy.request.relative_uri})

        return self.redirect_to_url('/app/%s' % splunk.auth.getUserPrefs('default_namespace'))

    @expose_page(must_login=False)
    def login(self):
        """Legacy 3.x login url"""
        return self.redirect_to_url('/account/login')

    @expose_page(must_login=False)
    def info(self):
        """
        Provides table of contents for all locally hosted resources
        """

        # gather all of the XML schema files
        dir = util.make_splunkhome_path(['share', 'splunk', 'search_mrsparkle', 'exposed', 'schema'])
        schemaFiles = [x[0:-4] for x in os.listdir(dir) if x.endswith('.rnc')]
        return self.render_template('top/info.html', {'schemaFiles': schemaFiles})

    @expose_page(must_login=False)
    def licensing(self, return_to=None, **unused):
        if util.isLite():
            return self.redirect_to_url('/manager/system/licensing/')

        return self.redirect_to_url('/manager/system/licensing/switch', _qs={'return_to': return_to})

    @expose_page(must_login=False)
    def paths(self):
        """
        Generates an HTML page documenting accessible paths on this site
        and the methods responsible for generating them
        """
        mappings = util.urlmappings(self, cherrypy.request.script_name+'/', exclude=cherrypy.request.script_name+'/api')
        mappings.sort(key=lambda x: x['path'])
        paths = [ (i, data['path']) for (i, data) in enumerate(mappings) ]
        return self.render_template('top/paths.html', { 'pathnames' : paths, 'mappings' : mappings })

    @expose_page(must_login=True)
    def modules(self, **kwargs):
        """
        Generates an HTML page documenting all registered modules
        """
        definitions = moduleMapper.getInstalledModules()
        names = sorted(definitions.keys())

        # pull out additional meta info
        groupedNames = []
        for module in definitions:
            definitions[module]['isAbstract'] = True if module.find('Abstract') > -1 else False
            definitions[module]['isPrototype'] = True if definitions[module]['path'].find('/prototypes') > -1 else False

            # get general classification from folder path
            group = 'Base'
            try:
                folders = definitions[module]['path'].split(os.sep)
                pivot = folders.index('search_mrsparkle')
                if pivot > -1 and folders[pivot + 1] == 'modules' and len(folders) > (pivot + 2):
                    group = folders[pivot + 2]
            except Exception as e:
                logger.error(e)
            groupedNames.append((group, module))
        groupedNames.sort()


        show_wiki = True if 'show_wiki' in kwargs else False
        return self.render_template('top/modules.html', {
            'modules': definitions,
            'names': names ,
            'show_wiki': show_wiki,
            'groupedNames': groupedNames
        })

    @expose_page(must_login=False)
    @set_cache_level('never')
    def help(self, **kwargs):
        """
        Redirects user to context-sensitive help
        """

        locale = i18n.current_lang_url_component()
        location = kwargs.get('location', '')
        productType = cherrypy.config.get('product_type')
        isEnterpriseCloud = util.isCloud() and not util.isLite()

        params = {
            'location': location,
            'license': 'free' if cherrypy.config.get('is_free_license') else 'pro',
            'installType': 'trial' if cherrypy.config.get('is_trial_license') else 'prod',
            'versionNumber': cherrypy.config.get('version_label'),
            'skin': 'default',
            'locale': locale,
            'product': 'cloud' if isEnterpriseCloud else productType
        }
        return self.render_template('top/help.html', {'help_args': params})

    @expose_page(must_login=False)
    def redirect(self, **kwargs):
        """
        Simple url redirector. Expects 'to' arg to contain the target url. External links must
        begin with the protocol.
        """
        referer = cherrypy.request.headers.get("Referer", "")
        base = cherrypy.request.base

        if not referer.startswith(base):
           raise cherrypy.HTTPError(403, _('Splunk will not redirect if the referring web page is not Splunk itself.'))

        raise cherrypy.HTTPRedirect(kwargs.get('to'))

    @expose_page()
    def _bump(self, **kwargs):
        """
        Bumps push_version so that clients are forced to reload static resources.
        Static resources are currently under /static/@12345.  If the bump number
        is non-zero, then the URI becomes /static/@12345.6, where '6' is the
        bump number.

        Usage:

            POST /splunk/_bump
        """
        self.web_debug_capability_check()
        if cherrypy.request.method == 'POST':
            self.incr_push_version()
            logger.info('appserver static bump number set to %s' % self.push_version())
            return "Version bumped to %i" % self.push_version()
        return """<html><body>Current version: %i<br>
            <form method=\"post\">
            <input type="hidden" name="splunk_form_key" value="%s">
            <input type=\"submit\" value=\"Bump versions\">
            </form></body></html>""" % (self.push_version(), util.getFormKey())


# Copy TopControllers attributes into the APIController, except for api to avoid recursion
[ setattr(APIController, attr, TopController.__dict__[attr]) for attr in TopController.__dict__ if attr[:2]!='__' and attr!='api' ]
