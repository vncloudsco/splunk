from __future__ import absolute_import
#   Version 4.0
import logging as logger
import copy, os, shutil
import splunk.clilib.cli_common as comm
from splunk.clilib.control_exceptions import ConfigError
import xml.dom.minidom
from splunk.clilib import bundle_paths
from splunk.clilib.bundle_paths import make_splunkhome_path

DEPL_CLIENT_NAME = "Deployment Client"
DEPL_SERVER_NAME = "Deployment Server"
DIST_SEARCH_NAME = "Distributed Search"

DEPL_CLI_CONFIG  = "deployment"
DEPL_CLI_STANZA  = "deployment-client"

DEPL_SERV_CONFIG = "deployment"
DEPL_SERV_STANZA = "distributedDeployment"

DIST_SEARCH_CONFIG = "distsearch"
DIST_SEARCH_STANZA = "distributedSearch"

MODULE_PATH_SEP  = ":"

BATCH_PATH  = os.path.join(os.path.sep, "modules", "input", "batchfile")
EXEC_PATH   = os.path.join(os.path.sep, "modules", "input", "exec")
FIFO_PATH   = os.path.join(os.path.sep, "modules", "input", "FIFO")
TAIL_PATH   = os.path.join(os.path.sep, "modules", "input", "tailfile")
TCP_PATH    = os.path.join(os.path.sep, "modules", "input", "TCP")
UDP_PATH    = os.path.join(os.path.sep, "modules", "input", "UDP")

BATCH_NAME  = "Batch Input"
EXEC_NAME   = "Exec Input"
FIFO_NAME   = "FIFO Input"
TAIL_NAME   = "Tail Input"
TCP_NAME    = "TCP Input"
UDP_NAME    = "UDP Input"

ARG_AUTHSTR = "authstr"
ARG_CONFIG  = "config"       # which [merged] .conf file to search for the stanza in
ARG_MODNAME = "modname"
ARG_MODPATH = "modpath"
ARG_MODULE  = "module"
ARG_STANZA  = "stanza"       # which stanza to pick out of the given .conf file
ARG_USEFS   = "uselocalfs"   # special case for deployment stuff...

KEY_DISABLED = "disabled"

########################################################################################################

# Wrappers for dealing with deployment client module.
# fyi this stuff doesn't pass in the auth string because the functions are only exposed from the CLI,
# which can actually use the btool type of stuff to get our merged conf files.  the UI will never expose
# these particular functions, so not bothering supporting it.

def deplClientStatus(args, fromCLI):
  """Checks whether or not deployment client module is enabled."""
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  return stanzaStatus({ARG_CONFIG : DEPL_CLI_CONFIG, ARG_MODNAME : DEPL_CLIENT_NAME, ARG_STANZA : DEPL_CLI_STANZA}, fromCLI)

def deplClientEnable(args, fromCLI):
  """Enables the deployment client if currently disabled."""
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  return stanzaEnable({ARG_CONFIG : DEPL_CLI_CONFIG, ARG_MODNAME : DEPL_CLIENT_NAME, ARG_STANZA : DEPL_CLI_STANZA, ARG_USEFS : "true"}, fromCLI)

def deplClientDisable(args, fromCLI):
  """Enables the deployment client if currently enabled."""
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  return stanzaDisable({ARG_CONFIG : DEPL_CLI_CONFIG, ARG_MODNAME : DEPL_CLIENT_NAME, ARG_STANZA : DEPL_CLI_STANZA, ARG_USEFS : "true"}, fromCLI)



########################################################################################################
###################################################################################################three
########################################################################################################

# New functions that work based off .conf files and [stanzas]

def stanzaStatus(args, fromCLI):
  """
  Wrapper that prints stuff.
  """
  paramsReq = (ARG_CONFIG, ARG_MODNAME, ARG_STANZA)
  paramsOpt = (ARG_AUTHSTR,)
  comm.validateArgs(paramsReq, paramsOpt, args)
  
  returnDict = stanzaStatusInternal(args, fromCLI)
  if fromCLI:
    if returnDict["enabled"]:
      logger.info("%s is enabled." % args[ARG_MODNAME])
    else:
      logger.info("%s is disabled." % args[ARG_MODNAME])
  return returnDict

