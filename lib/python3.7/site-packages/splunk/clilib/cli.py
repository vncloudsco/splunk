from __future__ import absolute_import
from __future__ import print_function
from builtins import input

#   Version 4.0

# It's important that we set this ASAP.  when cli_commmon is imported, it will
# check for this setting existing in __main__ (whatever that is - for the CLI,
# that will be this file/module).  If present/False, it will run btool to get
# the latest splunk settings.  Otherwise, the cached var/run/splunk/merged/
# files would be used (which the UI relies on), and could potentially give the
# CLI old, outdated configs.
from builtins import object
from builtins import range

useCachedConfigs = False

import logging as logger
import logging.handlers
import os, sys, traceback, copy, stat
import xml.dom.minidom
import errno

import splunk.clilib.cli_common as comm
import splunk.clilib.control_api as ca
from splunk.clilib.control_exceptions import ArgError, AuthError, FilePath, SearchError, StopException,SuccessException
from splunk.clilib.control_exceptions import VersionError, PCLException
from splunk.clilib.literals import helpLong, hasHelp

from splunk.clilib import exports
from splunk.clilib import imports
from splunk.clilib import _internal
from splunk.clilib import manage_search as ms
from splunk.clilib import index

#### EAI CLI ####
import splunk
import splunk.auth as auth
from splunk.rcUtils import makeRestCall, CliArgError, NoEndpointError, InvalidStatusCodeError
from splunk import ResourceNotFound
from splunk.util import objUnicode
import time
import threading
if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from cStringIO import StringIO
import lxml.etree as etree
import socket
import subprocess

import splunk.clilib.log_handlers
import base64
import json

global timer_func

#cmd not suppoted: live-tail
 
#'stop', 'start', 'restart', 'status' and 'watchdog' are handled by the launcher
#list of commands which can be run locally if remote version is not available. Also, those cmds do NOT make any legacy invoke api calls except maybe one invokeapi call to determine if splunk is running or not
run_local = ['logout', 'activate', 'diag', 'diag2', 'diag3', 'diag4', 'diag5', 'diag6', 'clean', 'anonymize', '*:blacklist', 'export', 'find', 'import', 'validate', 'recover', 'resurrect', 'spool', 'test', 'train', 'unresurrect', 'extract', '*:module', 'migrate', '*:s2s-blacklist', '_internal', '*:fifo', '*:s2s', '*:auth-roles', 'display:web-ssl', 'display:webserver', 'live-tail', 'remove:index', 'bucket-maint']

#rpc
#remove:forward-server

# things we expect to be passed in
ARG_ACCEPT_LIC  = "-accept-license"
ARG_ANSWER_YES  = "-answer-yes"
ARG_AUTH        = "-auth"
ARG_TOKEN       = "-token"
ARG_DEBUG       = "-debug"
ARG_FORCE_SHORT = "-f"
ARG_FORCE_LONG  = "-force"
ARG_MULTIVAL    = "-multival"
ARG_NOPROMPT    = "-no-prompt"
ARG_QUIET       = "-quiet"
ARG_URI         = "-uri"
VALUE_SEPARATOR = ":"

# return codes from this script
ERR_NOERR        = 0
ERR_NUMARGS      = 1
ERR_UNKNOWN      = 2
ERR_AUTH         = 3
ERR_ARG          = 4
ERR_DOTSPLUNK    = 5
ERR_VERSION      = 6
ERR_PIPE         = 7
ERR_STOP         = 21
ERR_SPLUNKD_DOWN = 22
ERR_NO_ENDPOINT  = 23
ERR_INVALID_STATUS_CODE = 24
ERR_AUTH_TOKEN_XML = 25
ERR_REST          = 26
ERR_SPLUNKD       = 27
ERR_SUCCESS       = 28

# exception messages given to us by splunkd
MSG_INVALID_TOKEN = "User Session is not valid."
#### EAI CLI ####
#MSG_INVALID_TOKEN = "Client is not authenticated"

dotSplunk       = None
dotSplunkErr    = "Setting dir uninitialized."

ENV_AUTH_TOKEN  = "SPLUNK_TOK"
ENV_SPLUNK_TOKEN = "SPLUNK_AUTH_JWT"
ENV_DEBUG       = "SPLUNK_CLI_DEBUG"
ENV_URI         = "SPLUNK_URI"

def printHelp(args, fromCLI = False):
  paramsReq = ()
  paramsOpt = ("cmdname",)

  comm.validateArgs(paramsReq, paramsOpt, args)

  #
  # looks sane at this point.
  #

  if "cmdname" in args:
    cmd = args["cmdname"].lower()
    if hasHelp(cmd):
      logger.info(helpLong(cmd))
    else:
      logger.error("\nThere is no extended help for '%s'." % cmd)
      question = didYouMean(cmd)
      if question != None:
         logger.error(question)
  else:
    logger.info(helpLong("help"))


def list_commands(args, fromCLI = True):
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)

  mainCommands = sorted(cList.listCmds())
  logger.info("Available PCL commands (and applicable subcommands).  Note that this does not list commands that the bash script accepts (ie, splunk start).")
  logger.info("=" * 80)
  for oneCmd in mainCommands:
    logger.info("\n%s" % oneCmd)
    if cList.hasSubCmd(oneCmd):
      subCommands = sorted(cList.listSubCmds(oneCmd))
      logger.info("\t%s" % str.join(str(", "), subCommands))
    else:
      logger.info("\t(no subcommands)")


# -------------------------------------------
def user_friendly_login(username, password, save = False):
   """
   """
   global timer_func
   #wait_msg will be called after every 5 secs 
   timer_func = threading.Timer(5.0, wait_msg)
   timer_func.start()
   try:
      authToken =  auth.getSessionKey(username, password)
      timer_func.cancel()
      if authToken == None: #the SDK returns None for some reason if auth fails...
         raise splunk.AuthenticationFailed

      if save:
        try:
           # it's safer to chmod the file when it exists and is closed?
           try:
              authFile = open(getAuthFilePath(), 'w')
              authFile.close()
           except IOError:
              #SPL-25347, maybe we do not have permissions to write to this file, blow away the file and try again
              #if u cannot remove the file also, abort...
              os.unlink(getAuthFilePath())
              authFile = open(getAuthFilePath(), 'w')
              authFile.close()

           os.chmod(getAuthFilePath(), stat.S_IRUSR | stat.S_IWUSR) # mode 600 - don't want others getting our precioussssss auth token!
           authFile = open(getAuthFilePath(), 'w')

           # working: add some way of finding out whether .splunk is valid, and check that before using .splunk/authtoken, etc.
           auth_str = '<auth><username>%s</username><sessionkey>%s</sessionkey></auth>' % (username, authToken)
           authFile.write(auth_str)
           authFile.close()
        except OSError:
           logger.error("Could not write to auth token file '%s'." % getAuthFilePath())
           raise

      return authToken
   except:
      timer_func.cancel()
      raise

# --------------
def wait_msg():
   """
   """
   global timer_func
   print('please wait, attempting to login...')
   timer_func = threading.Timer(5.0, wait_msg)
   timer_func.start()

#----------------------------------
def print_login_banner():
  """
  query splunkd for the CLI login banner
  """
  uri = comm.getMgmtUri()
  if subprocess.call([os.path.join(os.environ["SPLUNK_HOME"], "bin", "splunk"), "banner", "-uri", uri]) != 0:
    sys.exit(ERR_SPLUNKD_DOWN)	# bin/splunk will already print an error message

