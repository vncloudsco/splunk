"""
An override of cherrypy.tools.staticdir that allows for a callback resolver to be triggered
prior to serving a static file.  The resolver can return a local pathname to serve instead of
allowing staticdir to default to serving files out of its configured directory.

Ideally this would be implemented as a completely separate tool (ie. not clobber cherrypy.tools.staticdir)
but unfortunately cherrypy's default dispatcher makes assumptions about how static files are served
at the moment; hopefully it'll be fixed in the future.
"""
from __future__ import absolute_import

import cherrypy
import datetime
import logging
import os.path
import sys
import re
from future.moves.urllib import parse as urllib_parse

import splunk.util
import splunk.appserver.mrsparkle.lib.util as util
import splunk.appserver.mrsparkle.lib.i18n as i18n
from email.utils import parsedate


logger = logging.getLogger('splunk.appserver.lib.staticdir')

# when serving CSS files, only this many bytes will be read
CSS_FILE_SIZE_LIMIT = 1000000

def custom_staticdir(section, dir, root="", match="", content_types=None, index="", generate_indexes=False, resolver=None, strip_version=False, default_ext=None):
    """
    Backwards compatible, i18n enabled, staticdir tool replacement.
    If a callable called resolver is supplied then it is called prior to the original staticdir tool being fired.
    If the resolver returns a pathname, then we attempt to static serve that file.
    If the resolver returns False, or serve_file raises a NotFound exception, then we fallback
    to the original staticdir behaviour.
    """
    # first path segment should be locale
    if section == 'global':
        section = "/"

    branch_offset = cherrypy.request.path_info.find(section)
    branch = cherrypy.request.path_info[branch_offset + len(section):]
    branch = urllib_parse.unquote(branch.lstrip(r"\/"))

    if strip_version and len(branch) and branch[0]=='@':
        version = branch.split('/', 1)[0]
        branch = branch[len(version):].lstrip('/')
        util.use_future_expires()

    if resolver:
        # call the user's resolver callback
        filename = resolver(section, branch, dir)
        if filename:
            # try to find localized versions of the requested file
            fnlist = i18n.path_to_i18n_paths(filename)
            for fn in fnlist:
                if cherrypy.lib.static._attempt(fn, content_types):
                    return True

    # duplicate the original staticdir functionality but add i18n filename matching
    if match and not re.search(match, cherrypy.request.path_info):
        return False

    # Allow the use of '~' to refer to a user's home directory.
    dir = os.path.expanduser(dir)

    # If dir is relative, make absolute using "root".
    if not os.path.isabs(dir):
        if not root:
            msg = _("Static dir requires an absolute dir (or root).")
            raise ValueError(msg)
        dir = os.path.join(root, dir)

    # If branch is "", filename will end in a slash
    filename = os.path.join(dir, branch)

    # There's a chance that the branch pulled from the URL might
    # have ".." or similar uplevel attacks in it. Check that the final
    # filename is a child of dir.
    if not os.path.normpath(filename).startswith(os.path.normpath(dir)):
        raise cherrypy.HTTPError(403, "%s does not start with %s" % (filename, dir)) # Forbidden

    # get filenames based on user's current locale
    fnlist = []
    filenames = [filename]
    if default_ext:
        filenames.append("%s.%s" % (filename, default_ext))
    for try_filename in filenames:
        fnlist += i18n.path_to_i18n_paths(try_filename) # get filenames

    # see if we can serve any of the local language filenames
    handled = False
    for fn in fnlist:
        if fn.endswith('.css') or fn.endswith('.less'):
            if os.path.exists(fn):
                serve_static_css(fn)
                return True
        else:
            handled = cherrypy.lib.static._attempt(fn, content_types)
            if handled:
                return handled

    # didn't find a file if we reach here; perhaps it's a directory
    if not handled:
        # Check for an index file if a folder was requested.
        if index:
            handled = cherrypy.lib.static._attempt(os.path.join(filename, index), content_types)
            if handled:
                cherrypy.request.is_index = filename[-1] in (r"\/")
        if not handled and generate_indexes:
            if callable(generate_indexes):
                handled = generate_indexes(filename, branch)
            else:
                handled = cherrypy.lib.static.render_index(filename, branch)
    return handled


