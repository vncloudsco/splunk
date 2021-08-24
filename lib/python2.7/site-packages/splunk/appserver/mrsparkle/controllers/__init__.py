from builtins import object
import os, copy, types, inspect, json
import cgi
import cherrypy
import splunk.clilib.cli_common
import splunk.util
import mako.lookup
import splunk
from splunk.appserver.mrsparkle.lib import routes
from splunk.appserver.mrsparkle.lib import util
from splunk.appserver.mrsparkle.lib import i18n
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib import startup
import logging
import splunk.entity as en
from future.utils import with_metaclass

logger = logging.getLogger('splunk.appserver.controllers')


mako_lookup = None

import re, os.path, posixpath
from mako import exceptions
from splunk.appserver.mrsparkle.lib.apps import local_apps


# GUIDELINES FOR ADDING TO THE BLACKLIST:
# - keep the list in alphabetical order by endpoint
# - there is no need to include the leading '/', 'en-US'
# - do not include the app name, unless you know what you are doing

_SPLUNK_BLACKLIST = { 'splunk.appserver.mrsparkle.controllers.admin' : [
                        {'endpoint': 'manager/[^/]*/accesscontrols',               'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/admin/commandsconf',           'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/advancedsearch',               'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/apps/local/_new',              'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/authentication/providers',     'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/authentication/users/_new',    'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/authoverview',                 'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/authorization',                'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/authorization/tokens',                'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/clustering',                   'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/data/outputs/',                'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/data/ui/(?!panels).*',         'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/distsearch',                   'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/licenseusage',                 'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/messages',                     'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/search/dist',                  'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/scheduled/views',              'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/summarization',                'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/ui',                           'modes': ['lite', 'lite_free']},
                        {'endpoint': 'manager/[^/]*/control',                      'modes': ['lite', 'lite_free']}
                       ],
                      'splunk.appserver.mrsparkle.controllers.appinstall' : [
                        {'endpoint': 'manager/appinstall/_upload',                 'modes': ['lite', 'lite_free']}
                       ]
                    }

def precompile_blacklist():
    for module_black_list in _SPLUNK_BLACKLIST.values():
        for props in module_black_list:
            regex_string =  props['endpoint']
            regex = re.compile(regex_string)
            props['endpoint'] = regex

precompile_blacklist()
#_SPLUNK_BLACKLIST = tuple(_SPLUNK_BLACKLIST)


class I18NDict(object):
    """
    Wraps a dict like object that TemplateLookup uses to maintain its cache of
    templates.
    We make one dict per language in use so that a french template is kept separate
    from an english one for example
    """
    def __init__(self, source):
        """source is a dict like object - it could be an actual dict or a LRUCache object"""
        self.__original = source
        self.__targets = {}

    @property
    def _i18n_dict(self):
        lang, locale, enc = i18n.current_lang()
        return self.__targets.setdefault((lang, locale), copy.copy(self.__original))

    def __getitem__(self, key):
        return self._i18n_dict[key]

    def __contains__(self, key):
        return key in self._i18n_dict

    def __iter__(self):
        return iter(self._i18n_dict)

    def __setitem__(self, key, val):
        self._i18n_dict[key] = val

    def values(self):
        return list(self._i18n_dict.values())

    def setdefault(self, key, value):
        return self._i18n_dict.setdefault(key, value)

    def pop(self, *a, **kw):
        return self._i18n_dict.pop(*a, **kw)


class TemplateRenderError(cherrypy.HTTPError):
    def get_error_page(self, *args, **kwargs):
        kwargs['noexname'] = 'true'
        return super(TemplateRenderError, self).get_error_page(*args, **kwargs)