def stanzaStatusInternal(args, fromCLI):
  """
  Returns boolean based on whether or not a given stanza in a given file has the "disabled" parameter set.
  """
  paramsReq = (ARG_CONFIG, ARG_MODNAME, ARG_STANZA)
  paramsOpt = (ARG_AUTHSTR,)
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {"enabled" : False}
  stanza = args[ARG_STANZA]

  authStr = (ARG_AUTHSTR in args) and args[ARG_AUTHSTR] or None

  currStatus = comm.getMergedConf(args[ARG_CONFIG])

  if stanza in currStatus:
    returnDict["enabled"] = True # found the stanza, let's say it's enabled unless we learn otherwise.
    if KEY_DISABLED in currStatus[stanza]:
      if "true" == currStatus[stanza][KEY_DISABLED].lower():
        returnDict["enabled"] = False # if disabled=true, override what we thought above.

  returnDict["stanzas"] = currStatus
  return returnDict



def stanzaDisable(args, fromCLI):
  """
  Disables a given stanza in a given conf file.
  """
  paramsReq = (ARG_CONFIG, ARG_MODNAME, ARG_STANZA)
  paramsOpt = (ARG_AUTHSTR, ARG_USEFS)
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {}
  stanza = args[ARG_STANZA]
  confFile = bundle_paths.make_path(args[ARG_CONFIG] + ".conf")

  authStr = (ARG_AUTHSTR in args) and args[ARG_AUTHSTR] or ""

  # see if it's currently enabled.
  currStatus = stanzaStatusInternal({ARG_CONFIG : args[ARG_CONFIG], ARG_MODNAME : args[ARG_MODNAME], ARG_STANZA : stanza, ARG_AUTHSTR: authStr}, fromCLI)
  currEnabled = currStatus["enabled"]

  # get the local .conf file.  don't use the stanzas given to us from "status",
  # because they're merged - we don't want to write out all the merged settings.
  # btw, readConfFile checks to see if the path exists and does the right thing.
  confStanzas = comm.readConfFile(confFile)

  if currEnabled: # then disable it
    returnDict["restartRequired"] = True
    # create the stanza if it's not in the .conf already (could be on via default bundle)
    if not stanza in confStanzas:
      confStanzas[stanza] = {}
    # and make sure we set the disabled key in local to be true.
    confStanzas[stanza][KEY_DISABLED] = "true"
    stanzaXml = comm.flatDictToXML(confStanzas[stanza]) 
    # the following is now always true:
    # in order to support "splunk set deploy-poll", we allow this stuff to also write to the local filesystem.
    logger.debug("Attempting to disable module via local filesystem.")
    comm.writeConfFile(confFile, confStanzas)

  if not currEnabled:
    logger.info("%s is already disabled." % args[ARG_MODNAME])
  else:
    logger.info("%s disabled." % args[ARG_MODNAME])
  return returnDict