#----------------------------------
def login(args, fromCLI = True):
  """
  changes for the new eai cli
  """
  if not dotSplunk:
    logger.error("Cannot save authentication token because Splunk settings directory is invalid.")
    sys.exit(ERR_DOTSPLUNK)
  
  print_login_banner()
  username  = input("Splunk username: ").strip()
  password  = comm.promptPassword("Password: ")
  #authToken = comm.getAuthInfo(username, password)
 
  #### EAI CLI ####
  authToken = user_friendly_login(username, password, save=True)

  """
  try:
    # it's safer to chmod the file when it exists and is closed?
    authFile = open(authPath, 'w')
    authFile.close()
    os.chmod(authPath, stat.S_IRUSR | stat.S_IWUSR) # mode 600 - don't want others getting our precioussssss auth token!
    authFile = open(authPath, 'w')

    # working: add some way of finding out whether .splunk is valid, and check that before using .splunk/authtoken, etc.
    auth_str = '<auth><username>%s</username><sessionkey>%s</sessionkey></auth>' % (username, authToken)
    authFile.write(auth_str)
    authFile.close()
  except OSError:
    logger.error("Could not write to auth token file '%s'." % authPath)
    raise
  """



def logout(args, fromCLI = True):
  if not os.path.exists(getAuthFilePath()):
    logger.info("Authentication session key does not exist - no logout needed.")
  else:
    try:
      comm.remove_file(getAuthFilePath())
    except OSError:
      logger.error("Unable to remove authentication session key file at '%s'." % getAuthFilePath())
      sys.exit(ERR_DOTSPLUNK)


class SplunkCmd(object):
  cmd  = subCmd = default = func = None
  auth = True
  pro  = False
  def __init__(self, command, subCommand, function, defArg = None, authReq = True, proReq = False, anonArgs = False, allSubCommandsApply = False,
      removed = False, redirect = None):
    """Sets up a command object with lots of helpers for determining command
    behavior via booleans and such."""
    if "" in (command, subCommand, defArg):
      raise ArgError("Creating new SplunkCmd, command names and default arg cannot be empty.")
    if anonArgs and (None != defArg):
      raise ArgError("U CANT SPECIFY DEFAULT ARG WHEN U HAS UNNAMD ARGS.  MAK UP UR MIND, KTHXBAI.") # only ever seen in-house :)
    else:
      self.cmd      = command
      self.subCmd   = subCommand
    self.anonArgs   = anonArgs
    self.deprecated = (None != redirect)
    self.default    = defArg
    self.func       = function
    self.pro        = proReq
    self.allSubCommandsApply = allSubCommandsApply
    self.removed    = removed
    self.auth       = (self.removed and (False,) or (authReq,))[0] # stupid python tricks.
    if self.deprecated:
      if 2 != len(redirect):
        raise ArgError("Commands that are being redirected should provide 2 strings.")
      self.redirect = redirect
  def argsAreUnnamed(self):
    return self.anonArgs
  def call(self, args, fromCLI = False):
    """Call the function that this maps to."""
    if self.isRemoved():
      raise ArgError("This command has been removed.")
    return self.func(args, fromCLI)
  def getCmdName(self):
    """Returns name of command."""
    return self.cmd
  def getDefaultArg(self):
    """Returns default argument name, or None if it doesn't exist."""
    return self.default
  def getRedirect(self):
    """Returns a 2-tuple of the command & subcommand to redirect to."""
    return self.redirect
  def getSubCmdName(self):
    """Returns name of subcommand, or None if it doesn't exist."""
    return self.subCmd
  def hasDefaultArg(self):
    """Returns boolean based on whether or not there is a default arg name for this command."""
    return self.default != None
  def hasSubCmd(self):
    """Returns boolean based on whether or not there are subcommands for this command."""
    return self.subCmd != None
  def isDeprecated(self):
    """Returns boolean based on whether or not the command redirects to another."""
    return self.deprecated
  def isRemoved(self):
    """Returns whether or not this command has been removed from the CLI."""
    return self.removed
  def reqAuth(self):
    """ Returns boolean based on whether or not this command requires authentication."""
    return self.auth
  def reqPro(self):
    """ Returns boolean based on whether or not this command requires the pro version of the product."""
    return self.pro


def didYouMean(command):
    import difflib
    # this sucks, but, self.cmdList.keys() doesn't seem to have a lot of these, like start and stop. someone clean up.
    commands = ["search", "login", "logout", "start", "stop", "restart", "status", "add", "edit", "list", "import", "export", "clean", "summary", "enable", "disable", "display", "train", "test", "validate", "anonymize", "find", "help", "diag", "dispatch", "getconf", "install", "migrate", "package", "recover", "refresh", "reload", "remove", "set", "show", "spool", "upgrade", "bootstrap", "rolling-restart"]
    matches = difflib.get_close_matches(command, commands) # self.cmdList.keys())
    text = "Did you mean the "
    count = len(matches)
    if count == 0 or (count == 1 and matches[0] == command):
        return None
    for i in range(0, count):
        if i > 0:
            if i == count-1:
              text += " or "
            else:
              text += ", "
        text += "'" + matches[i] + "'"
    text += " command"
    if count > 1:
         text+= "s"
    text += "? "
    return text

def diag2(a, b):
  print("We're taking this baby to the moooon.")
def diag3(a, b):
  print("Surely you jest.")
def diag4(a, b):
  print("Who's Shirley?")
def diag5(a, b):
  print("You stop it.")
def diag6(a, b):
  print("Vishal says get back to work.")

class CommandList(object):
  cmdList = {}
  #def __init__(self):
    #self.cmdList = []
  def addCmd(self, cmd):
    name = cmd.getCmdName()
    # command name already exists in our list
    if name in self.cmdList:
      existingHasSubCmd = isinstance(self.cmdList[name], dict)
      if cmd.hasSubCmd() != existingHasSubCmd:
        raise ArgError("Subcommand stuff doesn't match.  Either the existing command has a subcommand and the new one doesn't, or vice versa.")
      # new command has subcommand
      if cmd.hasSubCmd():
        self.cmdList[name][cmd.getSubCmdName()] = cmd
      else:
        self.cmdList[name] = cmd
    # entirely new command being added
    else:
      if cmd.hasSubCmd():
        self.cmdList[name] = {}
        self.cmdList[name][cmd.getSubCmdName()] = cmd
      else:
        self.cmdList[name] = cmd
  def hasCmd(self, cmdName):
    return cmdName in self.cmdList

  def hasSubCmd(self, cmdName):
    return isinstance(self.getCmd(cmdName), dict)

  #version for EAI CLI that does not do any argument checking, will be done at splunkd end
  #basically just like the original getCmd but one that never returns a ArgError
  def getCmdEAICLI(self, cmdName, subCmd = None):
    #if not cmdName in self.cmdList:
    #  logger.info("%s, %s" % (cmdName, subCmd))
    #  raise ArgError("Command '%s' does not exist." % cmdName)
    if not isinstance(self.cmdList[cmdName], dict) or not subCmd:
      return self.cmdList[cmdName]
    else:
      if not subCmd in self.cmdList[cmdName]:
        #raise ArgError("The subcommand '%s' is not valid for command '%s'." % (subCmd, cmdName))
        #return a SplunkCmd object created on the fly will lots of dummy info
        return SplunkCmd(cmdName, subCmd,  None, "dummy")
      return self.cmdList[cmdName][subCmd]

  def getCmd(self, cmdName, subCmd = None):
    if not cmdName in self.cmdList:
      logger.info("%s, %s" % (cmdName, subCmd))
      raise ArgError("Command '%s' does not exist." % cmdName)
    if isinstance(self.cmdList[cmdName], SplunkCmd) and self.cmdList[cmdName].allSubCommandsApply:
      return self.cmdList[cmdName]
    if not isinstance(self.cmdList[cmdName], dict) or not subCmd:
      return self.cmdList[cmdName]
    else:
      if not subCmd in self.cmdList[cmdName]:
        raise ArgError("The subcommand '%s' is not valid for command '%s'." % (subCmd, cmdName))
      return self.cmdList[cmdName][subCmd]
  def listCmds(self):
    ret = sorted(self.cmdList.keys())
    return ret
  def listSubCmds(self, name):
    subCmds = []
    if self.hasSubCmd(name):
      subCmds = list(self.cmdList[name].keys())
    return subCmds



