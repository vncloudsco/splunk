from __future__ import absolute_import
from __future__ import division
from builtins import object
from builtins import filter
from splunk.util import cmp
from builtins import zip
from builtins import range
import collections
import hashlib
import imp
import json
import logging
import math
import os
import random
import re
import subprocess
import sys
import threading
import time

import cherrypy
from cherrypy.lib import httputil as http

from splunk.appserver.mrsparkle.lib import times
import splunk.clilib.bundle_paths
import splunk.clilib.cli_common
import splunk.entity as en
import splunk.rest.payload
import splunk.search.Parser
import splunk.search.Transformer as xformer
import splunk.util

logger = logging.getLogger('splunk.appserver.lib.util')

parserLogger = logging.getLogger('splunk.parseLogger')

system_random = random.SystemRandom()

class SplunkRestartException(Exception):
    pass

class InvalidURLException(Exception):
    pass


def isLite():
    product_type = cherrypy.config.get('product_type')
    return product_type == 'lite' or product_type == 'lite_free'

def isCloud():
    instance_type = cherrypy.config.get('instance_type')
    return instance_type == 'cloud'

def isSingleCloud():
    if not isCloud():
        return False
    try: 
        cloud_indexes = en.getEntity('cluster_blaster_indexes', 'sh_indexes_manager')
        if cloud_indexes:
            return False
        else:
            return True
    except Exception as e:
        return True

def getProductName():
    if isLite():
        productName = 'Light'
    elif isCloud():
        productName = 'Cloud'
    else:
        productName = 'Enterprise'
    return productName

def getAppType():
    return 'add-on' if isLite() else 'app'

def getFaviconURL():
    customFavicon = cherrypy.config.get('customFavicon')
    if customFavicon:
        colonIndex = customFavicon.find(':')
        if colonIndex == -1:
            appName = 'search'
            directoryArray = customFavicon.split("/")
        else:
            appName = customFavicon[:colonIndex]
            directoryArray = customFavicon[colonIndex+1:].split("/")
        directoryArray.insert(0, appName)
        directoryArray.insert(0, 'app')
        directoryArray.insert(0, 'static')
        return make_url(directoryArray)

    faviconFile = getFaviconFileName()

    return make_url(['static', 'img', faviconFile])

def getFaviconFileName():
    if 'product_type' not in cherrypy.config:
        return 'favicon.ico'
    if cherrypy.config['product_type'] == 'hunk':
        return 'favicon_hunk.ico'
    elif isLite():
        return 'favicon_lite.ico'
    else:
        return 'favicon.ico'

def getDashboardV1TemplateUri():
    return '/pages/dashboard.html'

def getDashboardV2TemplateUri():
    '''
    Version 2 dashboards can only be rendered by a separate app as of Pinkie Pie release
    '''
    DEFAULT_APP_NAME = 'splunk-dashboard-app'
    conf_settings = en.getEntity('/configs/conf-web', 'settings')
    name = conf_settings.get('splunk_dashboard_app_name', DEFAULT_APP_NAME)

    # We only allow A-Z and dashes in the name. Search to see if we have bad names.
    has_bad_name = re.search(
        r'[^a-z-]',
        name,
        re.IGNORECASE)

    if has_bad_name:
        logger.warn(
            'web.conf.in: key "splunk_dashboard_app_name" has unsupported characters in value. Please use only A-z and dashes. Defaulting to %s.'
            % DEFAULT_APP_NAME)
        name = DEFAULT_APP_NAME

    return '/view/{}:/templates/dashboard.html'.format(name)

def getServerInfoPayload():
    server_info = splunk.rest.payload.scaffold()
    server_info['entry'][0]['content']['isFree'] = cherrypy.config['is_free_license']
    server_info['entry'][0]['content']['isTrial'] = cherrypy.config['is_trial_license']
    server_info['entry'][0]['content']['version'] = cherrypy.config['version_number']
    server_info['entry'][0]['content']['guid'] = cherrypy.config['guid']
    server_info['entry'][0]['content']['build'] = cherrypy.config['build_number']
    server_info['entry'][0]['content']['staticAssetId'] = cherrypy.config['staticAssetId']
    server_info['entry'][0]['content']['product_type'] = cherrypy.config['product_type']
    server_info['entry'][0]['content']['serverName'] = cherrypy.config['serverName']
    server_info['entry'][0]['content']['instance_type'] = cherrypy.config['instance_type']
    server_info['entry'][0]['content']['licenseState'] = cherrypy.config['license_state']
    server_info['entry'][0]['content']['addOns'] = cherrypy.config['addOns']
    server_info['entry'][0]['content']['activeLicenseSubgroup'] = cherrypy.config['activeLicenseSubgroup']
    return server_info

def decomposeIntentions(q, hostPath, namespace, owner) :
    '''
    Given a set of params, returns a dictionary capable of being passed to the client and turned into a SearchContext.
    '''
    decompositionFailed = False
    try:
        parsedObj = splunk.search.Parser.parseSearch(
            q,
            hostPath=hostPath,
            sessionKey=cherrypy.session['sessionKey'],
            namespace=namespace,
            owner=owner
        )
        decomposedSearch, intentions = xformer.decomposeSearch(namespace, owner, parsedObj, q)
        baseSearch = str(parsedObj)

        sequence = str(time.time())
        #parserLogger.debug('DECOMPOSE %s IN  %s' % (sequence, json.dumps({'q': q})))
        #parserLogger.debug('DECOMPOSE %s OUT %s' % (sequence, json.dumps({'q': decomposedSearch.jsonable(), 'intentions': intentions})))

    except Exception as e: #never break on resurrecting.  except xformer.SearchTransformerException as e:
        logger.warn("Exception in resurrectSearch when trying to parse the following search - " + q)

        # import traceback; logger.error(traceback.format_exc())
        baseSearch = q
        intentions = []
        decompositionFailed = True

    return { "fullSearch" : q, "baseSearch" : baseSearch, "intentions": intentions, "decompositionFailed": decompositionFailed}


def layPiping(q):
    """ensure that the search string passed to client is qualified with a '|'
    if not search; 'qualifiedSearch' always begins with a command"""
    q = q.lstrip(' \t\r\n')
    if not q.startswith('search '):
        q = '| ' + q
    return q

def resurrectFromSavedSearch(savedSearchObject, hostPath, namespace, owner, now=None) :
    '''
    Wraps the return from decomposeIntentions() to pass saved search data to
    the client
    '''

    def nowedTime(time_arg, now):
        try:
            nowed = times.splunktime2Iso(time_arg, now=now)
            return str(splunk.util.dt2epoch(splunk.util.parseISO(nowed[time_arg])))
        except KeyError:
            logger.warn("Could not properly map a saved searche's time argument using the 'now' paramter: '%s'" % now)
            return time_arg

    q = layPiping(savedSearchObject["qualifiedSearch"])

    returnDict = decomposeIntentions(q, hostPath, namespace, owner)

    # Grab earliest / latest also for the client
    if savedSearchObject.get('dispatch.earliest_time'):
        earliestTime = savedSearchObject.get('dispatch.earliest_time')

        if now:
            earliestTime = nowedTime(earliestTime, now)

        returnDict["earliest"] = earliestTime
        if (isEpochTimeArg(earliestTime)):
            returnDict["earliestTZOffset"] = getTZOffsetMinutes(earliestTime)

    returnDict['acl'] = savedSearchObject.get('eai:acl')

    if savedSearchObject.get('dispatch.latest_time'):
        latestTime = savedSearchObject.get('dispatch.latest_time')

        if now:
            latestTime = nowedTime(latestTime, now)

        returnDict["latest"] = latestTime
        if (isEpochTimeArg(latestTime)):
            returnDict["latestTZOffset"] = getTZOffsetMinutes(latestTime)

    returnDict["next_scheduled_time"] = savedSearchObject.get("next_scheduled_time", None)

    returnDict["s"] = savedSearchObject.getLink('alternate')
    returnDict["name"] = savedSearchObject.name

    return returnDict

