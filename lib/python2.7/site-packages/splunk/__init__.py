from __future__ import absolute_import
import __main__
import os
import logging
import splunk.util


#
# Set default server connection settings
#
_DEFAULT_HOST = 'localhost'
_DEFAULT_PORT = 8089
_DEFAULT_PROTOCOL = 'https'
_DEFAULT_NAMESPACE = 'search'
#SPL-23698
__version__ = '4.0'

def getReleaseVersion():
    '''
    Get the exact version of this Splunk release, as opposed to the Splunk
    release series above.
    '''
    import splunk.version
    return splunk.version.__version__


def getLocalServerInfo():
    '''
    Look on local filesystem for splunkd connection info
    '''

    try:
        import splunk.clilib.cli_common as comm
        hostpath = comm.getMgmtUri()
        if hostpath:
            mergeHostPath(hostpath, True)

    except ImportError:
        pass
        
    return mergeHostPath()
        
def getWebServerInfo():
    '''
    Look on local filesystem for appserver connection info
    '''

    import splunk.clilib.cli_common as comm
    return comm.getWebUri()

def setDefault(key=None, value=None):
    '''
    Sets default values for the Splunk class methods.  Stores frequently used
    items such as 'host' and 'port'.
    '''
    
    if 'SPLUNK_DEFAULTS' not in __main__.__dict__:
        __main__.SPLUNK_DEFAULTS = {
            'host': _DEFAULT_HOST,
            'port': _DEFAULT_PORT,
            'protocol': _DEFAULT_PROTOCOL,
            'namespace': _DEFAULT_NAMESPACE,
            'username': None,
            'sessionKey': None
        }
        getLocalServerInfo()
        
    if key:
        __main__.SPLUNK_DEFAULTS[key] = value
        return value
    
def getDefault(key):
    '''
    Gets default values set using the setDefault() method.  Returns None if the
    key value does not exist.
    '''
    
    if 'SPLUNK_DEFAULTS' not in __main__.__dict__:
        setDefault()
        
    if key in __main__.SPLUNK_DEFAULTS:
        return __main__.SPLUNK_DEFAULTS[key]
    else:
        return None
        
def getSessionKey(return_source=False):
    if hasattr(__main__, 'IS_CHERRYPY'):
        import cherrypy
        # Check that we're actually handling a current request and not in a non CP unit test
        if cherrypy.request.handler: 
            return (cherrypy.session.get('sessionKey'), 'cherrypy' ) if return_source else cherrypy.session.get('sessionKey')
    return (getDefault('sessionKey'), 'SDK') if return_source else getDefault('sessionKey')
    

def mergeHostPath(hostpath=None, saveAsDefault=False):
    '''
    Returns a host URI to connect to Splunk. Merges values from input with 
    default values.  Accepts string values like:
    
    -- hostname
    -- hostname:port
    -- protocol://hostname:port
    
    # first two tests assume configuration, SPL-32127
    >>> mergeHostPath('hostname1') # doctest: +SKIP
    'https://hostname1:8089'
    >>> mergeHostPath('hostname1:345') # doctest: +SKIP
    'https://hostname1:345'
    >>> mergeHostPath('ftp://hostname1:345')
    'ftp://hostname1:345'
    >>> mergeHostPath('http://decider.splunk.com:8089')
    'http://decider.splunk.com:8089'
    '''
    
    host = getDefault('host')
    port = getDefault('port')
    protocol = getDefault('protocol')
    
    if hostpath:
        hostpath = hostpath.strip(' /')
    
        s = hostpath.split('://', 1)
        if len(s) > 1:
            protocol = s[0]
            s = s[1]
        else:
            s = s[0]

        from splunk import util
        (host, splitport) = util.splithost(s)
        if splitport:
            port = splitport
        
        if saveAsDefault:
            setDefault('host', host)
            setDefault('port', int(port))
            setDefault('protocol', protocol)

    if host.find(':') >= 0:
        host = "[" + host + "]"

    return '%s://%s:%s' % (protocol, host, port)



def setupSplunkLogger(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose=True):
    '''
    Takes the base logging.logger instance, and scaffolds the splunk logging namespace
    and sets up the logging levels as defined in the config files
    '''
    
    levels = getSplunkLoggingConfig(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose)
    
    for item in levels:
        loggerName = item[0]
        level = item[1]
        if hasattr(logging, level):
            logging.getLogger(loggerName).setLevel(getattr(logging, level))
        if verbose and (loggerName == "appender.python.maxFileSize" or loggerName == "appender.python.maxBackupIndex"):
            baseLogger.info('Python log rotation is not supported. Ignoring %s' % loggerName)
        

def getSplunkLoggingConfig(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose):

    loggingLevels = []
    
    # read in config file and set logging levels
    if os.access(localConfigFile, os.R_OK):
        if verbose:
            baseLogger.info('Using local logging config file: %s' % localConfigFile)
        logConfig = open(localConfigFile, 'r')
    else:
        if verbose:
            baseLogger.info('Using default logging config file: %s' % defaultConfigFile)
        logConfig = open(defaultConfigFile, 'r')

    try:
        inStanza = False
        for line in logConfig:

            # strip comments
            line = line.strip()
            if '#' in line:
                line = line[:(line.index('#'))]

            # skip blank lines
            line = line.strip()
            if not line:
                continue

            # # # skip malformatted lines: stanza, key=value, or WTF?
            if line.startswith('['):
                if not line.endswith(']') or line.index(']') != (len(line) - 1):
                    continue
            elif '=' in line:
                key_test, value_test = line.split('=')
                if not key_test or not value_test:
                    continue
            else:
                continue

            # # # validation done, now we finally have parsing logic proper
            if not inStanza and line.startswith('[%s]' % loggingStanzaName):
                inStanza = True
                continue
            elif inStanza:
                if line.startswith('['):
                    break
                else:
                    name, level = line.split('=', 1)
                    if verbose:
                        baseLogger.info('Setting logger=%s level=%s' % (name.strip(), level.strip()))
                    loggingLevels.append((name.strip(), level.strip().upper()))
    except Exception as e:
        baseLogger.exception(e)
    finally:
        if logConfig: logConfig.close()
    
    return loggingLevels
    
    
    
