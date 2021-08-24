from __future__ import absolute_import
# Main dispatch point for splunkd REST <-> Python endpoint integration
#
#

from builtins import range
from builtins import object
from builtins import map

import os, sys, time
import logging
import lxml.etree as et
import json
import xml.sax.saxutils as su
try:
    import httplib
except ImportError:
    import http.client as httplib
import splunk
import splunk.util as util
import __main__
import socket
import base64
from future.moves.urllib import parse as urllib_parse
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.rest import format

logger = logging.getLogger('splunk.rest')

SPLUNK_NS   = 'http://dev.splunk.com/ns/rest'
SPLUNK_TAGF = '{%s}%%s' % SPLUNK_NS

AUTH_HEADER_PREFIX_SPLUNK = 'Splunk '
AUTH_HEADER_PREFIX_BEARER = 'Bearer '
AUTH_HEADER = 'Authorization'

# set root path name
REST_ROOT_PATH = '/services'

# number of seconds to wait for splunkd HTTP connection to complete before
# raising a socket.timeout exception

# while this is no longer a constant, we don't know if any externally developed modules were referring
# directly to the constant, so leave the variable in constant ALL-CAPS style
SPLUNKD_CONNECTION_TIMEOUT = 30

# SPL-38789 - get Splunk Web's caCertPath and privKeyPath in order to
# provide these values to simpleRequest() and streamingRequest()
# NB: if requireClientCert = true in server.conf, both Splunk Web
# and splunkd must be using certificates provided by the same Root CA.
# Otherwise, Splunk Web will not be able to communicate with splunkd.
#
# NOTE: ensure certificates ONLY when needed as this operation is pretty
#       expensive to perform at module import time
WEB_KEYFILE = None
WEB_CERTFILE = None
CHECKED_CERTS = False

def checkCerts():
    global CHECKED_CERTS, WEB_CERTFILE, WEB_KEYFILE
    if not CHECKED_CERTS:
       (WEB_KEYFILE, WEB_CERTFILE) = util.ensureCerts()
       CHECKED_CERTS = True

def getWebKeyFile():
    checkCerts()
    global WEB_KEYFILE
    return WEB_KEYFILE

def getWebCertFile():
    checkCerts()
    global WEB_CERTFILE
    return WEB_CERTFILE


#  Define main Python interface for HTTP server
#
#  This dispatcher is invoked when a REST endpoint has been defined and calls
#  a script to handle its processing
# /////////////////////////////////////////////////////////////////////////////