def alerts_allowed():
    from splunk.models.saved_search import SavedSearch
    saved_search = SavedSearch('', cherrypy.session['user']['name'], 'newsearch')
    return saved_search.is_mutable('alert.severity')

def isEpochTimeArg(arg) :
    '''
    we simply check whether the argument is accepted by float().
    nice and short, and according to the internets this is faster than regex approaches.
    (http://mail.python.org/pipermail/python-list/2002-September/164892.html)
    '''
    try:
        float(arg)
        return True
    except (ValueError, TypeError) as e:
        return False



def getTZOffsetMinutes(epochTime) :
    '''
    returns the offset time in GMT in minutes, that the local timezone has at the given epochtime.
    In effect we merge dst offset and timezone offset logic into this one number
    and send down epochTimes with these numbers always to the client,  so we can
    completely short circuit the browsers timezone + dst handling, which is often faulty.
    Note:this is purely so that modules that need to display the date to the user can do
        so safely and without a trip to the server.
    '''
    t = time.localtime(float(epochTime))
    if (t[-1] == 1):
        return -time.altzone // 60
    else:
        return -time.timezone // 60


def resurrectSearch(hostPath, q, earliest=None, latest=None, remote_server_list=None, namespace=None, owner=None):

    # DC: problematic --  q = layPiping(q)

    returnDict = decomposeIntentions(q, hostPath, namespace, owner)

    if (earliest) :
        returnDict["earliest"] = earliest
        if (isEpochTimeArg(earliest)):
            returnDict["earliestTZOffset"] = getTZOffsetMinutes(earliest)
    if (latest) :
        returnDict["latest"] = latest
        if (isEpochTimeArg(latest)):
            returnDict["latestTZOffset"] = getTZOffsetMinutes(latest)

    if (remote_server_list) :
        returnDict["remote_server_list"] = remote_server_list

    return returnDict

def timeToAgoStr(t):
    import time
    result = 'Never'
    if t > 0:
        ago = time.time() - t
        result = ''
        if ago > 60:
            if ago >= 86400:
                days = ago // 86400
            hours = ago // 3600
            mins  = (ago%3600) // 60

            if len(result) > 0 or hours > 0:
                result +=  ("%dh " % (hours))

            result +=  ("%dm " % (mins))
            result += "ago"
        else:
            result = "< 1 min ago"

    return result

def timeToAgoSeconds(t):
    import time
    ago = 0
    if t > 0:
        ago = time.time() - t
    return ago


def remove_special_chars(mystring):
    return re.sub('[^A-Za-z0-9]+', '', mystring)



def current_url_path(include_qs=True):
    """
    Return the current url path, optionally with the query string
    encoded so it's safe to include anywhere in an HTML page
    """
    # path_info is fully decoded, so we need to encode it
    # query_string is encoded from the browser, but it may contain raw single quotes, etc
    # so we run the encoder over it again to pick up any stray dangerous characters
    if include_qs and cherrypy.request.query_string:
        return cherrypy.request.script_name+splunk.util.safeURLQuote(cherrypy.request.path_info)+'?'+splunk.util.safeURLQuote(cherrypy.request.query_string, '&%=+#')
    else:
        return cherrypy.request.script_name+splunk.util.safeURLQuote(cherrypy.request.path_info)

def make_absolute(fn, postfix='', basedir=None):
    if fn[0] == '/':
        return fn

    fragment = os.path.join(postfix, fn)

    fullpath = None
    if basedir is None:
        fullpath = splunk.clilib.bundle_paths.make_splunkhome_path_helper(fragment)
    else:
        fullpath = os.path.join(basedir, fragment)

    #logger.debug('make_absolute - returning %s' % os.path.join(basedir, postfix, fn) )
    return os.path.abspath(fullpath)

def make_url(target, _qs=None, translate=True, relative=False, __app_cache=None, encode=True, validate=True, appendcachebust=False):
    """
    Build a url from a relative or absolute url with optional query string

    Set translate to false if you don't want /splunk (or whatever root_path in the config is set to)
    prefixed to the url - Usually you want this on though.

    Can also add a query string by passing a list of tuples or a dict as _qs:
        self.url('/search/jobs', job_id=1234, action=delete, _qs=[('q', 'search val to quote')])
    or
        self.url('/search/jobs', job_id=1234, action=delete, _qs=dict(q='search val to quote'))
    dict values can be strings or lists of strings

    Static paths are constructed with a cache defeater segement embedded:

        /static/@<build_number>[.<push_number>]/

    This results in static paths like:

        /static/@12345/js/foo
        /static/@12345.1/js/foo

    Static assets for apps have an additional cache defeater number correlating to the app's
    build number as defined in app.conf:

        /static/@12345.1:2/app/unix/static/foo.png

    The URL handler in root.py strips out any requests with this schema
    """

    import splunk.appserver.mrsparkle.lib.module as module

    try:
        __app_cache = cherrypy.config['app_build_cache'] if __app_cache is None else __app_cache
    except KeyError:
        __app_cache = cherrypy.config['app_build_cache'] = {}

    if isinstance(target, list):
        if encode:
            target = '/'.join([splunk.util.safeURLQuote(x) for x in target])
        else:
            target = '/'.join(target)

        # target is now a string!
        if not relative:
            target = '/' + target
    else:
        if (not '?' in target and not '#' in target) and (encode):
            target = splunk.util.safeURLQuote(target)

    if validate and not url_has_valid_charset(target):
        raise InvalidURLException("Illegal characters in URL")

    if _qs:
        if isinstance(_qs, dict):
            # translate {'v1':'k1', 'v2':['v2-1','v2-2']} to [('v1','k1'), ('v2','v2-1'), ('v2','v2-2')]
            # nexted list comprehensions ftw
            qargs = []
            [ qargs.extend([(k, e) for e in v]) for k, v in [ (k, v if isinstance(v, (list, tuple)) else (v,) ) for k, v in _qs.items() ] ]
            _qs = qargs
        qargs = '?' + '&'.join([ '%s=%s' % (splunk.util.safeURLQuote(k, safe=''),
                                            splunk.util.safeURLQuote(v, safe='')) for k, v in _qs])
    else:
        qargs = ''

    if translate and target[0]=='/':
        segments = target.split('/')
        target_segment = target.split('/', 2)[1] if target!='/' else ''

        if segments[1] in ('static', 'modules'):
            app_name = segments[3] if len(segments)>4 and segments[2]=='app' else None
            if segments[1] == 'modules' and len(segments) > 2:
                moduleList = module.moduleMapper.getInstalledModules()
                if ('Splunk.Module.' + segments[2]) in moduleList:
                    app_name = moduleList.get('Splunk.Module.' + segments[2])['appName']

            if app_name:
                if app_name not in __app_cache:
                    # XXX Temporary hack to cache app config data until getConf() handles caching itself.
                    try:
                        rawConfig = splunk.bundle.getConf('app', namespace=app_name)
                        app_version = ':%d' % int(rawConfig['install'].get('build', 0))
                    except (splunk.ResourceNotFound, ValueError, TypeError):
                        app_version = ':0'
                    __app_cache[app_name] = app_version
                else:
                    app_version = __app_cache[app_name]
            else:
                app_version = ''

            target = target.replace('/%s/' % (target_segment,), '/%s/%s%s/' % (target_segment, static_asset_version(), app_version))
        elif segments[1].startswith('i18ncatalog') or appendcachebust:
            target = add_url_params(target + qargs, {'version': static_asset_version()})
            """Already added qargs so reset it"""
            qargs = ''
        return make_i18n_url(target+qargs)
    return target+qargs