class TemplateLookup(mako.lookup.TemplateLookup):
    TEMPLATE_APPSCOPE_SEPARATOR = ':'

    def __init__(self, *a, **kw):
        super(TemplateLookup, self).__init__(*a, **kw)
        # replace the cache dictionaries with i18n aware ones that
        # internally maintain one dict per language/locale
        self._collection = I18NDict(self._collection)
        self._uri_cache = I18NDict(self._uri_cache)

    def _find_i18n_template(self, filename):
        """
        Determines whether a version of the requested template filename exists for the
        user's current locale
        """
        for path in i18n.path_to_i18n_paths(filename):
            if os.path.exists(path):
                return path
        return filename

    def _normalize_template_path(self, path):
        """
        Convenience wrapper around normalizing a template path and finding the
        internationalized version of the template
        """
        normalized = posixpath.normpath(path)
        normalized = self._find_i18n_template(normalized)
        return normalized

    def get_template(self, uri):
        """
        Override Mako's template lookup routine to add support for templates located
        by an absolute path rather than a relative one.
        Absolute path names must begin with an equals sign ('=') to denote
        that they are absolute relative to the filesystem root, rather than the root
        of one of the TemplateLookup directories

        Also allows templates to be defined in apps that contain a templates folder
        Priority is given to app defined templates so that they may override system
        defined ones.

        If the requested uri has an appname followed by a colon (':') then followed
        by a template path, this will attempt to find the given template within the
        specified application.
        e.g. uri = '/some_application:/event_renderers/_some_renderer.html"
            will attempt to return _some_renderer.html from
            /etc/apps/some_application/appserver/event_renderers
        """
        def raise_top_level_lookup_exception(uri):
            raise exceptions.TopLevelLookupException(_("Splunk has failed to locate the template for uri '%s'." % uri))

        def optional_paths_from_root(root):
            return [os.path.abspath(os.path.join(root, optional_path)) for optional_path in splunk.util.stringToFieldList(cherrypy.config.get("allowableTemplatePaths"))]

        try:
            if self.filesystem_checks:
                return self._check(uri, self._collection[uri])
            else:
                return self._collection[uri]
        except KeyError:
            template_path = uri[1:]
            if uri[0] == '=' and os.path.exists(template_path):
                template_path = os.path.abspath(template_path)
                optional_paths = optional_paths_from_root(os.environ['SPLUNK_HOME'])
                if not util.is_valid_template_path(os.environ['SPLUNK_HOME'], template_path, optional_paths=optional_paths):
                    raise_top_level_lookup_exception(template_path)
                return self._load(template_path, self._find_i18n_template(uri))
            else:
                u = re.sub(r'^\/+', '', uri)
                # see if an app has a custom template
                appflag = "APP/"
                if u.startswith(appflag):
                    basedir = os.path.abspath(util.get_apps_dir())
                    srcfile = self._normalize_template_path(os.path.join(basedir, u[len(appflag):]))
                    if os.path.exists(srcfile) and os.path.abspath(srcfile).startswith(basedir):
                        return self._load(srcfile, uri)
                else:
                    # see if it's been defined in a specific app. we only do this if we find a ':' in the requested path
                    if u.find(self.TEMPLATE_APPSCOPE_SEPARATOR) > -1:
                        appScope = u.split(self.TEMPLATE_APPSCOPE_SEPARATOR)[0]
                        if appScope in [k for k, v in local_apps.items()]: # local_apps is not an instance of dictionary
                            app = local_apps.apps[appScope]
                            appPath = re.sub(r'^\/+', '', u[len(appScope)+1:] )
                            basedir = os.path.abspath(posixpath.join(app['full_path'], 'appserver'))
                            srcfile = self._normalize_template_path(posixpath.join(basedir, appPath ) )
                            if os.path.exists(srcfile) and os.path.abspath(srcfile).startswith(basedir):
                                return self._load(srcfile, uri)

                    # now see if an app has defined this template for a module
                    for appname, app in local_apps.items(): # local_apps is not an instance of dictionary
                        basedir = os.path.abspath(posixpath.join(app['full_path'], 'appserver', 'modules'))
                        srcfile = self._normalize_template_path(posixpath.join(basedir, u))
                        if os.path.exists(srcfile) and os.path.abspath(srcfile).startswith(basedir):
                            return self._load(srcfile, uri)


                    # finally, look in the directories we were given at setup
                    for dir in self.directories:
                        srcfile = posixpath.normpath(posixpath.join(dir, u))
                        srcfile = self._find_i18n_template(srcfile)
                        if os.path.exists(srcfile) and os.path.abspath(srcfile).startswith(dir):
                            return self._load(srcfile, uri)
                raise_top_level_lookup_exception(uri)

    def adjust_uri(self, uri, relativeto):
        if uri[0]=='=':
            return uri
        if relativeto[0] == '=':
            relativeto = relativeto[1:]

        #warkaround our internal I18N cache layer
        key = (uri, relativeto)

        if uri[0] != '/':
            if relativeto is not None:
                v = self._uri_cache[key] = posixpath.join(
                                            posixpath.dirname(relativeto), uri)
            else:
                v = self._uri_cache[key] = '/' + uri
        else:
            v = self._uri_cache[key] = uri
        return v


