import io

from builtins import filter

import cherrypy
import xml.sax.saxutils as su
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.appserver.mrsparkle.lib.util import make_url
from splunk.appserver.mrsparkle.lib.util import checkRequestForValidFormKey
import logging
import splunk.rest
import splunk.rest.format
import json
import re
from future.moves.urllib import parse as urllib_parse
import requests

logger = logging.getLogger('splunk.appserver.controllers.proxy')
#logger.setLevel(logging.DEBUG)

PDFGEN_RENDER_TIMEOUT_IN_SECONDS = 3600 # same as cherrypy.tools.sessions.timeout
                                        # since this module is loaded before settings are
                                        # fully loaded, we can't use web.conf value here

def _get_wrapped_buffered_random(buffered_random):
    """ Thin wrapper around standard library's BufferedRandom which
    keeps its interface, except it ensures the 'name' property is of type
    str. This is to address the fact that under Python2 tempfile.TemporaryFile()
    returns a file object whose 'name' attribute is string whereas in
    Python3 the same call returns an instance of BufferedRandom whose 'name'
    attribute is an integer, which troubles libraries (e.g., requests) down in the
    call chain.
    """
    class _BufferedRandomWrapper(object):
        def __init__(self, buffer):
            self._buffer = buffer

        def __getattr__(self, attr):
            if attr == 'name':
                return str(self._buffer.name)
            else:
                return getattr(self._buffer, attr)

    if isinstance(buffered_random, io.BufferedRandom):
        return _BufferedRandomWrapper(buffered_random)
    return buffered_random


def precompile_whitelist():
    import splunk.clilib.cli_common as comm
    import splunk.util as splutil
    webconf = comm.getConfStanzas('web')
    whitelist = []
    for stanzaname in webconf:
        if not stanzaname.startswith('expose:'):
            continue
        stanza = webconf[stanzaname]
        if splutil.normalizeBoolean(stanza.get('disabled', '0')):
            continue
        try:
            pattern = stanza['pattern']
        except KeyError:
            logger.warn('web.conf stanza [%s] had no pattern setting, ignoring' % stanzaname)
            continue
        parts = pattern.split('/')
        newparts = []
        for e in parts:
           if e == '**':
              newparts.append('.*')
           elif e.endswith('*'):
              newparts.append(re.escape(e[:-1]) + '[^/]*')
           else:
              newparts.append(re.escape(e))
        newelem = {}
        newelem['endpoint'] = re.compile('(^|^services/|^servicesNS/[^/]+/[^/]+/)' + ('/'.join(newparts)) + '$')
        newelem['methods'] = list(filter(len, [x.strip() for x in stanza.get('methods', 'GET').upper().split(',')]))
        for opt in [ 'oidEnabled', 'skipCSRFProtection' ]:
            if splutil.normalizeBoolean(stanza.get(opt, '0')):
                newelem[opt] = True
        whitelist.append(newelem)
    return whitelist


_PROXY_WHITE_LIST = precompile_whitelist()

from datetime import datetime