cList = CommandList()
cList.addCmd(SplunkCmd("activate", None, None, removed = True, authReq = False))

cList.addCmd(SplunkCmd("add",    "auth-method",      None, "authType"))
cList.addCmd(SplunkCmd("add",    "blacklist",        None, "path", removed = True))
cList.addCmd(SplunkCmd("add",    "exec",             None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("add",    "fifo",             None, "source", removed = True))
cList.addCmd(SplunkCmd("add",    "forward-server",   None, "hostport"))
cList.addCmd(SplunkCmd("add",    "index",            None, "name", authReq = False))
cList.addCmd(SplunkCmd("add",    "monitor",          None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("add",    "saved-search",     None, "name"))
cList.addCmd(SplunkCmd("add",    "scripted",         None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("add",    "search-server",    None, "host"))
cList.addCmd(SplunkCmd("add",    "tail",             None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("add",    "tcp",              None, "source"))
cList.addCmd(SplunkCmd("add",    "udp",              None, "source"))
cList.addCmd(SplunkCmd("add",    "user",             None, "username", proReq = True))
cList.addCmd(SplunkCmd("add",    "watch",            None, redirect = ("add", "monitor")))

cList.addCmd(SplunkCmd("diag",   None,               ca.diagnose, authReq = False))
cList.addCmd(SplunkCmd("diag2",   None,              diag2, authReq = False))
cList.addCmd(SplunkCmd("diag3",   None,              diag3, authReq = False))
cList.addCmd(SplunkCmd("diag4",   None,              diag4, authReq = False))
cList.addCmd(SplunkCmd("diag5",   None,              diag5, authReq = False))
cList.addCmd(SplunkCmd("diag6",   None,              diag6, authReq = False))

# SPL-44064
cList.addCmd(SplunkCmd("upgrade", None,               None, removed = True, allSubCommandsApply = True))

cList.addCmd(SplunkCmd("install", "bundle",           None, removed = True))
cList.addCmd(SplunkCmd("package", "bundle",           None, removed = True))
# cList.addCmd(SplunkCmd("upgrade", "bundle",           None, removed = True))
cList.addCmd(SplunkCmd("remove",  "bundle",           None, removed = True))
cList.addCmd(SplunkCmd("list",    "bundle",           None, removed = True))
cList.addCmd(SplunkCmd("disable", "bundle",           None, removed = True))
cList.addCmd(SplunkCmd("enable",  "bundle",           None, removed = True))

cList.addCmd(SplunkCmd("edit",   "auth-method",      None, "authType"))
cList.addCmd(SplunkCmd("edit",   "deploy-client",    ca.deplClient_edit))
cList.addCmd(SplunkCmd("edit",   "exec",             None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("edit",   "fifo",             None, "source", removed = True))
cList.addCmd(SplunkCmd("edit",   "index",            None, "name", authReq = False))
cList.addCmd(SplunkCmd("edit",   "monitor",          None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("edit",   "s2s",              None, proReq = True, removed = True))
cList.addCmd(SplunkCmd("edit",   "saved-search",     None, "name"))
cList.addCmd(SplunkCmd("edit",   "search-server",    None, "url", proReq=True))
cList.addCmd(SplunkCmd("edit",   "scripted",         None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("edit",   "tail",             None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("edit",   "tcp",              None, "source"))
cList.addCmd(SplunkCmd("edit",   "user",             None, "username", proReq = True))
cList.addCmd(SplunkCmd("edit",   "udp",              None, "source"))
cList.addCmd(SplunkCmd("edit",   "watch",            None, redirect = ("edit", "monitor")))

cList.addCmd(SplunkCmd("list",   "auth-roles",       None, removed = True))
cList.addCmd(SplunkCmd("list",   "auth-method",      None))
cList.addCmd(SplunkCmd("list",   "blacklist",        None, removed = True))
cList.addCmd(SplunkCmd("list",   "deploy-clients",   None))
cList.addCmd(SplunkCmd("list",   "deploy-info",      None, removed = True))
cList.addCmd(SplunkCmd("list",   "exec",             None)) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("list",   "fifo",             None, removed = True))
cList.addCmd(SplunkCmd("list",   "forward-server",   None))
cList.addCmd(SplunkCmd("list",   "index",            None, "name", authReq = False))
cList.addCmd(SplunkCmd("list",   "monitor",          None)) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("list",   "role-mappings",    None))
cList.addCmd(SplunkCmd("list",   "saved-search",     None))
cList.addCmd(SplunkCmd("list",   "scripted",         None)) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("list",   "search-server",    None))
cList.addCmd(SplunkCmd("list",   "tail",             None)) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("list",   "tcp",              None))
cList.addCmd(SplunkCmd("list",   "udp",              None))
cList.addCmd(SplunkCmd("list",   "user",             None, proReq = True))
cList.addCmd(SplunkCmd("list",   "watch",            None, redirect = ("list", "monitor")))
cList.addCmd(SplunkCmd("list",   "jobs",             None))

cList.addCmd(SplunkCmd("migrate", "bundle",          ca.bundle_migrate, "name", authReq = False))
cList.addCmd(SplunkCmd("migrate", "win-searches",    ca.mig_winSavedSearch, authReq = False))

cList.addCmd(SplunkCmd("recover", None,              None, removed = True))

# SPL-30879
cList.addCmd(SplunkCmd("bucket-maint", "roll-hot-buckets", comm.rollHotBuckets))
cList.addCmd(SplunkCmd("bucket-maint", "rebuild-metadata", comm.rebuildMetadata))
cList.addCmd(SplunkCmd("bucket-maint", "rebuild-bucket-manifests", comm.rebuildBucketManifests))
cList.addCmd(SplunkCmd("bucket-maint", "rebuild-metadata-and-manifests", comm.rebuildMetadataAndManifests))

cList.addCmd(SplunkCmd("remove", "auth-method",    None, redirect = ("add", "auth-method")))
cList.addCmd(SplunkCmd("remove", "blacklist",        None, "path", removed = True))
cList.addCmd(SplunkCmd("remove", "exec",             None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("remove", "fifo",             None, "source", removed = True))
cList.addCmd(SplunkCmd("remove", "index",            None, "name", authReq = False, removed = True))

cList.addCmd(SplunkCmd("remove", "monitor",          None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("remove", "forward-server",   None, "hostport"))
cList.addCmd(SplunkCmd("remove", "saved-search",     None, "name"))
cList.addCmd(SplunkCmd("remove", "scripted",         None, "source")) # note: scripted and exec are currently identical.
cList.addCmd(SplunkCmd("remove", "search-server",    None, "url", proReq = True))
cList.addCmd(SplunkCmd("remove", "tail",             None, "source")) # note: tail and monitor are currently identical.
cList.addCmd(SplunkCmd("remove", "tcp",              None, "source"))
cList.addCmd(SplunkCmd("remove", "udp",              None, "source"))
cList.addCmd(SplunkCmd("remove", "user",             None, "username", proReq = True))
cList.addCmd(SplunkCmd("remove", "watch",            None, redirect = ("remove", "monitor")))

cList.addCmd(SplunkCmd("disable", "app",             ca.local_appDisable, "name", authReq = False))
cList.addCmd(SplunkCmd("disable", "deploy-client",   ca.deplClient_disable, authReq = False))
cList.addCmd(SplunkCmd("disable", "index",           None, "name", authReq = False))
cList.addCmd(SplunkCmd("disable", "local-index",     None))
cList.addCmd(SplunkCmd("disable", "dist-search",     None))

#SPL-22732
cList.addCmd(SplunkCmd("disable", "module",          None, "module", removed = True))

cList.addCmd(SplunkCmd("help",    None,              printHelp, "cmdname", authReq = False))

cList.addCmd(SplunkCmd("display", "app",             ca.local_appStatus, "name", authReq = False))
cList.addCmd(SplunkCmd("display", "deploy-client",   ca.deplClient_status, authReq = False, proReq = True))
cList.addCmd(SplunkCmd("display", "local-index",     None))
cList.addCmd(SplunkCmd("display", "dist-search",     None))

##SPL-22732
cList.addCmd(SplunkCmd("display", "module",          None, "module", removed = True))

cList.addCmd(SplunkCmd("help",    None,              printHelp, "cmdname", authReq = False))

cList.addCmd(SplunkCmd("display", "webserver",       None, removed = True))
cList.addCmd(SplunkCmd("display", "web-ssl",         None, removed = True))

cList.addCmd(SplunkCmd("enable", "app",              ca.local_appEnable, "name", authReq = False))
cList.addCmd(SplunkCmd("enable",  "deploy-client",   ca.deplClient_enable, authReq = False))
cList.addCmd(SplunkCmd("enable",  "index",           None, "name", authReq = False))
cList.addCmd(SplunkCmd("enable",  "local-index",     None))
cList.addCmd(SplunkCmd("enable",  "dist-search",     None))

#SPL-22732
cList.addCmd(SplunkCmd("enable", "module",          None, "module", removed = True))

cList.addCmd(SplunkCmd("export",  "eventdata",       ca.export_eventdata, "index", authReq = False))
cList.addCmd(SplunkCmd("export",  "globaldata",      None, removed = True))
cList.addCmd(SplunkCmd("export",  "userdata",        exports.exUserSplunk, "dir", authReq = False, proReq = True))
cList.addCmd(SplunkCmd("import",  "globaldata",      None, removed = True))
cList.addCmd(SplunkCmd("import",  "userdata",        imports.imUserSplunk, "dir", authReq = False, proReq = True))

# some of these are here for FTR's use on the local filesystem.  others for internal testing.
#cList.addCmd(SplunkCmd("_internal", "call",              comm.restCall, "path"))
#cList.addCmd(SplunkCmd("_internal", "check-xml-files",   ca.checkXmlFiles, "path", authReq = False))
cList.addCmd(SplunkCmd("_py_internal", "check-xml-files",   ca.checkXmlFiles, "path", authReq = False))
#cList.addCmd(SplunkCmd("_internal", "first-time-run",    ca.firstTimeRun, authReq = False))
cList.addCmd(SplunkCmd("_py_internal", "first-time-run",    ca.firstTimeRun, authReq = False))
cList.addCmd(SplunkCmd("_internal", "list-commands",     list_commands, authReq = False))
#cList.addCmd(SplunkCmd("_internal", "prefixcount",       None, removed = True))
#cList.addCmd(SplunkCmd("_internal", "pre-flight-checks", ca.preFlightChecks, authReq = False))
#cList.addCmd(SplunkCmd("_internal", "totalcount",        None, removed = True))
#SPL-28146
#cList.addCmd(SplunkCmd("_internal", "https",             ms.setLocalHttps, "port", authReq = False))
#cList.addCmd(SplunkCmd("_internal", "rpc",               None, redirect = ("_internal", "call")))
#cList.addCmd(SplunkCmd("_internal", "rpc-auth",          None, redirect = ("_internal", "call")))
#cList.addCmd(SplunkCmd("_internal", "soap-call",         None, redirect = ("_internal", "rpc")))
#cList.addCmd(SplunkCmd("_internal", "soap-call-auth",    None, redirect = ("_internal", "rpc-auth")))

cList.addCmd(SplunkCmd("live-tail", None, None, removed=True))

cList.addCmd(SplunkCmd("login",  None,               login, authReq = False, proReq = True))
#ported to C
#cList.addCmd(SplunkCmd("logout", None,               logout, authReq = False, proReq = True))
cList.addCmd(SplunkCmd("reload", "auth",             None))

cList.addCmd(SplunkCmd("refresh", "deploy-clients",  None))
cList.addCmd(SplunkCmd("reload",  "deploy-server",   None, "class", authReq=True))

cList.addCmd(SplunkCmd("search", None,               None, "terms"))
cList.addCmd(SplunkCmd("dispatch", None,             None, "terms"))
                       
cList.addCmd(SplunkCmd("set",  "auth-method",        None, redirect = ("add", "auth-method")))
cList.addCmd(SplunkCmd("set",  "server-type",        None, "name", authReq = False))
#EAI-CLI
cList.addCmd(SplunkCmd("set",  "datastore-dir",      None, "datastore-dir"))
cList.addCmd(SplunkCmd("set",  "deploy-poll",        ca.set_depPoll, "uri", authReq = False))
#EAI-CLI
cList.addCmd(SplunkCmd("set",  "default-hostname",   None, "default-hostname"))
cList.addCmd(SplunkCmd("set",  "default-index",      ca.set_defIndex, "value", authReq = False))
cList.addCmd(SplunkCmd("set",  "web-version",        ca.setUIVersion, "version"))
cList.addCmd(SplunkCmd("show", "auth-method",        None))
cList.addCmd(SplunkCmd("show", "config",             ca.showConfig, "name", authReq = False))
cList.addCmd(SplunkCmd("show", "datastore-dir",      None))
cList.addCmd(SplunkCmd("show", "default-index",      ca.get_defIndex, authReq = False))
cList.addCmd(SplunkCmd("show", "deploy-poll",        ca.get_depPoll, authReq = False))
cList.addCmd(SplunkCmd("show", "web-version",        ca.getUIVersion, authReq = False))

cList.addCmd(SplunkCmd("test", "dates",              ca.testDates, authReq = False, anonArgs = True))
cList.addCmd(SplunkCmd("test", "fields",             ca.testFields, authReq = False))
cList.addCmd(SplunkCmd("test", "sourcetype",         ca.testStypes, "file", authReq = False))
cList.addCmd(SplunkCmd("test", "system",             None, removed = True))

cList.addCmd(SplunkCmd("train", "dates",             ca.trainDates,  authReq = False))
cList.addCmd(SplunkCmd("train", "fields",            ca.trainFields, authReq = False))
cList.addCmd(SplunkCmd("train", "sourcetype",        None))

cList.addCmd(SplunkCmd('extract', 'i18n',            ca.i18n_extract, authReq = False))

cList.addCmd(SplunkCmd("create", "app",              None, "name", authReq = True))

cList.addCmd(SplunkCmd("show", "jobs",               None, "jobid", authReq = True))
cList.addCmd(SplunkCmd("display", "jobs",            None, "jobid", authReq = True))
cList.addCmd(SplunkCmd("remove", "jobs",             None, "jobid", authReq = True))
cList.addCmd(SplunkCmd("add", "oneshot",             None, "source", authReq = True))
cList.addCmd(SplunkCmd("edit", "app",                None, "name", authReq = True))
cList.addCmd(SplunkCmd("remove", "app",              None, "name", authReq = True))
cList.addCmd(SplunkCmd("enable",  "deploy-server",   None, "tenant", authReq = True))
cList.addCmd(SplunkCmd("disable",  "deploy-server",   None, "tenant", authReq = True))
cList.addCmd(SplunkCmd("display",  "deploy-server",   None, "tenant", authReq = True))
cList.addCmd(SplunkCmd("package",  "app",            None, "name", authReq = True))
cList.addCmd(SplunkCmd("bootstrap",    "shcluster-captain",    None, None))
cList.addCmd(SplunkCmd("rolling-restart", "shcluster-members", None, None))
cList.addCmd(SplunkCmd("rolling-restart", "cluster-peers", None, None))
cList.addCmd(SplunkCmd("upgrade-init", "cluster-peers", None, None))
cList.addCmd(SplunkCmd("upgrade-finalize", "cluster-peers", None, None))

def logCmdFailed(cmd, subCmd, args):
    eType, eValue = sys.exc_info()[0:2]
    # DO NOT change this to use '%' string formatting with value.message.
    # We want any embedded \n, \t, etc to be interpreted properly by print.
    err = ("\nAn error occurred: " + str('\n'.join(eValue.args)) \
        + "\nWhile running cmd: %s, subCmd: %s, args: %s." \
        + "\nPrinting debug info and backtrace:\n" \
        + "\tException: %s, Value: %s\n") % (cmd, subCmd, args, eType, eValue) \
        + traceback.format_exc()
    logger.error(err)

# Input is a string, output is bytes
def b64urldecode(data):
    if sys.version_info >= (3, 0):
        data = data.encode()
    missing_padding = len(data) % 4
    data += b'=' * (4 - missing_padding)
    return base64.urlsafe_b64decode(data)

# If a token is used on the CLI, deserialize the token string to obtain owner info
# from the subject header.
def get_token_subject(token):
    split_token = token.split('.')
    try:
        header = b64urldecode(split_token[0])
        payload = b64urldecode(split_token[1])
        signature = b64urldecode(split_token[2])
    except TypeError:
        logger.error("Unable to deserialize token information for the CLI command.")
        raise
    json.loads(header) # Just to verify it
    return json.loads(payload)['sub']

def parseAndRun(argsList):
  #### EAI CLI ####
  global run_local
  #######
  command = argsList[1].lower()
  if not cList.hasCmd(command):
     question = didYouMean(command)
     if question == None:
       raise ArgError("'%s' is not a valid command.  Please run 'splunk help' to see the valid commands.\n" % command)
     else:
       raise ArgError("'%s' is not a valid command. " % command + question)
  else:
    argList   = {}
    hasSubCmd = True
    subCmd    = None
    # whether we are using a JWT to authenticate user
    usingToken = False
    username  = password = tokenVal = authInfo = defArg = retVal = passcode =  None

    #
    #
    # for most commands, any passed in parameters will start at the 3rd position.
    # this gets adjusted for commands that don't have sub-commands.  after figuring
    # this out, also get the sub-command for use below.
    #
    #

    hasSubCmd = cList.hasSubCmd(command)
    if not hasSubCmd:
      startOfParams = 2
    else:
      startOfParams = 3
      subCmdStr = "Please type \"splunk help %s\" for usage and examples." % command
      if len(argsList) < startOfParams:
        raise ArgError("Additional arguments are needed for the '%s' command.  %s" % (command, subCmdStr))
      else:
        subCmd = argsList[2].lower()
        #### EAI CLI ####
        #we don't want to do any arg checking here, will be done at splund
       
        try:
          cList.getCmd(command, subCmd)
        except ArgError:
          raise ArgError("'%s' is not a valid argument for the '%s' command.  %s" % (subCmd, command, subCmdStr))
       

    #### EAI CLI ####
    #moved this snippet of code downstairs when we are attempting the local version
    #for remote version, splunkd will provide this info
    """
    targetCmd = cList.getCmd(command, subCmd)
    if targetCmd.isDeprecated():
      command, subCmd = targetCmd.getRedirect()
      redirStr = "%s%s" % (command, ((None != subCmd) and (" %s" % subCmd) or ""))
      raise ArgError("This command is deprecated.  Instead, use '%s'." % redirStr)
    """
    targetCmd = cList.getCmdEAICLI(command, subCmd)
    
    defArg    = targetCmd.getDefaultArg()

    #
    # Is this an auth-requiring command?
    #
    noAuthReq = not targetCmd.reqAuth() # heh.. 'not' to match old var name.

    def getNextArg(currArg, args, currArgNum, numArgs):
      # make sure a param after this exists so we can get the value
      if not currArgNum < (numArgs - 1):
        raise ArgError("The parameter '%s' must be followed by a value, in the form '-parameter value'." % currArg)
      return args[currArgNum + 1]
    def addParamValue(argList, argName, argVal, isMultival):
      if argName in argList and isMultival:
        if not isinstance(argList[argName], list):
          argList[argName] = [argList[argName]]
        argList[argName].append(argVal)
      else:
        argList[argName] = argVal
    #
    #
    # any args past the mode & subcommand?  if so, shove them all into a dict.
    #
    #
    if command != "diag" and len(argsList) > startOfParams:
      multiVal = ARG_MULTIVAL in argsList # allow multiple values per argument.

      paramList  = argsList[startOfParams:]
      paramCount = len(paramList)
      skipNext = False # used for skipping the parameter values on the next iteration..
      foundDef = False # whether or not we've found the one default paramter for a command.
      anonArgs = targetCmd.argsAreUnnamed() # "splunk foo x y z" vs "splunk foo -x a -y b -z c"
      numAnons = 0     # number of unnamed arguments, used for inserting into argList.
      for paramNum in range(0, paramCount):
        if skipNext:
          skipNext = False
          continue
        param = paramList[paramNum] # current working argument
        #
        # begin by handling any special parameters
        #
        if param in (ARG_FORCE_SHORT, ARG_FORCE_LONG):
          argList["force"] = True
        elif param == ARG_ANSWER_YES:
          comm.answerYes = True
        elif param == ARG_ACCEPT_LIC:
          comm.acceptLic = True
        elif param == ARG_AUTH:
          value = getNextArg(param, paramList, paramNum, paramCount)
          if value.count(VALUE_SEPARATOR) > 0:
            # only split once, password can have ":" in it.
            username, password = value.split(VALUE_SEPARATOR, 1)
          else: # no password specified
            username = value
          skipNext = True
        elif param == ARG_TOKEN:
          value = getNextArg(param, paramList, paramNum, paramCount)
          tokenVal = value
          skipNext = True
        elif param == ARG_NOPROMPT:
          comm.isNoPrompt = True
        elif param == ARG_QUIET:
          comm.ninjaMode = True
        elif param == ARG_URI:
          value = getNextArg(param, paramList, paramNum, paramCount)
          ca.set_uri(value)
          skipNext = True
        elif param == ARG_MULTIVAL:
          continue # we already handled this one by this point.
        elif param == ARG_DEBUG:
          continue # we already handled this one by this point.
        #
        # now handle the "real" args, ones that matter to the functions being called.
        #
        else:
          if anonArgs:
            argList[numAnons] = param
            numAnons += 1
          else:
            # make sure we let empty args fall through to the else..
            if (len(param) > 0) and param[0] == "-":
              paramName = param[1:]
              value = getNextArg(param, paramList, paramNum, paramCount)
              skipNext = True
              addParamValue(argList, paramName, value, multiVal)
              if paramName == defArg: # set this cuz the user could do
                foundDef = True       # "cmd -defArg blah blah" and the 2nd would override the defArg
            else:
              if foundDef or not defArg:
                raise ArgError("The argument '%s' is invalid.  Arguments must be specified in the form '-argument value'." % param)
              else:
                addParamValue(argList, defArg, param, multiVal)
                foundDef = True
            #SPL-75246 ugly hack to let cli accept class when /deployment/server/config/_reload accept
            #serverclass. There's no better way I can think of to make this work 
            if command == "reload" and subCmd == "deploy-server":
                argList2={}
                for argument, value in argList.items():
                    if argument == "class":
                        argList2["serverclass"]=value
                    else:
                        argList2[argument]=value
                argList=argList2

    # toss out the parsed args if in debug mode
    logger.debug("Command: %s" % command)
    logger.debug("Subcmd:  %s" % (None != subCmd and subCmd or "(none)"))
    logger.debug("Begin parsed arguments:")
    logger.debug(str.join(str("\n"), ["  \"%s\" = \"%s\"" % (arg, val) for arg, val in argList.items()]))
    logger.debug("End parsed arguments.\n\n")

    #
    # Does this command require the pro server?
    # it doesn't matter what the default here is, just setting it True.
    # we only use it to provide graceful errors, anyway.
    #

    #### EAI CLI ####
    #all pro/free checks to be done at splunkd
    """
    isProVersion = True
    # best to check this only if necessary.  if the server's down, we don't want exceptions.
    if (not noAuthReq) or targetCmd.reqPro():
      isProVersion = comm.isProVersion()

    logger.debug('isProVersion:%s' % str(isProVersion))

    try:
      if targetCmd.reqPro() and not isProVersion:
        raise VersionError("This command is not available with the free Splunk license.")
    except comm.ServerState:  # we don't care if splunkd is down - pro features
      pass                    # won't even be attempted in such a case
    """

    #
    # if user/pass isn't set explicitly above, try getting it from the environment
    #
    if not username: # safe enough - no need to support empty username (see password comment)
      if "SPLUNK_USERNAME" in os.environ:
        username = os.environ["SPLUNK_USERNAME"]
    if password == None: # don't just do a bool test of password, cuz empty pass is false
      if "SPLUNK_PASSWORD" in os.environ:
        password = os.environ["SPLUNK_PASSWORD"]

    if passcode == None: # passcode for RSA 2FA
      if "SPLUNK_PASSCODE" in os.environ:
        passcode = os.environ["SPLUNK_PASSCODE"]

    logger.debug('noAuthReq: %s', noAuthReq)
    #logger.debug('isProVersion: %s', isProVersion)



    # Are we pro?  If so, do we have the user/pass?  If so, get the auth token so we can pass it in.
    if not noAuthReq:
        #
        # if we have a username but no password, from any source, then prompt for password.
        # of course, this is the only really secure way to get a password.
        # TODO: should we accept password from mode 600 file, like rsync?  secure enough..
        #
        logger.debug('username: %s', username)
        logger.debug('password: %s', password)

        if username and password == None:
          print_login_banner()
          password = comm.promptPassword("\nPlease enter the password for Splunk user '%s': " % username)
        if username and password != None:
          #authInfo = comm.getAuthInfo(username, password)
          #### EAI CLI ####
          #authInfo = auth.getSessionKey(username, password)
          authInfo = user_friendly_login(username, password)
        elif tokenVal != None:
          # if we haven't seen a username and password passed in, we'll look for
          # the '-token' param value and set the authInfo to the JWT string.
          authInfo = tokenVal
          # no username/password found, so we will use a JWT if one is provided.
          usingToken = True
        else:
          # before prompting about needing auth, let's see if the auth token is in our environment.
          if ENV_AUTH_TOKEN in os.environ:
            authInfo = os.environ[ENV_AUTH_TOKEN]
          elif ENV_SPLUNK_TOKEN in os.environ:
            authInfo = os.environ[ENV_SPLUNK_TOKEN]
            usingToken = True
          else:
            # before prompting about needing auth, let's see if the auth token is cached.
            authInfo = readAuthToken()
          
          if not authInfo:
             #try prompting the use as a last resort
             login({}, True)
             authInfo = readAuthToken()

          if not authInfo: # looks like we don't have a cached auth token.  give up.. right... about.... now!
            raise AuthError("Splunk requires authentication for this command.  Please see \"splunk help\".")


        # if we're not pro, then send an empty string - the modules expect this variable anyway.
        #else:
          #authInfo = ""
        argList["authstr"] = authInfo
        if usingToken: 
            argList["owner"] = get_token_subject(authInfo)

    #
    #
    # finally, run the appropriate command (w/ loops to handle invalid user sessions)
    #
    #
    logger.debug('authInfo: %s', authInfo)

    authWorked = False
    # if the command fails due to anything other than invalid session, this loop will terminate.
    # it is meant to only succeed when the command results in no exception.
    while not authWorked:
      #try:
      #the 'check-xml-files', 'pre-flight-checks' are not intended to be accessed by the outside world
      if not (command in ['login', 'diag'] or subCmd in ['check-xml-files', 'pre-flight-checks', 'first-time-run']):
           timeout = None
           if "timeout" in argList:
              try:
                  timeout = int(argList["timeout"])
              except ValueError as e:
                  timeout = None
              del argList["timeout"]
           try:

              #if no auth is required and it is NOT a local command
              if noAuthReq and not (command in run_local or '%s:%s' % (command, subCmd) in run_local or '*:%s' % (subCmd) in run_local):
                 #this means that for the local version no auth was needed. But the remote version always needs one
                 if username and password != None:
                    #authInfo = auth.getSessionKey(username, password)
                    authInfo = user_friendly_login(username, password)
                 else:
                    authInfo = readAuthToken()

 
              #make eai cli call

              #if an 'owner' parameter is not provided, default to the current logged in user...
              if 'owner' not in argList: argList['owner'] = auth.getCurrentUser()['name']
              retVal = makeRestCall(cmd=command, obj=subCmd,
                                    restArgList=objUnicode(argList),
                                    sessionKey=authInfo, dotSplunk=dotSplunk,
                                    timeout=timeout, token=usingToken)
              authWorked = True # if no exception thrown...
           except splunk.AuthenticationFailed as e:
              type, value, tb = sys.exc_info()
              # we ONLY want to handle invalid session errors here
              #EAi CLI, always ask at least once more to login
              #if value.message == MSG_INVALID_TOKEN: # must re-login

              #if we're using a JWT and failed authentication, raise an error. don't retry.
              if usingToken:
                   raise
              logger.error("Your session is invalid.  Please login.")
              loginSuccessful = False
              # loop the login until the user succeeds
              while not loginSuccessful:
                   try:
                      login({}, True)
                      authInfo = readAuthToken()
                      loginSuccessful = True # if no exception thrown...
                      # login will store the auth token in the file, so get it out of there now.
                      argList["authstr"] = readAuthToken()
                      logger.info("Login successful, running command...")

                      #if an 'owner' parameter is not provided, default to the current logged in user...
                      if 'owner' not in argList: argList['owner'] = auth.getCurrentUser()['name']

                      retVal = makeRestCall(cmd=command, obj=subCmd, restArgList=objUnicode(argList), sessionKey=authInfo, timeout=timeout)
                      authWorked = True # if no exception thrown...
                   except splunk.AuthenticationFailed as e:
                      #logger.error("\nAn authentication error occurred: " + '\n'.join(e.args) + "\nAborting...")
                      loginSuccessful = False
                      raise
                   except:
                      raise # let this be handled elsewhere
              #else:
              #   raise # let this be handled elsewhere
           ########
 
           except splunk.RESTException as e:
              raise e
           except (CliArgError, InvalidStatusCodeError) as e:
              raise e
           except NoEndpointError as e:
              logger.debug('Remote cli command not available, trying local version')

              #before you go ahead, perform the check that we skipped upstairs for remote version
              targetCmd = cList.getCmd(command, subCmd)
              if targetCmd.isRemoved():
                print("This command has been removed.")
                sys.exit()
              if targetCmd.isDeprecated():
                 command, subCmd = targetCmd.getRedirect()
                 redirStr = "%s%s" % (command, ((None != subCmd) and (" %s" % subCmd) or ""))
                 raise ArgError("This command is deprecated.  Instead, use '%s'." % redirStr)

              if command in run_local or '%s:%s' % (command, subCmd) in run_local or '*:%s' % (subCmd) in run_local:
                 #no need of owner arg when running local
                 if 'owner' in argList:
                    argList.pop('owner')
                 logger.debug('cmd: %s, obj: %s, argList: %s' % (command, subCmd, str(argList)))
                 #no eai call and is allowed to be run locally, so drop down into local cli and do as before...

                 try:
                   retVal = cList.getCmd(command, subCmd).call(argList, fromCLI = True)
                   authWorked = True # if no exception thrown...
                 except:
                   if comm.isWindows:
                     # SPL-152536 Always use exit code 2 on failed cmd.
                     logger.warn("Failed cli cmd %s" % command)
                     if comm.debugMode:
                       logCmdFailed(command, subCmd, argsList)
                     sys.exit(2)

                   else:
                     raise
              else:
                 logger.debug(str(e))
                 #we don't need to see the session key in the error msg, so pop it out
                 if 'authstr' in argList:
                    argList.pop('authstr')
                 logger.error('The cmd "%s %s %s" is currently not supported in the CLI' % (command, subCmd, ' '.join(['-%s %s' % (x[0], x[1]) for x in argList.items()])  ))
                 raise e
      else:
           try:
             retVal = cList.getCmd(command, subCmd).call(argList, fromCLI = True)
             authWorked = True # if no exception thrown...
           except:
             if comm.isWindows:
               logger.warn("Failed cli cmd %s" % command)
               if comm.debugMode:
                 logCmdFailed(command, subCmd, argsList)
               sys.exit(2)
             else:
               raise
    if isinstance(retVal, dict):
      if "restartRequired" in retVal:
        logger.info("You need to restart the Splunk Server for your changes to take effect.")

"""
# ----------------------
def readUserName(path):

   authInfo = None
   try:
    authFile  = open(path, 'r')
    authToken = authFile.read()

    logger.debug('In function readUserName, Contents of ./splunk/authToken file: %s' % authToken)

    if len(authToken) > 1: # probably always have 1 because of newline char.
      tree = etree.parse(StringIO(authToken))
      s = tree.find('username')
      if s != None:
         authInfo = s.text
    authFile.close()
   except (OSError, IOError) as e:
    logger.debug(str(e))
    pass # so we couldn't find an auth token file...

   logger.debug('Username: %s' % authInfo)
   return authInfo
"""

# ------------------------
def readAuthToken():
  path = getAuthFilePath()
  authInfo = None
  try:
    authFile  = open(path, 'r')
    authToken = authFile.read()

    logger.debug('Contents of ./splunk/authToken file: %s' % authToken)

    if len(authToken) > 1: # probably always have 1 because of newline char.
      tree = etree.parse(StringIO(authToken))
      s = tree.find('sessionkey')
      if s != None:
         authInfo = s.text

      #just to be sure, set the defaul user also
      u = tree.find('username')
      if u != None:
         splunk.setDefault('username', u.text)

    authFile.close()
  except (OSError, IOError):
    pass # so we couldn't find an auth token file...
  except etree.XMLSyntaxError as e:
     logger.debug('Invalid xml format encountered in authToken file. Blowing away the ./splunk/authToken file and prompting user to login again...')
     try:
        comm.remove_file(path)
     except OSError:
        logger.error("Unable to remove old authentication session key file at '%s'." % path)
        sys.exit(ERR_DOTSPLUNK)
     #raise e

  return authInfo
 

def initGlobals():
  """
  we want to set this up at start so it's only done once, but not
  throw errors unless they're relevant to the user.
  """
  global dotSplunk, dotSplunkErr

  if sys.platform == "win32":
    homeEnvVar = "HOMEPATH"
  else:
    homeEnvVar = "HOME"

  # find out whether .splunk exists, is usable, etc.  set the global dotSplunk appropriately.
  try:
    userHome = os.environ[homeEnvVar]
    if sys.platform == "win32":
      userHomePrefix = os.environ.get("HOMESHARE")
      if userHomePrefix is None or userHomePrefix == "":
        homeEnvVar = "HOMEDRIVE"
        userHomePrefix = os.environ[homeEnvVar]
        userHome = os.path.join(userHomePrefix, userHome)
      else:
        # When HOMESHARE is set to UNC share, and userHome starts with '\' (resembling absolute path)
        userHome = os.path.join(userHomePrefix, userHome.strip("\\"))
    dotSplunk = os.path.join(userHome, ".splunk") # this is set to None below if the .splunk dir is not usable.
    if not os.path.exists(dotSplunk):
      os.mkdir(dotSplunk)
    else:
      if not os.path.isdir(dotSplunk):
        dotSplunkErr = "Splunk settings directory '%s' exists, but is not a directory." % dotSplunk
        dotSplunk    = None
  except KeyError:
    dotSplunkErr = "Could not determine user's home directory because %s shell variable is not set." % homeEnvVar
    dotSplunk    = None
  except OSError:
    dotSplunkErr = "Could not create Splunk settings directory at '%s'." % dotSplunk
    dotSplunk    = None


def getAuthFilePath():
  hostname = socket.gethostname()
  for ch in "/<>:\\|?*":
    hostname = hostname.replace(ch, '_')

  port = splunk.getDefault('port')

  return os.path.join(getSettingsDir(), "authToken_%s_%s" % (hostname, port))

def getSettingsDir():
  if None != dotSplunk:
    return dotSplunk
  raise FilePath(dotSplunkErr)

# returns path to the message file to be used for logging to an event log
def getMessageFileName():
  debug_dll   = os.path.join(comm.splunk_home, "bin", "win32service_d.pyd")
  release_dll = os.path.join(comm.splunk_home, "bin", "win32service.pyd")
  if os.path.exists(debug_dll):
    return debug_dll
  return release_dll

def main(argsList):
  initGlobals()

  if len(argsList) < 2:
    logger.error("\nNot enough arguments.  Please specify a valid command from this list:")
    printHelp({}, fromCLI = False)
    return ERR_NUMARGS
  else:
    try:
      parseAndRun(argsList)

    except ArgError:
      type, value, tb = sys.exc_info()

      logger.error("\nCommand error: " + '\n'.join(value.args))
      return ERR_ARG

    #except (AuthError, comm.AuthError):   # FIXME: exception namespaces..
    #### EAI CLI ####
    except splunk.AuthenticationFailed: 
      type, value, tb = sys.exc_info()
      logger.error("\nAn authentication error occurred: " + '\n'.join(value.args))
      return ERR_AUTH

    #if it's caus of a broken pipe, just ignore that exception #SPL-25699
    except IOError as e:
       if e.errno == errno.EPIPE:
           logger.debug(str(e))
       else:
          raise # just as before
 
    except (KeyboardInterrupt, SystemExit):
      raise # let these through because other parts may use it

    except SearchError:
      type, value, tb = sys.exc_info()
      logger.error("\nAn error occurred during search: " + '\n'.join(value.args))

    except splunk.SearchException:
      type, value, tb = sys.exc_info()
      logger.error("\nAn error occurred during search: " + '\n'.join(value.args))

    except StopException as e:
      logger.notice("\n" + '\n'.join(e.args))
      return ERR_STOP

    except SuccessException as e:
      logger.notice("\n" + '\n'.join(e.args))
      return ERR_SUCCESS

    except VersionError as e:
      logger.error('\n'.join(e.args))
      return ERR_VERSION

    # catch-all for our exceptions, if they're not handled specially above.
    except (PCLException, comm.PCLException):
      type, value, tb = sys.exc_info()
      # DO NOT change this to use '%' string formatting with value.message.
      # We want any embedded \n, \t, etc to be interpreted properly by print.
      logger.error("\nAn error occurred: " + str('\n'.join(value.args)))
      if comm.debugMode:
        logger.error("Printing debug info and backtrace:\n")
        logger.error("\tException: %s, Value: %s\n" % (type, value))
        logger.error(traceback.format_exc())
      return ERR_UNKNOWN

    #### EAI CLI ####

    #SPL-23125 - make error messages cleaner. Show more stuff only in debug mode

    except splunk.SplunkdConnectionException as e:
       logger.debug('\nAn error occurred:\n' + '\n'.join(e.args))
       #why don't we save the returned status code in the error objects???
       #SPL-55271 Adding an extra check for winsock error code 10061, since windows chooses to refuse connection differently.
       if e.args[0].find('Connection refused') != -1 or e.args[0].find('10061') != -1:
          logger.error('Splunk is not running, and it must be for this operation. To start splunk, run "splunk start". For more help, use "splunk help"')
       return ERR_SPLUNKD_DOWN

    except NoEndpointError as e:
       logger.debug('\nAn error occurred:\n' + '\n'.join(e.args))
       logger.error('Please check the command being executed. It is invalid.')
       return ERR_NO_ENDPOINT

    except CliArgError as e:
       logger.error('\nAn error occurred:\n' + '\n'.join(e.args))
       return ERR_ARG

    except InvalidStatusCodeError as e:
       logger.error('\nAn error occurred:\n' + '\n'.join(e.args))
       return ERR_INVALID_STATUS_CODE

    except ResourceNotFound as e:
       logger.error('The uri does not exists: ' + str(e))
       return ERR_NO_ENDPOINT 

    except splunk.RESTException as e:
       logger.error('\n'.join(e.args))
       logger.debug('\n' + str(e))
       return ERR_REST

    except etree.XMLSyntaxError as e:
       logger.debug(str(e))
       logger.error('Invalid xml format encountered in authToken file. To rectify: try ./splunk logout; and then retry your command')
       return ERR_AUTH_TOKEN_XML 

    #SPL-24352
    except splunk.SplunkdException as e:
       logger.debug(str(e))
       logger.error('\n'.join(e.args))
       return ERR_SPLUNKD 

    # python exception.  print whatever we can, including a backtrace..
    except:
      type, value, tb = sys.exc_info()
      logger.error("\nAn unforeseen error occurred:\n")
      logger.error("\tException: %s, Value: %s\n" % (type, value))
      logger.error(traceback.format_exc())
      logger.error("\nPlease file a case online at http://www.splunk.com/page/submit_issue\n")
      return ERR_UNKNOWN

    return ERR_NOERR


if __name__ == "__main__":
  # this is out here in case someone ^C's during the main() block 
  try:
    # start by setting up logging.  we don't always do this in case someone has imported us,
    # like from the appserver.  best to only do this when we're run directly.

    # handle the debug arg as soon as possible, so we can do the right thing.
    if ARG_DEBUG in sys.argv or ENV_DEBUG in os.environ:
      comm.debugMode = True
    if ENV_URI in os.environ:
      ca.set_uri(os.environ[ENV_URI])

    # set this pretty much undocumented variable to 0, so the logging stuff doesn't just print tons
    # of exceptions when logs are going to a pipe and the pipe closes (ie, | head).  dunno who the
    # hell thought it was a good idea to just let this thing print via traceback.print_exception,
    # instead of raising a real exception, but it's kinda lame. </rant>
    logger.raiseExceptions = 0
    logger.getLogger().setLevel(comm.debugMode and logger.DEBUG or logger.INFO)
    # "normal" logs, aka just info statements, go to stdout.  all else to stderr.
    stdout_logger = comm.newLogHandler(sys.stdout, comm.debugMode, normal = True)
    stderr_logger = comm.newLogHandler(sys.stderr, comm.debugMode, normal = False)
    logger.getLogger().addHandler(stdout_logger)
    logger.getLogger().addHandler(stderr_logger)
    # these get retained in case they need to be switched off
    splunk.clilib.log_handlers.add('stdout', stdout_logger)
    splunk.clilib.log_handlers.add('stderr', stderr_logger)
    if not comm.isTerminal:
      # we're probably running headless, or at least non-interactively.
      if comm.isWindows:
        logger.getLogger().addHandler(logging.handlers.NTEventLogHandler("Splunk Utility", getMessageFileName()))

    # notify of debug status after all logging is setup.
    logger.debug("Running in debug mode.\n")
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    logger.error("\nKilled via Ctrl-C.")
    sys.exit(ERR_NOERR)
  # this exception seems to be thrown mainly when you're piping the output and the pipe is bad - ie, piping
  # to a non-existing command.  can't reliably do anything here.  if both stdout AND stderr are screwed,
  # then printing an error will result in more exceptions.  let the shell or something report the error.
  except IOError:
    # if this is really a pipe error, these writes may fail too.  don't barf.
    try:
      type, value, tb = sys.exc_info()
      logger.error("\nAn unforeseen error occurred:\n")
      logger.error("\tException: %s, Value: %s\n" % (type, value))
      logger.error(traceback.format_exc())
      logger.error("Please file a case online at http://www.splunk.com/page/submit_issue\n")
    except:
      pass
    sys.exit(ERR_PIPE)