def dispatch(handlerClassName, requestInfo, sessionKey):
    """
    Factory for producing a request handler.  Returns the appropriate REST
    handler, or exception if not found.
    """

    # parse the incoming requestInfo XML string
    try:
        requestXml = et.fromstring(requestInfo)

    except Exception as e:
        logger.error('Python REST dispatcher received invalid XML from HTTP server')
        logger.debug('XML DUMP >>>\n%s' % requestInfo)
        logger.exception(e)
        raise

    requestDict = {}
    try:
        httpVerb = requestXml.findtext('method').upper()

        explicitOutMode = su.unescape(requestXml.findtext('output_mode/explicit_request')).lower()
        requestDict.update({
            'userName': su.unescape(requestXml.findtext('user/name')),
            'userId': su.unescape(requestXml.findtext('user/id')),
            'remoteAddr': su.unescape(requestXml.findtext('connectionData/ip')),
            'output_mode': su.unescape(requestXml.findtext('output_mode/mode')),
            'explicit_output_mode': explicitOutMode == "true" and True or False,
            'path': REST_ROOT_PATH + '/' + su.unescape(requestXml.findtext('path')).strip('/'),
            'headers': {},
            'query': {},
            'form': {},
            'systemAuth': requestXml.findtext('systemAuth'),
            'payload': su.unescape(requestXml.findtext('payload')),
            'restmap': {}
        })
        for node in requestXml.findall('headers/header'):
            requestDict['headers'][node.get('key', '').lower()] = su.unescape(node.text or "")
        for node in requestXml.findall('query/arg'):
            requestDict['query'][node.get('key')] = su.unescape(node.text or "")
        for node in requestXml.findall('form/arg'):
            requestDict['form'][node.get('key')] = su.unescape(node.text or "")
        for node in requestXml.findall('restmap/key'):
            requestDict['restmap'][node.get('name')] = su.unescape(node.text or "")

        # set the host and port
        try:
            (host, port) = util.splithost(requestDict['headers']['host'])
            splunk.setDefault('host', host)
            if port:
                splunk.setDefault('port', port)
        except KeyError:
            # It must have been an HTTP/1.0 request with no Host: header
            localIP = su.unescape(requestXml.findtext('connectionData/nicIPaddr'))
            if localIP == "":
                localIP = "127.0.0.1"
                if requestDict['remoteAddr'].find(':') >= 0:	# if connection was IPv6, use that
                    localIP = "::1"
            splunk.setDefault('host', localIP)
            splunk.setDefault('port', su.unescape(requestXml.findtext('connectionData/listeningPort')))

        # check if payload content can be auto-converted to primitives
        # parsedPayload = format.parseFeedDocument(requestDict['payload'])

    except Exception as e:
        logger.error('Python REST dispatcher received well-formed but unrecognized XML from HTTP server.')
        raise

    # locate module
    parts = handlerClassName.split('.')
    if not len(parts) or len(parts) > 2 or not handlerClassName:
        raise SyntaxError('The "handler=%s" key is incorrect. Handler names must be in the form "<module_name>.<class_name>".' \
            % handlerClassName)

    # close stdout/stderr so that any import errors generated by the target script don't
    # affect the xml response that's ultimately sent to stdout
    org_stdout, sys.stdout = sys.stdout, open(os.devnull, 'w' if sys.version_info >= (3, 0) else 'wb')
    org_stderr, sys.stderr = sys.stderr, open(os.devnull, 'w' if sys.version_info >= (3, 0) else 'wb')
    try:
        try:
            module = __import__('splunk.rest.external.%s' % parts[0], None, None, parts[0])
        except Exception as e:
            logger.error('The REST handler module "%s" could not be found.  Python files must be in $SPLUNK_HOME/etc/apps/$MY_APP/bin/' \
                % parts[0])
            logger.exception(e)
            raise

        # locate class
        try:
            classObject = getattr(module, parts[1])
        except Exception as e:
            logger.error('The REST handler module "%s" was found, but the class "%s" was not.' \
                % (parts[0], parts[1]))
            logger.exception(e)
            raise

        responseObject = HTTPResponse()
        classInstance = classObject(httpVerb, requestDict, responseObject, sessionKey)

        if not isinstance(classInstance, BaseRestHandler):
            raise TypeError('The class "%s" was found, but needs to be a subclass of BaseRestHandler' % handlerClassName)

        # locate method
        try:
            # by convention, all requests with ?view=docs will be redirected to introspection
            if 'view' in requestDict['query'] and requestDict['query']['view'] == 'docs':
                httpVerb = 'VIEW'
            #logger.debug('Custom handler trying method: handle_%s' % httpVerb)
            method = getattr(classInstance, 'handle_%s' % httpVerb)

        except Exception as e:
            logger.error('Handler class "%s" does not support %s operations.  Add a "handle_%s()" method to enable.' \
                % (parts[1], httpVerb, httpVerb))
            raise

        # execute handler method; log exceptions and dump message back to response
        try:
            # for greppability:  this is where we call handle_GET, handle_POST, handle_DELETE, etc.
            methodOutput = method()
        except Exception as e:
            logger.exception(e)
            if isinstance(e, splunk.RESTException):
                responseObject.setStatus(e.statusCode)
            else:
                responseObject.setStatus(500)
            responseObject.setHeader('content-type', 'text/plain')
            # TODO: these errors get returned as plain text.  should make them structured (XML or JSON, as requested by the client).
            responseObject.write(str(e), True)
            # this is the python-to-splunk XML, which contains a base64 encoded payload that may be in a non-XML format.
            return responseObject.toXml()
    finally:
        sys.stdout = org_stdout
        sys.stderr = org_stderr

    # if the script writer has used the HTTPResponse.write() method, then use
    # that as the raw output
    if responseObject.hasBufferedData():
        # this is the python-to-splunk XML, which contains a base64 encoded payload that may be in a non-XML format.
        return responseObject.toXml()

    # otherwise, methods that return dictionaries or lists or strings get their
    # contents auto-converted into individual entries
    feed = format.primitiveToAtomFeed(splunk.mergeHostPath(), requestDict['path'], methodOutput)
    feed.messages = classInstance.messages

    if requestDict["explicit_output_mode"]:
        if requestDict["output_mode"] == "json":
            import json
            responseObject.setHeader('content-type', 'application/json; charset=utf-8')
            responseObject.write(json.dumps(feed.asJsonStruct(), separators=(',', ':')))
        elif requestDict["output_mode"] == "xml":
            responseObject.setHeader('content-type', 'text/xml; charset=utf-8')
            responseObject.write(feed.toXml())
        else:
            raise splunk.BadRequest("Output mode='%s' not supported by this endpoint." % requestDict["output_mode"])

    else:
        responseObject.setHeader('content-type', 'text/xml; charset=utf-8')
        responseObject.write(feed.toXml())

    # this is the python-to-splunk XML, which contains a base64 encoded payload that may be in a non-XML format.
    return responseObject.toXml()



