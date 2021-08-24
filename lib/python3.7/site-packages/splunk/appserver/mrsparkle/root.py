#!/usr/bin/python

from __future__ import absolute_import
import __main__
import os
import splunk
import logging
import logging.handlers
import sys
from cherrypy import expose
from splunk.appserver.mrsparkle.lib import util
from splunk.appserver.mrsparkle.controllers import BaseController


# Windows specific paths which are different from *nix os's:
# Windows:  $SPLUNK_HOME/Python2.5/Lib
# *nix:     $SPLUNK_HOME/lib/python2.5
SPLUNK_SITE_PACKAGES_PATH = os.path.dirname(os.path.dirname(splunk.__file__))


# define filepath for logging files
BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')

# define fallback filepath for UI module assets
FAILSAFE_MODULE_PATH = os.path.join('share', 'splunk', 'search_mrsparkle', 'modules')

# define the fallback root URI
FAILSAFE_ROOT_ENDPOINT = '/'

# define the fallback static rss URI
FAILSAFE_RSS_DIR = 'var/run/splunk/rss'

# define fallback static root URI
FAILSAFE_STATIC_DIR = 'share/splunk/search_mrsparkle/exposed'

# define fallback testing resource root URI
FAILSAFE_TESTING_DIR = 'share/splunk/testing'

# define logging configuration
LOGGING_DEFAULT_CONFIG_FILE = os.path.join(os.environ['SPLUNK_ETC'], 'log.cfg')
LOGGING_LOCAL_CONFIG_FILE = os.path.join(os.environ['SPLUNK_ETC'], 'log-local.cfg')
LOGGING_STANZA_NAME = 'python'
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t[%(requestid)s] %(module)s:%(lineno)d - %(message)s"

# Set a limit on how much data we're prepared to receive (in MB)
DEFAULT_MAX_UPLOAD_SIZE = 500 

IS_CHERRYPY = True
__main__.IS_CHERRYPY = True # root.py is not always __main__


#
# init base logger before all imports
#



# this class must be defined inline here as importing it from appserver.* will
# cause other loggers to be bound to the wrong class
if (sys.version_info >= (3, 0)):

    old_factory = logging.getLogRecordFactory()

    def cherrypy_requestid_factory(*args, **kwargs):
        """
        A logger that knows how to make our custom Cherrypy requestid available to
        the handler's log formatter
        """
        record = old_factory(*args, **kwargs)
        try:
            from splunk.appserver.mrsparkle.lib.util import get_request_id
            record.requestid = get_request_id()
        except:
            record.requestid = "-"
        return record

    logging.setLogRecordFactory(cherrypy_requestid_factory)

else:

    class SplunkLogger(logging.Logger):
        """
        this is only kept for backward compatibilty with py2
        """

        def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
            try:
                from splunk.appserver.mrsparkle.lib.util import get_request_id
                if extra is None:
                    extra = {}
                extra['requestid'] = get_request_id()
            except ImportError as e:
                extra = {'requestid': '-'}
            return logging.Logger.makeRecord(self, name, level, fn, lno, msg, args, exc_info, func, extra)


    logging.setLoggerClass(SplunkLogger)

# If $SPLUNK_APPSERVER_SUFFIX is in the enironment, insert it into the filename.  This converts "foo.log" -> "foo-SUFFIX.log"
def insert_appserver_suffix(path):
    suffix = os.environ.get("SPLUNK_APPSERVER_SUFFIX", "")
    if suffix == "":
        return path
    dot_pos = path.rfind('.')
    if dot_pos > path.rfind(os.sep):
        return path[0:dot_pos] + "-" + suffix + path[dot_pos:]
    return path + "-" + suffix


logger = logging.getLogger('splunk')
logger.setLevel(logging.INFO)
splunk_log_handler = logging.handlers.RotatingFileHandler(insert_appserver_suffix(os.path.join(os.environ['SPLUNK_HOME'], BASE_LOG_PATH, 'web_service.log')), mode='a') # will set limits/thresholds later
splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
logger.addHandler(splunk_log_handler)

# Change the default lxml parsing to not allow imported entities
import splunk.lockdownlxmlparsing