def reset_app_build(app_name):
    try:
        del cherrypy.config['app_build_cache'][app_name]
    except KeyError:
        pass

def strip_url(path):
    """Return a URL without the root_endpoint or i18n prefixes"""
    return strip_i18n_url(path)

def make_url_internal(url):
    """Return the URL as a safe internal URL"""
    try:
        return '/' + url.lstrip('/')
    except:
        return None

def url_has_valid_charset(url):
    """
    HTTP URLs as a whole may only contain a subset of the ASCII character set; other characters should
    of been percent encoded.  See RFC 3986
    We could be more through here by parsing the URL itself, but this should stop basic attacks
    """
    return False if re.search(r'[^a-zA-Z0-9._~:/?#\[\]@!$&\'()*+,;=%-|]', url) else True


def push_version():
    """
    push_version is a local-to-installed-instance version number
    used in combination with the build number to specify a revision of static
    resources in /static
    This number should be incremented by POSTing to /_bump any time
    a static resource has been changed to force the client to fetch the new
    resource regardless of the Expires headers that were sent with it.
    """
    _push_version = cherrypy.config.get('_push_version', None)
    if _push_version is None:
        try:
            f = open(make_absolute('var/run/splunk/push-version.txt'), 'r')
            num = int(f.read(20))
            f.close()
            _push_version = cherrypy.config['_push_version'] = num
        except:
            _push_version = cherrypy.config['_push_version'] = 0
    return _push_version

def normalize_value(value):
    """
    Convert a string value into an integer or boolean if appropriate
    """
    if not isinstance(value, splunk.util.string_type):
        return value

    # first try to cast to ints; if fail, try to cast to boolean
    try:
        value = int(value)
    except ValueError:
        value = splunk.util.normalizeBoolean(value)

    return value

def splunk_to_cherry_cfg(conf, stanza):
    '''
    Cast conf settings to proper assumed types;
    CherryPy wants integers to be integers and bools to be bools
    '''

    cfg = {}
    for k, v in splunk.clilib.cli_common.getConfStanza(conf, stanza).items():
        cfg[k] = normalize_value(v)

    if conf == "web" and stanza == "settings":
        if "caCertPath" in cfg: # copy deprecated caCertPath to serverCert
            cfg["serverCert"] = cfg["caCertPath"]

    return cfg

def get_apps_dir():
    return splunk.clilib.bundle_paths.get_base_path()

def get_slaveapps_dir():
    return splunk.clilib.bundle_paths.get_slaveapps_base_path()

def make_splunkhome_path(parts):
    return splunk.clilib.bundle_paths.make_splunkhome_path(parts)

def is_api():
    is_api = getattr(cherrypy.request, 'is_api', None)

    if is_api is None:
        path = cherrypy.request.path_info.lstrip('/').split('/')
        # [ 'en-US', 'api', '...' ]
        is_api = len(path)>1 and path[1] == 'api'
        cherrypy.request.is_api = is_api

    return is_api

def is_xhr():
    '''
    Determine if XHR request.
    '''
    return True if cherrypy.request.headers.get("X-Requested-With")=="XMLHttpRequest" else False

def urlmappings(ctrl, root_path='/', exclude=[], _seen=None):
    """Recurse the controller tree and extract data used for documentation"""
    import inspect
    import types
    import splunk.appserver.mrsparkle.controllers as controllers
    assert isinstance(ctrl, controllers.BaseController)
    if _seen is None:
        _seen = set()
    maplist = []
    ctrlname = ctrl.__class__.__name__
    for propname in dir(ctrl):
        prop = getattr(ctrl, propname)
        if root_path+propname in exclude:
            continue
        if isinstance(prop, types.MethodType):
            args, varargs, varkw, argdefaults = inspect.getargspec(prop)
            otherargs = args[0:len(args)-len(argdefaults)] if argdefaults else args
            sig = []
            if otherargs:
                sig.append(', '.join(otherargs))
            if argdefaults:
                defaults = dict( zip(args[0-len(argdefaults):], argdefaults) )
                sig.append(', '.join( [ '%s=%s' % (k, v) for k, v in defaults.items() ] ))
            else:
                defaults = {}
            pathdata = {
                'sig' : ', '.join(sig),
                'path' : None,
                'basepath' : None,
                'pathextra' : '',
                'ctrl' : ctrlname,
                'method' : propname,
                'is_route' : False,
                'doc' : prop.__doc__,
                'varargs' : varargs,
                'varkw' : varkw,
                'args' : otherargs,
                'defaults' : defaults
            }
            routes = getattr(prop, 'routes', None)
            if routes:
                pathdata['is_route'] = True
                for route in routes:
                    for argname in route.defaults:
                        del defaults[argname]

                    pathdata['path'] = "%s[%s]" % (root_path, route.route_str)
                    pathdata['basepath'] = root_path
                    pathdata['pathextra'] = route.route_str
                    pathdata['route_defaults'] = route.defaults
                    pathdata['args'] = [ arg for arg in otherargs if (arg not in route.defaults) and (arg not in route.requires)]
                    pathdata['defaults'] = defaults
                    maplist.append(pathdata)
                continue
            if getattr(prop, 'exposed', None):
                if propname == 'index':
                    pathdata['path'] = root_path
                    pathdata['basepath'] = root_path
                elif propname == 'default':
                    pathdata['pathextra'] = '?'
                    pathdata['path'] = root_path+'?'
                    pathdata['basepath'] = root_path
                else:
                    pathdata['path'] = root_path+propname
                    pathdata['basepath'] = root_path+propname
                maplist.append(pathdata)
        elif isinstance(prop, controllers.BaseController) and not id(prop) in _seen:
            maplist.extend(urlmappings(prop, "%s%s/" % (root_path, propname), exclude=exclude, _seen=_seen))
            _seen.add(id(prop))
    return maplist

def use_future_expires():
    """
    Convenience method for setting cherrypy future expires headers.
    Will only enable futures expires headers if use_future_expires config is True.
    For full details see: http://www.mnot.net/cache_docs/
    """
    if cherrypy.config.get('use_future_expires', False):
        cherrypy.response.headers["Expires"] = http.HTTPDate(cherrypy.response.time + 31536000 ) # set expires 1 year ahead
        cherrypy.response.headers["cache-control"] = 'public, max-age=31536000' # 1 year


def get_module_classes(module, parent=None):
    """
    Returns all classes defined in a python module.
    Takes an optional parent parameter that returns a list of classes subclassed from parent.
    """
    import inspect
    classes = [ item for item in module.__dict__.values() if inspect.isclass(item) and item.__module__ == module.__name__ ]
    if not parent == None:
        classes = [c for c in classes if issubclass(c, parent)]
    return classes