# /////////////////////////////////////////////////////////////////////////////
#  Define classes used by dispatcher system
# /////////////////////////////////////////////////////////////////////////////

class HTTPResponse(object):
    """
    Represents a complete HTTP response to pass back to main HTTP server
    """

    def __init__(self):
        # set defaults
        self.headers = {
            'content-type': 'text/plain; charset=utf-8'
        }
        self.status = 200
        self.responseBuffer = []

    def setHeader(self, key, value):
        self.headers[key.lower()] = value

    def setStatus(self, value):
        self.status = value

    def write(self, data, flushBuffer=False):

        if flushBuffer:
            self.responseBuffer = []

        if isinstance(data, list):
            self.responseBuffer.extend(data)
        else:
            self.responseBuffer.append(data)

    def hasBufferedData(self):
        if len(self.responseBuffer): return True
        return False

    def toXml(self):
        """
        Return XML representation of response for use with REST dispatcher
        """

        xml = ['<response>']
        xml.append('<statusCode>%s</statusCode>' % self.status)
        xml.append('<headers>')
        for key in self.headers:
            xml.append('<header key="%s">%s</header>' % (su.escape(key), su.escape(self.headers[key])))
        xml.append('</headers>')
        if sys.version_info >= (3, 0) and len(self.responseBuffer) > 0 and isinstance(self.responseBuffer[0], str):
            payload = ''.join(self.responseBuffer).encode()
        else:
            payload = b''.join(self.responseBuffer)
        payload = base64.b64encode(payload)
        if sys.version_info >= (3, 0):
            payload = payload.decode()
        xml.append('<encodedpayload>%s</encodedpayload>' % payload)
        xml.append('</response>')

        return '\n'.join(xml).encode('utf-8')


class BaseRestHandler(object):
    """
    Defines the abstract class for all python script-based REST endpoint
    handlers
    """

    def __init__(self, method, requestInfo, responseInfo, sessionKey):

        self.method = method
        self.request = requestInfo
        self.response = responseInfo
        self.sessionKey = sessionKey

        # merge the GET and POST args into 1 convenience property
        self.args = {}
        self.args.update(self.request['query'])
        self.args.update(self.request['form'])

        self.pathParts = list(map(urllib_parse.unquote, requestInfo['path'].strip('/').split('/')))
        self.messages = []

    def getProductType(self):
        return getattr(__main__, "___productType")

    def addMessage(self, type, text, errorCode=0):
        self.messages.append({
            'type': type.upper(),
            'text': text,
            'errorCode': int(errorCode)
        })


    def handle_VIEW(self):
        """
        Default getter for the .spec file
        """

        # determine the path of the spec file
        # strip extra path
        specPath = self.pathParts[:]
        if specPath[0] == REST_ROOT_PATH.strip('/'):
            specPath.pop(0)

        path = make_splunkhome_path(['etc', 'spec', '.'.join(specPath)])
        path = path + '.spec'

        try:
            specHandle = open(path, 'r')
            self.response.setHeader('content-type', 'text/xml')
            self.response.write(specHandle.readlines())
            specHandle.close()
        except Exception as e:
            logger.error('BaseRestHandler - unable to load the spec file=%s' % path)
            logger.exception(e)
            self.response.write(str(e))



