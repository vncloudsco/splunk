from builtins import map
import cherrypy
import logging
import random
import threading
import time
import os
import uuid

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import lock_session
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level


from splunk.appserver.mrsparkle.lib import decorators
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib import startup
from splunk.appserver.mrsparkle.lib import util

from splunk.models.user import User

import splunk
import splunk.auth
import splunk.bundle
import splunk.entity
import splunk.util

import logging
logger = logging.getLogger('splunk.appserver.controllers.account')

class AccountController(BaseController):
    """
    Handle logging in and logging out
    """

    # define filepath for successful login flag
    FLAG_FILE = util.make_splunkhome_path(['etc', '.ui_login'])

    # Store up to 100 credentials in memory during change password operations
    credential_cache = util.LRUDict(capacity=100)

    # The LRUDict is not thread safe; acquire a lock before operating with it
    credential_lock = threading.Lock()

    @expose_page(methods='GET')
    def index(self):
        return self.redirect_to_url('/')

    def genCookieTest(self):
        """ Creates a random cval integer """
        return random.randint(0, 2**31)

    def updateCookieTest(self):
        """ set a cookie to check that cookies are enabled and pass the value to the form """
        cval = cherrypy.request.cookie.get('cval')
        if cval:
            try:
                cval = int(cval.value)
            except:
                cval = self.genCookieTest()
        else:
            cval = self.genCookieTest()
        cherrypy.response.cookie['cval'] = cval
        if splunk.util.normalizeBoolean(cherrypy.config.get('enableSplunkWebSSL'), False):
            cherrypy.response.cookie['cval']['secure'] = 1
        return cval

    @expose_page(must_login=False, methods=['GET','POST'], verify_session=False)
    @set_cache_level('never')
    def proxy_login(self, username=None, password=None, return_to=None, cval=None, newpassword=None, **kwargs):
        server_info = splunk.rest.payload.scaffold()
        server_info['entry'][0]['content']['isFree'] = cherrypy.config['is_free_license']
        server_info['entry'][0]['content']['isTrial'] = cherrypy.config['is_trial_license']
        server_info['entry'][0]['content']['version'] = cherrypy.config['version_number']
        server_info['entry'][0]['content']['guid'] = cherrypy.config['guid']
        server_info['entry'][0]['content']['master_guid'] = cherrypy.config['master_guid']
        server_info['entry'][0]['content']['build'] = cherrypy.config['build_number']
        server_info['entry'][0]['content']['product_type'] = cherrypy.config['product_type']
        server_info['entry'][0]['content']['instance_type'] = cherrypy.config['instance_type']
        server_info['entry'][0]['content']['serverName'] = cherrypy.config['serverName']
        server_info['entry'][0]['content']['licenseState'] = cherrypy.config['license_state']
        server_info['entry'][0]['content']['cpu_arch'] = cherrypy.config['cpu_arch']
        server_info['entry'][0]['content']['os_name'] = cherrypy.config['os_name']
        server_info['entry'][0]['content']['license_labels'] = cherrypy.config['license_labels']
        session = splunk.rest.payload.scaffold()
        session['entry'][0]['content']['cval'] = self.updateCookieTest() #see method for server cookie setting logic
        session['entry'][0]['content']['time'] = int(time.time()) #used for server/client time delta comparison
        session['entry'][0]['content']['hasLoggedIn'] = self.hasLoggedIn() #see method for new login check
        """
        Description: session.entry[0].content.forcePasswordChange
        Toggle this session variable to
        1) Control if the skip password change link is present (bypass the enforcement)
        AND/OR
        2) The login/logout route (/:locale/account/login|logout) displays the change passpassword (/:locale/account/passwordchange) route content/form.
        """
        session['entry'][0]['content']['forcePasswordChange'] = False
        web = splunk.rest.payload.scaffold()
        web['entry'][0]['content']['login_content'] = cherrypy.config.get('login_content', '')
        web['entry'][0]['content']['enable_autocomplete_login'] = cherrypy.config.get('enable_autocomplete_login', '')
        web['entry'][0]['content']['updateCheckerBaseURL'] = cherrypy.config.get('updateCheckerBaseURL', '')
        data = {
            'app': '-',
            'page': 'account',
            'splunkd': {
                '/services/server/info': server_info,
                '/services/session': session,
                '/configs/conf-web': web
            }
        }
        return self.render_template('pages/base.html', data)

    @expose_page(must_login=False, methods=['GET'], verify_session=False)
    def sso_error(self, **kw):
        '''
        Called to tell user that SSO login worked, but no splunk user exists.
        '''
        return self.render_template('account/sso_error.html')

    @expose_page(must_login=False, verify_session=False, methods=['GET', 'POST'])
    def proxy_passwordchange(self, newpassword=None, confirmpassword=None, return_to=None, cval=None, **kwargs):
        return self.proxy_login(**kwargs)

    @expose_page(must_login=False, methods='GET')
    @set_cache_level('never')
    def proxy_logout(self, **kwargs):
        return self.proxy_login(**kwargs)

    def isAutoComplete(self):
        return splunk.util.normalizeBoolean(cherrypy.config.get('enable_autocomplete_login', True))


    def getServerInfo(self):
        '''
        Retrieve a python dictionary of the /services/server/info endpoint.
        '''

        output = {}
        for k in ['build_number', 'cpu_arch', 'version_label', 'is_free_license', 'is_trial_license', 'license_state', 'os_name', 'guid', 'master_guid', 'license_desc', 'install_type', 'addOns', 'activeLicenseGroup', 'product_type', 'instance_type']:
            output[k] = cherrypy.config.get(k)
        return output


    def setLoginFlag(self, setFlag=None):
        '''
        Persists a flag (via an empty file) that indicates if someone has
        successfully logged into the system before
        '''

        flagged = os.path.isfile(self.FLAG_FILE)

        try:
            if not flagged and setFlag:
                f = open(self.FLAG_FILE, 'w')
                f.close()
                logger.info('setting successful login flag to: true')
            elif flagged and not setFlag:
                os.remove(self.FLAG_FILE)
                logger.info('setting successful login flag to: false')

        except Exception as e:
            logger.error('Unable to set the login flag')
            logger.exception(e)


    def hasLoggedIn(self):
        '''
        Indicates if someone has logged into this system before.
        '''
        return os.path.isfile(self.FLAG_FILE)