def getPercentiles(orderedList, lowerPercentile, upperPercentile):
    '''
    This is an approximation method for obtaining a pair of lower and upper percentile values from a list
    '''

    if len(orderedList) == 0: return (None, None)

    def f(p, ln):
        n = p * (ln - 1) + 1
        d, k = math.modf(n)
        return int(n), int(k), d

    def v(percentile, oList):
        n, k, d = f(percentile, len(oList))
        if k == 0 or len(oList) == 1:
            return oList[0]
        elif k == len(oList) - 1:
            return oList[-1]
        else:
            return oList[k] + d * (oList[k + 1] - oList[k])

    return (v(lowerPercentile, orderedList), v(upperPercentile, orderedList))

def is_valid_cherrypy_session_id(token):
    return (token == cherrypy.session.id)


def args_to_dict(args=None, accept=None, ignore_invalid=True):
    """
    Convert application arguments to a dictionary
    All arguments beginning with "--" are converted to a key value pair
    so --foo=bar --boolflag converts to {'foo':'bar', 'boolflag': True}

    args should be a list of arguments; defaults to sys.argv
    If accept is a list of argument names then any arguments not in that list
    will throw a ValueError
    """
    result = {}
    if args is None:
        args = sys.argv[1:]
    for arg in args:
        if arg[:2]!='--':
            if ignore_invalid:
                continue
            raise ValueError("Invalid argument '%s'" % arg)
        arg = arg[2:].split('=', 1)
        if accept is not None and arg[0] not in accept:
            raise ValueError("Invalid argument '--%s'" % arg[0])
        if len(arg)==1:
            arg, param = arg[0], True
        else:
            arg, param = arg[0], normalize_value(arg[1])
        result[arg] = param
    return result


def apply_etag(contentstring):
    '''
    Applies the ETag conditional header to the outgoing HTTP response.  A hash
    of contentstring is generated and inserted as an ETag HTTP header.  If
    the request contains an 'If-None-Match' header and the value matches the
    new hash, the response status will be set to 304, and this method will
    return True.  Otherwise, False.

    Example usage:

        if util.apply_etag(output):
            return None
        else:
            return output
    '''

    if contentstring == '': return False
    hash = hashlib.sha1()
    if sys.version_info >= (3, 0) and isinstance(contentstring, str):
        contentstring = contentstring.encode("utf-8")
    hash.update(contentstring)
    outputhash = '"' + hash.hexdigest() + '"'
    cherrypy.response.headers['ETag'] = outputhash
    if (cherrypy.request.headers.get('If-None-Match', False) == outputhash):
        cherrypy.response.status = 304
        return True
    else:
        return False

def set_cache_level(cache_level, response):
    '''
    Sets the HTTP caching headers to a preset configuration.
    Returns either the original response or None.

    cache_level
        'never': explicit defeat of client-side caching
        'etag': applies an ETag header by MD5 hashing the body
        'always': sets max caching

    Returns either the given response or None.  Returns None if the cache_level
    is set to 'etag' and a hash of the given response matches the If-None-Match
    header in the request.

    Herein lies another fantastic IE quirk, this time relating to the following
    combination: SSL webserver, IE client, HTTP request from Flash/ActionScript.
    The 'Cache-Control' header *must* begin with 'no-store', otherwise Flash
    will error out with the ever helpful, "IO Error #2032".  One is free to
    append any other header one wishes after the 'no-store'.

    Usage:

    return util.set_cache_level('etag', response)
    '''

    if cache_level == 'never':
        cherrypy.response.headers['Cache-Control'] = 'no-store, max-age=0, no-cache, must-revalidate'
        cherrypy.response.headers['Expires'] = 'Thu, 26 Oct 1978 00:00:00 GMT'

    elif cache_level == 'etag':
        # ie6 requires max-age=0 to ensure etag validation is performed otherwise it will not make a request
        if is_ie():
            cherrypy.response.headers['Cache-Control'] = 'max-age=0, must-revalidate, no-cache'
        # immediately return 304 with empty body if etag matches
        if apply_etag(response):
            return None

    elif cache_level == 'always':
        # set 1 year ahead
        cherrypy.response.headers['Cache-Control'] = 'max-age=31536000'
        cherrypy.response.headers['Expires'] = http.HTTPDate(cherrypy.response.time + 31536000)

    else:
        raise ValueError('Unrecognized cache level: %s' % cache_level)

    return response

def import_from_path(path, filter=None, ignoreInit=True):
    modnames = [filename[:-3] for filename in os.listdir(path) if filename.endswith('.py')]
    if filter:
        modnames = [modname for modname in modnames if modname.find(filter) >= 0]
    mods = []
    for modname in modnames:
        if ignoreInit and modname.startswith('__init__'):
            continue
        try:
            f = None
            f, name, desc = imp.find_module(modname, [path])
            if not f == None:
                mods.append(imp.load_module(modname, f, name, desc))
        except ImportError as e:
            logger.info(e.args[0])
            continue
        finally:
            if hasattr(f, "close"):
                f.close()

    return mods

def restart_splunk():
    logger.info("SERVER RESTART: Restarting Splunk Server...")

    new_pid = None
    command = [os.path.join(os.environ["SPLUNK_HOME"], "bin", "splunk"), "restart", "--answer-yes", "--no-prompt"]
    if sys.platform == "win32":
        try:
            # We cannot use subprocess.Popen under Windows, since it
            # makes the child process inherit all handles, including
            # any open ports.  This makes it impossible for the child
            # to restart SplunkWeb, since the ports will remain opened.
            # So, we use WinAPI's CreateProcess directly.

            #pylint: disable=F0401
            import pywintypes
            import win32process
            creationflags = win32process.CREATE_DEFAULT_ERROR_MODE | win32process.CREATE_NO_WINDOW
            startupinfo = win32process.STARTUPINFO()

            logger.info("SERVER RESTART: Creating Windows Process...")
            hp, ht, pid, tid = win32process.CreateProcess(
                                     None,
                                     ' '.join(command),
                                     # no special security
                                     None, None,
                                     # must NOT inherit handles, as any
                                     # open ports are also inherited,
                                     # making the restart impossible
                                     0,
                                     creationflags,
                                     os.environ,
                                     None,
                                     startupinfo)
            new_pid = pid
            logger.info("SERVER RESTART: Windows Process Preated...")

            # prevent handle leaks
            hp.Close()
            ht.Close()

        except pywintypes.error as e:
            logger.error("SERVER RESTART: %s" % str(e))
            raise SplunkRestartException(str(e))
    else:
        import subprocess
        new_pid = subprocess.Popen(command, env = os.environ, close_fds=True).pid

    logger.info("SERVER RESTART: Child PID: " + str(new_pid))

    # reset the search service flag
    #SearchService.gSearchService.clearSystemError("restartRequired")
    return True



def check_restart_required():
    '''
    Indicates if splunkd has raised the restart flag as a result of new
    configuration changes.
    '''

    try:
        en.getEntity('messages', 'restart_required')
        return True
    except splunk.ResourceNotFound:
        return False
    except Exception as e:
        logger.warn('unable to determine if restart is required: %s' % e)
    return False



def get_time(hours=0, minutes=0, seconds=0, microseconds=0, hourCap=False):
    '''
    Returns a struct with time-relevant values in the format of:
    (year, days, hours, minutes, seconds)

    if hourCap is True, put all time above 60 min in hours. do not set years and days.

    This allows you to provide a number beyond the bounds of a typical Python
    Time object and return some time-relevant values which can then be used
    to instantiate a Python Time object.

    For example if I have 600 seconds I can call get_time like:
    get_time(seconds=600)

    Returns:
    (0.0, 0.0, 0.0, 10.0, 0.0)
    '''
    seconds = float(seconds)
    seconds = seconds + hours * 60 * 60
    seconds = seconds + minutes * 60
    seconds = seconds + microseconds * 1e-6

    if not hourCap:
        years, seconds = divmod(seconds, 31557600) # 365.25 days / year
    else:
        years = 0
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if not hourCap:
        days, hours = divmod(hours, 24)
    else:
        days = 0

    return years, days, hours, minutes, seconds