class BaseController(with_metaclass(routes.RoutableType, object)):
    mako_lookup = None

    def __init__(self):
        ssl_enabled_conf_str = self.conf(key='enableSplunkdSSL', name="server", stanza="sslConfig", default="true")
        # normalizeBoolean doesn't do its job, so we clean up for unusual cases
        try:
            ssl_enabled = splunk.util.normalizeBoolean(ssl_enabled_conf_str, enableStrictMode=True)
        except ValueError:
            ssl_enabled = False

        if ssl_enabled:
            protocol = 'https'
        else:
           protocol = 'http'

        # old way
        self._splunkd_urlhost = '%s://%s' % (protocol, self.conf('mgmtHostPort'))

        # better way: this sets the global default for any object that uses the
        # the splunk.* SDK
        splunk.setDefault('protocol', protocol)
        splunk.mergeHostPath(self.conf('mgmtHostPort'), True)

    @property
    def splunkd_urlhost(self):
        """
        New code should rely on the default value when calling the Splunk API
        as set above.
        """
        return self._splunkd_urlhost

    def make_url(self, *a, **kw):
        return util.make_url(*a, **kw)

    def strip_url(self, path):
        return util.strip_url(path)

    def push_version(self, *a, **kw):
        return util.push_version(*a, **kw)

    def setup_mako(self):
        # init mako_lookup after the cherrypy config has been setup
        global mako_lookup
        if not mako_lookup:
            mako_lookup = TemplateLookup(
                input_encoding='utf-8',
                directories=[
                    util.make_absolute(cherrypy.config.get('templates', 'share/splunk/search_mrsparkle/templates')),
                    util.make_absolute(cherrypy.config.get('module_dir'))
                ],
                imports=[
                    'import splunk',
                    'import cherrypy',
                    'from lib import i18n',
                    'from lib.util import json_html_safe as jsonify',#legacy
                    'from lib.util import json_decode',#replacement
                    'from lib.util import is_xhr, generateSelfHelpLink, extract_help_links'
                ]#,
                #module_directory=cherrypy.config.get('mako_cache_path', '/tmp/mako_cache')
            )

    def conf(self, key, name='web', stanza='settings', cast=None, default=None):
        """Fetch a configuration key from the Splunk config"""
        try:
            value = splunk.clilib.cli_common.getConfKeyValue(name, stanza, key)
        except KeyError as e:
            if default:
                value = default
            else:
                raise
        if cast is bool:
            return splunk.util.normalizeBoolean(value)
        if cast is int:
            return int(value)
        return value

    def render_template(self, template_name, template_args=None):
        logger.debug('render_template - reading template=%s' % template_name)

        self.setup_mako()
        if template_args is None:
            template_args = {}
        template_args['make_url'] = self.make_url
        template_args['make_route'] = self.make_route
        template_args['h'] = cgi.escape
        template_args['attributes'] = {}
        template_args['controller'] = self
        template_args['isCloud'] = util.isCloud()

        check_server_info = self.checkServerInfo()

        if check_server_info == True and 'splunkd' in template_args:
            server_info = util.getServerInfoPayload()
            template_args['splunkd']['/services/server/info'] = server_info

        try:
            templateInstance = mako_lookup.get_template(template_name)
        except Exception as e:
            # If we couldn't render the template from the global view templates then
            # it is likely an app specified template.
            def notfound_exception(template_name):
                logger.error('Unable to obtain template "%s": %s' % (template_name, mako.exceptions.text_error_template().render()))
                if logging.getLogger('splunk').getEffectiveLevel() == logging.DEBUG:
                    return mako.exceptions.html_error_template().render()
                raise TemplateRenderError(500, _('An error occurred while reading the page template.  See web_service.log for more details'))

            if template_name.startswith('/view/'):
                alt_template_name = template_name[6:]
                try:
                    templateInstance = mako_lookup.get_template(alt_template_name)
                except Exception as e:
                    return notfound_exception(alt_template_name)
            else:
                return notfound_exception(template_name)

        try:
            return templateInstance.render(**template_args)
        except splunk.QuotaExceededException as e:
            raise
        except:
            logger.error('Mako failed to render: %s' % mako.exceptions.text_error_template().render())
            if logging.getLogger('splunk').getEffectiveLevel() == logging.DEBUG:
                return mako.exceptions.html_error_template().render()
            raise TemplateRenderError(500, _('An error occurred while rendering the page template.  See web_service.log for more details'))

    @classmethod
    def render_json(self, response_data, set_mime='text/json'):
        cherrypy.response.headers['Content-Type'] = set_mime

        if isinstance(response_data, jsonresponse.JsonResponse):
            response = response_data.toJson().replace("</", "<\\/")
        else:
            response = json.dumps(response_data).replace("</", "<\\/")

        # Pad with 256 bytes of whitespace for IE security issue. See SPL-34355
        return ' ' * 256  + '\n' + response

    def checkServerInfo(self):
        if 'server_info_fetch' not in cherrypy.config:
            successful_fetch = startup.initVersionInfo(force=True)
            if successful_fetch == True:
                cherrypy.config['server_info_fetch'] = True
            return successful_fetch
        else:
            return False

    def make_route(self, *a, **kw):
        return routes.make_route(*a, **kw)

    def redirect_to_url(self, *a, **kw):
        redirect_url = self.make_url(*a, **kw)
        raise cherrypy.HTTPRedirect(redirect_url)

    def redirect_to_route(self, *a, **kw):
        raise cherrypy.HTTPRedirect(self.make_route(*a, **kw))

    def incr_push_version(self):
        """Called by /_bump to increment the push_version number"""
        # splunkd will already have bumped the version, we just need to re-read the file
        cherrypy.config['_push_version'] = None
        return util.push_version()

    def supports_blacklist_validation(self):
        """
        Sub-classes should override this method and return true if it indends to support blacklist validation!
        Default is turned off so that it can be enabled by controller!
        """
        return False

    def is_route_blacklisted(self, module_name=""):
        '''
            This method validates a URL against the blacklist tuple created at the begining of this module.
            The idea is to black list certain URLs depending upon the mode you are in,
            e.g. in lite mode a lot of manager URLs need to be prevented from accessing!

            This method gets called from decorators.py !!
        '''
        if self.supports_blacklist_validation() == False:
            return False

        relative_uri = "/".join(cherrypy.request.path_info.split('/')[2:]) #remove the locale from the front of the URI
        mode=cherrypy.config['product_type']
        logger.debug('Checking if URL %s is black listed for %s' % (relative_uri, mode))

        if mode == 'enterprise': #prevent having to run the through blacklist for Enterprise, for now. TODO: Cloud mode will need certain black listed URLs however
            return

        relative_uri = relative_uri.lower()

        if module_name == "":
            module_name = self.__module__

        if module_name in _SPLUNK_BLACKLIST:
            module_black_list = _SPLUNK_BLACKLIST[module_name]
            for props in module_black_list:
                if props['endpoint'].match(relative_uri):
                    if mode in props['modes']:
                        return True
        return False

    def raise_403_error(self):
        raise cherrypy.HTTPError(403, _('Unauthorized to access this resource.'))

    def web_debug_capability_check(self):
        try:
            entity = en.getEntity('/authentication/', 'current-context', namespace=splunk.getDefault('namespace'))
        except Exception as e:
            self.raise_403_error()
        else:
            capabilities = entity.get('capabilities')
            if capabilities and 'web_debug' in capabilities:
                return
            self.raise_403_error()
