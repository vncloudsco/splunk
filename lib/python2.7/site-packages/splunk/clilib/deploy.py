from __future__ import absolute_import
#   Version 4.0
import logging as logger
import splunk.clilib.cli_common as comm
from splunk.clilib import control_exceptions as cex
from splunk.clilib import module, validate
import os, time, xml.dom.minidom
from splunk.clilib import bundle_paths


ARG_AUTHSTR     =  "authstr"
ARG_URI         =  "uri"

XML_CLASS       =  "class"
XML_CLASSES     =  "classes"
XML_CLASSNAME   =  "name"
XML_CLIENT      =  "client"
XML_HOSTNAME    =  "hostName"
XML_IPADDR      =  "ip"
XML_LASTUPDATE  =  "lastUpdateTime"
XML_REPHOSTNAME =  "reportedHostName"
XML_SRVCLASS    =  "serverClasses"
XML_TIMESTART   =  "timeStarted"
XML_TIMESENT    =  "timeSent"
XML_UPDATEATTR  =  "updateTime"

ARG_CLASS,       XML_CLASS       =  "class",           "class"
ARG_CLASSPATH,   XML_CLASSPATH   =  "class-path",      "serverClassPath"
ARG_DEPSERVURI,  XML_DEPSERVURI  =  "poll-uri",        "deploymentServerUri"
ARG_POLLFREQ,    XML_POLLFREQ    =  "poll-freq",       "pollingFrequency"

optionMapClient = {
  ARG_DEPSERVURI  : XML_DEPSERVURI,
  ARG_POLLFREQ    : XML_POLLFREQ
}

ERR_CLIENT_DIS   = "The Deployment Client module is not currently enabled."
ERR_CLI_STANZA   = "No client stanza found in '%s', your configuration may be corrupt." % module.DEPL_CLI_CONFIG

############################  DEPLOYMENT CLIENT OPTIONS ############################


def editClient(args, fromCLI):
  """
  Edits the various options of a deployment client.
  THIS WORKS ON THE LOCAL FILESYSTEM.  We usually don't want this,
  so this will only be used for certain options.
  """
  paramsReq = ()
  paramsOpt = tuple(optionMapClient.keys())
  comm.validateArgs(paramsReq, paramsOpt, args)

  returnDict = {}

  if 0 == len(args):
    raise cex.ArgError("No changes have been specified.")

  if not module.deplClientStatus({}, fromCLI)["enabled"]:
    raise cex.ServerState(ERR_CLIENT_DIS)

  
  currConf = comm.getMergedConf(module.DEPL_CLI_CONFIG)
  if not module.DEPL_CLI_STANZA in currConf:
    raise cex.ParsingError(ERR_CLI_STANZA)

  # assuming that we only support one of each of these tags - replace every tag found, and add if non-existent.
  for arg, val in list(args.items()):
    paramName = optionMapClient[arg]

    # validate the few types of args we recognize, ignore anything else.
    try:
      if arg == ARG_DEPSERVURI:
        validate.checkIPPortOrHostPort(arg, val)
      elif arg == ARG_POLLFREQ:
        validate.checkPosInt(arg, val)
    except cex.ValidationError:
      if "0" != val: # we use 0 to disable these things, i guess.
        raise

    # remove if 0.
    if "0" == val and paramName in currConf[module.DEPL_CLI_STANZA]:
      currConf[module.DEPL_CLI_STANZA].pop(paramName)
    # or add/set.
    else:
      currConf[module.DEPL_CLI_STANZA][paramName] = val

    # if we're at this point, *something* has changed.
    returnDict["restartRequired"] = True

  comm.writeConfFile(bundle_paths.make_path(module.DEPL_CLI_CONFIG + ".conf"), currConf)
  if fromCLI:
    logger.info("Configuration updated.")

  return returnDict


def ensureClientEnabled(fromCLI):
  if not module.deplClientStatus({}, fromCLI)["enabled"]:
    # make sure we relay fromCLI here intact.  want the messages from this to show up.
    module.deplClientEnable({}, fromCLI) 

def getPoll(args, fromCLI):
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  retDict  = {"enabled" : False}
  currConf = comm.getMergedConf(module.DEPL_CLI_CONFIG)
  try:
    retDict["uri"] = currConf[module.DEPL_CLI_STANZA][XML_DEPSERVURI]
    retDict["enabled"] = True
  except KeyError:
    pass

  if fromCLI:
    if retDict["enabled"]:
      logger.info("Deployment Server URI is set to \"%s\"." % retDict["uri"])
    else:
      logger.info("Deployment Server URI is not set.")
  return retDict

def setPoll(args, fromCLI):
  paramsReq = (ARG_URI,)
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  ensureClientEnabled(fromCLI)
  return editClient({ARG_DEPSERVURI : args[ARG_URI]}, fromCLI)