# /////////////////////////////////////////////////////////////////////////////
#  convenience methods
# /////////////////////////////////////////////////////////////////////////////
def makeSplunkdUri():
    # setup args
    host = splunk.getDefault('host')
    if ':' in host:
        host = '[%s]' % host

    uri = '%s://%s:%s/' % \
        (splunk.getDefault('protocol'), host, splunk.getDefault('port'))

    return uri

def enforcePathSecurityPolicy(path, sessionKey):
    enableSplunkWebClientNetloc = True
    # Check that we are running in appserver
    if hasattr(__main__, 'IS_CHERRYPY'):
        import cherrypy
        enableSplunkWebClientNetloc = cherrypy.config.get('enableSplunkWebClientNetloc', False)
    if not enableSplunkWebClientNetloc and (sessionKey is None or not isSplunkSessionKey(sessionKey)):
        parsedPathUrl = urllib_parse.urlparse(path)
        parsedPathUrlScheme = parsedPathUrl.scheme
        parsedPathUrlNetloc = parsedPathUrl.netloc
        parsedSplunkdUrl = urllib_parse.urlparse(makeSplunkdUri())
        if (parsedPathUrlScheme and parsedPathUrlScheme != parsedSplunkdUrl.scheme) or (parsedPathUrlNetloc and parsedPathUrlNetloc != parsedSplunkdUrl.netloc):
            raise splunk.InternalServerError('Setting of custom netloc unsupported (enable via enableSplunkWebClientNetloc in web.conf). %s' % path)

def isSplunkSessionKey(sessionKey):
    return sessionKey == splunk.getSessionKey()