def serve_static_css(fn):
    """
    Translate urls defined in static css files into local urls
    taking locale and root prefix into account

    This is called above, broken out because CSS uses a simpler in-memory
    cache that's computationally cheaper, whereas JS uses an expensive i18n
    cache that we store on disk so it will persist between splunkweb restarts

    For SPL-70474, this method has been overloaded to handle LESS files in addition to CSS,
    since the same cache-ing rules apply.
    """
    # make sure we keep cached copies for each locale/version tuple
    lang = i18n.current_lang_url_component()
    cache = serve_static_css.cache.setdefault(lang, {})
    is_less_file = fn.endswith('.less')
    # embed can possibly have it's own base uri - handle munger
    is_embed = splunk.util.normalizeBoolean(cherrypy.request.params.get('embed'))
    if is_embed:
        util.embed_modify_request()

    #define our function for replacing CSS urls
    def url_replace(match):
        container = match.group(1)
        url = match.group(2)
        if url and not url.startswith("data:"):
            try:
                url = util.make_url(url)
            except AttributeError as e:
                logger.error("AttributeError -- Could not run make_url on url: %s" % url)
        return container + url

    def static_prefix_replace(match):
        # to get the correct cache buster, call make_url with a dummy static asset
        # then strip out the file name and trailing slash to get the "static with buster" path
        staticWithBuster = util.make_url('/static/foo.js')[0:-7]
        return match.group(1).replace('/static', staticWithBuster)

    # ensure file hasn't been modified since we cached it
    # handle embed scenario - read correct cache base on embed_uri
    if is_embed and cherrypy.request.config.get('embed_uri'):
        cache_key = cherrypy.request.config.get('embed_uri') + fn
    else:
        cache_key = fn
    if cache_key in cache and cache[cache_key][0]==os.path.getmtime(fn):
        css = cache[cache_key][1]
    else:
        with open(fn, 'rb') as f:
            read_f_raw = f.read(CSS_FILE_SIZE_LIMIT)
            try:
                read_f = read_f_raw.decode('utf-8')
            except UnicodeDecodeError:
                logger.warn("%s is not encoded in ASCII or UTF-8. Please use one of these encodings." % fn)
                import chardet
                detected_encoding = chardet.detect(read_f_raw)
                read_f = read_f_raw.decode(detected_encoding['encoding'])
            if is_less_file:
                # for .less files, search for any url() or string literal that starts with '/static'
                # (since it could be in a variable assignment)
                # and replace that '/static' portion with the root-endpoint aware path to /static
                css = re.sub(r'((?:url\(|["\']{1})/static)', static_prefix_replace, read_f)
            else:
                css = re.sub(r'([\s:,]+url\([\'"]?)([^\)\'"]+)', url_replace, read_f)
            cache[cache_key] = (os.path.getmtime(fn), css)

            # if there is anything left in the file, that means it was longer than our limit, so log an error
            if f.read(1):
                logger.error('File Size Error -- %s is longer than the CSS size limit, only the first %s bytes were served' %
                                (fn, CSS_FILE_SIZE_LIMIT))

    if is_less_file:
        cherrypy.response.headers['Content-Type'] = 'text/plain'
    else:
        cherrypy.response.headers['Content-Type'] = 'text/css'
    cherrypy.response.headers['Last-Modified'] = datetime.datetime.utcfromtimestamp(cache[cache_key][0]).strftime('%a, %d %b %Y %H:%M:%S GMT')
    serve_static_content(css)

def serve_static_content(content):
    """
    This is for serving arbritary content from sources like in-memory caches
    where we don't want to write the content to disk

    Headers like Content-Type and Last-Modified must have already been set as needed, e.g.
    cherrypy.response.headers['Content-Type'] = 'text/css'
    so we can properly compare Last-Modified with If-Modified-Since in the request
    If Last-Modified is not set, we will fall back to 200 and return the content
    """

    if sys.version_info >= (3, 0) and isinstance(content, str): content = content.encode('utf-8')

    if cherrypy.request.headers.get('Pragma') == 'no-cache' or cherrypy.request.headers.get('Cache-Control') == 'no-cache':
        # Hard reload (Command-Shift-R)
        # HTTP response code will be set to 200 upstream
        cherrypy.response.body = content
    elif not cherrypy.request.headers.get('If-Modified-Since'):
        # first request
        # HTTP response code will be set to 200 upstream
        cherrypy.response.body = content
    elif not cherrypy.response.headers.get('Last-Modified'):
        # no way to see whether content is outdated - 200 to be safe
        # HTTP response code will be set to 200 upstream
        cherrypy.response.body = content
    elif parsedate(cherrypy.response.headers.get('Last-Modified')) > parsedate(cherrypy.request.headers.get('If-Modified-Since')):
        # content passed in is newer than what the browser has
        # HTTP response code will be set to 200 upstream
        cherrypy.response.body = content
    else:
        cherrypy.response.status = 304
        # unset unnecessary headers
        if cherrypy.response.headers.get('Last-Modified'):
            del cherrypy.response.headers['Last-Modified']
        if cherrypy.response.headers.get('Content-Type'):
            del cherrypy.response.headers['Content-Type']
        if cherrypy.response.headers.get('Expires'):
            del cherrypy.response.headers['Expires']

serve_static_css.cache = {}

# clobber Cherrypy's default staticdir handler :-/
# this thread might help explain why: http://osdir.com/ml/python.cherrypy/2006-10/msg00021.html
cherrypy.tools.staticdir = cherrypy._cptools.HandlerTool(custom_staticdir, name='staticdir')
