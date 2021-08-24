from __future__ import absolute_import
#   Version 4.0
###########################################################
##
##  manage_splunkd:
##      module for manipulating splunk settings values
##
###########################################################

import logging as logger
import xml.dom.minidom
import copy, os, sys
from splunk.clilib.control_exceptions import ArgError
import splunk.clilib.cli_common as comm
from splunk.clilib import validate
from splunk.clilib import bundle_paths
from splunk.clilib.bundle_paths import make_splunkhome_path


####
##  global consts in this module
####

CONFIG_SERVER     = "server"
CONFIG_WEB        = "web"
STANZA_SSL        = "sslConfig"
STANZA_SETTINGS   = "settings"

_searchConfigPath = os.path.join("myinstall", "search.xml")
_userConfigPath   = os.path.join("myinstall", "search.user.xml")
fullSearchConfig  = make_splunkhome_path(["etc", _searchConfigPath])
userSearchConfig  = make_splunkhome_path(["etc", _userConfigPath])
fullSplunkdConfig = make_splunkhome_path(["etc", "myinstall", "splunkd.xml"])
fullServerConfig  = bundle_paths.make_path("server.conf")
fullWebConfig     = bundle_paths.make_path("web.conf")

# regex's for input validation
_URLpattern = '^http[s]?://[\w\S\-\./]*(:[\d]+)?[\w\S\-\./%~\(\)]*$'
_namespacepattern = '^[\w\S\-\.:/%~\(\)]+$'
_truefalsepattern = '[(true)(false)10]?'

webSettingsStanza = "settings"
serverGeneralStanza = "general"

prettyNameMap = {"uiversion" : "Web version", "sslport" : "SSL Web port"}
# map of command line params to xml tags
tagmap = {
    'mgmturl'   : 'managerURL',
    'mgmtns'    : 'managerNamespace',
    'searchurl' : 'searchEngineURL',
    'searchns'  : 'searchEngineNamespace',
    'splunkservice' : 'ServiceFormPostURL',
    'dirmon-readonly'    : 'isReadonly',
    'dirmon'    : 'directoryMonitorLocation',
    'guid'      : 'guid',
    'startwebserver'    : 'start_web_server',
    'name'      : 'name',
    'privkey'   : 'privKeyPath',
    'certificate'       : 'caCertPath'
}


####
## start of exposed defs
####


def getMgmtURL(argsDict, fromCLI):
    reqkeys = ('authstr',)
    optkeys = ()
    
    # we take only one optional arg
    comm.validateArgs(reqkeys, optkeys, argsDict )
    returnDict = {}
    returnDict["mgmturl"] = comm.getWebConfKeyValue("mgmtHostPort")
    
    return returnDict


def getMgmtPort(argsDict, fromCLI):
    """
    Returns the management PORT.  Not URL.  Will fix the name mismatches in the future.
    """
    # TODO (above)
    reqkeys = ("authstr",)
    optkeys = ()
    
    returnDict = {}
    mgmtUrl = getMgmtURL({"authstr" : argsDict["authstr"]}, False)["mgmturl"]
    mgmtUrl = mgmtUrl[mgmtUrl.find(":") + 1:]
    returnDict["mgmturl"] = mgmtUrl
    if fromCLI:
      logger.info("Splunkd port: %s." % returnDict["mgmturl"])
    return returnDict
    

def getUIVersion(argsDict, fromCLI):
  '''DEPRECATED: uiversion switching is no longer supported'''
  paramsReq = ()
  paramsOpt = ()

  comm.validateArgs(paramsReq, paramsOpt, argsDict)
  retDict   = {'uiversion': 'DEPRECATED'}
  
  if fromCLI:
    logger.warn("Web UI version setting has been deprecated")
  return retDict


def setUIVersion(argsDict, fromCLI):
  '''DEPRECATED: uiversion switching is no longer supported'''
  paramsReq = ()
  paramsOpt = ()

  if fromCLI:
    logger.warn("Web UI version setting has been deprecated")
  return {}


###########################################################
##
## stuff to get/set settings from splunkd.xml
##
###########################################################

    
def getInstanceName(argsDict, fromCLI):
    reqkeys = ()
    optkeys = ()
    returnDict = {}
    comm.validateArgs(reqkeys, optkeys, argsDict )

    currSetts = comm.readConfFile(fullServerConfig)
    returnDict["instancename"] = "(unset)";
    if serverGeneralStanza in currSetts:
      if "serverName" in currSetts[serverGeneralStanza]:
        returnDict["instancename"] = currSetts[serverGeneralStanza]["serverName"]

    if fromCLI:
      logger.info("Server name: %s." % returnDict["instancename"])
    return returnDict

def setInstanceName(argsDict, fromCLI):
    reqkeys = ('instancename',)
    optkeys = ()
    comm.validateArgs(reqkeys, optkeys, argsDict )
    returnDict = setLocalName({"name" : argsDict["instancename"]}, fromCLI)
    returnDict["restartRequired"] = True
    return returnDict


def setLocalMgmtPort(args, fromCLI):
  paramReq = ("port",)
  paramOpt = ()
  comm.validateArgs(paramReq, paramOpt, args)
  if fromCLI:
    validate.checkPortNum("port", args["port"])

  retDict = {}
  host = "localhost"
  key  = "mgmtHostPort"
  currSetts = comm.readConfFile(fullWebConfig)

  if not webSettingsStanza in currSetts:
    currSetts[webSettingsStanza] = {}
  if key in currSetts[webSettingsStanza]:
    try:
      # this expects the uri as "blah:8000" - or just "a:b", really.
      host, oldPortWhichIsGarbage = currSetts[webSettingsStanza][key].split(":", 1)
    except ValueError:
      pass # leaves localhost value from above

  currSetts[webSettingsStanza][key] = "%s:%s" % (host, args["port"])
  comm.writeConfFile(fullWebConfig, currSetts)
  return retDict

def setLocalHttp(args, fromCLI):
  paramReq = ("port",)
  paramOpt = ()
  comm.validateArgs(paramReq, paramOpt, args)
  if fromCLI:
    validate.checkPortNum("port", args["port"])

  retDict = {}
  key = "httpport"
  currSetts = comm.readConfFile(fullWebConfig)

  if not webSettingsStanza in currSetts:
    currSetts[webSettingsStanza] = {}
  currSetts[webSettingsStanza][key] = args["port"]

  comm.writeConfFile(fullWebConfig, currSetts)
  return retDict

def setLocalHttps(args, fromCLI):
  raise ArgError("Setting the HTTPS port is deprecated.  There is a single web port now, which is stored as the HTTP port.  See \"splunk help set\".")

def setLocalName(args, fromCLI):
  paramReq = ("name",)
  paramOpt = ()
  comm.validateArgs(paramReq, paramOpt, args)
  name = args["name"]
  if name.count(" ") + name.count(":") > 0:
    raise ArgError("Name '%s' is invalid.  Names cannot contain spaces or colons." % name)

  currSetts = comm.readConfFile(fullServerConfig)
  if not serverGeneralStanza in currSetts:
    currSetts[serverGeneralStanza] = {}
  currSetts[serverGeneralStanza]["serverName"] = name
  comm.writeConfFile(fullServerConfig, currSetts)
  return {}