# /////////////////////////////////////////////////////////////////////////////
# Splunk Exceptions
# /////////////////////////////////////////////////////////////////////////////

#
# Standard HTTP status errors
#

class RESTException(Exception):
    '''
    Indicates that a REST call returned an HTTP status, usually in the 400-599 
    range.
    '''
    
    def __init__(self, statusCode, msg=None, extendedMessages=None):
        Exception.__init__(self, msg)
        self.msg = msg
        try:
            statusCode = int(statusCode)
            if not msg:
                if 400 <= statusCode < 500:
                    self.msg = 'General client request error'
                elif 500 <= statusCode < 600:
                    self.msg = 'General server error'
                else:
                    self.msg = 'Unexpected HTTP status code'
        except:
            pass
        self.statusCode = statusCode
        self.extendedMessages = extendedMessages
        
    def __str__(self):
        if self.extendedMessages is None:
            return '[HTTP %s] %s' % (self.statusCode, self.msg)
        return '[HTTP %s] %s; %s' % (self.statusCode, self.msg, self.extendedMessages)

    def get_message_text(self):
        """ Return the first error string in the message list """
        if isinstance(self.msg, list) and len(self.msg)>0:
            if isinstance(self.msg[0], dict):
                return self.msg[0].get("text")
        
        if isinstance(self.extendedMessages, list) and len(self.extendedMessages)>0:
            if isinstance(self.extendedMessages[0], dict):
                return self.extendedMessages[0].get("text")

        if isinstance(self.msg, splunk.util.string_type):
            return self.msg
        
        return '' 

    def get_extended_message_text(self):
        """ 
        Return the first error string in the message list 
        Same as get_message_text() but prefers the extended message over the short
        """
        if isinstance(self.extendedMessages, list) and len(self.extendedMessages)>0:
            if isinstance(self.extendedMessages[0], dict):
                return self.extendedMessages[0].get("text")

        if isinstance(self.msg, list) and len(self.msg)>0:
            if isinstance(self.msg[0], dict):
                return self.msg[0].get("text")

        if isinstance(self.msg, splunk.util.string_type):
            return self.msg
        
        return '' 
    
class AuthenticationFailed(RESTException):
    '''
    Indicates that a request to splunkd was denied because the client was
    not authenticated.
    '''
    
    def __init__(self, msg='Client is not authenticated', extendedMessages=None):
        RESTException.__init__(self, 401, msg, extendedMessages)


class LicenseRestriction(RESTException):
    '''
    Indicates that a request to splunkd was denied because the license did
    not authorize user to perform the action.
    '''

    def __init__(self, msg='Current license does not allow the requested action'):
        RESTException.__init__(self, 402, msg)

        
class AuthorizationFailed(RESTException):
    '''
    Indicates that a request to splunkd was denied because the client was
    not authorized to perform the action.
    '''

    def __init__(self, msg='Client is not authorized to perform requested action', extendedMessages=None):
        RESTException.__init__(self, 403, msg, extendedMessages)


class BadRequest(RESTException):
    '''
    Indicates that a request to splunkd could not be understood due to
    malformed syntax.
    
    extendedMessages -- a list of messages, as generated by 
        splunk.rest.extractMessages()
    '''

    def __init__(self, msg=None, extendedMessages=None):
        if not msg: msg = 'Bad Request'
        RESTException.__init__(self, 400, msg, extendedMessages)


class InternalServerError(RESTException):
    '''
    Indicates that splunkd encountered an unexpected condition which prevented
    it from fulfilling a request.

    extendedMessages -- a list of messages, as generated by 
        splunk.rest.extractMessages()
    '''

    def __init__(self, msg=None, extendedMessages=None):
        if not msg: msg = 'Splunkd internal error'
        RESTException.__init__(self, 500, msg, extendedMessages)


class ResourceNotFound(RESTException):
    '''
    Indicates that a requested HTTP resource was not found.
    '''

    def __init__(self, msg='Resource was not found', resourceInfo=None, extendedMessages=None):
        RESTException.__init__(self, 404, msg, extendedMessages)
        self.resourceInfo = resourceInfo

#
# General splunkd exceptions
#
    
class SplunkdException(Exception):
    '''
    Indicates error generated by splunkd
    '''

class SplunkdConnectionException(Exception):
    '''
    Indicates error establishing connection to the splunkd server
    '''
    def __init__(self, message="Socket error connecting to the Splunk server."):
       Exception.__init__(self, message)

    def __str__(self):
        return "Splunkd daemon is not responding: %s" % str(self.args)


#
# Splunk search exceptions
#

class SearchException(SplunkdException):
    '''
    Indicates error generated by Splunk search subsystem.
    '''

class QuotaExceededException(SearchException):
    '''
    Indicates that the search dispatch was not accepted because the user has
    reached the active search quota
    '''


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