class DeferCall(object):
    """
    Late binding function proxy
    Defers execution of a function until the point its result is required

    eg. to defer gettext lookups in a data structure until the user's context is known:
    mapping = {
        'prompt' : DeferCall(_, 'Enter your Username and password to continue'),
        'invalid': DeferCall(_, 'Invalid Password'),
        'delete': DeferCall(ungettext, 'Delete %d file?', 'Delete %d files?')
    }

    The result can then be displayed later:
    print(mapping['delete'] % filecount)
    The function won't be executed until the print statement fetches the value

    The result of the function call isn't cached, so the proxy can be used
    multiple times in different contexts
    """

    __slots__ = ('_proxy_fn', '_proxy_a', '_proxy_kw')
    def __init__(self, fn, *a, **kw):
        self._proxy_fn = fn
        self._proxy_a = a
        self._proxy_kw = kw

    def __unicode__(self):
        return splunk.util.unicode(self._proxy_fn(*self._proxy_a, **self._proxy_kw))

    for n in ('str', 'repr', 'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'cmp',
                'hash', 'nonzero', 'getattr',
                'delattr', 'len', 'getitem', 'setitem', 'delitem', 'iter',
                'contains', 'add', 'sub', 'mul', 'floordiv', 'mod', 'divmod',
                'pow', 'lshift', 'rshift', 'and', 'xor', 'or', 'div', 'truediv',
                'radd', 'rsub', 'rmul', 'rdiv', 'rtruediv', 'rfloordiv', 'rmod',
                'rdivmod', 'rpow', 'rlshift', 'rrshift', 'rand', 'rxor', 'ror'
                'iadd', 'isub', 'imul', 'idiv', 'itruediv', 'ifloordiv', 'imod',
                'ipow', 'ilshift', 'irshift', 'iand', 'ixor', 'ior', 'neg'
                'pos', 'abs', 'invert', 'complex', 'int', 'long', 'float',
                'oct', 'hex', 'index', 'coerce', 'call'):
        exec('def __%s__(self, *a, **kw): return self._proxy_fn(*self._proxy_a, **self._proxy_kw).__%s__(*a, **kw)' % (n, n))
    del n



def deep_update_dict(original, overlay):
    """
    Recursively update a dictionary with another dictionary
    ie. dict values in the original dict and recursively merged with a correspecting overlay dict
    should it exist, rather than the latter just replacing the former.

    NOTE this does an in-place update and thus modifies original
    """
    for key, val in overlay.items():
        if key in original and isinstance(val, dict):
           original[key] = deep_update_dict(original[key], val)
        else:
            original[key] = val
    return original


class IterCache(object):
    def __init__(self, it):
        self.it = it
        self._cache = []
        self._complete = False

    def __iter__(self):
        return iter(self._cache) if self._complete else self

    def __next__(self):
        try:
            result = next(self.it)
            self._cache.append(result)
            return result
        except StopIteration:
            self._complete = True
            raise

def json_html_safe(item):
    """
    !!!DEPRECATED USE json_decode!!!
    Used by templates as a filter
    """
    return json.dumps(item, html_safe=True)

def json_decode(value):
    """
    JSON-encodes the given Python object.
    JSON permits but does not require forward slashes to be escaped.
    This is useful when json data is emitted in a <script> tag
    in HTML, as it prevents </script> tags from prematurely terminating
    the javscript.  Some json libraries do this escaping by default,
    although python's standard library does not, so we do it here.
    http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    """
    return json.dumps(value).replace("</", "<\\/")

def is_safari():
    user_agent_lower = cherrypy.request.headers.get("User-Agent", "").lower()
    return ('safari' in user_agent_lower and not 'chrome' in user_agent_lower)

def is_ios():
    user_agent_lower = cherrypy.request.headers.get("User-Agent", "").lower()
    return ('ipad' in user_agent_lower or 'ipod' in user_agent_lower or 'iphone' in user_agent_lower)

def is_ie():
    user_agent = cherrypy.request.headers.get("User-Agent", "")
    return user_agent.find("MSIE")>-1

def is_ie_6():
    user_agent = cherrypy.request.headers.get("User-Agent", "")
    return user_agent.find("MSIE 6")>-1

def redirect_url_is_ie_6_safe(url):
    """
    In IE 6, if a redirect Location header is specified with both a query string and a fragment id, the entire URL
    (including fragment) will be sent to the server, which will cause CherryPy to return a 400.
    This method checks that a URL is safe to use as a redirect in IE 6.
    """
    hash_pos = url.find('#')
    if hash_pos < 0:
        # if there is no fragment id in the url, it is safe
        return True

    # if there is a fragment but no query string, it is safe
    # otherwise it is unsafe
    return (not '?' in url[0:hash_pos])

def agent_supports_flash():
    """
    WARNING: this is not an exhaustive check for Flash support, current implementation is treating only iOS devices
    as Flash-incompatible
    """
    return (not is_ios())

def replace_vars(template, replacement_map, decorators=None, open_delimiter="$", close_delimiter="$", escape="\\", safe=True, retain_escape=False, default=None):
    '''
    Given a template string, look for any substrings delimited by the given open and close
    delimiter, and replace them with values from the replacement_map. Allows for escaping
    of delimit characters and multi-character open and close delimiters.

    __Escape characters must not appear in the delimiters.__

    template        -- The template containing the variables.
    replacement_map -- The replacement map, this should be a regular python dictionary.
    decorators      -- A list of functions to call on the replacement value before it is substitued into the template.
    open_delimiter  -- The character or characters that denote the start of a variable in the template.
    close_delimiter -- The character or characters that denote the end of a variable in the template.
    escape          -- The character that instructs the processor to ignore the next character in the template.
    safe            -- Denotes if all the varialbes must be in replacement_map. If safe == False and a variable is missing, raises ValueError.
    retain_escape   -- Instructs the processor to return escape characters in their original positions.

    TODO: This could be done much more quickly using the Template class from string.py, because it uses a
          regex to do the variable parsing. However, it would not be capable of handling escaped delimiters
          inside of the variable name. Whether that's a practical concern is unclear, but as long as
          this remains "fast enough" it should suffice.
    '''

    inVar = False
    varbuffer = []
    output = []
    o_delim_len = len(open_delimiter)
    c_delim_len = len(close_delimiter)
    iterator = enumerate(template)

    if decorators != None and not isinstance(decorators, list):
        decorators = [decorators]

    for i, c in iterator:

        if c == escape:
            try:
                val = next(iterator)
                if inVar:
                    if retain_escape:
                        varbuffer.append(c)
                    varbuffer.append(val[1])
                else:
                    if retain_escape:
                        output.append(c)
                    output.append(val[1])
            except StopIteration:
                pass
            continue

        if template[i:i+o_delim_len] == open_delimiter and not inVar:
            inVar = True
            varbuffer.append(c)
            if o_delim_len > 1:
                for j in range(i+1, i+o_delim_len):
                    varbuffer.append(iterator.next()[1])
            continue

        elif template[i:i+c_delim_len] == close_delimiter and inVar:
            inVar = False

            # Guard against $$
            if len(varbuffer) != o_delim_len:
                varbuffer.append(c)
                if c_delim_len > 1:
                    for j in range(i+1, i+c_delim_len):
                        varbuffer.append(iterator.next()[1])

                var = ''.join(varbuffer)
                var_name = var[o_delim_len:-(c_delim_len)]
                if var_name in replacement_map:
                    val = replacement_map[var_name]
                elif default != None:
                    val = default
                elif safe:
                    val = var
                else:
                    raise ValueError("Could not find the variable %s in the replacement map." % var)

                val = splunk.util.unicode(val)
                if decorators:
                    for dec in decorators:
                        val = dec(val)
                    output.append(val)
                else:
                    output.append(val)

            # If we found a close delimiter right after an open delimiter just return the
            # two delimiters together.
            else:
                varbuffer.append(c)
                if c_delim_len > 1:
                    for j in range(i+1, i+c_delim_len):
                        varbuffer.append(iterator.next()[1])
                output.append(''.join(varbuffer))

            varbuffer = []
            continue

        if inVar:
            varbuffer.append(c)
        else:
            output.append(c)

    # Found an unclosed variable so dumping this to the output.
    # This is definitely a candidate for being scrapped.
    if len(varbuffer) > 0:
        output.append(''.join(varbuffer))

    return ''.join(output)


