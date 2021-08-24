from __future__ import absolute_import
import cherrypy

from decorator import decorator
import json
import logging
import os

import splunk
import splunk.appserver.mrsparkle.lib.routes as routes
import splunk.appserver.mrsparkle.lib.startup as startup
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.list_helpers.formattermapper import FormatterMapper  # NOQA
import splunk.util

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.decorators')

ONLY_API=1
SPLUNKD_SESSION_KEY = 'sessionKey'

# SSO related constants
# These are referenced in account.py and debug.py
DEFAULT_REMOTE_USER_HEADER = 'REMOTE_USER'
REMOTE_USER_SESSION_KEY = 'REMOTE_USER'
SPLUNKWEB_REMOTE_USER_CFG = 'remoteUser'
SPLUNKWEB_TRUSTED_IP_CFG = 'trustedIP'
SPLUNKWEB_SSO_MODE_CFG = 'SSOMode'

def chain_decorators(fn, *declist):
    """
    Called from a decorator to chain other decorators together
    eg. chain_decorators(fn, require_login(), cherrypy.expose)
    """

    for dec in declist[::-1]: # wrap them in the same order as they'd be wrapped if they were used normally
        fn = dec(fn)

    @decorator
    def rundecs(_fn, *a, **kw):
        return fn(*a, **kw)

    return rundecs

def expose_page(must_login=True, handle_api=False, methods=None, verify_session=True, verify_sso=True, trim_spaces=False, respect_permalinks=False, embed=False):
    """
    Use this instead of cherrypy.expose
    Ensures that user's are logged in to view the page by default
    
    set handle_api=True to have requests beginning with /api sent to the handler 
    as well as non-api requests
    set handle_api=ONLY_API to have it only accept api requests
    (check cherrypy.request.is_api to see whether this is an api request if set to True)

    set methods to a list of method names to accept for this handler (default=any)

    set respect_permalinks=True when the route requires login and must support resurrecting the permalink info after login.
    """
    @decorator
    def check(fn, self, *a, **kw):
        if util.parse_xsplunkd_header().get('proxy_token') != cherrypy.config.get('proxy_token'):
            raise cherrypy.HTTPError(503, _('Cannot access appserver directly with appServerPorts configured.'))
        is_api = util.is_api()
        request = cherrypy.request

        if not handle_api and is_api:
            raise routes.RequestRefused(404)
        if handle_api is ONLY_API and not is_api:
            raise routes.RequestRefused(404)
        _methods = methods
        if _methods:
            if isinstance(_methods, splunk.util.string_type):
                _methods = [ _methods ]
            if request.method not in _methods:
                raise routes.RequestRefused(405)

        sessionKey = cherrypy.session.get(SPLUNKD_SESSION_KEY)
        # verify that version info is good; do it here so that any URI access
        # will trigger the check
        startup.initVersionInfo(sessionKey=sessionKey)

        # embed enabled handler
        if embed:
            util.embed_modify_request();
        else:
            cherrypy.request.embed = False

        # disallow access to blacklisted URLs
        if 'is_route_blacklisted' in dir(self):
            if self.is_route_blacklisted(self.__module__):
                raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found
        #else:
        #    logger.info('isRouteBlackListed NOT found in %s' % self.__module__)

        # add a convenience property to all request objects to get at the
        # current relative URI
        request.relative_uri = request.path_info + (('?' + request.query_string) if request.query_string else '')
        if cherrypy.config.get('root_endpoint') not in ['/', None, '']:
            request.relative_uri = cherrypy.config.get('root_endpoint') + request.relative_uri

        # CSRF protection -- on POST/PUT/DELETE
        if verify_session and not util.checkRequestForValidFormKey(requireValidFormKey=must_login):
            # checkRequestForValidFormKey() will raise an error if the request was an xhr
            return self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path()) ] )

        # set X-FRAME-OPTIONS header
        x_frame_options_sameorigin = splunk.util.normalizeBoolean(cherrypy.config.get("x_frame_options_sameorigin"))
        if x_frame_options_sameorigin:
            cherrypy.response.headers["X-FRAME-OPTIONS"] = "SAMEORIGIN"

        # basic input cleansing
        if trim_spaces:
            for key, value in kw.items():
                if isinstance(value, splunk.util.string_type):
                    kw[key] = value.strip()
                    if kw[key] != value:
                        logger.debug('Leading/trailing whitespaces were trimmed in "%s" argument' % key)

        return fn(self, *a, **kw)

    def dec(fn):
        if must_login:
            return chain_decorators(fn, check, sso_ip_validation(verify_sso), sso_check(), require_login(respect_permalinks), ExceptionHandler(), cherrypy.expose)(fn)
        else:
            return chain_decorators(fn, check, sso_ip_validation(verify_sso), ExceptionHandler(), cherrypy.expose)(fn)
            
    return dec

    
def clean_session():
    '''Safely clean the session. This is used primarily by the SSO mechanism.'''
    # Secure the file
    cherrypy.session.escalate_lock()

    # Clears the data from the in memory session
    cherrypy.session.clear()

    # Abandons the session. Strangely we still need to call clear
    # even though a read of regenerate() seems to imply it works
    # on the in memory session (though never calls clear()).
    cherrypy.session.regenerate()