def simpleRequest(path, sessionKey=None, getargs=None, postargs=None, method='GET', raiseAllErrors=False,
                  proxyMode=False, rawResult=False,
                  timeout=None, jsonargs=None, token=False):
    """
    Makes an HTTP call to the main splunk REST endpoint

    path: the URI to fetch
        If given a relative URI, then the method will normalize to the splunkd
        default of "/services/...".
        If given an absolute HTTP(S) URI, then the method will use as-is.
        If given a 'file://' URI, then the method will attempt to read the file
        from the local filesystem.  Only files under $SPLUNK_HOME are supported,
        so paths are 'chrooted' from $SPLUNK_HOME.

    getargs: dict of k/v pairs that are always appended to the URL

    postargs: dict of k/v pairs that get placed into the body of the
        request. If postargs is provided, then the HTTP method is auto
        assigned to POST.

    method: the HTTP verb - [GET | POST | DELETE | PUT]

    raiseAllErrors: indicates if the method should raise an exception
        if the server HTTP response code is >= 400

    rawResult: don't raise an exception if a non 200 response is received;
        return the actual response

    timeout: if not set, will default to SPLUNKD_CONNECTION_TIMEOUT

    forceContentType: optionally supply the value for the Content-Type header
        to be set when sending the request to splunkd

    Return:

        This method will return a tuple of (serverResponse, serverContent)

        serverResponse: a dict of HTTP status information
        serverContent: the body content
    """

    if timeout is None:
        timeout = SPLUNKD_CONNECTION_TIMEOUT

    # if absolute URI, pass along as-is
    if path.startswith('http'):
        enforcePathSecurityPolicy(path, sessionKey)
        uri = path

    # if file:// protocol, try to read file and return
    # the serverStatus is just an empty dict; file contents are in serverResponse
    # TODO: this probably doesn't work in windows
    elif path.startswith('file://'):
        enforcePathSecurityPolicy(path, sessionKey)
        workingPath = path[7:].strip(os.sep)
        lines = util.readSplunkFile(workingPath)
        return ({}, ''.join(lines))

    else:
        # prepend convenience root path
        if not path.startswith(REST_ROOT_PATH): path = REST_ROOT_PATH + '/' + path.strip('/')

        uri = makeSplunkdUri() + path.strip('/')

    if getargs:
        getargs = dict([(k, v) for (k, v) in getargs.items() if v != None])
        uri += '?' + util.urlencodeDict(getargs)

    payload = ''
    if postargs or jsonargs and method in ('GET', 'POST', 'PUT'):
        if method == 'GET':
            method = 'POST'
        if jsonargs:
            # if a JSON body was given, use it for the payload and ignore the postargs
            payload = jsonargs
        else:
            payload = util.urlencodeDict(postargs)

    # proxy mode bypasses all header passing
    headers = {}
    sessionSource = 'direct'
    if not proxyMode:
        if jsonargs:
            headers['Content-Type'] = 'application/json'
        else:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Content-Length'] = str(len(payload))

        # get session key from known places: first the appserver session, then
        # the default instance cache
        if not sessionKey:
            sessionKey, sessionSource = splunk.getSessionKey(return_source=True)
        # if we're using a JWT, we'll be using a bearer header.
        if token:
            headers[AUTH_HEADER] = AUTH_HEADER_PREFIX_BEARER + '%s' % sessionKey
        else:         
            headers[AUTH_HEADER] = AUTH_HEADER_PREFIX_SPLUNK + '%s' % sessionKey

    #
    # make request
    #
    if logger.level <= logging.DEBUG:
        if uri.lower().find('login') > -1:
            logpayload = '[REDACTED]'
        else:
            logpayload = payload
        #logger.debug('simpleRequest >>>\n\tmethod=%s\n\turi=%s\n\tbody=%s' % (method, uri, logpayload))
        logger.debug('simpleRequest > %s %s [%s] sessionSource=%s timeout=%s' % (method, uri, logpayload, sessionSource, timeout))
        t1 = time.time()

    # Add wait and tries to check if the HTTP server is up and running
    tries = 4
    wait = 10
    try:
        import httplib2
        for aTry in range(tries):
            h = httplib2.Http(timeout=timeout, disable_ssl_certificate_validation=True, proxy_info=None)
            if getWebKeyFile() and getWebCertFile():
                h.add_certificate(getWebKeyFile(), getWebCertFile(), '')
            serverResponse, serverContent = h.request(uri, method, headers=headers, body=payload)
            if serverResponse == None:
                if aTry < tries:
                    time.sleep(wait)
            else:
                break
    except socket.error as e:
        logger.error('Socket error communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Error connecting to %s: %s' % (path, str(e)))
    except socket.timeout as e:
        logger.error('Socket timeout communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Time out connecting to splunkd daemon at %s: %s. Splunkd may be hung. (timeout=%s)' % (path, str(e), timeout))
    except AttributeError as e:
        logger.error('Connection error communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Unable to establish connection with splunkd deamon at %s: %s' % (path, str(e)))

    serverResponse.messages = []

    if logger.level <= logging.DEBUG:
        logger.debug('simpleRequest < server responded status=%s responseTime=%.4fs' % (serverResponse.status, time.time() - t1))

    # Don't raise exceptions for different status codes or try and parse the response
    if rawResult:
        return serverResponse, serverContent

    #
    # we only throw exceptions in limited cases; for most HTTP errors, splunkd
    # will return messages in the body, which we parse, so we don't want to
    # halt everything and raise exceptions; it is up to the client to figure
    # out the best course of action
    #
    if serverResponse.status == 401:
        #SPL-20915
        logger.debug('simpleRequest - Authentication failed; sessionKey=%s' % sessionKey)
        if serverContent.count(b'forced_password_change') or serverContent.count(b'inval_pass_min_len'):
            err = et.fromstring(serverContent).find('messages').find('msg').text
            raise splunk.AuthenticationFailed(msg='fpc', extendedMessages=err)
        else:
            raise splunk.AuthenticationFailed

    elif serverResponse.status == 402:
        raise splunk.LicenseRestriction

    elif serverResponse.status == 403:
        raise splunk.AuthorizationFailed(extendedMessages=uri)

    elif serverResponse.status == 404:

        # Some 404 reponses, such as those for expired jobs which were originally
        # run by the scheduler return extra data about the original resource.
        # In this case we add that additional info into the exception object
        # as the resourceInfo parameter so others might use it.
        try:
            body = et.fromstring(serverContent)
            resourceInfo = body.find('dict')
            if resourceInfo is not None:
                raise splunk.ResourceNotFound(uri, format.nodeToPrimitive(resourceInfo))
            else:
                raise splunk.ResourceNotFound(uri, extendedMessages=extractMessages(body))
        except et.XMLSyntaxError:
            pass

        raise splunk.ResourceNotFound(uri)

    elif serverResponse.status == 201:
        try:
            body = et.fromstring(serverContent)
            serverResponse.messages = extractMessages(body)
        except et.XMLSyntaxError as e:
            # do nothing, just continue, no messages to extract if there is no xml
            pass
        except e:
            # warn if some other type of error occurred.
            logger.warn("exception trying to parse serverContent returned from a 201 response.")
            pass

    elif serverResponse.status < 200 or serverResponse.status > 299:

        # service may return messages in the body; try to parse them
        try:
            body = et.fromstring(serverContent)
            serverResponse.messages = extractMessages(body)
        except:
            try:
                body = json.loads(serverContent)
                serverResponse.messages = extractJsonMessages(body)
            except:
                pass

        if raiseAllErrors and serverResponse.status > 399:

            if serverResponse.status == 500:
                raise splunk.InternalServerError(None, serverResponse.messages)
            elif serverResponse.status == 400:
                raise splunk.BadRequest(None, serverResponse.messages)
            else:
                raise splunk.RESTException(serverResponse.status, serverResponse.messages)


    # return the headers and body content
    return serverResponse, serverContent