def parse_xsplunkd_header():
    '''
        The new X-Splunkd: header format for authed users is

        X-Splunkd: <proxy_token> <csrf_token> <authtoken> <0/1>
    '''
    header = cherrypy.request.headers.get('X-Splunkd')
    if header:
        parts = header.split(' ', 3)
        parts_len = len(parts)
        if parts_len == 1:
            return {
                'proxy_token': parts[0]
            }
        if parts_len > 3:
            return {
                'proxy_token': parts[0],
                'csrf_token': parts[1],
                'authtoken': parts[2],
                'sso_created_session': splunk.util.normalizeBoolean(parts[3])
            }
    return {}

def get_request_id():
    """
    Generate a string id that's unique to the active request
    If there's no active request then it returns '-'
    """
    response = cherrypy.serving.response
    return '%04x%02x%04x' % (int(response.time), (int(response.time % 1 * 256)), id(response)) if response else '-'

def get_active_controller():
    """Return the class of controller that the current request handler belongs to"""
    return cherrypy.request.handler.callable.__self__.__class__

def parse_breadcrumbs_string(arg):
    """
    Parse a breadcrumb list passed via url
    Breadcrumbs are tuples of name|url
    Breadcrumb tuples are tab separated
    eg.  "Manager|/en-US/manager/search\tData Inputs|/en-US/manager/search/datainputstats"

    Returns a list of (name, url) tuples suitable for passing to admin templates as the breadcrumbs argument
    """
    if not arg:
        return [('Manager', make_url(['manager', splunk.getDefault('namespace')], translate=False)) ]
    tuples = arg.split('\t')
    return splunk.util.sanitizeBreadcrumbs([ entry.split('|') for entry in tuples ])

def build_breadcrumbs_string(breadcrumbs):
    """
    Build a readable breadcrumb string for use with urls (after url encoding)
    from a standard list of (name, url) tuples
    """
    tuples = [ '%s|%s' % (name, url) for (name, url) in breadcrumbs ]
    return "\t".join(tuples)

def extend_breadcrumb(breadcrumb, current_url, new_title):
    result = breadcrumb[:-1] # exclude final entry that doesn't have a url
    result.append( (breadcrumb[-1][0], current_url) ) # add url to final entry
    result.append( (new_title, None) )
    return result

def complete_breadcrumb(breadcrumb, current_url):
    """Add a URL to the final entry of a breadcrumb"""
    result = breadcrumb[:-1] # exclude final entry that doesn't have a url
    result.append( (breadcrumb[-1][0], current_url) ) # add url to final entry
    return result


def convert_to_bytes(relative_value):
    '''
    Converts a string value of a size specifier to a byte integer. This method
    uses base-2 to do calculations.

    NOTE: relative_value is assumed to use not have any thousands separators,
          and use a period (.) to denote decimals.

    USAGE

        >>> convert_to_bytes('10MB')
        102400000
        >>> convert_to_bytes('40 GB')
        42949672960
        >>> convert_to_bytes('300')
        300

    '''


    prefix_table = {
        'YB': 80,
        'ZB': 70,
        'EB': 60,
        'PB': 50,
        'TB': 40,
        'GB': 30,
        'MB': 20,
        'KB': 10,
        'YiB': 80,
        'ZiB': 70,
        'EiB': 60,
        'PiB': 50,
        'TiB': 40,
        'GiB': 30,
        'MiB': 20,
        'KiB': 10,
        'B': 0
    }
    try:
        relative_value = relative_value.strip()
    except:
        raise ValueError('value must be a string')

    rex = re.compile(r'([0-9\-\.]+)\s*([A-Za-z]{1,3})?')
    match = rex.search(relative_value)

    if match:
        if match.group(2):
            val = match.group(1)
            units = match.group(2)
            if units not in prefix_table:
                raise ValueError('unrecognized units: %s' % units)
            return float(val) * (2**prefix_table[units])

        elif match.group(1):
            return int(match.group(1))

    raise ValueError('cannot convert to bytes: %s' % relative_value)

# sniff in a pem-style SSL certificate to see if it is passphrase (or otherwise) encrypted
# for SPL-34126
def is_encrypted_cert(cert_filename):
    cf = open(cert_filename)
    for line in cf.readlines():
        if line.startswith("Proc-Type:") and "ENCRYPTED" in line:
            cf.close()
            return True
    cf.close()
    return False


def generateSelfHelpLink(context=None):
    '''
    Generates the contextual URI to the splunk.com help system
    '''

    locale = current_lang_url_component()

    if not context:
        # generate standard help link by passing a keyword that is composed
        # of a cleansed URI (remove locale and namespace)
        context = cherrypy.request.path_info.strip('/').split('/')
        appContext = ''

        if context[0].startswith(locale):
            context.pop(0)
        if context[0] in ('manager'):
            context.pop(1)
        if context[0] in ('app'):
            appName = context[1]
            entity = en.getEntity('apps/local', appName)
            if any(filter((lambda x: x[0] == 'disable'), entity.links)):
                # make sure it's not an internal Splunk app
                appVersion = entity.get('version')
                appContext = '[%s:%s]' % (appName, appVersion)

        context = appContext + '.'.join(context)

    params = {
        'location': context
    }

    uri = make_url(['help'], _qs=params)
    return uri

def extract_help_links(text):
    if not text or len(text)==0:
        return ''
    help_pattern = "(\[\[\?([^\]]+)\]\])"
    matches = re.findall(help_pattern, text)
    for m in matches:
        if isinstance(m, tuple):
            text = text.replace(m[0], generateSelfHelpLink(m[1]))
    return text


_popen_lock = threading.Lock()
def Popen(*a, **kw):
    """
    close_fds is not supported on Windows if stdin/stderr/stdout are redirected
    (which they inevitably are for splunkweb) so strip that option.  Doesn't seem
    to trigger the same level of side effects as its omission does in *nix

    In addition, there's indication that Popen has a race condition in a threaded
    environment, so avoid running more than one task concurrently
    ( see http://bugs.python.org/issue2320 )
    """
    if 'close_fds' in kw and sys.platform == 'win32':
        del kw['close_fds']
    with _popen_lock:
        return subprocess.Popen(*a, **kw)

def getFormKey():
    """Return a per-session nonce value for use with CSRF prevention"""
    # When running under splunkd's control, let it pick the CSRF token
    if cherrypy.request.headers.get('X-Splunkd'):
        return parse_xsplunkd_header().get('csrf_token')
    return None