try:
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)


    #
    # continue importing
    #

    import re, time, shutil, hashlib
    import splunk.clilib.cli_common
    import splunk.clilib.bundle_paths
    import splunk.util, splunk.entity
    # TODO: this * needs to be removed
    from splunk.appserver.mrsparkle.controllers.top import TopController
    import cherrypy
    from splunk.appserver.mrsparkle.lib.util import make_absolute
    from splunk.appserver.mrsparkle.lib.util import splunk_to_cherry_cfg
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
    from splunk.appserver.mrsparkle.lib.util import is_encrypted_cert
    from splunk.appserver.mrsparkle.lib import i18n
    from splunk.appserver.mrsparkle.lib import filechain
    from splunk.appserver.mrsparkle.lib import error
    from splunk.appserver.mrsparkle.lib import startup
    from splunk.appserver.mrsparkle.lib.customlogmanager import SplunkedLogManager
    from splunk.appserver.mrsparkle.lib import module
    from splunk.util import normalizeBoolean

    # override Cherrypy's default staticdir handler so we can handle things like custom module locations
    from splunk.appserver.mrsparkle.lib import customstaticdir

    # Make sure CherryPy doesn't shutdown if the user logs out of Windows
    try:
        #pylint: disable=F0401
        import win32con
        win32con.CTRL_LOGOFF_EVENT = object()
    except ImportError:
        pass

    # override Cherrypy's default session locking behaviour
    from splunk.appserver.mrsparkle.lib import sessions


    # replace CherryPy's LogManager class with our subclassed one
    from cherrypy import _cplogging
    _cplogging.LogManager = SplunkedLogManager
    cherrypy.log = _cplogging.LogManager()
    def _cp_buslog(msg, level):
        logger.log(level, 'ENGINE: %s' % msg)

    cherrypy.engine.unsubscribe('log', cherrypy._buslog)
    cherrypy.engine.subscribe('log', _cp_buslog)

    # define etc, site-packages and share/search/mrsparkle in a os agnostic way:
    SPLUNK_ETC_PATH = make_splunkhome_path(['etc'])
    SPLUNK_MRSPARKLE_PATH = make_splunkhome_path(['share', 'search', 'mrsparkle'])

    # define filepath for pid file
    PID_PATH = make_splunkhome_path(['var', 'run', 'splunk', 'splunkweb.pid'])

    # define filepath where compiled mako templates are stored
    MAKO_CACHE_PATH = make_splunkhome_path(['var', 'run', 'splunk', 'mako_cache'])

    from splunk.appserver.mrsparkle.lib.noreferrerhook import NoReferrerHook
    from splunk.appserver.mrsparkle.lib.htmlinjectiontoolfactory import HtmlInjectionToolFactory

    HtmlInjectionToolFactory.singleton().register_head_injection_hook(NoReferrerHook.singleton())
    HtmlInjectionToolFactory.register_cherrypy_hook()

    if sys.version_info >= (3, 0):
        # SPL-172724 override multipart handler to support UTF-8 instead of ISO-8859-1
        from cherrypy.lib import httputil
        class UnicodePart(cherrypy._cpreqbody.Part):
            @classmethod
            def read_headers(cls, fp):
                headers = httputil.HeaderMap()
                while True:
                    line = fp.readline()
                    if not line:
                        # No more data--illegal end of headers
                        raise EOFError('Illegal end of headers.')

                    if line == b'\r\n':
                        # Normal end of headers
                        break
                    if not line.endswith(b'\r\n'):
                        raise ValueError('MIME requires CRLF terminators: %r' % line)

                    if line[0] in b' \t':
                        # It's a continuation line.
                        v = line.strip().decode('UTF-8')
                    else:
                        k, v = line.split(b':', 1)
                        k = k.strip().decode('UTF-8')
                        v = v.strip().decode('UTF-8')

                    existing = headers.get(k)
                    if existing:
                        v = ', '.join((existing, v))
                    headers[k] = v

                return headers

        cherrypy._cpreqbody.Entity.part_class = UnicodePart
    
    # SPL-180503: Disable cherrypy traceback to prevent internal path disclosure on exceptions
    cherrypy._cprequest.Request.show_tracebacks = False

    # SPL-166285
    # In CherryPy 3.1.2 all GET params in a POST were deduplicated into a flat dictionary.
    # Sometime after 3.1.2, CherryPy changed to combining the collisions into an array.
    # We rely too much on the 3.1.2 behavior to change to the new behavior.
    # see: https://stackoverflow.com/questions/31310705/cherrypy-combining-querystring-value-with-form-value-in-post-body

    # merging request.params with body.params. 
    # this will prevent creating an array in request.params with same values
    def postOverride():
        if (cherrypy.request.body.params and cherrypy.request.params):
            cherrypy.request.params.update(cherrypy.request.body.params)

    cherrypy.tools.postoverride = cherrypy.Tool('before_handler', postOverride)

    class RootController(BaseController):
        """This controller is only used if the site root is something other than /"""
        @expose
        def index(self):
            raise cherrypy.HTTPRedirect(cherrypy.config['root_endpoint'])



    def mount_static(ctrl, global_cfg, cfg):
        static_endpoint = global_cfg['static_endpoint']
        static_app_dir= make_absolute('etc/apps', '')

        if (global_cfg.get('static_dir', '') == ''):
            logger.warn('static endpoint configured, but no static directory. Falling back to ' + FAILSAFE_STATIC_DIR)
        staticdir = make_absolute(global_cfg.get('static_dir', FAILSAFE_STATIC_DIR), '')
        global_cfg['staticdir'] = staticdir

        # resolver for static content bundled with applications
        def static_app_resolver(section, branch, dir):
            """ Resolver that pulls application specific assets. """

            parts = branch.split('/')
            subbranch, app, asset = parts[0], parts[1], '/'.join(parts[2:] )
            appstaticdir = os.path.normpath(os.path.join(dir, app, 'appserver', 'static'))
            fn = os.path.normpath(os.path.join(appstaticdir, asset))
            if fn.startswith(appstaticdir) and fn.startswith(os.path.normpath(dir)):
                if os.path.exists(fn):
                    sp = os.path.splitext(asset)
                    if sp[1] == '.js' and not asset.startswith('build') and not asset.startswith('js/contrib') and 'i18noff' not in cherrypy.request.query_string:
                        i18n_cache = i18n.translate_js(fn)
                        if i18n_cache:
                            return i18n_cache
                    return fn
                elif asset in ('dashboard.css', 'dashboard.js'):
                    return os.path.join(staticdir, 'fallback', asset)
            return False

        def static_resolver(section, branch, dir):
            """resolver that knows how to add translations to javascript files"""

            # chain off to another resolver for statics served from application bundles.
            # overrides the 'dir' param with where applications are stored.
            if branch.startswith('app/'):
                return static_app_resolver(section, branch, static_app_dir)
            
            sp = os.path.splitext(branch)
            fn = os.path.join(dir, branch)
            if branch == 'js/i18n.js':
                return i18n.dispatch_i18n_js(fn) # send the locale data with the i18n.js system
            elif branch.endswith('common.min.js'):
                return filechain.chain_common_js() # returns the path to a cached file containing the finished cache file
            elif branch.startswith('js/splunkjs') or branch.startswith('docs/js'):
                return False
            elif not branch.startswith('build') and not branch.startswith('js/contrib') and sp[1] == '.js' and os.path.exists(fn) and 'i18noff' not in cherrypy.request.query_string:
                return i18n.translate_js(fn) # returns the path to a cached file containing the original js + json translation map
            return False # fallback to the default handler

        cfg[static_endpoint] = {
            'tools.sessions.on' : False, # no session required for static resources
            'tools.staticdir.on' : True,
            'tools.staticdir.dir' : staticdir,
            'tools.staticdir.strip_version' : True,
            'tools.staticdir.resolver' : static_resolver,
            'tools.staticdir.content_types' : {
                'js' : 'application/javascript', 
                'css': 'text/css',
                # SPL-87571: Response Headers: Content-Type: text/plain for SVG files, which should be Content-Type: image/svg+xml
                # FYI: if there's any file type that splunk doesn't recognize, just add it here.
                'svg': 'image/svg+xml',
                'svgz': 'image/svg+xml',
                'cache': 'text/javascript', # correct python's application/x-javascript
                'woff': 'application/font-woff'
            },            
            'tools.gzip.on' : True,
            'tools.gzip.mime_types' : ['text/plain', 'text/html', 'text/css', 'application/javascript', 'application/x-javascript', 'text/javascript']
        }

        ctrl.robots_txt = cherrypy.tools.staticfile.handler(os.path.join(staticdir, 'robots.txt'))
        ctrl.favicon_ico = cherrypy.tools.staticfile.handler(os.path.join(staticdir, 'img', util.getFaviconFileName()))


    def run(blocking=True):
        # get confs
        global_cfg = splunk_to_cherry_cfg('web', 'settings')

        # allow command line arguments to override the configuration
        # eg. --httpport=80
        args = util.args_to_dict()

        # For security reasons do not echo application server information (default is CherryPy/x.x.x)
        global_cfg['tools.response_headers.on'] = True
        global_cfg['tools.response_headers.headers'] = [('Server', 'Splunk')]

        # SPL-16963: add port number to session key to allow for sessions for multiple
        # instances to run on a single host, without mutually logging each other out.
        global_cfg['tools.sessions.name'] = "session_id_%s" % global_cfg['httpport']
        global_cfg['tools.csrfcookie.name'] = "splunkweb_csrf_token_%s" % global_cfg['httpport']
        global_cfg['tools.csrfcookie.port'] = "%s" % global_cfg['httpport']

        # splunkd passes in --proxied which overrides some of the settings
        # that we used to read from web.conf
        proxied_arg = args.get('proxied')
        if not proxied_arg:
            logger.error("splunkweb FAILED to start!\nPlease make sure valid non-zero appServerPorts are specified in web.conf")
            return
        del args['proxied']
        proxied_parts = proxied_arg.split(',')
        if len(proxied_parts) != 3:
            logger.error("Proxied mode flag invalid '%s'. --proxied=' IP_ADDR PORT'" % proxied_arg)
            return
        proxied_ip_addr = proxied_parts[0]
        proxied_port = int(proxied_parts[1])
        exposed_ui_port = int(proxied_parts[2])
        logger.info('Proxied mode ip_address=%s port=%s exposed_port=%s:' % (proxied_ip_addr, proxied_port, exposed_ui_port))
        global_cfg['startwebserver'] = 1
        global_cfg['httpport'] = proxied_port
        global_cfg['enableSplunkWebSSL'] = False
        global_cfg['remoteUser'] = 'REMOTE-USER'
        global_cfg['SSOMode'] = 'strict'
        global_cfg['trustedIP'] = proxied_ip_addr
        global_cfg['server.socket_host'] = proxied_ip_addr
        global_cfg['tools.sessions.name'] = "session_id_%s" % exposed_ui_port
        global_cfg['tools.csrfcookie.name'] = "splunkweb_csrf_token_%s" % exposed_ui_port
        global_cfg['tools.csrfcookie.port'] = "%s" % exposed_ui_port
        cp_proxy_on = global_cfg.get('tools.proxy.on')
        if cp_proxy_on:
            if proxied_ip_addr.find(':') >= 0:
                proxied_ip_addr = "[" + proxied_ip_addr + "]"
            global_cfg['tools.proxy.base'] = "%s:%s" % (proxied_ip_addr, exposed_ui_port)
            global_cfg['tools.proxy.remote'] = ''

        # debugging can be turned on from the command line with --debug
        if args.get('debug'):
            del args['debug']
            logger.setLevel(logging.DEBUG)
            for lname, litem in list(logger.manager.loggerDict.items()):
                if not isinstance(litem, logging.PlaceHolder):
                    logger.debug("Updating logger=%s to level=DEBUG" % lname)   
                    litem.setLevel(logging.DEBUG)
            args['js_logger_mode'] = 'Server'
            args['enableWebDebug'] = True
        global_cfg.update(args)

        global_cfg['server.socket_port'] = global_cfg['httpport']

        if normalizeBoolean(global_cfg.get('enableSplunkWebSSL', False)):
            logger.info('Enabling SSL')
            priv_key_path = os.path.expandvars(str(global_cfg['privKeyPath']))
            ssl_certificate = os.path.expandvars(str(global_cfg['serverCert']))
            ssl_ciphers = str(global_cfg['cipherSuite'])

            if os.path.isabs(priv_key_path):
                global_cfg['server.ssl_private_key'] = priv_key_path
            else:
                global_cfg['server.ssl_private_key'] = make_splunkhome_path([priv_key_path])

            if os.path.isabs(ssl_certificate):
                global_cfg['server.ssl_certificate'] = ssl_certificate
            else:
                global_cfg['server.ssl_certificate'] = make_splunkhome_path([ssl_certificate])

            if not os.path.exists(global_cfg['server.ssl_private_key']):
                raise ValueError("%s Not Found" % global_cfg['server.ssl_private_key'])

            if not os.path.exists(global_cfg['server.ssl_certificate']):
                raise ValueError("%s Not Found" % global_cfg['server.ssl_certificate'])

            if global_cfg.get('supportSSLV3Only'):
                global_cfg['server.ssl_v3_only'] = True

            global_cfg['server.ssl_options'] = 0

            if global_cfg.get('sslVersions'):
                from ssl import PROTOCOL_SSLv3, PROTOCOL_SSLv23, PROTOCOL_TLSv1, PROTOCOL_TLSv1_1, PROTOCOL_TLSv1_2, OP_NO_SSLv2, OP_NO_SSLv3

                if global_cfg.get('sslVersions') == 'all':
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv23

                elif global_cfg.get('sslVersions') == 'ssl3':
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv3

                elif global_cfg.get('sslVersions') == 'tls1.0':
                    global_cfg['server.ssl_version'] = PROTOCOL_TLSv1

                elif global_cfg.get('sslVersions') == 'tls1.1':
                    global_cfg['server.ssl_version'] = PROTOCOL_TLSv1_1

                elif global_cfg.get('sslVersions') == 'tls1.2':
                    global_cfg['server.ssl_version'] = PROTOCOL_TLSv1_2

                elif global_cfg.get('sslVersions') == 'ssl3, tls':
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv23
                    global_cfg['server.ssl_options'] = OP_NO_SSLv2

                elif global_cfg.get('sslVersions') == 'tls':
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv23
                    global_cfg['server.ssl_options'] = OP_NO_SSLv2 | OP_NO_SSLv3

                elif global_cfg.get('supportSSLV3Only'):
                    # if someone upgraded from 6.1.4 to 6.1.5 with supportSSLV3Only,
                    # ensure their preference is honored
                    logger.warn("Undefined sslVersion='%s'. Please select from 'all', 'ssl3, tls' or 'tls'." % global_cfg.get('sslVersions'))
                    logger.warn("Defaulting sslVersion to 'ssl3, tls'")
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv23
                    global_cfg['server.ssl_options'] = OP_NO_SSLv2

                else:
                    #default case ssl2+
                    logger.warn("Undefined sslVersion='%s'. Please select from all', 'ssl3, tls' or 'tls'." % global_cfg.get('sslVersions'))
                    logger.warn("Defaulting sslVersion to 'all'")
                    global_cfg['server.ssl_version'] = PROTOCOL_SSLv23


            if ssl_ciphers:
                global_cfg['server.ssl_ciphers'] = ssl_ciphers
        elif normalizeBoolean(global_cfg.get('tools.sessions.forceSecure', True)):
            logger.info('Enforcing secure session cookie without Splunk Web SSL.')
            global_cfg['tools.sessions.secure'] = True
        else:
            # make sure the secure flag is not set on session cookies if we're not serving over SSL and 
            # tools.sessions.forceSecure is not set to True
            global_cfg['tools.sessions.secure'] = False

        # setup cherrypy logging infrastructure
        if 'log.access_file' in global_cfg:
            filename = insert_appserver_suffix(make_absolute(global_cfg['log.access_file'], BASE_LOG_PATH))
            maxsize = int(global_cfg.get('log.access_maxsize', 0))
            maxcount = int(global_cfg.get('log.access_maxfiles', 5))
            if maxsize > 0:
                cherrypy.log.access_file = ''
                h = logging.handlers.RotatingFileHandler(filename, 'a', maxsize, maxcount)
                h.setLevel(logging.INFO)
                h.setFormatter(_cplogging.logfmt)
                cherrypy.log.access_log.addHandler(h)
                del global_cfg['log.access_file']
            else:
                global_cfg['log.access_file'] = filename

        if 'log.error_file' in global_cfg:
            # we've already committed to web_service.log by this point
            del global_cfg['log.error_file']
        cherrypy.log.error_file = ''
        cherrypy.log.error_log.addHandler(splunk_log_handler)
        if 'log.error_maxsize' in global_cfg:
            splunk_log_handler.maxBytes = int(global_cfg['log.error_maxsize'])
            splunk_log_handler.backupCount = int(global_cfg.get('log.error_maxfiles', 5))
            
        # now that we have somewhere to log, test the ssl keys. - SPL-34126
        # Lousy solution, but python's ssl itself hangs with encrypted keys, so avoid hang by
        # bailing with a message
        if global_cfg['enableSplunkWebSSL']:
            for cert_file in (global_cfg['server.ssl_private_key'], 
                              global_cfg['server.ssl_certificate']):
                if is_encrypted_cert(cert_file):
                    logger.error("""Specified cert '%s' is encrypted with a passphrase.  SplunkWeb does not support passphrase-encrypted keys at this time.  To resolve the problem, decrypt the keys on disk, generate new
passphrase-less keys, or disable ssl for SplunkWeb.""" % cert_file)
                    raise Exception("Unsupported encrypted cert file.")

        # set login settings
        if global_cfg.get('tools.sessions.storage_type') == 'file':
            global_cfg['tools.sessions.storage_path'] = make_absolute(global_cfg['tools.sessions.storage_path'])

        # set mako template cache directory
        global_cfg.setdefault('mako_cache_path', MAKO_CACHE_PATH)
        
        root_name = global_cfg.get('root_endpoint', FAILSAFE_ROOT_ENDPOINT).strip('/')
        
        ctrl = TopController()
        cfg = {'global' : global_cfg}

        # initialize all of the custom endpoints that are registered in the
        # apps
        ctrl.custom.load_handlers()


        # Serve static files if so configured
        if 'static_endpoint' in global_cfg:
            mount_static(ctrl, global_cfg, cfg)
        
        if 'testing_endpoint' in global_cfg:
            if (global_cfg.get('static_dir', '') == '') :
                logger.warn('testing endpoint configured, but no testing directory. Falling back to ' + FAILSAFE_TESTING_DIR)
            staticdir = make_absolute(global_cfg.get('testing_dir', FAILSAFE_TESTING_DIR), '')

            cfg[global_cfg['testing_endpoint']] = {
                'tools.staticdir.on' : True,
                'tools.staticdir.dir' : staticdir,
                'tools.staticdir.strip_version' : True
            }
        
        if 'rss_endpoint' in global_cfg:
            rssdir = make_absolute(global_cfg.get('rss_dir', FAILSAFE_RSS_DIR), '')
            logger.debug('using rss_dir: %s' % rssdir)
            cfg[global_cfg['rss_endpoint']] = {
                'tools.staticdir.on' : True,
                'tools.staticdir.dir' : rssdir,
                'tools.staticdir.strip_version' : False,
                'tools.staticdir.default_ext' : 'xml',
                'error_page.404': make_splunkhome_path([FAILSAFE_STATIC_DIR, 'html', 'rss_404.html'])
            }
            

        # Modules served statically out of /modules or out of an app's modules dir
        def module_resolver(section, branch, dir):
            from splunk.appserver.mrsparkle.lib.apps import local_apps
            # first part of branch is the module name
            parts = os.path.normpath(branch.strip('/')).replace(os.path.sep, '/').split('/')
            locale = i18n.current_lang(True)
            if not parts:
                return False
            module_path = local_apps.getModulePath(parts[0])
            if module_path:
                # this means there is a module named parts[0]
                # SPL-51365 images should load irrespective of css_minification.
                if parts[0]==parts[1]:
                    # ignore of repetition of module name
                    # happens for image request when minify_css=False
                    fn = os.path.join(module_path, *parts[2:])
                else:
                    fn = os.path.join(module_path, *parts[1:])
                #verified while fixing SPL-47422
                #pylint: disable=E1103 
                if fn.endswith('.js') and os.path.exists(fn):
                    return i18n.translate_js(fn) # returns the path to a cached file containing the original js + json translation map
                return fn
            elif parts[0].startswith('modules-') and parts[0].endswith('.js'):
                hash = parts[0].replace('modules-', '').replace('.min.js', '')
                return make_absolute(os.path.join(i18n.CACHE_PATH, '%s-%s-%s.cache' % ('modules.min.js', hash, locale)))
            elif parts[0].startswith('modules-') and parts[0].endswith('.css'):
                return filechain.MODULE_STATIC_CACHE_PATH + os.sep + 'css' + os.sep + parts[0]
            return False

        moddir = make_absolute(global_cfg.get('module_dir', FAILSAFE_MODULE_PATH))
        cfg['/modules'] = {
            'tools.staticdir.strip_version' : True,
            'tools.staticdir.on' : True,
            'tools.staticdir.match' : re.compile(r'.*\.(?!html$|spec$|py$)'), # only files with extensions other than .html, .py and .spec are served
            'tools.staticdir.dir' : moddir,
            'tools.staticdir.resolver' : module_resolver,
            'tools.staticdir.content_types' : {'js' : 'application/javascript', 'css': 'text/css', 'cache': 'text/javascript'} # correct python's application/x-javascript
        }

        cfg['/'] = {
            'request.dispatch': i18n.I18NDispatcher(),
            'tools.postoverride.on' : True
        }

        # enable gzip + i18n goodness
        if global_cfg.get('enable_gzip', False):
            cfg['/'].update({
                'tools.gzip.on': True,
                'tools.gzip.mime_types': ['text/xml', 'text/plain', 'text/html', 'text/css', 'application/javascript', 'application/x-javascript', 'application/json'],
            })

        #cfg['/']['tools.gzip.on'] = False

        # Set maximum filesize we can receive (in MB)
        maxsize = global_cfg.get('max_upload_size', DEFAULT_MAX_UPLOAD_SIZE)
        cfg['global']['server.max_request_body_size'] = int(maxsize) * 1024 * 1024

        if global_cfg.get('enable_throttle', False):
            from splunk.appserver.mrsparkle.lib import throttle
            cfg['global'].update({
                'tools.throttle.on' : True,
                'tools.throttle.bandwidth': int(global_cfg.get('throttle_bandwidth', 50)), 
                'tools.throttle.latency': int(global_cfg.get('throttle_latency', 100))
            })

        if global_cfg.get('enable_log_runtime', False):
            points = global_cfg.get('enable_log_runtime')
            if points == 'All': points = 'on_start_resource,before_request_body,before_handler,before_finalize,on_end_resource,on_end_request'
            if points is True: points = 'on_end_resource'
            for point in points.split(','):
                def log_closure(point):
                    def log():
                        import time
                        starttime = cherrypy.response.time
                        endtime = time.time()
                        delta = (endtime - starttime) * 1000
                        logger.warn('log_runtime point=%s path="%s" start=%f end=%f delta_ms=%.1f' % (point, cherrypy.request.path_info, starttime, endtime, delta))
                    return log
                setattr(cherrypy.tools, 'log_'+point, cherrypy.Tool(point, log_closure(point)))
                cfg['/']['tools.log_%s.on' % point] = True

        if global_cfg.get('override_JSON_MIME_type_with_text_plain', False):
            import splunk.appserver.mrsparkle
            splunk.appserver.mrsparkle.MIME_JSON = "text/plain; charset=UTF-8"
            logger.info("overriding JSON MIME type with '%s'" % splunk.appserver.mrsparkle.MIME_JSON)

        #
        # process splunkd status information
        #
        
        startup.initVersionInfo()

        # set start time for restart checking
        cfg['global']['start_time'] = time.time()

        # setup global error handling page
        cfg['global']['error_page.default'] = ctrl.error.handle_error

        # set splunkd connection timeout
        import splunk.rest
        defaultSplunkdConnectionTimeout = 30
        try:
            splunkdConnectionTimeout = int(global_cfg.get('splunkdConnectionTimeout', defaultSplunkdConnectionTimeout))
            if splunkdConnectionTimeout < defaultSplunkdConnectionTimeout:
                splunkdConnectionTimeout = defaultSplunkdConnectionTimeout

            splunk.rest.SPLUNKD_CONNECTION_TIMEOUT = splunkdConnectionTimeout
        except ValueError as e:
            logger.error("Exception while trying to get splunkdConnectionTimeout from web.conf e=%s" % e)
            splunk.rest.SPLUNKD_CONNECTION_TIMEOUT = defaultSplunkdConnectionTimeout
        except TypeError as e:
            logger.error("Exception while trying to get splunkdConnectionTimeout from web.conf e=%s" % e)
            splunk.rest.SPLUNKD_CONNECTION_TIMEOUT = defaultSplunkdConnectionTimeout
        finally:    
            logger.info("splunkdConnectionTimeout=%s" % splunk.rest.SPLUNKD_CONNECTION_TIMEOUT)

        #
        # TODO: refactor me into locale stuff
        #
        cfg['global']['DISPATCH_TIME_FORMAT'] = '%s.%Q'
        # END
        
        
        # Common splunk paths
        cfg['global']['etc_path'] = make_absolute(SPLUNK_ETC_PATH)
        cfg['global']['site_packages_path'] = make_absolute(SPLUNK_SITE_PACKAGES_PATH)
        cfg['global']['mrsparkle_path'] = make_absolute(SPLUNK_MRSPARKLE_PATH)
        
        listen_on_ipv6 = global_cfg.get('listenOnIPv6')
        socket_host = global_cfg.get('server.socket_host')
        if not socket_host:
            if listen_on_ipv6:
                socket_host = global_cfg['server.socket_host'] = '::'
            else:
                socket_host = global_cfg['server.socket_host'] = '0.0.0.0'
            logger.info("server.socket_host defaulting to %s" % socket_host)

        if ':' in socket_host:
            if not listen_on_ipv6:
                logger.warn('server.socket_host was set to IPv6 address "%s", so ignoring listenOnIPv6 value of "%s"' % (socket_host, listen_on_ipv6))
        else:
            if listen_on_ipv6:
                logger.warn('server.socket_host was to to IPv4 address "%s", so ignoring listenOnIPv6 values of "%s"' % (socket_host, listen_on_ipv6))

        if socket_host == '::':
            # Start a second server to listen to the IPV6 socket
            if isinstance(listen_on_ipv6, bool) or listen_on_ipv6.lower() != 'only':
                global_cfg['server.socket_host'] = '0.0.0.0'
                from cherrypy import _cpserver
                from cherrypy import _cpwsgi_server
                server2 = _cpserver.Server()
                server2.httpserver = _cpwsgi_server.CPWSGIServer()
                server2.httpserver.bind_addr = ('::', global_cfg['server.socket_port'])
                server2.socket_host = '::'
                server2.socket_port = global_cfg['server.socket_port']
                for key in ('ssl_private_key', 'ssl_certificate', 'ssl_v3_only', 'ssl_ciphers'):
                    if 'server.'+key in global_cfg:
                        setattr(server2, key, global_cfg['server.'+key])
                        setattr(server2.httpserver, key, global_cfg['server.'+key])
                server2.subscribe()

        if root_name:
            # redirect / to the root endpoint
            cherrypy.tree.mount(RootController(), '/', cfg)

        cherrypy.config.update(cfg)
        if global_cfg.get('enable_profile', False):
            from cherrypy.lib import profiler
            cherrypy.tree.graft(
                profiler.make_app(cherrypy.Application(ctrl, '/' + root_name, cfg), 
                path=global_cfg.get('profile_path', '/tmp/profile')), '/' + root_name
                )
        else:
            cherrypy.tree.mount(ctrl, '/' + root_name, cfg)
        cherrypy.engine.signal_handler.subscribe()

        # this makes Ctrl-C work when running in nodaemon
        if splunk.clilib.cli_common.isWindows:
            from cherrypy.process import win32
            cherrypy.console_control_handler = win32.ConsoleCtrlHandler(cherrypy.engine)
            cherrypy.engine.console_control_handler.subscribe() 

        if 'server_info_fetch' in cherrypy.config:
            del cherrypy.config['server_info_fetch']

        # log active config
        for k in sorted(cherrypy.config):
            logger.info('CONFIG: %s (%s): %s' % (k, type(cherrypy.config[k]).__name__, cherrypy.config[k]))

        # clean up caches on init
        filechain.clear_cache()
        i18n.init_i18n_cache(flush_files=True)
 
        # We're under the control of the proxy and we want to automatically shutdown
        # as soon as stdin closes since that indicates that splunkd died
        # We also receive a single line of text at startup which gives us a token
        # that splunkd will include on every request
        from threading import Thread, Event
        got_token = Event()
        class StdinThread(Thread):
            def __init__(self):
                Thread.__init__(self)
            def run(self):
                # Note: we can't use the iterator-style ("for line in sys.stdin") here
                # since that causes it to buffer waiting for data that will never come
                while True:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    line = line.rstrip()
                    token, sep, staticAssetId = line.partition(',')
                    cherrypy.config['proxy_token'] = token
                    cherrypy.config['staticAssetId'] = staticAssetId
                    got_token.set()
                cherrypy.engine.exit()
        StdinThread().start()
        got_token.wait()

        cherrypy.engine.start()

        if blocking:
            # this routine that starts this as a windows service will not want us to block here.
            cherrypy.engine.block()

    if __name__ == '__main__':
        run(blocking=True)


except Exception as e:
    logger.error('Unable to start splunkweb')
    logger.exception(e)
    sys.exit(1)