def stanzaEnable(args, fromCLI):
  """
  Enables a given stanza in a given conf file.
  """
  paramsReq = (ARG_CONFIG, ARG_MODNAME, ARG_STANZA)
  paramsOpt = (ARG_AUTHSTR, ARG_USEFS)
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {}
  authStr = (ARG_AUTHSTR in args) and args[ARG_AUTHSTR] or ""
  stanza = args[ARG_STANZA]
  confFile = bundle_paths.make_path(args[ARG_CONFIG] + ".conf")
  currStatus = stanzaStatusInternal({ARG_CONFIG : args[ARG_CONFIG], ARG_MODNAME : args[ARG_MODNAME], ARG_STANZA : stanza, ARG_AUTHSTR: authStr}, fromCLI)
  currEnabled = currStatus["enabled"]

  # get the local .conf file.  don't use the stanzas given to us from "status",
  # because they're merged - we don't want to write out all the merged settings.
  # btw, readConfFile checks to see if the path exists and does the right thing.
  confStanzas = comm.readConfFile(confFile)

  if not currEnabled: # then enable it
    returnDict["restartRequired"] = True
    # create the stanza if it's not in the .conf already (if it was never enabled)
    if not stanza in confStanzas:
      confStanzas[stanza] = {}
    # at this point the only way for it to be disabled is for the disabled key to be true.
    # set it false regardless of whether or not it exists.
    confStanzas[stanza][KEY_DISABLED] = "false"
    stanzaXml = comm.flatDictToXML(confStanzas[stanza]) 
    # the following is now always true:
    # if applicable, just write to the local FS (used by splunk set deploy-poll).
    logger.debug("Attempting to enable module via local filesystem.")
    comm.writeConfFile(confFile, confStanzas)

  if currEnabled:
    logger.info("%s is already enabled." % args[ARG_MODNAME])
  else:
    logger.info("%s enabled." % args[ARG_MODNAME])
  return returnDict



########################################################################################################
###################################################################################################three
########################################################################################################

def getNameAndPath(module):
  """
  takes colon-separated path (easier to write os-independent code).
  """
  # build somewhat descriptive module name, based on path.
  moduleName = str.join(os.path.sep, module.split(MODULE_PATH_SEP))
  # build full path to module xml file.
  modulePath = make_splunkhome_path(["etc", "modules", moduleName, "config.xml"])
  return (moduleName, modulePath)


def getDisabledPath(path):
  return str(path) + ".disabled"



def localModuleStatus(args, fromCLI):
  """
  Works only on the local filesystem.
  Returns boolean based on whether or not module of given name is enabled.
  "module" param is path relative to etc/modules, with dirs separted by colons.
  """
  paramsReq = (ARG_MODULE,)
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {"enabled" : False}
  moduleName, modulePath = getNameAndPath(args[ARG_MODULE])
  if os.path.exists(modulePath):
    returnDict["enabled"] = True

  if fromCLI:
    if returnDict["enabled"]:
      logger.info("%s is enabled." % moduleName)
    else:
      logger.info("%s is disabled." % moduleName)
  return returnDict


def localModuleEnable(args, fromCLI):
  """
  Works only on the local filesystem.
  Enables module of given name.
  "module" param is path relative to etc/modules, with dirs separted by colons.
  """
  paramsReq = (ARG_MODULE,)
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {}
  moduleName, modulePath = getNameAndPath(args[ARG_MODULE])
  currEnabled = os.path.exists(modulePath)

  if not currEnabled: # then enable it
    returnDict["restartRequired"] = True
    disabledPath = getDisabledPath(modulePath)
    if not os.path.exists(disabledPath):
      raise ConfigError("Could not find required file - looking for disabled config file at %s." % disabledPath)
    shutil.copy(disabledPath, modulePath)

  if fromCLI:
    if currEnabled:
      logger.info("%s is already enabled." % moduleName)
    else:
      logger.info("%s enabled." % moduleName)
  return returnDict


def localModuleDisable(args, fromCLI):
  """
  Works only on the local filesystem.
  Disables module of given name.
  "module" param is path relative to etc/modules, with dirs separted by colons.
  """
  paramsReq = (ARG_MODULE,)
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {}
  moduleName, modulePath = getNameAndPath(args[ARG_MODULE])
  currEnabled = os.path.exists(modulePath)

  if currEnabled: # then disable it
    returnDict["restartRequired"] = True
    disabledPath = getDisabledPath(modulePath)
    if os.path.exists(disabledPath):
      os.unlink(modulePath)
    else:
      shutil.move(modulePath, disabledPath)

  if fromCLI:
    if not currEnabled:
      logger.info("%s is already disabled." % moduleName)
    else:
      logger.info("%s disabled." % moduleName)
  return returnDict