def isValidFormKey(key):
    """Check that the supplied key matches that stored in the session"""
    try:
        session = cherrypy.session
    except AttributeError:
        return False
    match = False
    try:
        key = str(key)
        match = getFormKey() == key
    except (ValueError, TypeError):
        pass

    if not match:
        logger.warn('CSRF form_key mismatch received=%s expected=%s' % (key, getFormKey()))

    return match

def doesFormKeyMatchCookie(key):
    cookie_name = cherrypy.config.get('tools.csrfcookie.name')
    cookie_val = cherrypy.request.cookie.get(cookie_name)

    if not cookie_val:
        logger.warn('CSRF form_key mismatch; cookie not present in request')
        return False
    elif cookie_val.value != key:
        logger.warn('CSRF form_key mismatch with cookie received=%s cookie=%s' % (key, cookie_val))
        return False

    return True

def checkRequestForValidFormKey(requireValidFormKey=True):
    """
    check the current request for the need for, and if needed, the existence of a valid form key
    if the request is good (no form key needed, or form key is good) return True
    if the request is bad (form key needed and invalid) raise an error if the request is an XHR, or return False
    Disable in tests by setting cherrypy.config.update({'environment': 'test_suite'})
    """
    if cherrypy.request.method in ['POST', 'PUT', 'DELETE'] and not cherrypy.config.get('environment') == 'test_suite':
        request_is_xhr = is_xhr()
        form_key = cherrypy.request.headers.get('X-Splunk-Form-Key') if request_is_xhr else cherrypy.request.params.get('splunk_form_key')

        # verify that the incoming form key matches server's version
        if not isValidFormKey(form_key) or not doesFormKeyMatchCookie(form_key):
            if request_is_xhr:
                logger.warn('CSRF: validation failed because client XHR did not include proper header')
            else:
                logger.warn('CSRF: validation failed because HTTP POST did not include expected parameter')

            if requireValidFormKey:
                if request_is_xhr:
                    raise cherrypy.HTTPError(401, _('Splunk cannot authenticate the request. CSRF validation failed.'))
                else:
                    return False
            else:
                logger.warn('CSRF: skipping 401 redirect response because endpoint did not request protection')

    return True

def generateBaseLink():
    """
    Construct a link suitable for giving to the PDF server
    Utilize the configured link hostname if available, else use the
    url from this instance of splunkweb
    """
    settings = en.getEntity('/configs/conf-alert_actions', 'email', namespace='system')
    linkhost = settings.get('hostname')
    if linkhost:
        linkhost = linkhost.strip()
    if not linkhost:
        result = cherrypy.request.base
    elif linkhost.startswith('http://') or linkhost.startswith('https://'):
        result = linkhost
    else:
        port = cherrypy.request.local.port
        hasport = False
        if '[' in linkhost:
            addrend = linkhost.find(']')
            if addrend < 2:
                raise ValueError('Incorrect IPv6 address specified for link hostname')
            hasport =  len(linkhost) > (addrend + 3) and linkhost[addrend+1] == ':'
        elif ':' in linkhost:
            addrend = linkhost.find(':')
            hasport = len(linkhost) > (addrend + 3)
        result = cherrypy.request.scheme + '://' + linkhost
        if not hasport and port not in (80, 443):
            result += ':%s' % port
    return result

auto_refresh_views = None

def auto_refresh_ui_assets(assetPath):
    global auto_refresh_views

    if auto_refresh_views is None:
        settings = splunk.clilib.cli_common.getConfStanza('web', 'settings')
        auto_refresh_views = splunk.util.normalizeBoolean(settings.get('auto_refresh_views'))

    if auto_refresh_views:
        en.getEntity(assetPath, '_reload')


class LRUDict(collections.OrderedDict):
    """A capacity limited OrderedDict

    On reaching capacity, least recently used items are discarded.
    """
    def __init__(self, *args, **kwargs):
        self.capacity = kwargs.pop("capacity", None)
        collections.OrderedDict.__init__(self, *args, **kwargs)
        self._enforce_capacity()

    def __setitem__(self, key, value):
        collections.OrderedDict.__setitem__(self, key, value)
        self._enforce_capacity()

    def _enforce_capacity(self):
        if self.capacity is not None:
            while len(self) > self.capacity:
                self.popitem(last=False)

def embed_modify_request():
    """
    Modifies the request object for a embed enabled handler.
    This adds a boolean attribute embed to the request object and updates
    the root_endpoint value in the thread safe copied cherrypy.request.config dict
    with embed_uri if defined. Used by make_url and friends:)
    """
    cherrypy.request.embed = True
    if cherrypy.request.config.get('embed_uri'):
        cherrypy.request.config['root_endpoint'] = cherrypy.request.config.get('embed_uri')

def path_split(path):
    """
    Takes file path, trims leading/trailing slashes and returns a list of the parts based
    on the os specific separator.
    """
    return path.lstrip(os.sep).rstrip(os.sep).split(os.sep)

def is_valid_template_path(root, template_path, optional_paths=None):
    """
    Validates if a template path is within an allowable range of locations.

    Valid Paths:
    ${SPLUNK_HOME}/etc/apps/${APP}/appserver/modules/**
    ${SPLUNK_HOME}/etc/apps/${APP}/appserver/templates/**
    ${SPLUNK_HOME}/share/splunk/search_mrsparkle/modules/**
    ${SPLUNK_HOME}/share/splunk/search_mrsparkle/templates/**
    """
    if not template_path.startswith(root):
        return False
    relative_path = template_path[len(root)+1:]
    if optional_paths:
        relative_path_parts = path_split(relative_path)
        for optional_path in optional_paths:
            optional_path_parts = path_split(optional_path[len(root)+1:])
            if len(relative_path_parts) > len(optional_path_parts) and cmp(optional_path_parts, relative_path_parts[0:len(optional_path_parts)]) == 0:
                return True
    if relative_path.startswith(os.path.join("etc", "apps")):
        sub_app_path = path_split(relative_path)
        if len(sub_app_path) < 6:
            return False
        sub_app_path = sub_app_path[3:]
        if sub_app_path[0] != "appserver":
            return False
        if sub_app_path[1] not in ("modules", "templates"):
            return False
    elif not relative_path.startswith(os.path.join("share", "splunk", "search_mrsparkle")):
        return False
    elif len(path_split(relative_path))<5 or path_split(relative_path)[3] not in ("templates", "modules"):
        return False
    return True

def static_asset_version():
    """Return staticAssetId with _push_version"""
    version = push_version()
    suffix = '.%s' % version if version else ''
    return '@%s%s' % (cherrypy.config['staticAssetId'], suffix)