def checkResourceExists(uri, sessionKey=None):
    '''
    Determines if a URI resource exists
    '''

    try:
        serverResponse, serverContent = simpleRequest(uri, sessionKey)
    except splunk.ResourceNotFound:
        return False
    return True


def invokeApi(methodName, args, sessionKey):
    """
    Provides legacy compatibility services with the invokeAPI system, as
    exposed via the /services/invokeapi endpoint
    """

    serverResponse, serverContent = simpleRequest('/invokeapi/%s' % methodName, sessionKey, postargs=args)
    return serverContent


def extractMessages(inputXmlNode):
    '''
    Inspects an XML node and extracts any messages that have been passed through
    the standard XML messaging spec
    '''

    output = []
    messages = inputXmlNode.find('messages')
    if messages == None:
        # logger.debug("The atom feed uses the splunk namespace, so check there too")
        messages = inputXmlNode.find(SPLUNK_TAGF % 'messages')

    if messages is not None:
        for child in messages:
            item = {
                'type': child.get('type'),
                'code': child.get('code'),
                'text': child.text
            }
            output.append(item)
            logger.debug('extractMessages - message type=%(type)s code=%(code)s text=%(text)s' % item)
    return output

def extractJsonMessages(inputJsonDict):
    output = []
    messages = inputJsonDict.get('messages')
    if messages is not None:
        for child in messages:
            item = {
                'type': child.get('type'),
                'code': child.get('code'),
                'text': child.get('text')
            }
            output.append(item)
            logger.debug('extractMessages - message type=%(type)s code=%(code)s text=%(text)s' % item)
    return output

class StreamingResponse(object):
    """
    Response returned from calls to streamingRequest()

    Has two properties:
    conn - An HTTPConnection or HTTPSConnection object
    response - An HTTPResponse object

    Call readall() to return a generator
    """
    def __init__(self, conn, response):
        self.conn = conn
        self.response = response

    def readall(self, blocksize=32768):
        """
        Returns a generator reading blocks of data from the response
        until all data has been read
        """
        response = self.response
        while True:
            data = response.read(blocksize)
            if not data:
                break
            yield data