def sso_ip_validation(verify_sso=True):
    '''
    SSO strict mode lockdown.                      
    Screen the incoming requests and ensure they are originating from a valid IP address.
    If we're in SSO strict mode we lock down all endpoints, except those that specify verify_sso=False
    via the expose_page decorator.
    '''
    @decorator
    def validate_ip(fn, self, *a, **kw):
        if verify_sso:
            incoming_request_ip = cherrypy.request.remote.ip
            splunkweb_trusted_ip = splunk.util.stringToFieldList(cherrypy.config.get(SPLUNKWEB_TRUSTED_IP_CFG))
            sso_mode = cherrypy.request.config.get(SPLUNKWEB_SSO_MODE_CFG, 'strict')
            current_remote_user = cherrypy.session.get(REMOTE_USER_SESSION_KEY)
            
            if incoming_request_ip not in splunkweb_trusted_ip:
                if current_remote_user:
                    logger.warn('There was a user logged by SSO and somehow the splunkweb trustedIP is no longer valid. Removing the logged in user.')
                    clean_session()
                
                if sso_mode and sso_mode.lower() == 'strict':
                    raise cherrypy.HTTPError(403, _("Forbidden: Strict SSO Mode"))
                    
        return fn(self, *a, **kw)
        
    return validate_ip

def update_session_user(sessionKey, user):
    # Escalate the lock again just in case.
    cherrypy.session.escalate_lock()

    # Store the splunkd session key
    cherrypy.session[SPLUNKD_SESSION_KEY] = sessionKey
    
    # Store the incoming user in the Remote-User header. This is critical!
    cherrypy.session[REMOTE_USER_SESSION_KEY] = user

    if cherrypy.config.get('is_free_license'):
        cherrypy.session['user'] = {
            'name': 'admin',
            'fullName': 'Administrator',
            'id': 1
        }
    else:
        # now get the user's full name
        en = splunk.entity.getEntity('authentication/users', user, sessionKey=sessionKey)
        fullName = user
        if en and 'realname' in en and en['realname']:
            fullName = en['realname']

        # This was stolen from account.py
        cherrypy.session['user'] = {
            'name': user.lower(),
            'fullName': fullName,
            'id': -1
        }

def sso_check():
    '''
    Preforms the SSO validation and authentication.
    '''
    def login(handler_inst, user):
        '''
        Attempts to login the user via splunkd's trusted endpoint.
        This will only ever work if splunkd is in trusted auth mode.
        '''
        # Clean the sessionKey, something has gone wrong, but we're going to make it right.
        clean_session()

        sessionKey = splunk.auth.getSessionKeyForTrustedUser(user)
        if sessionKey != None:
            update_session_user(sessionKey, user)
        else:
            logger.warn('Could not authenticate user %s via SSO. Does %s have a matching splunk account with the same username?' % (user, user))
            handler_inst.redirect_to_url('/account/sso_error')


    @decorator
    def preform_sso_check(fn, self, *a, **kw):
        '''
        Get the user data (including authtoken) that the splunkd proxy
        is providing for this user.
        '''
        sessionKey = util.parse_xsplunkd_header().get('authtoken')
        old_user = cherrypy.session.get(REMOTE_USER_SESSION_KEY)
        if sessionKey is None:
            logger.debug('proxied_mode request to appserver made with missing X-Splunkd authtoken')
            if old_user is not None:
                clean_session()
        elif cherrypy.session.get(SPLUNKD_SESSION_KEY) != sessionKey:
            remote_user = cherrypy.request.headers.get('REMOTE-USER')
            if old_user == remote_user:
                logger.debug('proxied_mode got refreshed sessionKey for user %s' % remote_user)
                cherrypy.session.escalate_lock()
                cherrypy.session[SPLUNKD_SESSION_KEY] = sessionKey
            else:
                if old_user is None:
                    logger.debug('proxied_mode session created for user %s' % remote_user)
                else:
                    logger.info('proxied_mode session changed from user %s to %s' % (old_user, remote_user))
                clean_session()
                update_session_user(sessionKey, remote_user)
        return fn(self, *a, **kw)
        
    return preform_sso_check

def lock_session(fn):
    """
    Use this if your handler will make changes to cherrypy.session
    It causes CherryPy to acquire an exclusive lock on the session for the 
    duration of the request ensuring there aren't any race conditions with
    other requests that are also accessing session data.
    """
    fn.lock_session = True
    return fn