def add_url_params(url, params):
    """
    Return a URL after adding params to it. Order of params will not be retained
    """
    from future.moves.urllib import parse as urllib_parse
    url_parts = list(urllib_parse.urlparse(url))
    query = dict(urllib_parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib_parse.urlencode(query)
    return urllib_parse.urlunparse(url_parts)

if __name__ == '__main__':

    import unittest

    class MainTest(unittest.TestCase):

        def setUp(self):
            cherrypy.config['staticAssetId'] = random.randint(0, 100000)
            cherrypy.request.lang = "en-US"
            cherrypy.request.config = {'root_endpoint': '/'}

        def test_path_split(self):
            path = os.sep + "foo" + os.sep + "bar" + os.sep + "baz" + os.sep
            split = path_split(path)
            self.assertEquals(len(split), 3)
            self.assertEquals(split[0], "foo")
            self.assertEquals(split[1], "bar")
            self.assertEquals(split[2], "baz")

        def test_is_valid_template_path(self):
            splunk_home = os.environ["SPLUNK_HOME"]
            optional_paths = [os.path.join(splunk_home, "bar", "foo")]

            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "nottemplates"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "templates"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "templates", "foo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "templates", "bar", "foo.html"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "notmodules"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "modules"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "modules", "foo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "etc", "apps", "foo", "appserver", "modules", "bar", "foo.html"), optional_paths=optional_paths))

            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk"), optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "nottemplates"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "templates"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "templates", "foo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "templates", "bar", "foo.html"), optional_paths=optional_paths))

            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "notmodules"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "modules"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "modules", "foo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "share", "splunk", "search_mrsparkle", "modules", "bar", "foo.html"), optional_paths=optional_paths))

            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "bar"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "bar", "foo"), optional_paths=optional_paths))
            self.assertFalse(is_valid_template_path(splunk_home, os.path.join(splunk_home, "bar", "boo", "barfoo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "bar", "foo", "barfoo.html"), optional_paths=optional_paths))
            self.assertTrue(is_valid_template_path(splunk_home, os.path.join(splunk_home, "bar", "foo", "barfoo", "barfoo.html"), optional_paths=optional_paths))

        def test_convert_to_bytes(self):

            self.assertEquals(convert_to_bytes('0'), 0)
            self.assertEquals(convert_to_bytes('0B'), 0)
            self.assertEquals(convert_to_bytes('10MB'), 10485760)
            self.assertEquals(convert_to_bytes('40 GB'), 42949672960)
            self.assertEquals(convert_to_bytes('-100KB'), -102400)
            self.assertEquals(convert_to_bytes('-100'), -100)
            self.assertEquals(convert_to_bytes('123456789012345678901234567890'), 123456789012345678901234567890)
            self.assertRaises(ValueError, convert_to_bytes, None)
            self.assertRaises(ValueError, convert_to_bytes, '')
            self.assertRaises(ValueError, convert_to_bytes, 'nonsense')
            self.assertRaises(ValueError, convert_to_bytes, 'GB')
            self.assertRaises(ValueError, convert_to_bytes, 0)
            self.assertRaises(ValueError, convert_to_bytes, 23)

        def XXtestGetPercentiles(self):

            self.assertEquals(getPercentiles([], .05, .95), (None, None))
            self.assertEquals(getPercentiles([0, 1], .05, .95), (.05, .95))
            self.assertEquals(getPercentiles(list(range(11)), .05, .95), (1.5, 9.5))
            self.assertEquals(getPercentiles(list(range(101)), .05, .95), (15, 95))

        def test_isEpochTime(self):
            self.assertEquals(isEpochTimeArg("123123421.159"), True)
            self.assertEquals(isEpochTimeArg("123123421.000"), True)
            self.assertEquals(isEpochTimeArg("123123421.040"), True)
            self.assertEquals(isEpochTimeArg("fred"), False)
            self.assertEquals(isEpochTimeArg("-1d@d"), False)

        def test_basic_replacement(self):
            string = "One $one$ two, $two$."
            expect = "One foo two, bar."
            found = replace_vars(string, {'one': 'foo', 'two': 'bar'})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_escaping_replacement(self):
            string = "One $one$ two, \\\\\\$two\\$ $three$\\"
            expect = "One foo two, \\$two$ bar"
            found = replace_vars(string, {'one': 'foo', 'three': 'bar'})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_escape_variable_in_replacement(self):
            string = "one $two\\$$"
            expect = "one bar"
            found = replace_vars(string, {'two$': 'bar'})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_unclosed_variable(self):
            string = "one $two three four \\$ five"
            expect = "one $two three four $ five"
            found = replace_vars(string, {})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_spaces_in_variables(self):
            string = "one $two three$ four"
            expect = "one bar four"
            found = replace_vars(string, {'two three': 'bar'})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_retain_escapes(self):
            string = "one $two\\$three$ $four$"
            expect = "one $two\\$three$ bar"
            found = replace_vars(string, {'four': 'bar'}, retain_escape=True)
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

            string = r"one \$@two\$ three"
            expect = r"one \$@two\$ three"
            found = replace_vars(string, {'two': 'two'}, retain_escape=True, open_delimiter="$@")
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_change_delimiters(self):
            string = "one $@field_value$ two"
            expect = "one bar two"
            found = replace_vars(string, {'field_value': 'bar'}, open_delimiter="$@")
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_make_url(self):
            string = "/i18ncatalog?autoload=1"
            found = make_url(string)
            self.assertTrue("version=" in found)

        def test_make_url_js_i18n(self):
            string = "/static/js/i18n.js"
            expect = "/en-US/static/" + static_asset_version() + "/js/i18n.js"
            found = make_url(string)
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_make_url_common(self):
            string = "/static/build/pages/enterprise/common.js"
            expect = "/en-US/static/" + static_asset_version() + "/build/pages/enterprise/common.js"
            found = make_url(string)
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_add_url_param(self):
            string = "i18ncatalog"
            expect = "i18ncatalog?version=1"
            found = add_url_params(string, {'version': '1'})
            self.assertEquals(found, expect, "Did not find '%s', found '%s'." % (expect, found))

        def test_add_second_url_param(self):
            string = "i18ncatalog?autoload=1"
            expect1 = "i18ncatalog?version=1&autoload=1"
            expect2 = "i18ncatalog?autoload=1&version=1"
            found = add_url_params(string, {'version': '1'})
            self.assertTrue(found == expect1 or found == expect2)

    # run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(MainTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


##
# these are all i18n code that is required to be here
def current_lang(as_string=False): # moved from util
    """
    Return the user's current language/locale
    If as_string==True then returns a string fr, fr_FR, fr_FR.ISO8859-1 etc
    else returns a tuple (lang, locale, encoding)
    """
    if as_string:
        return cherrypy.request.lang
    return parse_localestr(cherrypy.request.lang)


def parse_localestr(locale): # moved from util
    """
    Parse a locale string such as en, fr_FR, fr_FR.ISO8859-1 into language, locale and encoding
    """
    langenc = locale.replace('-', '_').split('.')
    langloc = langenc[0].split('_')
    return (
        langloc[0],
        langloc[1] if len(langloc)>1 else None,
        langenc[1] if len(langenc)>1 else None
        )

def current_lang_url_component():  # moved from util
    """
    Returns the string used to represent the current lang/locale in the url
    eg. en-US, fr, fr-FR
    """
    locale = current_lang()
    return "%s-%s" % (locale[0], locale[1]) if locale[1] else locale[0]

def make_i18n_url(path, translate=True):  # move to util
    """
    Translate a request path into an i18n path by prefixing the user's
    current locale onto the url: /en-US/account/login
    If translate==True true then also prefixes the configured root_endpoint to the path

    You probably don't want to call this anyway, you probably want make_url() or make_route()
    """
    path = path.strip('/')
    locale = current_lang()
    # return "fr-FR" if the locale component is available, else just return "fr"
    locale = "%s-%s" % (locale[0], locale[1]) if locale[1] else locale[0]
    root_endpoint = cherrypy.request.config.get('root_endpoint')
    localed_path = "/%s/%s" % (locale, path)

    if translate and root_endpoint not in ('/', '', None):
        return '%s/%s/%s' % (root_endpoint, locale, path)
    return localed_path

def strip_i18n_url(path):  # moved from util
    """
    Return a URL path stripped of the root_endpoint prefix and the en-US segment
    """
    return '/' + path[len(cherrypy.request.script_name)+7:]