def streamingRequest(path, sessionKey=None, getargs=None, postargs=None, method='GET', timeout=None):
    """
    A streaming counterpart to simpleRequest
    Returns an instance of StreamingResponse which has a readall() method
    that will return a generator to stream a response from splundk rather than buffering
    it in memory
    """
    if timeout is None or timeout < SPLUNKD_CONNECTION_TIMEOUT:
        timeout = SPLUNKD_CONNECTION_TIMEOUT

    # if absolute URI, pass along as-is
    if path.startswith('http'):
        enforcePathSecurityPolicy(path, sessionKey)
        uri = path
        parsedUri = urllib_parse.urlsplit(uri)
        host = parsedUri.hostname
        path = parsedUri.path
        port = parsedUri.port

    else:
        # prepend convenience root path
        if not path.startswith(REST_ROOT_PATH): path = REST_ROOT_PATH + '/' + path.strip('/')

        # setup args
        host = splunk.getDefault('host')
        port = splunk.getDefault('port')
        urihost = '[%s]' % host if ':' in host else host

        uri = '%s://%s:%s/%s' % \
            (splunk.getDefault('protocol'), urihost, port, path.strip('/'))

    if getargs:
        getargs = dict([(k, v) for (k, v) in getargs.items() if v != None])
        querystring = '?' + util.urlencodeDict(getargs)
        uri += querystring
        path += querystring

    isssl = uri.startswith('https:')

    headers = {}
    sessionSource = 'direct'
    # get session key from known places: first the appserver session, then
    # the default instance cache
    if not sessionKey:
        sessionKey, sessionSource = splunk.getSessionKey(return_source=True)
    headers['Authorization'] = 'Splunk %s' % sessionKey

    payload = ''
    if postargs and method in ('GET', 'POST', 'PUT'):
        if method == 'GET':
            method = 'POST'
        payload = util.urlencodeDict(postargs)

    #
    # make request
    #
    if logger.level <= logging.DEBUG:
        if uri.lower().find('login') > -1:
            logpayload = '[REDACTED]'
        else:
            logpayload = payload
        logger.debug('streamingRequest > %s %s [%s] sessionSource=%s' % (method, uri, logpayload, sessionSource))
        t1 = time.time()

    logger.debug('streamingRequest opening connection to host=%s path=%s method=%s postargs=%s payload=%s' % (host, path, method, postargs, payload))

    try:
        conn = httplib.HTTPSConnection(host, port, getWebKeyFile(), getWebCertFile(), timeout=timeout) if isssl else httplib.HTTPConnection(host, port, timeout=timeout)
        conn.connect()
        conn.putrequest(method, path)
        for key, val in headers.items():
            conn.putheader(key, val)
        if payload:
            conn.putheader('Content-Type', 'application/x-www-form-urlencoded')
            conn.putheader('Content-Length', str(len(payload)))
            conn.endheaders()

            if sys.version_info >= (3, 0):
                payload = payload.encode()

            conn.send(payload)
        else:
            conn.endheaders()

        response = conn.getresponse()
    except socket.error as e:
        logger.error('Socket error communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Error connecting to %s: %s' % (path, str(e)))
    except socket.timeout as e:
        logger.error('Socket timeout communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Time out connecting to splunkd daemon at %s: %s. Splunkd may be hung. (timeout=%s)' % (path, str(e), timeout))
    except AttributeError as e:
        logger.error('Connection error communicating with splunkd (error=%s), path = %s' % (str(e), path))
        raise splunk.SplunkdConnectionException('Unable to establish connection with splunkd deamon at %s: %s' % (path, str(e)))


    if response.status == 401:
        logger.debug('simpleRequest - Authentication failed; sessionKey=%s' % sessionKey)
        raise splunk.AuthenticationFailed

    elif response.status == 402:
        raise splunk.LicenseRestriction()

    elif response.status == 403:
        raise splunk.AuthorizationFailed(extendedMessages=uri)

    elif response.status == 404:
        body = response.read()

        # Some 404 reponses, such as those for expired jobs which were originally
        # run by the scheduler return extra data about the original resource.
        # In this case we add that additional info into the exception object
        # as the resourceInfo parameter so others might use it.
        try:
            body = et.fromstring(body)
            resourceInfo = body.find('dict')
            if resourceInfo is not None:
                raise splunk.ResourceNotFound(uri, format.nodeToPrimitive(resourceInfo))
            else:
                raise splunk.ResourceNotFound(uri, extendedMessages=extractMessages(body))
        except et.XMLSyntaxError:
            pass

        raise splunk.ResourceNotFound(uri)

    return StreamingResponse(conn, response)