def require_login(respect_permalinks=False):
    """
    If for some reason you're not using the expose_page decorator
    you can use this to require a user to be logged in instead.
    use expose_page though. really.
    """
    @decorator
    def check_login(fn, self, *a, **kw):
        session_key = cherrypy.session.get('sessionKey', None)
        is_api = util.is_api()

        if not session_key:
            logger.info('require_login - no splunkd sessionKey variable set; request_path=%s' % (cherrypy.request.path_info))
            logger.debug('require_login - cookie request header: %s' % str(cherrypy.request.cookie))
            logger.debug('require_login - cookie response header: %s' % str(cherrypy.response.cookie))
            if is_api or util.is_xhr():
                logger.info('require_login - is api/XHR request, raising 401 status')
                raise cherrypy.HTTPError(401)
            else:
                current_path = util.current_url_path()
                logger.info('require_login - redirecting to login')
                self.redirect_to_url('/account/login', _qs=[ ('return_to', current_path) ])
            
        try:
            return fn(self, *a, **kw)
        except splunk.AuthenticationFailed:
            logger.info('sessionKey rejected by splunkd')
            cherrypy.session.delete()
            if is_api or util.is_xhr():
                raise cherrypy.HTTPError(401)
            else:
                self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path()) ] )

    return check_login


def ExceptionHandler():
    """
    Handles exceptions returned by simpleRequest
    """
    @decorator
    def handle_exceptions(fn, self, *a, **kw):

        try:
            return fn(self, *a, **kw)
            
        except splunk.AuthenticationFailed:
            # redirect to the login page if auth fails
            cherrypy.session['sessionKey'] = None
            self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path()) ] )
            
        except splunk.AuthorizationFailed as e:
            if 'render_admin_template' in dir(self): #only for manager pages
                return self.render_admin_template('admin/error.html', {'namespace' : 'search', 'excp_msg': e, 'excp_details' : 'None'})   
            else:
                raise
                
        except splunk.SplunkdConnectionException as e:
            logger.exception(e)
            raise cherrypy.HTTPError(503, _('The splunkd daemon cannot be reached by splunkweb.  Check that there are no blocked network ports or that splunkd is still running.'))
            
        except splunk.BadRequest as e:
            logger.exception(e)
            if e.msg == "Couldn't parse xml reply":
                raise cherrypy.HTTPError(500, _('The splunkd python dispatcher was unable to properly process script output.'))
            else:
                raise
                
    return handle_exceptions


def conditional_etag():
    '''
    DEPRECATED.  Use @set_cache_level('etag') instead.
    
    Similar to the util.apply_etag(content) method this wraps the 
    entire response with predefined 304 behavior.
    '''
    @decorator
    def apply_etag(fn, self, *a, **kw):
        response = fn(self, *a, **kw)
        if (util.apply_etag(response)):
            return None
        else:
            return response
        
    return apply_etag

def set_cache_level(cache_level):
    '''
    This is a convience wrapper for util.set_cache_level, providing
    backwards compatibility with the original set_cache_level decorator.
    
    The body of this method was moved to the util module so that individual
    modules could dictate whether or not they need to cache their getResults
    responses.
    '''
    @decorator
    def apply_cache_headers(fn, self, *a, **kw):
        response = fn(self, *a, **kw)
        return util.set_cache_level(cache_level, response)
    return apply_cache_headers

def normalize_list_params():
    '''
    Requires the underlying class implements the default list params:
        COUNT
        OFFSET
        SORT_KEY
        SORT_DIR
    '''
    
    @decorator
    def apply_normalized_list_params(fn, self, *a, **kw):
        params = {
            'count': kw.get('count', self.COUNT),
            'offset': kw.get('offset', self.OFFSET),
            'sort_key': kw.get('sort_key', self.SORT_KEY),
            'sort_dir': kw.get('sort_dir', self.SORT_DIR)
        }
        
        try:
            params['count'] = int(params['count'])
        except ValueError:
            params['count'] = int(self.COUNT)
            
        try:
            params['offset'] = int(params['offset'])
        except ValueError:
            params['offset'] = int(self.OFFSET)
        
        kw.update(params)

        return fn(self, *a, **kw)
    
    return apply_normalized_list_params

def format_list_template():

    def decode_fields(fields):
        if not isinstance(fields, list):
            fields = [fields]
    
        decoded_fields = []
        for field in fields:
            try:
                decoded_fields.append(json.loads(field))
            except ValueError as e:
                decoded_fields.append(field)
        return decoded_fields
    
    @decorator
    def response_template(fn, self, *a, **kw):

        # Retrieve the list of dictionaries
        kw['list_data'] = fn(self, *a, **kw)

        # protect against dir traversal 
        # We might want to consider more strict filtering, but shouldn't
        # have any issues with double encoding or unicode filtering based
        # on quick testing.
        output_mode = os.path.join('lists', '%s.html' % os.path.basename(kw.get('output_mode', 'li')))
        
        fields = kw.get('fields')
        staticFields = kw.get('staticFields')
       
        # TODO: make this more sane using a cherrypy tool that translates
        # field[0][label]=foo,field[0][value]=bar to:
        # field = {'0': {'label':'foo', 'value':'bar'}}
        if fields:
            kw['fields'] = decode_fields(fields)

        if staticFields:
            kw['staticFields'] = decode_fields(staticFields)

        # Some list templates require delimiters.
        # This may not be the ideal place to put this, but where else?
        if not kw.get('delimiter'):
            kw['delimiter'] = ''

        return self.render_template(output_mode, kw)

    return response_template