class ProxyController(BaseController):
    """/splunkd"""

    @route('/*_proxy_path')
    @expose_page(must_login=False, verify_session=False, methods=['GET', 'POST', 'PUT', 'DELETE'])
    def index(self, oid=None, **args):

        if cherrypy.request.method in ['POST', 'DELETE'] and not cherrypy.config.get('enable_proxy_write'):
            return self.generateError(405, _('Write access to the proxy endpoint is disabled.'))

        # We have to handle the fact that CherryPy is going to %-decode
        # the URL, including any "/" (%2F). As such, we use the relative_uri
        # (which doesn't %-decode %2F), and simply re-encode that URL
        logger.debug('[Splunkweb Proxy Traffic] %s request to: %s' % (cherrypy.request.method, cherrypy.request.relative_uri))
        relative_uri = cherrypy.request.relative_uri

        if cherrypy.config.get('root_endpoint') and cherrypy.config.get('root_endpoint').startswith('/splunkd'):
            total_matches = [m.start() for m in re.finditer('/splunkd', relative_uri)]
            relative_uri = relative_uri[total_matches[1]+9:]
        else:
            relative_uri = relative_uri[relative_uri.find("/splunkd")+9:]

        query_start = relative_uri.rfind("?")
        if (query_start > -1) and (cherrypy.request.query_string):
            relative_uri = relative_uri[:query_start]

        uri = urllib_parse.quote(relative_uri)

        if uri.startswith('__raw/'):
            # Don't parse any response even if it's a 404 etc
            rawResult = True
            uri = uri[6:]
        elif uri.startswith('__upload/'):
            rawResult = True
            uri = uri[9:]
        else:
            rawResult = False

        endpointProps = self.getAllowedEndpointProps(uri, cherrypy.request.method)
        if endpointProps is None:
            # endpoint not allowed
            logger.info("Resource not found: %s" % uri)
            raise cherrypy.HTTPError(404, _('Resource not found: %s' % uri))

        # sessionKey extraction:
        # Use oid request param.
        if oid:
            if not endpointProps.get('oidEnabled', False):
                raise cherrypy.HTTPError(401, _('Splunk cannot authenticate the request. oid unsupported for this resource.'))
            sessionKey = oid
            logger.info('Using request param oid as app server sessionKey and removing from request.params')
            del cherrypy.request.params['oid']
        # Use cherrypy session object.
        else:
            sessionKey = cherrypy.session.get('sessionKey')
            cherrypy.session.release_lock()

        if not sessionKey:
            logger.info('proxy accessed without stored session key')

        # CSRF Protection
        requireValidFormKey = not endpointProps.get('skipCSRFProtection', False)
        if not checkRequestForValidFormKey(requireValidFormKey):
            # checkRequestForValidFormKey() will raise an error if the request was an xhr, but we have to handle if not-xhr
            raise cherrypy.HTTPError(401, _('Splunk cannot authenticate the request. CSRF validation failed.'))

        # Force URI to be relative so an attacker can't hit any arbitrary URL
        uri = '/' + uri

        if cherrypy.request.query_string:
            queryArgs = cherrypy.request.query_string.split("&")
            # need to remove the browser cache-busting _=XYZ that is inserted by cache:false (SPL-71743)
            modQueryArgs = [queryArg for queryArg in queryArgs if not queryArg.startswith("_=") and not queryArg.startswith("oid=")]
            uri += '?' + '&'.join(modQueryArgs)

        fs = args.get('spl-file')
        isFileUpload = isinstance(fs, cherrypy._cpreqbody.Part) and fs.file

        postargs = None
        body = None
        if cherrypy.request.method in ('POST', 'PUT') and not isFileUpload:
            content_type = cherrypy.request.headers.get('Content-Type', '')
            if not content_type or content_type.find('application/x-www-form-urlencoded') > -1:
                # We use the body_params to avoid mixing up GET/POST arguments,
                # which is the norm with output_mode=json in Ace.
                logger.debug('[Splunkweb Proxy Traffic] request body: %s' % cherrypy.request.body_params)
                postargs = cherrypy.request.body_params
            else:
                # special handing for application/json POST
                # cherrypy gives file descriptor for POST's
                body = cherrypy.request.body.read()
                logger.debug('[Splunkweb Proxy Traffic] request body: %s' % body)

        proxyMode = False
        if 'authtoken' in args:
            proxyMode = True

        simpleRequestTimeout = splunk.rest.SPLUNKD_CONNECTION_TIMEOUT
        if 'timeout' in endpointProps:
                simpleRequestTimeout = endpointProps['timeout']

        try:
            if isFileUpload:
                #if this is an upload, shortcircut here to uploadFile() which will handle request from here
                return self.uploadFile(args, sessionKey, uri)

            serverResponse, serverContent = splunk.rest.simpleRequest(
                make_url(uri, translate=False, relative=True, encode=False),
                sessionKey,
                postargs=postargs,
                method=cherrypy.request.method,
                raiseAllErrors=True,
                proxyMode=proxyMode,
                rawResult=rawResult,
                jsonargs=body,
                timeout=simpleRequestTimeout
            )

            for header in serverResponse:
                cherrypy.response.headers[header] = serverResponse[header]

            # respect presence of content-type header
            if(serverResponse.get('content-type') == None):
                del cherrypy.response.headers['Content-Type']

            logger.debug('[Splunkweb Proxy Traffic] response status code: %s' % serverResponse.status)

            if serverResponse.messages:
                return self.generateError(serverResponse.status, serverResponse.messages)

            if rawResult:
                cherrypy.response.status = serverResponse.status

            logger.debug('[Splunkweb Proxy Traffic] response body: %s' % serverContent)
            return serverContent

        except splunk.RESTException as e:
            logger.exception(e)
            return self.generateError(e.statusCode, e.extendedMessages)

        except Exception as e:
            logger.exception(e)
            return self.generateError(500, su.escape(str(e)))


    def getAllowedEndpointProps(self, uri, method):
        '''verify that that a given uri and associated method is white listed to be proxied to the endpoint.'''

        logger.debug("searching for uri: %s" % uri)
        for props in _PROXY_WHITE_LIST:
            if props['endpoint'].match(uri):
                if method in props['methods']:
                    return props
        else:
            return None

    def generateError(self, status, messages=None):
        def generateErrorJson():
            cherrypy.response.headers['Content-Type'] = "application/json"
            output = {}
            output["status"] = su.escape(str(status))
            if messages:
                if isinstance(messages, list):
                    escaped_messages = [{"type":su.escape(msg['type']),"text":su.escape(msg['text'])} for msg in messages]
                    output["messages"] = escaped_messages
                else:
                    msg = {"type":"ERROR","text":su.escape(messages)}
                    output["messages"] = [msg]
            return json.dumps(output)
        def generateErrorXml():
            output = [splunk.rest.format.XML_MANIFEST, '<response>']
            output.append('<meta http-equiv="status" content="%s" />' % su.escape(str(status)))
            if messages:
                output.append('<messages>')

                if isinstance(messages, list):
                    for msg in messages:
                        output.append('<msg type="%s">%s</msg>' % (su.escape(msg['type']), su.escape(msg['text'])))
                else:
                    output.append('<msg type="ERROR">%s</msg>' % str(messages))
                output.append('</messages>')

            output.append('</response>')
            return '\n'.join(output)


        logger.debug('[Splunkweb Proxy Traffic] response errors: %s' % str(messages))
        output_mode = cherrypy.request.params.get("output_mode")
        # make sure that error status is relayed back to client via status code, and not just content
        cherrypy.response.status = status
        if output_mode and output_mode == "json":
            return generateErrorJson()
        return generateErrorXml()

    def uploadFile(self, args, sessionKey, uri):
        fs = args.get('spl-file')
        filename = fs.filename
        if not (isinstance(fs, cherrypy._cpreqbody.Part) and fs.file):
            self.generateError('500', 'expected file named spl-file')

        uri = splunk.rest.makeSplunkdUri() + 'services' + uri
        resp = requests.post(
                uri,
                files={filename: _get_wrapped_buffered_random(fs.file)},
                headers={'Authorization': 'Splunk ' + sessionKey},
                verify=False #allow self signed certificates
            )

        for header in resp.headers:
            cherrypy.response.headers[header] = resp.headers[header]

        #TODO error handling/logging

        #TODO maybe should let callee set this, and just return tuple
        cherrypy.response.status = resp.status_code

        return resp.content
