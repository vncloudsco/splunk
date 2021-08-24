from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import range
from builtins import filter
import logging as logger
import splunk

import splunk.clilib.cli_common as comm
from splunk.clilib import control_exceptions as cex

import xml.etree.cElementTree as et
import xml.dom.minidom

import copy, filecmp, os, re, shutil, subprocess, sys, tarfile, time, traceback
from splunk.clilib import dbmanipulator_lib

import splunk.clilib.bundle_paths as bundle_paths
from splunk.clilib.bundle_paths import make_splunkhome_path

from future.moves.urllib import parse as urllib_parse

import glob

from splunk.clilib.migration_helpers import field_actions, app_maps



ARG_DRYRUN           = 'dry-run'
ARG_NOWAIT           = 'no-wait'

PERMS_OWNER_RW_ONLY = '600'

EMPTY_LINE     = "\n"

BACKUP_EXT     = "-migrate.bak"

STANZA_MIG_HISTORY   = 'history'

CONF_COMMANDS        = "commands"
CONF_SAVEDSEARCHES   = "savedsearches"
CONF_PROPS           = "props"

EXT_MIGRATE          = "migratePreview"
EXT_DEPRECATED       = "deprecated"
SUF_MIGRATE          = "." + EXT_MIGRATE

KEY_GUID             = "guid"
KEY_LAST_MIG_VERSION = "lastVersionMigratedTo"

PATH_APPS_DIR         = make_splunkhome_path(["etc", "apps"])

PATH_ETC_DIR          = make_splunkhome_path(["etc"])
PATH_SHARE_DIR        = make_splunkhome_path(["share"])

PATH_LOG_DIR          = make_splunkhome_path(["var", "log", "splunk"])
PATH_VERSION_FILE     = make_splunkhome_path(["etc", "splunk.version"])

PATH_LICENSE_ACTIVE   = make_splunkhome_path(["etc", "splunk.license"])
PATH_LICENSE_FREE     = make_splunkhome_path(["etc", "splunk-enttrial.license"])
PATH_LICENSE_USER     = make_splunkhome_path(["etc", "splunk-user.license"])

PATH_AUTHEN_CONF_OLD  = bundle_paths.make_path("auth.conf")
PATH_AUTHEN_CONF_BAK  = PATH_AUTHEN_CONF_OLD + BACKUP_EXT
PATH_AUTHEN_CONF_NEW  = bundle_paths.make_path("authentication.conf")

PATH_INPUTS_CONF      = bundle_paths.make_path("inputs.conf")
PATH_INDEXES_CONF     = bundle_paths.make_path("indexes.conf")
PATH_DISTSEARCH_CONF  = bundle_paths.make_path("distsearch.conf")

PATH_SPLUNKD_XML     = make_splunkhome_path(["etc", "myinstall", "splunkd.xml"])
PATH_SPLUNKD_XML_BAK = make_splunkhome_path(["etc", "myinstall", "splunkd.xml-migrate.bak"])
PATH_SPLUNKD_XML_DEF = make_splunkhome_path(["etc", "myinstall", "splunkd.xml.cfg-default"])

PATH_SEARCH_NAV_XML_OLD = make_splunkhome_path(['etc', 'apps', 'search', 'local', 'data', 'ui', 'nav', 'default.xml'])
PATH_SEARCH_NAV_XML_NEW = make_splunkhome_path(['etc', 'apps', 'search', 'local', 'data', 'ui', 'nav', 'old_default.xml'])

PATH_LDAP_CONF       = make_splunkhome_path(["etc", "openldap", "ldap.conf"])
PATH_LDAP_CONF_DEF   = make_splunkhome_path(["etc", "openldap", "ldap.conf.default"])

PATH_BATCHCONF_XML   = make_splunkhome_path(["etc", "modules", "input", "batchfile", "config.xml"])
PATH_BATCHCONF_DIS   = PATH_BATCHCONF_XML + ".upgraded"

PATH_TXN_TYPES_CONF   = bundle_paths.make_path("transactiontypes.conf")
PATH_SAVSRCH_CONF     = bundle_paths.make_path("savedsearches.conf")
PATH_EVTTYPE_CONF     = bundle_paths.make_path("eventtypes.conf")
PATH_TAGS_CONF        = bundle_paths.make_path("tags.conf")
PATH_PROPS_CONF       = bundle_paths.make_path("props.conf")
PATH_SECRET_FILE      = make_splunkhome_path(["etc", "splunk.secret"])

PATH_PASSWD_FILE     = make_splunkhome_path(["etc", "passwd"])
PATH_PASSWD_BAK_FILE = make_splunkhome_path(["etc", "passwd.bak"])

PATH_OLD_DEF_BUNDLES = make_splunkhome_path(["etc", "bundles", "default"])

PATH_AUTHORIZE_CONF  = bundle_paths.make_path("authorize.conf")
PATH_MIGRATION_CONF  = bundle_paths.make_path("migration.conf")
PATH_SERVER_CONF     = bundle_paths.make_path("server.conf")
PATH_SERVERCLASS_CONF= bundle_paths.make_path("serverclass.conf")
PATH_WEB_CONF        = bundle_paths.make_path("web.conf")
PATH_LOCALMETA_CONF  = make_splunkhome_path(["etc", "system", "metadata", "local.meta"])
PATH_WMI_CONF        = bundle_paths.make_path("wmi.conf")

PATH_SEARCH_LOCALMETA_CONF  = make_splunkhome_path(["etc", "apps", "search", "metadata", "local.meta"])
PATH_SEARCH_SAVSRCH_CONF    = make_splunkhome_path(["etc", "apps", "search", "local", "savedsearches.conf"])

PATH_ETC_USERS              = make_splunkhome_path(["etc", "users"])

PATH_FIELD_ACTIONS = bundle_paths.make_path('field_actions.conf')
PATH_FIELD_ACTIONS_NEW = make_splunkhome_path(['etc', 'apps', 'search', 'local', 'workflow_actions.conf'])

PATH_UI_MOD_ACTIVE   = make_splunkhome_path(["share", "splunk", "search_mrsparkle", "modules"])
PATH_UI_MOD_NEW      = "%s.new"    %  PATH_UI_MOD_ACTIVE
PATH_ALERT_ACTIONS_CONF = bundle_paths.make_path("alert_actions.conf")

# $SPLUNK_HOME/etc/apps/user-prefs/local/user-prefs.conf
PATH_USER_PREFS_CONF = bundle_paths.make_bundle_path("user-prefs", "user-prefs.conf")

# $SPLUNK_HOME/bin/scripts/echo.sh
PATH_BIN_ECHO_SH = make_splunkhome_path(["bin", "scripts", "echo.sh"])

# $SPLUNK_HOME/bin/scripts/echo_output.txt
PATH_BIN_ECHO_OUTPUT_TXT = make_splunkhome_path(["bin", "scripts", "echo_output.txt"])

#                         0-------------------------------------------------------------------------------80
TIMEZONE_WARNING_MSG =                                                                                           "\n" \
                       """WARNING: If you have configured timestamp offsets using pre-Splunk 3.2 POSIX$"""      + "\n" \
                       """instructions, you must reconfigure them using the information on this page:"""       + "\n" \
                       """http://docs.splunk.com/Documentation/Splunk/latest/Data/ApplyTimezoneOffsetstotimestamps."""   + "\n" \
                       """If you do not do this, your timestamp information will be incorrect."""

#                         0-------------------------------------------------------------------------------80
UNMIGRATABLE_PROMPT  =                                                                                           "\n" \
                       """The above configuration files cannot be migrated automatically.  They will need"""   + "\n" \
                       """to be migrated manually as documented at:"""                                         + "\n" \
                       """http://docs.splunk.com/Documentation/Splunk/4.0/Installation/Stepsformanualmigration""" + "\n" \
                                                                                                               + "\n" \
                       """You can choose to disregard this warning and continue with automatic migration"""    + "\n" \
                       """of the remaining configuration files, but this may result in certain features"""     + "\n" \
                       """being disabled or not working properly until the above files are migrated"""         + "\n" \
                       """properly."""                                                                         + "\n" \
                                                                                                               + "\n" \
                       """Would you like to ignore this warning and continue with migration? [y/n] """


#                         0-------------------------------------------------------------------------------80
UNMIGRATABLE_MSG     = """Stopping as requested."""                                                            + "\n" \
                                                                                                               + "\n" \
                       """To proceed, please complete the above steps and run 'splunk start' again."""



######################################## UTILS ######################################## 

def upgradingFromBeforeSplunk4():
  """
  Returns boolean after checking for serverName node in splunkd.xml.
  This check is ONLY valid when run before splunkd.xml is migrated 4.0.0.
  """
  return (0 != len(comm.grep("<serverName>", PATH_SPLUNKD_XML)))

def upgradingFromBeforeSplunk4_2():
  # SPL-52170: starting with 4.3.4, 'guid' has been moved to etc/instance.cfg
  instanceCfgPath = make_splunkhome_path(["etc", "instance.cfg"])
  if os.path.exists(instanceCfgPath):
    instanceCfg = comm.readConfFile(instanceCfgPath)
    if "general" in instanceCfg and KEY_GUID in instanceCfg["general"]:
      return False
    else:
      raise cex.StopException("File '%s' exists but is corrupt." % instanceCfgPath)

  config = comm.readConfFile(PATH_SERVER_CONF)
  # has already run 4.2.0 (and generated GUID).
  if "general" in config and KEY_GUID in config["general"]:
    return False
  return True

def findPreviewFiles():
  # skip over .snapshot subdirectories, which cause sadness when
  # SPLUNK_HOME is a netapp mountpoint with exposed snapshot dirs
  # SPL-104384 limit scope of search to etc and share dirs
  return (comm.findFiles(PATH_ETC_DIR, "\\.%s$" % EXT_MIGRATE, skipdir_pattern=r"[\\/].snapshot$") +
          comm.findFiles(PATH_SHARE_DIR, "\\.%s$" % EXT_MIGRATE, skipdir_pattern=r"[\\/].snapshot$"))

def getPreviewName(filename):
  return filename + SUF_MIGRATE

def getUnpreviewName(filename):
  if filename.endswith(SUF_MIGRATE):
    filename = filename[:-1 * len(SUF_MIGRATE)]
  return filename

def chooseFile(path, isDryRun, useNewPaths):
  # when we're in dry-run and migrating from the old bundles dir structure
  # to the new one, we haven't actually moved the files - so allow preview
  # to happen based on the old, still valid, file locations.
  if not useNewPaths:
    path = path.replace(bundle_paths.get_system_bundle_path(),
        bundle_paths.get_legacy_base_path(), 1)

  doritosRule = path
  if isDryRun:
    doritosRule = getPreviewName(doritosRule)
    if os.path.exists(path):
      shutil.copy(path, doritosRule)
  return doritosRule


def setMigHistory(key, val, isDryRun):
  if isDryRun:
    return
  migSettings = {}
  if os.path.exists(PATH_MIGRATION_CONF):
    migSettings = comm.readConfFile(PATH_MIGRATION_CONF)
  if not STANZA_MIG_HISTORY in migSettings:
    migSettings[STANZA_MIG_HISTORY] = {}
  migSettings[STANZA_MIG_HISTORY][key] = val
  comm.writeConfFile(PATH_MIGRATION_CONF, migSettings)

def getMigHistory(key):
  val = None
  if os.path.exists(PATH_MIGRATION_CONF):
    migSettings = comm.readConfFile(PATH_MIGRATION_CONF)
    if STANZA_MIG_HISTORY in migSettings:
      if key in migSettings[STANZA_MIG_HISTORY]:
        if key == KEY_LAST_MIG_VERSION:
          val = tuple(map(int, migSettings[STANZA_MIG_HISTORY][key].split(".")))
        else:
          val = migSettings[STANZA_MIG_HISTORY][key]
  return val

def askStoppedSplunkd(uri):
  proc = subprocess.Popen(["splunkd", "rest", "--noauth", "GET", uri], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  (out, err) = proc.communicate()
  if sys.version_info >= (3, 0):
      out = out.decode()
      err = err.decode()
  if 0 != proc.returncode:
    raise cex.InternalError("Failed to run splunkd rest:\nstdout:%s\n--\nstderr:%s\n--\n" % (out, err))
  return out

def setStoppedSplunkd(uri, args):
  proc = subprocess.Popen(["splunkd", "rest", "--noauth", "POST", uri] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  (out, err) = proc.communicate()
  if sys.version_info >= (3, 0):
    out = out.decode()
    err = err.decode()
  if 0 != proc.returncode:
    raise cex.InternalError("Failed to run splunkd rest:\nstdout:%s\n--\nstderr:%s\n--\n" % (out, err))
  return out

def isAppEnabled(appName):
  enabled = False
  result = str(askStoppedSplunkd("/services/admin/localapps/" + appName)).splitlines()
  regex = re.compile("=.disabled.>(0|false)") # we return 0 these days, but...
  for line in result:
    # not-None means we found a match for a non-disabled setting.
    if None != regex.search(line):
      enabled = True
      break
  return enabled


####################################### //UTILS ####################################### 

def checkCommandsConfig(confName):
  """
  Compare etc/searchscripts with the merged commands.conf, which now must
  specify all such scripts.
  
  If a given script does not have a corresponding FILENAME=<name> entry in
  some stanza of commands.conf, show a warning.

  Since some genius shoved a .conf file in that dir, we'll be sure to only
  inspect files ending in .pl or .py, which is what commands.conf.spec says
  we support.

  This function makes no changes to your filesystem.
  """
  logger.info("\nChecking script configuration...\n")
  keyFilename = 'filename'
  keyFileType = 'type'
  fileTypeMap = { 'perl' : '.pl', 'python' : '.py' }

  # collect all known script names from commands.conf into a list.
  commandsDict = comm.getMergedConf(confName)
  # this is the list of valid script filenames.
  commandList  = [kvPair[keyFilename] for kvPair in commandsDict.values() if keyFilename in kvPair]
  commandList = []
  for cmdName, cmdSetts in commandsDict.items():
    # if the filename is specified in the stanza settings, go with that.
    if keyFilename in cmdSetts:
      commandList.append(cmdSetts[keyFilename])
    # otherwise we have to figure it out.
    else:
      # figure out whether this is a python or perl file.
      fileType = (keyFileType in cmdSetts and cmdSetts[keyFileType] or 'python')
      if not fileType in fileTypeMap:
        logger.warn("File type '%s' in stanza '%s' is unrecognized.  This command may not work." % (fileType, cmdName))
        continue # skip this command, we dunno what it is.
      # add the stanza name + appropriate extension as a command.
      commandList.append(cmdName + fileTypeMap[fileType])
  logger.debug("The following commands are specified in commands.conf:  %s" % str.join(str(", "), commandList))

  # find all .py or .pl files in etc/searchscripts.
  scriptFiles = comm.findFiles(make_splunkhome_path(['etc', 'searchscripts']), r'\.(py|pl)', caseSens = False)
  
  # out of that script list, pick out all those that are not in the .conf file, discounting the path.
  badScripts = [x for x in scriptFiles if os.path.split(x)[1] not in commandList]

  if len(badScripts) > 0:
    logger.warn("The following scripts will not work without being configured in commands.conf:"
        "\n\t%s" % str.join(str("\n\t"), badScripts))


def checkSavedSearches(confName):
  """
  Iterates all saved searches (after bundles have been merged)
  and warns about searches that are now unsafe.

  This function makes no changes to your filesystem.

  Thanks to Steveyz for scripting this up.
  """
  logger.info("\nChecking saved search compatibility...")
  KEY_QUERY = "query"
  savedSearches = comm.getMergedConf(confName)
  for ssName, ssSetts in savedSearches.items():
    if not KEY_QUERY in ssSetts:
      continue

    searchString = ssSetts[KEY_QUERY]
    warning = ""
    
    searchModifiers = ("maxresults", "maxtime", "savedsplunk", "savedsearch", "eventtype", "tag",
        "typetag", "eventtypetag", "hosttag", "sourcetype", "source", "host", "index", "readlevel",
        "startdaysago", "startminutesago", "starthoursago", "startmonthsago", "enddaysago",
        "endminutesago", "endhoursago", "endmonthsago", "searchtimespanhours", "searchtimespanminutes",
        "searchtimespandays", "searchtimespanmonths", "starttime", "timeformat", "endtime", "timeformat",
        "starttimeu", "endtimeu", "daysago", "minutesago", "hoursago", "monthsago")
    specialExceptions = ("group",) # group = SPL-12442.
    
    firstTerm = searchString.split(" ")[0]
    if firstTerm in ("admin", "remote"):
      warning = "A search starting with '%s' will no longer invoke the %s operator.  To invoke the '%s'" \
          " operator, prepend '|' to your search, e.g. '| %s'." % (firstTerm, firstTerm, firstTerm, searchString)
    elif firstTerm == "search":
      warning = "A leading 'search' term is no longer ignored.  Your query will search for the literal term 'search'"
    else:
      # find maxresults/maxtime, which are deprecated
      maxrestimeRE = re.compile(r"($|.*\s+)(maxresults|maxtime)(\:\:|==?)\d+(\s+.*|$)")
      if maxrestimeRE.match(searchString):
        warning = "The maxresults and maxtime search modifiers have been deprecated and will be ignored."
      # this is trickier, find foo=bar terms in the search clause before the first pipe
      # not the most robust parsing, but simple and covers 99% of cases, should be good enough
      searchString = searchString.split("|")[0]
      srcfieldRE = re.compile(r"^.*?(\w+)=(.*)$")
      while True:
        sfmatch = srcfieldRE.match(searchString)
        if sfmatch == None:
          break
        fieldname = sfmatch.group(1)
        searchString = sfmatch.group(2)
        if (not fieldname in searchModifiers) and (not fieldname in specialExceptions):
          if len(warning) > 0:
            warning += "\n\n"
          warning += ("If '%s' is an indexed field with values not found in the raw event, you must indicate that" \
              " this is an indexed field in fields.conf or use '::' instead of '=' to separate the field name" \
              " from the value.") % fieldname

    # SPL-34447: "field::value" within literal quotes will now search for literal token
    if (searchString.find('"sourcetype::') >= 0) or (searchString.find('"source::') >= 0) or (searchString.find('"host::') >= 0):
      warning += '\n"<field>::<value>" (with literal quotes) will no longer search for <field>=<value> but rather that literal pattern including ::'
    
    if len(warning) > 0:
      logger.warn("WARNING for saved search '%s': %s" % (ssName, warning))


def checkTimezones(confName, isDryRun):
  """
  This is the check for SPL-13537, the issue with the previously-wrong timezone offset rules.

  The logic here is:
    - for each stanza from the post-merge props.conf,
    - if the stanza has a TZ key, check the value.
    - if there's a slash in the value, truncate the string just before it.
    - if the value has a 1-9 digit (not 0) at this point, show the warning.

  Upon showing the warning, when we're not in dry-run, a migration.conf file will be left behind.
  This will be checked the next time FTR goes through.  If we have a special flag in the file,
  we won't show the warning again - so people will only ever see it once per instance.
  """
  WARNING_VERSION = '1'
  KEY_TIMEZONE    = 'TZ'
  KEY_TZWARNING   = 'checkedOrDisplayedTimezoneWarning'

  # check and see if we've already shown this warning.
  migSettings = {}
  if os.path.exists(PATH_MIGRATION_CONF):
    migSettings = comm.readConfFile(PATH_MIGRATION_CONF)
    if STANZA_MIG_HISTORY in migSettings:
      if KEY_TZWARNING in migSettings[STANZA_MIG_HISTORY]:
        if migSettings[STANZA_MIG_HISTORY][KEY_TZWARNING] >= WARNING_VERSION:
          return

  logger.info("\nChecking for possible timezone configuration errors...")
  iTawtISawAPuddyTat = False
  propsStanzas = comm.getMergedConf(confName)
  # for each [stanza] in props...
  for settings in propsStanzas.values():
    # no TZ key?  skip it.
    if not KEY_TIMEZONE in settings:
      continue
    tzVal = settings[KEY_TIMEZONE]
    # strip any slashes and anything after them.
    firstSlashPos = tzVal.find('/')
    if firstSlashPos >= 0:
      tzVal = tzVal[:firstSlashPos]
    # position of first non-zero digit in this TZ value, if any.
    for oneChar in tzVal:
      if oneChar.isdigit() and ('0' != oneChar):
        iTawtISawAPuddyTat = True
        # don't bother checking anymore.
        break

  # do the warning if necessary.
  if iTawtISawAPuddyTat:
    logger.warn(TIMEZONE_WARNING_MSG)

  # if this isn't a dry run, make a note that we've done this warning check.
  if not isDryRun:
    if not STANZA_MIG_HISTORY in migSettings:
      migSettings[STANZA_MIG_HISTORY] = {}
    migSettings[STANZA_MIG_HISTORY][KEY_TZWARNING] = WARNING_VERSION
    comm.writeConfFile(PATH_MIGRATION_CONF, migSettings)


def migSplunkdXml_4_0_0(srcXml, destConf):
  """
  Migrates splunkd.xml values for server name and disk usage processor settings
  to server.conf.
  Overwrites existing splunkd.xml and server.conf.
  """

  STANZA_GENERAL = "general"
  KEY_SRV_NAME   = "serverName"

  # from...
  DISK_USAGE_NAME = "diskusage"
  FREE_SPACE_TAG  = "minFreeSpace"
  POLL_FREQ_TAG   = "pollingFrequency"
  # to...
  KEY_DISK_USAGE  = "diskUsage"

  srvName, minFreeSpace, pollFreq = None, None, None

  srcDom = xml.dom.minidom.parse(srcXml)

  # find serverName node and get value.
  nodeList = srcDom.getElementsByTagName(KEY_SRV_NAME)
  if 0 != len(nodeList):
    srvNameNode = nodeList[0]

    srvName = srvNameNode.firstChild.nodeValue
    if 0 == len(srvName):
      raise cex.ParsingError("Found splunkd.xml serverName node, but could not extract value.  Please file a case online at http://www.splunk.com/page/submit_issue")
    # remove node from dom.
    srvNameNode.parentNode.removeChild(srvNameNode)

  # find diskusage processor node and get value(s).
  diskUsageNode = None
  nodeList = srcDom.getElementsByTagName("processor")
  for node in nodeList:
    if node.hasAttribute("name") and DISK_USAGE_NAME == node.getAttribute("name"):
      diskUsageNode = node
      break
  if None != diskUsageNode:
    # get minFreeSpace value if avail.
    nodeList = diskUsageNode.getElementsByTagName(FREE_SPACE_TAG)
    if 0 != len(nodeList):
      node = nodeList[0]
      minFreeSpace = node.firstChild.nodeValue
      if 0 == len(minFreeSpace):
        raise cex.ParsingError("Found splunkd.xml minFreeSpace node, but could not extract value. Please file a case online at http://www.splunk.com/page/submit_issue")
    # get pollingFrequency if avail.
    nodeList = diskUsageNode.getElementsByTagName(POLL_FREQ_TAG)
    if 0 != len(nodeList):
      node = nodeList[0]
      pollFreq = node.firstChild.nodeValue
      if 0 == len(pollFreq):
        raise cex.ParsingError("Found splunkd.xml pollingFrequency node, but could not extract value. Please file a case online at http://www.splunk.com/page/submit_issue")
    diskUsageNode.parentNode.removeChild(diskUsageNode)

  if srvName == None and minFreeSpace == None and pollFreq == None:
    return # nothing changed, nothing to write out.

  # before editing xml file, load conf if it exists and save an updated version.
  destDict = {}
  if os.path.exists(destConf):
    destDict = comm.readConfFile(destConf)
  if srvName != None:
    if not STANZA_GENERAL in destDict:
      destDict[STANZA_GENERAL] = {}
    destDict[STANZA_GENERAL][KEY_SRV_NAME] = srvName
  if minFreeSpace != None:
    if not KEY_DISK_USAGE in destDict:
      destDict[KEY_DISK_USAGE] = {}
    destDict[KEY_DISK_USAGE][FREE_SPACE_TAG] = minFreeSpace
  if pollFreq != None:
    if not KEY_DISK_USAGE in destDict:
      destDict[KEY_DISK_USAGE] = {}
    destDict[KEY_DISK_USAGE][POLL_FREQ_TAG] = pollFreq
  # save local server.conf.
  comm.writeConfFile(destConf, destDict)

  # write out updated xml file.
  open(srcXml, "w").write(srcDom.toxml())


def migrateSavedSearches(path):
  """
  Change isGlobal in savedsearches.conf.  Use case insensitive because there was
  some confusion with this variable early on, we may have lowercase and camelcase.
    isGlobal = 1   ->   role = Everybody
    isGlobal = 0   ->   role = 
    isGlobal =     ->   role = 
  """
  if os.path.exists(path):
    change = lambda x, y: comm.sed(x, y, path, inPlace = True)
    change("is[Gg]lobal\\s*=\\s*1", "role = Everybody")
    change("is[Gg]lobal\\s*=\\s*0", "role = ")
    change("is[Gg]lobal\\s*=\\s*$", "role = \n")
    if len(comm.grep("^[^#]*is[Gg]lobal", path)) > 0:
      logger.warn("*** After saved search migration, still have isGlobal in %s.  This should not happen. Please file a case online at http://www.splunk.com/page/submit_issue" % path)



def migrateWebSSL(srvConfPath, webConfPath):
  """
  Changes from the old web/ssl variable in the server.conf to the new one in web.conf.
  """
  oldParm    = "enableSplunkSearchSSL"
  newParm    = "enableSplunkWebSSL"
  kvSep      = "="
  settStanza = "[settings]"
  # local file doesn't exist?  done.
  if not os.path.exists(srvConfPath):
    return
  # old string not in local file?  done.
  if 0 == len(comm.grep(oldParm, srvConfPath)):
    return

  # fyi, this is a little more complicated than it should be because we're preserving comments.

  # get all existing lines in server.conf.
  srvFile     = open(srvConfPath, 'r')
  oldSrvLines = srvFile.readlines()
  srvFile.close()
  # remove lines w/ old setting and store setting.
  newSrvLines = []
  oldSetting  = None
  for line in oldSrvLines:
    # if this line has no =, just add it to the new lines.
    if 0 == line.count(kvSep):
      newSrvLines.append(line)
    # otherwise, dig deeper.
    else:
      key, val = line.split(kvSep, 1)
      key = key.strip()
      # if this is the SSL key, save the value.
      if oldParm == key:
        oldSetting = val
      # otherwise add it to the lines to be written out again.
      else:
        newSrvLines.append(line)
  
  # write out the new server.conf.
  srvFile = open(srvConfPath, 'w+') # w+ = write/truncate.
  srvFile.write(str.join("", newSrvLines))
  srvFile.close()

  webConfLines = []
  # gather old web config lines, if it exists.
  if os.path.exists(webConfPath):
    webConfLines = open(webConfPath, 'r').readlines()
  settStanzaInd = None
  # find [settings] if possible.
  for i in range(0, len(webConfLines)):
    if settStanza == webConfLines[i].strip():
      settStanzaInd = i
      break
  # wasn't there?  add it as index 0.
  if None == settStanzaInd:
    webConfLines.append(settStanza + "\n")
    settStanzaInd = 0
  # insert the setting.
  webConfLines.insert(settStanzaInd + 1, "%s =%s" % (newParm, oldSetting))

  # write out new web.conf.
  newWebFile = open(webConfPath, 'w+') # w+ = write/truncate.
  newWebFile.write(str.join("", webConfLines))
  newWebFile.close()


def migrateWebPollerTimeoutInterval_4_1(path):
    """
    Migrates poller_timeout_interval key to ui_inactivity_timeout and runs a conversion from Millisecods to Minutes on the value if it can.
    """
    stanza = "settings"
    original_key = "poller_timeout_interval" #4.0.X deprecated key
    replacement_key = "ui_inactivity_timeout"
    conversion = 60000 #take ms value and convert to minutes
    if os.path.exists(path):
      stanzaDict = comm.readConfFile(path)
      if stanza in stanzaDict and original_key in stanzaDict[stanza]:
          value = stanzaDict[stanza].pop(original_key)
          logger.info("Original %s value: %s" % (original_key, value))
          try:
              value = int(value) // conversion #cast string to int and apply millisecond to minute conversion
          except:
              logger.warn("Could not convert %s value of %s to minutes, check that it is a valid number." % (original_key, value))
              return
          logger.info("Converted %s value: %s" % (original_key, value))
          if value>0:
              stanzaDict[stanza][replacement_key] = value
              comm.writeConfFile(path, stanzaDict)
              logger.info("Successful migration of %s to %s" % (original_key, replacement_key))
          else:
              logger.warn("Unsuccessful migration of %s to %s" % (original_key, replacement_key))


def migrateWeb_SSOMode_4_2_5 (serverConfPath, webConfPath):
  """
  Deal with ramifications of default value of 'SSOMode' changing from
  'permissive' to 'strict'.
  """

  # # # if SSO is disabled (i.e., server.conf[general]trustedIP is missing), quit
  serverConf = comm.readConfFile(serverConfPath)
  if ('general' not in serverConf) or ('trustedIP' not in serverConf['general']):
    return

  # # # fetch explicit (ie, in etc/system/local/) value of web.conf[settings]SSOMode
  explicitSSOMode = None
  webConf = comm.readConfFile(webConfPath)
  if ('settings' in webConf) and ('SSOMode' in webConf['settings']):
    explicitSSOMode = webConf['settings']['SSOMode']

  # # # if explicit value found, they know what they're doing; quit
  if explicitSSOMode:
    return

  # # # add 'permissive' (the old default value of SSOMode) to local/web.conf
  if not 'settings' in webConf:
    webConf['settings'] = {}
  webConf['settings']['SSOMode'] = 'permissive'
  comm.writeConfFile(webConfPath, webConf)

  # # # print warning, suggest they use 'strict' instead
  logger.warn('The suggested value of SSOMode (web.conf, [settings] stanza) is' +
              ' "strict", starting with 4.2.5; please consider switching to that.')


def removeDirMon(isDryRun):
  """
  disable the old batch module or we'll be in pain.
  """
  if os.path.exists(PATH_BATCHCONF_XML):
    if not isDryRun:
      logger.info("Upgrading batch file input module...")
    comm.moveItem(PATH_BATCHCONF_XML, PATH_BATCHCONF_DIS, isDryRun)


def removeDeprecated(isDryRun):
  """
  move now-unused or potentially harmful files out of the way.
  """
  logger.notice("\nHandling deprecated files...")

  bundleFiles = ("access_control.conf", "auth.conf", "metaevents.conf")
  # some files are moved elsewhere.  this one is done in rory's auth migration.
  # but, we still want to delete the example/spec files.
  exclude     = "auth.conf"
  bundlePath  = make_splunkhome_path(["etc", "bundles"])

  for filename in bundleFiles:
    # good idea to do case-insensitive, for windows in the future.
    #                                           match on foo, foo.example, foo.spec.
    fileList = comm.findFiles(bundlePath, "\\b%s(|.example|.spec)$" % filename, caseSens = False)
    for oneFile in fileList:
      if not oneFile.endswith(exclude):
        filename   = os.path.basename(oneFile)
        parentPath = os.path.dirname(oneFile)
        parentDir  = os.path.basename(parentPath)
        depDir     = os.path.join(parentPath, "deprecated")

        # apparently we install files in 3.2 that are pre-deprecated.  a winrar is us..
        if 'deprecated' != parentDir:
          if not isDryRun and not os.path.exists(depDir):
            os.mkdir(depDir)
          # if this file lives in our bundles/README or bundles/DEFAULT dir, move it to a "deprecated" subdir.
          if parentDir in ('default', 'README'):
            comm.moveItem(oneFile, os.path.join(depDir, filename + "." + EXT_DEPRECATED), isDryRun)
          # otherwise just rename it.
          else:
            comm.moveItem(oneFile, oneFile + "." + EXT_DEPRECATED, isDryRun)


def migrateAuth_3_2_0(newConfPath, isDryRun):
  """
  Migrate the old auth.conf -> authentication.conf for 3.2.0.
  """
  ROLE_ADMIN   = "Admin"
  ROLE_POWER   = "Power"
  ROLE_USER    = "User"
  STANZA_AUTH  = "auth"

  # if we don't have local/auth.conf, there's nothing to do.
  if not os.path.exists(PATH_AUTHEN_CONF_OLD):
    return

  # copy auth.conf to the new path.  this is what we'll edit.
  shutil.copy(PATH_AUTHEN_CONF_OLD, newConfPath)
  # rename auth.conf to auth.conf-migrate.bak or whatever.
  comm.moveItem(PATH_AUTHEN_CONF_OLD, PATH_AUTHEN_CONF_BAK, isDryRun)

  stanzaDict = comm.readConfFile(newConfPath)

  roleMap = {}
  # find Admin/Power/User settings as necessary.  save values and remove
  # from settings dictionary.
  for stanzaSetts in stanzaDict.values():
    for key, val in stanzaSetts.items():
      if   ROLE_ADMIN == key:
        roleMap[ROLE_ADMIN] = val
        del stanzaSetts[key]
      elif ROLE_POWER == key:
        roleMap[ROLE_POWER] = val
        del stanzaSetts[key]
      elif ROLE_USER  == key:
        roleMap[ROLE_USER]  = val
        del stanzaSetts[key]
    
  if 0 != len(roleMap):
    stanzaDict["roleMap"] = roleMap
  
  if STANZA_AUTH in stanzaDict:
    stanzaDict["authentication"] = stanzaDict.pop(STANZA_AUTH)

  # done, write out the new authentication.conf.
  comm.writeConfFile(newConfPath, stanzaDict)

def migrateDistSearchXML(xmlPath, confPath, isDryRun):
  # <config>
  BLOCK_CONFIG  = "config"
  # these live in <config>.
  BLOCK_BLIST   = "blacklist"
  BLOCK_SERVERS = "servers"

  TAG_SERVER    = "server"
  TAG_URL       = "url"

  ATTR_SERVNAME = "name"
  ATTR_SRVURL   = "url"

  KEY_SERVERS   = "servers"

  # load the XML and make sure we have <config>.
  distDom = xml.dom.minidom.parse(xmlPath)
  try:
    configBlock = distDom.getElementsByTagName(BLOCK_CONFIG)[0]
  except IndexError:
    raise cex.ParsingError("Bad distributed search config file. Please file a case online at http://www.splunk.com/page/submit_issue")

  # only migrate if we have xml nodes in <config></config> other than whitespace and comment nodes.
  if 0 == len([x for x in configBlock.childNodes if x.nodeType not in (x.TEXT_NODE, x.COMMENT_NODE)]):
    return # had 0 nodes left after filtering those useless ones out.

  # make a backup of the distributed search config.xml.  not in dry run though, looks kinda silly
  # to say we'd make a backup of the "preview" file.
  if not isDryRun:
    comm.copyItem(xmlPath, xmlPath + BACKUP_EXT, isDryRun)

  # this is where we'll collect all the settings from the xml file.
  settsDict = {}

  # iterate almost all xml tags in <config> and store them in our dict.
  for child in configBlock.childNodes:
    valueFound = False
    # if it's not an element, screw it.  prob whitespace/etc.
    if child.ELEMENT_NODE == child.nodeType:
      # skip <servers> and <blacklist>, we handle those specially.
      if not child.nodeName in (BLOCK_BLIST, BLOCK_SERVERS):
        # could be empty tags, check for that.
        if child.hasChildNodes():
          valueFound = True
          # add value in <tags>value</tags>.
          settsDict[child.nodeName] = child.firstChild.nodeValue
        # otherwise just add it with an empty value.
        else:
          settsDict[child.nodeName] = ""

  # now process the nested server nodes.
  serverList = []
  for servBlock in configBlock.getElementsByTagName(BLOCK_SERVERS):
    for urlTag in servBlock.getElementsByTagName(TAG_URL):
      if urlTag.hasChildNodes():
        serverList.append(urlTag.firstChild.data)
  # add any collected servers to the settings as a CSV list.
  if len(serverList) > 0:
    settsDict[KEY_SERVERS] = str.join(str(","), serverList)

  # create the file-level dictionary that we'll write out.
  #             stanza               k/v pairs
  confDict  = {"distributedSearch" : settsDict}

  # write out the new .conf file.
  comm.writeConfFile(confPath, confDict)

  # now that all that was successful, add an empty <config> block,
  # delete the old one, and write out the new xml file.
  configBlock.parentNode.appendChild(distDom.createElement("config"))
  configBlock.parentNode.removeChild(configBlock)
  open(xmlPath, "w").write(distDom.toxml())

  # done.


def fixPasswdPermissions(path, isDryRun):
  """
  In some versions prior to 3.2.0, passwd files were created world-readable.
  On Unix systems, just ensure the perms are set properly.
  """

  # can't do anything about this on windows, and free doesn't have a passwd file.
  if comm.isWindows or not os.path.exists(path):
    return
  else:
    if 0 != subprocess.call(['chmod', PERMS_OWNER_RW_ONLY, path]):
      raise cex.ArgError("Was unable to change permissions of '%s'.  Unwise to continue without figuring out why.")


def migQueryToSearch_3_3_0(pathSaved, pathEvttype):
  """
  The language police has mandated that the 'query' key change to 'search' for
  saved searches and event types.  This is critical.
  """
  for path in (pathSaved, pathEvttype):
    if os.path.exists(path):
      comm.sed(r'^(\s*)query(\s*=)', r'\1search\2', path, inPlace = True)


def migCapabilities_3_3_0(authorizeConf):
    """
    Migrate capabilities that have been renamed.
    """
    if not os.path.exists(authorizeConf):
        return
    for substr, replacement in (('edit_exec', 'edit_scripted'),
                                ('edit_watch', 'edit_batch'),
                                ('edit_tail', 'edit_monitor')):
        comm.sed(r'^(\s*)%s(\s*=)' % substr,
                 r'\1%s\2' % replacement,
                 authorizeConf,
                 inPlace = True)

def checkForEnabledIndexesEditCapAndWarn(authorizeConf):
    """
    Given an authorize.conf, logs a warning if any role
    has indexes_edit capability enabled. 
    Warning is about clustering capabilities.
    """
    if not os.path.exists(authorizeConf):
        return
    logger.debug("Operating on %s" % authorizeConf)
    stanzas = comm.readConfFile( authorizeConf )
    for stanza, settings in stanzas.items():
        if stanza.startswith('role_'):
            if 'indexes_edit' in settings and settings['indexes_edit'].lower() == 'enabled':
                logger.warn("In file=%s, found a role=%s with indexes_edit capability enabled. You can no longer"
                            " list (or) edit indexer cluster REST endpoints using indexes_edit capability. "
                            " If you want to use any custom roles to list (or) edit indexer cluster REST endpoints,"
                            " please make sure to grant list_indexer_cluster (or) edit_indexer_cluster"
                            " capabilities." % (authorizeConf, stanza))
                return None

def checkForEnabledIndexesEditCapAndWarn_AllApps():
    """
    Iterates over all apps in etc/apps and calls 
    checkForEnabledIndexesEditCapAndWarn() on every apps's 
    default and local authorize.conf paths.
    """
    for bundle in bundle_paths.bundles_iterator():
        defaultAuthorizeConf = os.path.join(bundle.location(), 'default', 'authorize.conf')
        localAuthorizeConf = os.path.join(bundle.location(), 'local', 'authorize.conf')
        checkForEnabledIndexesEditCapAndWarn(defaultAuthorizeConf)
        checkForEnabledIndexesEditCapAndWarn(localAuthorizeConf)

def is_int(s):
        try:
                int(s)
                return True
        except ValueError:
                return False

def migEtcUsers_4_0_5(users_dir, isDryRun):

        reserved_dir = os.path.join(users_dir, '_reserved')
        # no user dirs to migrate
        if not os.path.exists(reserved_dir) or not os.path.isdir(reserved_dir):
           return 

        # matches user.original_user_md5 dir names
        regex = re.compile('^(.*)\\..*')
        dirs  = os.listdir(reserved_dir) 
       
        for d in dirs:
          user_dir = os.path.join(reserved_dir, d)
          match    = regex.match(d) 
          if not os.path.isdir(user_dir) or match == None:
             continue
      
          new_user_dir = os.path.join(users_dir, match.group(1))

          if os.path.exists(new_user_dir):
              logger.warn("\nCannot automatically migrate user dir " + str(user_dir) + " to " + str(new_user_dir) + ". Destination dir already exists" )
              continue
 
          comm.moveItem(user_dir, new_user_dir, isDryRun)    
     
        users_ini = os.path.join(users_dir, "users.ini")
        if os.path.exists( users_ini ):
           comm.moveItem(users_ini, os.path.join(users_dir, "users.ini.pre405"), isDryRun)  

        comm.removeItem(reserved_dir, isDryRun)
        
        
def migTags_is_pre_4_1(tags_conf_path):
        if not os.path.exists( tags_conf_path ):
            return False
        stanzas = comm.readConfFile( tags_conf_path )
        
        if len(stanzas) == 0:
            return False
        
        for stanza in stanzas:
            # seems like new format - don't do anything
            if stanza.find("=") != -1:
                return False
        return True

def migTags_4_1(src_tags_conf_path, dst_tags_conf_path, isDryRun):
        
        # remove the old admin_field_values.xml 
        afv_tags =  make_splunkhome_path(["etc", "apps", "search", "default", "data", "ui", "manager", "admin_field_values.xml"])
        if os.path.exists(afv_tags): 
            comm.removeItem(afv_tags, isDryRun)
         
        if os.path.exists( src_tags_conf_path ):
            stanzas = comm.readConfFile( src_tags_conf_path )
            dst_stanzas = {}
            for stanza, settings in stanzas.items():
                # seems like new format - don't do anything
                if stanza.find("=") != -1:
                   dst_stanzas = {}
                   break
                
                for k, v in settings.items():
                    tokens = k.split("::")
                    if len(tokens) != 3 or tokens[0] != "tag":
                        continue
                    new_stanza = stanza+"="+urllib_parse.quote(tokens[1])
                    if not new_stanza in dst_stanzas:
                        dst_stanzas[new_stanza] = {}
                    
                    tag_name = tokens[2]
                    
                    # add tag=enabled|disabled 
                    dst_stanzas[new_stanza][tag_name] = v
                    
            old_backup_ext = ".old"
            if len(dst_stanzas) > 0:
               comm.copyItem( src_tags_conf_path, src_tags_conf_path + old_backup_ext, isDryRun )
               comm.writeConfFile(dst_tags_conf_path, dst_stanzas)


def replace_ui_modules_8_0_0(isDryRun):
  """
  SPL-30095 - ui modules aren't quite upgrade safe, work around that.
  SPL-173474 - Replaced existing modules folder instead of keeping a backup as .old.<timestamp>
  """
  if not os.path.exists(PATH_UI_MOD_NEW):
    logger.warn("\nCould not find new UI modules directory to install")
    return
  if os.path.exists(PATH_UI_MOD_ACTIVE): # not an error if DNE, maybe a failed prior run...
    comm.removeItem(PATH_UI_MOD_ACTIVE, isDryRun) 
  comm.moveItem(PATH_UI_MOD_NEW, PATH_UI_MOD_ACTIVE, isDryRun)

def remove_exposed_content_8_0_0(isDryRun):
  """
  SPL-173477 - Removed exposed folders should not be present after upgrade to Quake 8.0.0
  """
  logger.info("\nChecking for the modules related files and folders that should not be present after upgrade.")
  path_exposed_folder = make_splunkhome_path(["share", "splunk", "search_mrsparkle", "exposed"])
  path_lst = [os.path.join(path_exposed_folder, "flash"),
                     os.path.join(path_exposed_folder, "js", "contrib", "swfobject.js")]
  for path in path_lst:
    if os.path.exists(path): 
      comm.removeItem(path, isDryRun)
      
def remove_axml_8_0_0(isDryRun):
  """
  SPL-173477 - Removed AXML should not be present after upgrade to Quake 8.0.0
  """
  logger.info("\nChecking for the Advanced XML dashboard templates that should not be present after upgrade.")
  files_to_be_removed = [make_splunkhome_path(["share", "splunk", "app_templates", "sample_app", "local", "data", "ui", "views", "sample_notimeline.xml"]),
                          make_splunkhome_path(["share", "splunk", "app_templates", "sample_app", "local", "data", "ui", "views", "sample_search.xml"]),
                          make_splunkhome_path(["share", "splunk", "app_templates", "sample_app", "default", "viewstates.conf"]),
                          make_splunkhome_path(["etc", "apps", "dmc", "bin", "agent", "app_templates", "sample_app_cloud", "default", "data", "ui", "views", "sample_notimeline.xml"]),
                          make_splunkhome_path(["etc", "apps", "dmc", "bin", "agent", "app_templates", "sample_app_cloud", "default", "data", "ui", "views", "sample_search.xml"]),
                          make_splunkhome_path(["etc", "apps", "dmc", "bin", "agent", "app_templates", "sample_app_cloud", "default", "viewstates.conf"])]
  
  for file_path in files_to_be_removed:
    if os.path.exists(file_path):
      comm.removeItem(file_path, isDryRun)
      
def remove_axml_apps_8_0_0(isDryRun):
  """
  SPL-173477 - Removed Apps should not be present after upgrade to Quake 8.0.0
  """
  path_app_gettingstarted = make_splunkhome_path(["etc", "apps", "gettingstarted"])
  logger.info("\nChecking for the 'Getting Started' app that should not be present after upgrade.")
  # Remove the default Getting Started App from etc/apps/gettingstarted
  # Leaving the user specific app directories at etc/users/*/gettingstarted
  if os.path.exists(path_app_gettingstarted):
    comm.removeItem(path_app_gettingstarted, isDryRun)

def migSavedsearches_4_0_0(src_savedsearch_conf_path, dst_savedsearch_conf_path, local_meta_path, isDryRun):
        ###
        # see SPL-20459 - savedsearch.conf migration
        ###
        if not os.path.exists( src_savedsearch_conf_path ):
                return

        if not os.path.exists( os.path.dirname(dst_savedsearch_conf_path) ):
               os.makedirs ( os.path.dirname(dst_savedsearch_conf_path) )

        inPlace = src_savedsearch_conf_path == dst_savedsearch_conf_path

        old_backup_ext = ".old"

        # make backup of original if not dryrun
        comm.copyItem( src_savedsearch_conf_path, src_savedsearch_conf_path + old_backup_ext, isDryRun )

        stanzas = comm.readConfFile( src_savedsearch_conf_path )
        form_search_matcher = re.compile( "\$.*\$" )

        meta_stanza = comm.readConfFile( local_meta_path )

        id2user = comm.id2userMapFromPasswdFile(make_splunkhome_path(['etc', 'passwd']))

        for stanza, settings in stanzas.items():

                if 'search' in settings \
                        and form_search_matcher.search( settings['search'] ):
                                settings['disabled'] = '1'

                meta_stanza_key = 'savedsearches/' + urllib_parse.quote(stanza)
                tmp = { }

                if 'role' in settings:
                        lowercase_role = settings['role'].lower()
                        if lowercase_role == "everybody":
                                lowercase_role = "*"
                        access_val = 'read : [ ' + lowercase_role  + ' ]'
                        tmp[ 'access' ] = access_val

                if 'userid' in settings:
                        if settings['userid'] in id2user:
                                tmp[ 'owner' ] = id2user[ settings['userid'] ]
                        else:
                                new_owner = settings['userid']
                                if new_owner == "-1":
                                    new_owner = "nobody"
                                tmp[ 'owner' ] = new_owner
                                logger.warn('could not find user in splunk etc/passwd corresponding to id='
                                        + settings['userid'] 
                                        + ' from savedsearch: ' 
                                        + stanza
                                        + ' ... setting its ownership to "'+new_owner+'"') 
                tmp['export'] = 'system'
                if len(tmp) != 0 and not stanza == "default":
                        meta_stanza[ meta_stanza_key ] = tmp

        if inPlace:
            comm.writeConfFile(dst_savedsearch_conf_path, stanzas)
        else:
             dst_stanzas = comm.readConfFile( dst_savedsearch_conf_path )
             if not dst_stanzas is None and len(dst_stanzas) > 0:
                stanzas.update(dst_stanzas)
             dst_stanzas = stanzas

             comm.writeConfFile(dst_savedsearch_conf_path, dst_stanzas)

             f = open(src_savedsearch_conf_path, 'w')
             f.write("###############\n")
             f.write("# contents migrated to: " + str(dst_savedsearch_conf_path) + "\n")
             f.write("###############\n")
             f.close()

        # comment out default view states
        comm.sed( r'(^\s*viewstate.*$)', r'# \1 --commented out for migration-- ', dst_savedsearch_conf_path, inPlace = True )

        comm.writeConfFile(local_meta_path, meta_stanza )

def migTranactionTypes_4_0_0(txn_conf_path, isDryRun):

        if not os.path.exists( txn_conf_path ):
                return

        old_backup_ext = ".old"

        # make backup of original if not dryrun
        comm.copyItem( txn_conf_path, txn_conf_path + old_backup_ext, isDryRun )

        # comment out deprecated options
        comm.sed( r'(^\s*(?:aliases|pattern|match|exclusive|maxrepeats).*$)', r'# \1 --commented out by migration, this option has been deprecated -- ', txn_conf_path, inPlace = True )

        # migrate the usage of ` in starts/endswith
        comm.sed( r'(^\s*(?:startswith|endswith))\s*=\s*"([^"]+)"\s*$', r'\1 = eval( \2 )\n', txn_conf_path, inPlace = True )
        comm.sed( r"'([^']+)'", r'"\1"', txn_conf_path, inPlace = True )
        comm.sed( r"`([^`]+)`", r'"\1"', txn_conf_path, inPlace = True )
        
# Sourcetype aliasing used to be done with tags - migrate all tags on sourcetype to rename in props.conf
def migSourcetypeAliases_4_0_0(tags_conf_path, props_conf_path, isDryRun):
  if not os.path.exists( tags_conf_path ):
    return

  # check that a sourcetype stanza exists in tags.conf
  tag_stanzas = comm.readConfFile( tags_conf_path )
  if not "sourcetype" in tag_stanzas:
    return

  # move every enabled tag of sourcetype to props.conf
  renamePairs = {}
  for k, v in tag_stanzas["sourcetype"].items():
    if v == "enabled":
      toks = k.split("::")
      if len(toks) != 3 or toks[0] != "tag":
        print("Failed to parse " + str(k) + " as a tag")
      elif toks[1] in renamePairs:
        print("Multiple aliases found for sourcetype " + toks[1] + " - only renaming to " + renamePairs[toks[1]])
      else:
        renamePairs[toks[1]] = toks[2]

  if len(renamePairs) == 0:
    return

  # make backup of original if not dryrun
  comm.copyItem( tags_conf_path, tags_conf_path + ".old", isDryRun )
  if os.path.exists( props_conf_path ):
    comm.copyItem( props_conf_path, props_conf_path + ".old", isDryRun )

  del tag_stanzas["sourcetype"]
  props_stanzas = comm.readConfFile( props_conf_path )

  for oldname, newname in renamePairs.items():
    if oldname in props_stanzas:
      if "rename" in props_stanzas[oldname]:
        print("Sourcetype " + oldname + "already has a rename specified. Ignoring old alias " + newname)
      else:
        props_stanzas[oldname]["rename"] = newname
    else:
      props_stanzas[oldname] = {"rename":newname}

  # Write the new stanzas out to conf files
  comm.writeConfFile(tags_conf_path, tag_stanzas)
  comm.writeConfFile(props_conf_path, props_stanzas)


def validateServerclassConfObjectName (objType, name):
  problem = ''
  if len(name) > 255:
    problem += ' is too long: must be at most 255 in length;'

  if re.search('[^a-zA-Z0-9 _\.~@-]', name):
    problem += ' contains invalid characters: ' \
        'acceptable characters are only: ' \
        'letters, numbers, space, underscore, dash, dot, tilde, and ' \
        'the \'@\' symbol'

  if not problem:
    return

  msg = 'Your serverclass.conf has %s named "%s".  This name is no longer legal, ' \
      'because it%s.  Deployment Server will not come up until you change this ' \
      'name; Splunk operation will be unaffected otherwise.' % (objType, name, problem)
  logger.warn(msg)


def warnOfNowInvalid_serverclassConf_6_0 (serverclass_conf_path):
  stanzas = comm.readConfFile(serverclass_conf_path)

  seenServerclasses = []
  seenApps = []

  for stanza in stanzas:

    tokens = stanza.split(':')

    if (len(tokens) == 2 or len(tokens) == 4):
      scName = tokens[1]
      if scName not in seenServerclasses:
        seenServerclasses += [scName]
        validateServerclassConfObjectName('serverclass', scName)

    if (len(tokens) == 4):
      appName = tokens[3]
      if appName not in seenApps:
        seenApps += [appName]
        validateServerclassConfObjectName('app', appName)


def warnOfNowUnsupportedAttributes_serverclassConf_6_0 (serverclass_conf_path):
  stanzas = comm.readConfFile(serverclass_conf_path)

  for stanza, props in stanzas.items():
    if 'machineTypes' in props:

      msg = 'Found attribute "machineTypes" in serverclass.conf, stanza=%s.  This ' \
          'attribute is unsupported as of 6.x, and will be ignored by Splunk; ' \
          'please use "machineTypesFilter" instead.' % (stanza)
      logger.warn(msg)
        

def migIndexes_4_0_0(indexes_conf_path, isDryRun):
        ###
        # see SPL-20802 - indexes.conf migration
        ###
        if not os.path.exists( indexes_conf_path ):
                return

        old_backup_ext = ".old"

        # make backup of original if not dryrun
        comm.copyItem( indexes_conf_path, indexes_conf_path + old_backup_ext, isDryRun )

        stanzas = comm.readConfFile( indexes_conf_path )

        keys_to_remove = ['_actions'
                        , 'maxTerms'
                        , 'maxTermChars'
                        , 'maxPostings'
                        , 'maxValues'
                        , 'waitForOptimize'
                        , 'indexThreads'
                        , 'maxMemMB']

        for stanza, settings in stanzas.items():
                #
                # we guess that an index is high-volume in 3.X if indexThreads are
                # set to > 0 for this stanza
                #
                is_high_volume_index = False
                if stanza != 'default'                                  \
                        and 'indexThreads' in settings                  \
                        and is_int( settings['indexThreads'] )          \
                        and int( settings['indexThreads'] ) > 0:
                                is_high_volume_index = True

                for key in keys_to_remove:
                        if key in settings:
                                del settings[key]
                
                #
                # if we have a high-volume index, we better set 
                # the corresponding high-volume attributes
                #
                if is_high_volume_index:
                        settings['maxHotBuckets'] = '10'
                        settings['maxHotIdleSecs'] = '86400'
                        settings['maxMemMB'] = '20'

        comm.writeConfFile(indexes_conf_path, stanzas)


def migSampleIndex_4_2_1(system_indexes_conf, dryRun):
  """ SPL-38061 - 
  4.2 GA+ default-disables the sample_app app, which had an attached index, 'sample'. 
  If customers overrode some of the settings of the sample index outside the app,
  then they are left with an index without its paths fully defined, which causes
  a startup failure during splunk start sanity checks, including splunkd rest,
  used during migration... sigh
  """
  if not upgradingFromBeforeSplunk4_2():
    # 4.2 new installs never had this app enabled.
    return
  try:
    sample_index_conf = comm.getConfStanza('indexes', 'sample')
  except comm.ParsingError:
    # no sample index at all, done
    return
  logger.info("")
  logger.info("Verifying sample index...")
  logger.info("")

  # I don't want to talk about this construction.  It's not my fault
  try:
    state_str = sample_index_conf.get('disabled')
    if comm.isYes(state_str):
      logger.info("sample index already disabled, OK.")
      return
  except:
    pass

  required_keys = ('homePath', 'coldPath', 'thawedPath')
  sample_db_done_broke = False
  for key in required_keys:
    if key not in sample_index_conf:
      sample_db_done_broke = True

  if sample_db_done_broke:
      logger.info("You have a partially configured 'sample' index, associated with the historical splunk sample_app.")
      logger.info("Since Splunk will not start with a partially configured index (for safety reasons)")
      logger.info("  this index must be disabled.")
      logger.info("")

      if not dryRun:
          backup_file = system_indexes_conf + BACKUP_EXT
          logger.info("Backing up '%s' to '%s' before modifying" % (system_indexes_conf, backup_file))
          shutil.copy(system_indexes_conf, backup_file)

      sys_idx_cfg_info = comm.readConfFile(system_indexes_conf)
      sys_idx_cfg_info['sample']['disabled'] = "true"
      comm.writeConfFile(system_indexes_conf, sys_idx_cfg_info)
      if dryRun:
        logger.info("Unfortunately migration (even preview) requires a valid set of indexes to continue.")
        logger.info("Please manually resolve etc/system/local/indexes.conf, either one of the two methods:")
        logger.info("   1 - Edit the file, adding diabled=true to [sample] stanza")
        logger.info("   2 - Copy '%s' over the file" % system_indexes_conf)
        logger.info("After that, you can again preview migration for all other changes.")
        sys.exit(18) #wtf number should I use, I no longer care

# Migrates any enabled (and potentially modified) WMI inputs that were shipped
# under etc\system\default\wmi.conf.
def migWmi_4_0_0(migWmiConf, dryRun):
    if not upgradingFromBeforeSplunk4():
        return  # this is only relevant when upgrading from 3.4.x

    # 3.4.x's etc\system\default\wmi.conf in a dict
    wmi_conf_default = {
        "WMI:LocalApplication": { "interval" : "10", "event_log_file" : "Application", "disabled" : "1" },
        "WMI:LocalSystem": { "interval" : "10", "event_log_file" : "System", "disabled" : "1" },
        "WMI:LocalSecurity": { "interval" : "10", "event_log_file" : "Security", "disabled" : "1" },
        "WMI:CPUTime": { "interval" : "5", "wql" : "SELECT PercentProcessorTime FROM Win32_PerfFormattedData_PerfOS_Processor", "disabled" : "1" },
        "WMI:Memory": { "interval" : "5", "wql" : "SELECT CommittedBytes, AvailableMBytes, PagesPerSec FROM Win32_PerfFormattedData_PerfOS_Memory", "disabled" : "1" },
        "WMI:LocalDisk": { "interval" : "5", "wql" : "SELECT PercentDiskTime, AvgDiskQueueLength FROM Win32_PerfFormattedData_PerfDisk_PhysicalDisk", "disabled" : "1" },
        "WMI:FreeDiskSpace": { "interval" : "5", "wql" : "SELECT FreeMegabytes FROM Win32_PerfFormattedData_PerfDisk_LogicalDisk", "disabled" : "1" },
        }

    if not os.path.exists( migWmiConf ):
        return

    old_backup_ext = ".old"

    # make backup of original if not dryrun
    comm.copyItem( migWmiConf, migWmiConf + old_backup_ext, dryRun )

    # this makes sure that all required properties are available in the migrated file
    stanzas = comm.readConfFile( migWmiConf )
    for stanza in stanzas:
        if stanza in wmi_conf_default:
            for k in wmi_conf_default[stanza]:
                if k not in stanzas[stanza]:
                    stanzas[stanza][k] = wmi_conf_default[stanza][k]

    comm.writeConfFile(migWmiConf, stanzas)


def migWinScriptedInputs_4_1(dryRun, isAfterBundleMove):
    def makeName(name, ext):
        return "script://$SPLUNK_HOME\\bin\\scripts\\splunk-%s.%s" % (name, ext)
    pyName = lambda name: makeName(name, "py")
    pathName = lambda name: makeName(name, "path")

    def makeConfPath(app = ""):
        if app:
            return chooseFile(bundle_paths.make_bundle_path(app, "inputs.conf"), dryRun, isAfterBundleMove)
        else:
            return chooseFile(bundle_paths.make_path("inputs.conf"), dryRun, isAfterBundleMove)  # system

    # make backup of original if file exists and is not a dryrun
    def doBackup(filename):
        old_backup_ext = ".old"
        if os.path.exists(filename):
            comm.copyItem(filename, filename + old_backup_ext, dryRun)

    if comm.isWindows:
      # print this message on windows only (SPL-37350)
      logger.info("\nHandling Windows scripted inputs...\n")

    # a list of all windows scripted inputs
    sinputs = ["wmi", "regmon", "admon"]

    # paths to all config's to search for scripted inputs in
    source_confs = [
        makeConfPath(),
        makeConfPath("search"),
        makeConfPath("launcher"),
        makeConfPath("windows") ]

    for sc in source_confs:
        stanzas = {}
        if os.path.exists(sc):
            # only attempt to read if file is present
            stanzas = comm.readConfFile(sc)

        changed = False
        if stanzas:
            for si in sinputs:
                if pyName(si) in stanzas:
                    # copy the ".py" entry contents into the equivalent ".path"
                    stanzas[pathName(si)] = stanzas[pyName(si)]
                    # remove the ".py" entry
                    del stanzas[pyName(si)]
                    changed = True

            if changed:
                # save back with the ".py" entries removed

                doBackup(sc)
                if dryRun:
                    logger.info("Would migrate file %s" % sc)
                else:
                    logger.info("Migrating file %s" % sc)
                    comm.writeConfFile(sc, stanzas)

#
# Starting in 4.1.0, lookup tables and search scripts are user- and app-scoped
# just like other conf objects. As a result, a lookup table or a search script
# in an app must be exported globally for it to be used from other apps.
#
# Log warnings about lookup tables or search scripts that might require such
# exports.
#

EXPORT_HELP_URL = 'http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/SetPermissions#Make_objects_globally_available'

def isLookupTable(path):
    return os.path.basename(path) != 'README'

#
# subdir = bundle subdirectory to inspect
# type = object type used in metadata
# is_correct_file_type = function that tests whether file is of desired <type>
#
def suggestExport(bundle, metadata, subdir, type, is_correct_file_type):
    base = bundle.location()
    try:
        candidate_files = glob.glob(os.path.join(base, subdir, '*'))
        filtered_files  = list(filter(is_correct_file_type, candidate_files))
        files_to_export = len(filtered_files) > 0
        files_already_exported = (metadata[type]['export'] == 'system')
    except:
        # probably a KeyError, meaning metadata does not export globally
        files_already_exported = False
    return (files_to_export and not files_already_exported)

def suggestGlobalExports_4_1():
    type = 'lookups'
    readable_type = 'lookup table files'

    # find apps that might contain lookup files in need of global export
    apps_to_suggest = []
    for b in bundle_paths.bundles_iterator():
        base = b.location()
        # read metadata from default.meta without worrying about layering
        metadata = {}
        metadata_file = os.path.join(base, 'metadata', 'default.meta')
        if os.path.exists(metadata_file):
            metadata.update(comm.readConfFile(metadata_file))
        # check lookup table files
        if suggestExport(b, metadata, type, type, isLookupTable):
            apps_to_suggest.append(b)

    # cons together app names
    apps_str = ""
    for b in apps_to_suggest:
        name = b.name()
        if len(apps_str) == 0:
            apps_str += ('\t%s' % name)
        else:
            apps_str += ('\n\t%s' % name)

    # print global export warning
    if len(apps_str) > 0:
        path = os.path.join(os.path.dirname(b.location()),
                            '<app_name>', 'metadata', 'local.meta')
        logger.warn(('\nThe following apps might contain %s that are not '      +
                     'exported to other apps:\n\n%s\n\n'                      +
                     'Such %s could only be used within their source app.  '  +
                     'To export them globally and allow other apps to '       +
                     'access them, add the following stanza to each %s file:' +
                     '\n\n\t[%s]\n\texport = system\n\n'                      +
                     'For more information, see %s.')
                     % (readable_type, apps_str, readable_type, path, type,
                        EXPORT_HELP_URL))

#
# 4.0.x -> 4.1.x migration for user prefs.
#
def migDefaultAppStanza_4_1(userPrefsConf, srcStanza, dstStanza):
    if not os.path.exists(userPrefsConf):
        return
    conf = comm.readConfFile(userPrefsConf)
    if ((srcStanza in conf) and
        (len(conf[srcStanza]) > 0) and
        (dstStanza not in conf)):
        conf[dstStanza] = conf[srcStanza]
        del conf[srcStanza]
        comm.writeConfFile(userPrefsConf, conf)

#
# Settings to be applied to all users used to be stored in the [default] stanza
# of /etc/apps/user-prefs. Now, they are stored in the [general_default]
# stanza.
#
def migGlobalDefaultApp_4_1(userPrefsConf):
    migDefaultAppStanza_4_1(userPrefsConf, "default", "general_default")

#
# Settings for particular users used to be stored in [default] stanzas of
# /etc/users/*/user-prefs. Now, they are stored in [general] stanzas.
#
def migUserDefaultApp_4_1(dryRun, isAfterBundleMove):
    candidate_files = glob.glob(os.path.join(PATH_ETC_USERS, '*', 'user-prefs', 'local', 'user-prefs.conf'))
    maybe_preview_files = [ chooseFile(f, dryRun, isAfterBundleMove) for f in candidate_files ]
    for f in maybe_preview_files:
        migDefaultAppStanza_4_1(f, "default", "general")

#
# Make locally-created viewstates visible to all apps so that saved searches
# can be moved between apps without breaking viewstate references.
#

def makeViewstatesGlobal(meta):
    if not os.path.exists(meta):
        return
    conf = comm.readConfFile(meta)
    need_write = False
    for k, v in conf.items():
        if not k.startswith('viewstates/'):
            continue
        v['export'] = 'system'
        need_write = True
    if need_write:
        comm.writeConfFile(meta, conf)

def migViewstatesGlobalExport_4_1_5(dryRun, isAfterBundleMove):
    candidate_files = glob.glob(os.path.join(PATH_APPS_DIR, '*', 'metadata', 'local.meta'))
    maybe_preview_files = [ chooseFile(f, dryRun, isAfterBundleMove) for f in candidate_files ]
    for f in maybe_preview_files:
        makeViewstatesGlobal(f)

######################
# Begin eventtype tag migration from eventtypes.conf to tags.conf
######################
def getCurrentTaggedEventtypes( typeConfFile ):
    conf = comm.readConfFile( typeConfFile )
    eventtypeTags = {}
    for k, v in conf.items():
        eventtype = k
        if "tags" in v and len(v["tags"]) > 0:
            eventtypeTags[ eventtype ] = v["tags"].split()
    return eventtypeTags

def getCurrentEventtypeTags( tagConfFile ):
    conf = comm.readConfFile( tagConfFile )
    eventtypeTags = {}
    for k, v in conf.items():
        if k == "eventtype":
            for g, k in v.items():
                vars = g.split("::")
                if( len(vars) != 3 ):
                    print("Failed to parse " + str(vars) + " as a tag")
                type = vars[1]
                tag = vars[2]
                if type not in eventtypeTags:
                    eventtypeTags[type] = [ tag ]
                else:
                    eventtypeTags[type].append( tag )
    return eventtypeTags, conf

def mergeEventtypeTagsIntoTags( incomingTags, tagsConfFile, isDryRun=False ):
    if not incomingTags:
        ##Nothing to do
        return
    currentTags, conf = getCurrentEventtypeTags(tagsConfFile)    
    if "eventtype" not in conf:
        conf["eventtype"] = {}
    for type in incomingTags:
        tags = incomingTags[ type ]
        if type in currentTags:
            for ctag in currentTags[type]:
                if ctag in tags:
                    tags.remove( ctag )
        for tag in tags:
            conf["eventtype"]["tag::" + type + "::" + tag ] = "enabled"
        if tags:
            print("Migrated the following tags from eventtype=%s %s" % (type, str(tags)))
    if not isDryRun:
        comm.writeConfFile( tagsConfFile, conf )


def migEventTypeTags_4_0_0( typeConfFile, tagConfFile, isDryRun):
    mergeEventtypeTagsIntoTags( getCurrentTaggedEventtypes( typeConfFile ), tagConfFile, isDryRun )
##############
# End type tag migration
###############
    
def migInputs_3_3_0(path, isDryRun):
  """
  Convert deprecated inputs to new ones:
  - if there's a tail://, convert it to monitor://.
  - if there was a batch://...
    - if it had move_poly = sinkhole, leave it untouched!
    - otherwise, comment that line and change stanza to monitor://.

  In an attempt to preserve comments, some trickery is employed.  Instead of
  reading via readConfFile and writing out the new settings via
  writeConfFilePath, which will toss all the comments, we use the former to
  load all the settings, and then do a bunch of sed() calls to make changes.
  """
  if not os.path.exists(path):
    return

  tailInputs          = []
  batchInputsNormal   = [] # move_policy != sinkhole, or not specified.
  batchPrefix         = 'batch://'
  monitorPrefix       = 'monitor://'
  tailPrefix          = 'tail://'
  movePolicyKey       = 'move_policy'
  sinkholePolicy      = 'sinkhole'

  # start by reading the file into our dicts, to easily find all tail stanzas,
  # all batch stanzas that should change to monitor, and all batch stanzas that
  # are sinkholes and should remain untouched.
  localInputs = comm.readConfFile(path)
  for input, settings in localInputs.items():
    # tail:// inputs...
    if input.startswith(tailPrefix):
      tailInputs.append(input)
    # batch:// inputs...
    elif input.startswith(batchPrefix):
      # if it's not a sinkhole, hold on to it.
      if (not movePolicyKey in settings) or (settings[movePolicyKey] != sinkholePolicy):
        batchInputsNormal.append(input)

  # now that we know which stanzas should change to what, we can just do a bunch
  # of regex replacements on the conf file.
  
  # start by converting the tail and batch (non-sinkhole) stanzas...
  for inputList, inputPrefix in (
      (tailInputs,        tailPrefix),
      (batchInputsNormal, batchPrefix)
      ):
    for oneInput in inputList:
      # strip out the prefix and get the path.
      inputPath = oneInput.replace(inputPrefix, '', 1)
      # pick out everything surrounding input prefix in the stanza.
      searchRE  = r"^(\s*\[)%s(%s\]\s*)$" % (inputPrefix, re.escape(inputPath))
      # replace the stanza with tail:// or batch:// changed to monitor://.
      replaceRE = r"\1%s\2" % monitorPrefix
      # actually run the regex.
      comm.sed(searchRE, replaceRE, path, inPlace = True)

  # since move_policy settings that are 'passive_copy' and 'passive_symlink'
  # are no longer any use to us, just comment them out.  'sinkhole' remains.
  policySearch  = r'^(\s*move_policy\s*=\s*passive_.*)'
  policyReplace = r'# DEPRECATED (SPLUNK MIGRATED): \1'
  comm.sed(policySearch, policyReplace, path, inPlace = True)


def migWinSavedSearches(args, fromCLI):
  """
  CLI wrapper for windows saved search migration.
  """
  paramsReq = ()
  paramsOpt = (ARG_DRYRUN, ARG_NOWAIT,)
  comm.validateArgs(paramsReq, paramsOpt, args)

  delay, isDryRun = 5, False
  if ARG_NOWAIT in args and comm.getBoolValue(ARG_NOWAIT, args[ARG_NOWAIT]):
    delay = 0
  if ARG_DRYRUN in args and comm.getBoolValue(ARG_DRYRUN, args[ARG_DRYRUN]):
    isDryRun = True

  logger.info('This command will update your saved searches, but you must review its changes' + '\n' +
                'once it is finished.'                                                          + '\n' +
                                                                                                  '\n' +
                'Will begin in %d seconds (press Ctrl-C to cancel).' % delay                    + '\n')

  time.sleep(delay)

  if not os.path.exists(PATH_SAVSRCH_CONF):
    raise cex.FilePath("Nothing to migrate - path doesn't exist (%s)." % PATH_SAVSRCH_CONF)

  if not isDryRun:
    bakPath = PATH_SAVSRCH_CONF + BACKUP_EXT
    comm.copyItem(PATH_SAVSRCH_CONF, bakPath, isDryRun)

  path = chooseFile(PATH_SAVSRCH_CONF, isDryRun, useNewPaths=True)
  migWinSavedSearchesWorker(path, isDryRun)

  logger.info("Updated: %s." % path)


def migWinSavedSearchesWorker(path, isDryRun):
  """
  This guy does the work of actually migrating saved searches based on the old Windows
  field names.  It should only be run after 3.3.0 migration has finished, otherwise it
  will report errors.

  This SHOULD NOT be run as a part of autoMigrate(), as its results may not always be
  completely correct, due to the nature of the conversion.
  """
  if not os.path.exists(path):
    raise cex.FilePath("Nothing to migrate - path doesn't exist (%s)." % path)

  confDict = comm.readConfFile(path)


  def makeOldName(name):
    return str(name) + "-old"

  regexes = (
      (re.compile(r'\bevtlog_category\b'),  'CategoryString'),
      (re.compile(r'\bevtlog_id\b'),        'EventCode'),
      (re.compile(r'\bevtlog_severity\b'),  'Type'),
      (re.compile(r'\bevtlog_account\b'),   'User'),
      (re.compile(r'\bevtlog_domain\b'),    'ComputerName'),
      (re.compile(r'\bevtlog_sid\b'),       'Sid'),
      (re.compile(r'\bevtlog_sid_type\b'),  'SidType'))
  newSSs = {}
  for oneSSName, oneSSSetts in confDict.items():
    if "search" in oneSSSetts:
      copied = False
      for regex, replacement in regexes:
        if not copied:
          # should we backup?
          if regex.search(oneSSSetts["search"]) != None:
            copied = True
            newSSs[makeOldName(oneSSName)] = copy.deepcopy(oneSSSetts)
        confDict[oneSSName]["search"] = regex.sub(replacement, oneSSSetts["search"])
  for name, setts in newSSs.items():
    confDict[name] = setts

  comm.writeConfFile(path, confDict)


def migSSLConf_4_0_0(path):
  """
  Clear up ambiguities in server.conf:
    keyfile         -> sslKeysfile
    keyfilePassword -> sslKeysfilePassword
  """
  STANZA_SSL       = "sslConfig"
  KEY_KEYFILE_OLD  = "keyfile"
  KEY_KEYFILE_NEW  = "sslKeysfile"
  KEY_PASSWORD_OLD = "keyfilePassword"
  KEY_PASSWORD_NEW = "sslKeysfilePassword"

  if not os.path.exists(path):
    return

  changed = False

  settsDict = comm.readConfFile(path)
  if STANZA_SSL in settsDict and KEY_KEYFILE_OLD  in settsDict[STANZA_SSL]:
    changed = True
    settsDict[STANZA_SSL][KEY_KEYFILE_NEW]  = settsDict[STANZA_SSL].pop(KEY_KEYFILE_OLD)
  if STANZA_SSL in settsDict and KEY_PASSWORD_OLD in settsDict[STANZA_SSL]:
    changed = True
    settsDict[STANZA_SSL][KEY_PASSWORD_NEW] = settsDict[STANZA_SSL].pop(KEY_PASSWORD_OLD)

  if not changed:
    return

  comm.writeConfFile(path, settsDict)


def migAuthConf_4_0_0(path):
  """
  Lowercase splunk roles in LDAP role mappings, since our roles are all
  lowercased now.
  """
  STANZA_ROLEMAP = "roleMap"

  if not os.path.exists(path):
    return

  confDict = comm.readConfFile(path)

  if not STANZA_ROLEMAP in confDict:
    return

  changed = False
  for key in confDict[STANZA_ROLEMAP]:
    lowercased = key.lower()
    if key != lowercased:
      changed = True
      confDict[STANZA_ROLEMAP][lowercased] = confDict[STANZA_ROLEMAP].pop(key)

  if not changed:
    return

  comm.writeConfFile(path, confDict)

def migLDAP_4_1(path, isDryRun):
  """
  Backup etc/passwd if this is an LDAP setup before 4.1. This prevents old splunk users
  from being able to login. If we back up passwd, touch it afterwards so we do not seed
  it with admin/changeme. It will be seeded with the failsafeUser when LDAP is initialized.

  If we're treating users as groups, make sure groupMappingAttribute/groupMemberAttribute
  are set to the same attribute as userNameAttribute. Previously these attribute values
  were ignored if userBaseDN was the same as groupBaseDN.
  """
  if not os.path.exists(path):
    return

  confDict = comm.readConfFile(path)

  # First ensure we have the required keys
  authen = 'authentication'
  authType = 'authType'
  authSettings = 'authSettings'
  if authen not in confDict or authType not in confDict[authen] or authSettings not in confDict[authen]:
    return

  # Only migrate if we're using LDAP and the settings exist
  if confDict[authen][authType] != 'LDAP' or confDict[authen][authSettings] not in confDict:
    return

  stanza = confDict[authen][authSettings]
  settings = confDict[stanza]

  # Key names
  failsafeLogin = 'failsafeLogin'
  failsafePassword = 'failsafePassword'
  pageSize = 'pageSize'
  groupBase = 'groupBaseDN'
  userBase = 'userBaseDN'
  memberAttr = 'groupMemberAttribute'
  mappingAttr = 'groupMappingAttribute'
  usernameAttr = 'userNameAttribute'

  writeConf = False
  backupPasswd = False

  # Remove the deprecated pageSize key
  if pageSize in settings:
    del settings[pageSize]
    writeConf = True

  # Having a non-empty failsafe user means this is a pre-4.1 setup
  if failsafeLogin in settings and failsafePassword in settings:
    if len(settings[failsafeLogin]) == 0:
      # This installation has run 4.1: the failSafe has been cleared by in-code migration. Delete these keys
      del settings[failsafeLogin]
      del settings[failsafePassword]
      writeConf = True
    else:
      ##### This user has NOT run 4.1 yet, backup the passwd file to prevent splunk/LDAP user conflicts
      backupPasswd = True

      # If this is an old LDAP setup where users are treated as groups, set mapping/member attributes correctly
      if groupBase in settings and userBase in settings and settings[groupBase] == settings[userBase]:
        if usernameAttr in settings:
          settings[memberAttr] = settings[usernameAttr]
          settings[mappingAttr] = settings[usernameAttr]
          writeConf = True

  if backupPasswd:
    if os.path.exists(PATH_PASSWD_FILE):
      logger.info('LDAP was determined to be pre-4.1: Backing up etc/passwd file to etc/passwd.bak')
      comm.moveItem(PATH_PASSWD_FILE, PATH_PASSWD_BAK_FILE, isDryRun)

    # Regardless of whether we moved the passwd file or it didn't exist, touch it to prevent user seeding
    comm.touch(PATH_PASSWD_FILE)

  if writeConf:
    if isDryRun:
      logger.info('Would have modified LDAP configuration in ' + path)
    else:
      comm.writeConfFile(path, confDict)


def migLDAP_4_3(path, isDryRun):
  """
  Migrate for multi-domain LDAP
  - change [roleMap] to [roleMap_<active_strat>]
  - Replace any commas in strategy names
  """
  if not os.path.exists(path):
    return

  # Use the existence of [roleMap] to determine if we've migrated already
  STANZA_ROLEMAP = 'roleMap'
  confDict = comm.readConfFile(path)
  if STANZA_ROLEMAP not in confDict:
    return

  # If we're missing the required keys to find an active strategy, just move the rolemap somewhere
  authen = 'authentication'
  authType = 'authType'
  authSettings = 'authSettings'
  if    authen not in confDict or \
        authType not in confDict[authen] or \
        authSettings not in confDict[authen] or \
        confDict[authen][authType] != 'LDAP':
    confDict[STANZA_ROLEMAP + '_unused'] = confDict.pop(STANZA_ROLEMAP)
  else:
    # Okay, we have an active strategy. Check for commas in the strategy name and move the strategy/rolemap
    stratname = confDict[authen][authSettings]
    if stratname.count(',') > 0:
      stratname = stratname.replace(',', '-')
      if confDict[authen][authSettings] in confDict:
        confDict[stratname] = confDict.pop(confDict[authen][authSettings])
      confDict[authen][authSettings] = stratname

    confDict[STANZA_ROLEMAP + '_' + stratname] = confDict.pop(STANZA_ROLEMAP)

  if isDryRun:
    logger.info('Would have modified LDAP configuration in ' + path + ' for multi-domain support' )
  else:
    comm.writeConfFile(path, confDict)


def migPAM_Scripted_4_1(path, isDryRun):
  """
  The old pamScripted.py example auth script was heinously insecure, so check
  to see if they are using it with some grepping around. If they are, throw
  up a big warning message and move the script so they don't use it.
  """
  if not os.path.exists(path):
    return

  confDict = comm.readConfFile(path)

  # First ensure we have the required keys
  authen = 'authentication'
  authType = 'authType'
  authSettings = 'authSettings'
  if authen not in confDict or authType not in confDict[authen] or authSettings not in confDict[authen]:
    return

  # Only migrate if we're using Scripted and the settings exist
  if confDict[authen][authType] != 'Scripted' or confDict[authen][authSettings] not in confDict:
    return

  stanza = confDict[authen][authSettings]
  settings = confDict[stanza]

  # Look for the path of the script, making sure it exists
  if 'scriptPath' not in settings:
    return

  # The script path line contains the call to python, so grab everything after that and try that path
  # Clearly this won't ALWAYS work, a path could have 'python ' in it. But you can't simply split on spaces
  script = settings['scriptPath']
  pyloc = script.find('python ')
  if pyloc == -1:
    return

  script = script[pyloc + len('python '):]
  script = bundle_paths.expandvars(script.strip())

  if not os.path.exists(script):
    return

  # Read at most 20k bytes of the file (the initial sample script is ~6 KB)
  FH = open(script)
  contents = FH.read(20 * 1024)
  FH.close()

  # Search for some old indicators of the bad script. Print a big warning message
  if contents.find('shell=True') != -1 and contents.find('pamauth " + str(infoIn[') != -1:
    logger.warn('********************************   WARNING   ********************************')
    logger.warn('The sample PAM authentication script being used is deprecated and poses a security risk.')
    if not isDryRun:
      logger.warn('The script will be disabled by moving it to ' + script + '.bak')
      logger.warn('Please copy the new version of pamScripted.py to ' + script + ' and edit it with your PAM settings.')
    logger.warn('******************************** END WARNING ********************************')
    comm.moveItem(script, script + '.bak', isDryRun)

# helpers for migMANIFESTtoAppConf_4_1
def get_manifest_states(bundle):
    "return a dict for located manifest paths, of path -> enable/disable"

    def manifest_status(path):
        "is the MANIFEST enabled or disabled?, or not there"
        conf_dict = splunk.clilib.cli_common.readConfFile(path)
        manifest_state = None
        try:
            manifest_state = conf_dict['install']['state']
        except KeyError:
            pass
        if manifest_state not in ('enabled', 'disabled'):
            logger.warn("App state in '%s' is not declared enabled or disabled, we default to enabled." % path)
            manifest_state = 'enabled'
        return manifest_state

    states = {}
    app_path = bundle.location()
    for subdir in (app_path, os.path.join(app_path, 'default'), os.path.join(app_path, 'local')):
        manifest_path = os.path.join(subdir, 'MANIFEST')
        if not os.path.isfile(manifest_path):
            continue
        states[manifest_path] = manifest_status(manifest_path)
    return states

def create_appconf(appconf_path, enabled, dryRun):
    "make a app.conf (or preview) in the requested directory"
    dirname = os.path.dirname(appconf_path)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    conf_template = """
[default]

[install]
state = %s
"""
    if dryRun:
        appconf_path = getPreviewName(appconf_path)
    cf = open(appconf_path, 'w')
    cf.write(conf_template % enabled)


def migMANIFESTtoAppConf_4_1(dryRun):
    """ for apps that have MANIFEST files but no app.conf, create equivalent app.conf entires.
        This avoids cases where apps enable/disable themselves when upgraded from 3.x to 4.x """
    if getMigHistory('migrated_manifests'):
        # this thing already fired
        return

    for bundle in bundle_paths.bundles_iterator():
        manifest_states = get_manifest_states(bundle)

        local_appconf = os.path.join(bundle.location(), 'local', 'app.conf')
        default_appconf = os.path.join(bundle.location(), 'default', 'app.conf')

        # sanity checks
        if not manifest_states:
            # no manifests to convert, nothing to do
            continue

        if os.path.exists(local_appconf) or os.path.exists(default_appconf):
            # somehow already configured for 4.x
            logger.warn("""Note: The app '%s' has both 3.x style MANIFEST files and 4.x style app.conf files.  
You may wish to review this app's state in manager to ensure it is enabled or disabled in accordance with your desires.
""" % bundle.name())
            continue

        logger.info("Creating 4.x style app.conf config files for the app '%s' to match the previously existing 3.x style MANIFEST files." % bundle.name())
        
        #logger.info("confdata " + str(manifest_states))
        # create default app.conf for toplevel or default manifest
        app_def_setting = None
        for default_path in [os.path.join(bundle.location(), 'MANIFEST'),
                             os.path.join(bundle.location(), 'default', 'MANIFEST')]:
            #logger.info("testing " + default_path)
            if default_path in manifest_states:
                app_def_setting = manifest_states[default_path]
        if app_def_setting:
            #logger.info("adding " + default_appconf)
            create_appconf(default_appconf, app_def_setting, dryRun)

        # create locl app.conf for local manifest
        local_manifest_path = os.path.join(bundle.location(), 'local', 'MANIFEST')
        if local_manifest_path in manifest_states:
            #logger.info("adding " + local_appconf)
            create_appconf(local_appconf, manifest_states[local_manifest_path], dryRun)

    # if this isn't a dry run, make a note that we've done this warning check.
    setMigHistory('migrated_manifests', 'true', dryRun)


def showPreviewFiles(previewFileList):
  """
  if this is a dry run, let's make sure we display all the files that would have been changed.
  we will not display preview files that were unchanged from the original versions.
  """
  toRemove     = [] 
  # get rid of preview files that have not changed from the original version (if it exists).
  for prevFile in previewFileList:
    unprevFile = getUnpreviewName(prevFile)
    # for some of these preview files, a direct counterpart doesn't exist.  they don't need dupe checking anyway.
    if os.path.exists(unprevFile):
      fileIsSame = filecmp.cmp(prevFile, unprevFile, shallow = False)
      # if the file hasn't changed, add it to our trim list.
      if fileIsSame:
        toRemove.append(prevFile)
  # for every file that we saved, delete it and remove it from the list.
  for dupeFile in toRemove:
    # remove the .migratePreview file - it's the same as the existing file (no change).
    os.unlink(dupeFile)
    # and take it out of the list we display.
    previewFileList.remove(dupeFile)
  # now do the notifications.
  logger.notice("\nThe following files would be created or modified (without the %s extension):\n%s"
                % (SUF_MIGRATE, str.join(str("\n"), [("  " + x) for x in previewFileList])))


def warnUnmigratableFiles(isDryRun):
  """
  there are a few config files that we don't have any migration code for, at
  least in 4.0.  make sure users are aware of this if it affects them.
  """

  if not upgradingFromBeforeSplunk4():
    return

  badPaths_4_0_0 = (bundle_paths.make_path("deployment.conf"),
                    bundle_paths.make_path("distsearch.conf"),
                    bundle_paths.make_path("outputs.conf"))

  hasUnmigratableFiles = False
  for badPath in badPaths_4_0_0:
    if os.path.exists(badPath):
      if not hasUnmigratableFiles: # first occurrence
        logger.warn("\nCannot automatically migrate:")
      hasUnmigratableFiles = True
      logger.warn("  %s" % badPath)
  if hasUnmigratableFiles:
    if isDryRun:
      logger.warn(UNMIGRATABLE_PROMPT)
    else:
      if not comm.prompt_user(UNMIGRATABLE_PROMPT, checkValidResponse = True):
        raise cex.StopException(UNMIGRATABLE_MSG)


def replaceLicense(isDryRun):
  """
  the 3.x license is incompatible with 4.0.  if we haven't seen a 4.0 
  installation before, copy over our 4.0 splunk-free license to get the user
  started.  if a splunk-user.license exists, copy that over instead of the free
  license, so users have some reasonable way to automate this.

  we decide to replace the license only upon seeing <serverName> in splunkd.xml,
  as this indicates that we've come from a splunk version that's never been
  upgraded to 4.x.
  """

  if not upgradingFromBeforeSplunk4():
    return

  # backup old license.
  if os.path.exists(PATH_LICENSE_ACTIVE):
    comm.moveItem(PATH_LICENSE_ACTIVE, PATH_LICENSE_ACTIVE + BACKUP_EXT, isDryRun)

  # copy new license in place.
  licPath = os.path.exists(PATH_LICENSE_USER) and PATH_LICENSE_USER or PATH_LICENSE_FREE
  comm.copyItem(licPath, PATH_LICENSE_ACTIVE, isDryRun) 


def replaceSplunkdXml_4_0_7(srcPath, dstPath, isDryRun):
  """
  Clobber the user's existing splunkd.xml with our freshly shipped one.  As of
  4.0.0, there is no user-configurable data in splunkd.xml.  migSplunkdXml_4_0_0
  will have been called already, so any user settings are in server.conf at this
  point.
  """
  if not os.path.exists(srcPath):
    raise cex.FilePath("Cannot copy '%s' to '%s' - if this is a development build, you may"
        " want to:\n\tcp '%s' '%s'" % (srcPath, dstPath, dstPath, srcPath))
  comm.copyItem(srcPath, dstPath, isDryRun)


def warnOutdatedApps():
  """
  Upon initial upgrade from pre-4.0 to 4.x, warn about apps that don't appear to
  be compatible with 4.x.  We determine this by looking for the metadata
  directory in the app, which is essentially required for 4.x apps.
  Also special-case a warning for the CM and PCI apps, which are only for 3.x.
  """
  if not upgradingFromBeforeSplunk4():
    return # have already warned once before.
  knownIncompatibleApps = ("change_management", "pci") 

  # check for apps that we KNOW aren't yet 4.x.
  foundIncompatibleApps = []
  lowerAppList = [x.lower() for x in os.listdir(PATH_APPS_DIR)] # lowercase to ease comparisons.
  for app in knownIncompatibleApps:
    if app in lowerAppList:
      foundIncompatibleApps.append(app)
  if len(foundIncompatibleApps) > 0:
    logger.warn("")
    logger.warn("The following 3.x Apps in your Splunk deployment are incompatible with Splunk 4")
    logger.warn("and must be replaced:")
    for app in foundIncompatibleApps:
      logger.warn("  %s" % app)
    logger.warn("Updated versions of these Apps are not yet available. Please file a case online at http://www.splunk.com/page/submit_issue to")
    logger.warn("learn when updated versions will be released.")
  
  # now find the rest, by checking for metadata dirs.
  appsWithoutMetadata = []
  for app in os.listdir(PATH_APPS_DIR):
    if not app.lower() in knownIncompatibleApps: # skip dupes of above.
      metadataPath = os.path.join(PATH_APPS_DIR, app, "metadata")
      if not os.path.exists(metadataPath):
        appsWithoutMetadata.append(app)
  if len(appsWithoutMetadata) > 0:
    logger.warn("")
    logger.warn("The following 3.x Apps in your Splunk deployment must be updated before they will")
    logger.warn("work properly with Splunk 4:")
    for app in appsWithoutMetadata:
      logger.warn("  %s" % app)
    logger.warn("Visit the following URL and review the Splunk Developer Manual to learn how to")
    logger.warn("convert your 3.x Apps:")
    logger.warn("  http://docs.splunk.com/Documentation/Splunk/latest/Developer/Migrate3x")

  logger.info("")


def backupPasswdIfPre_4_1_4(path, dryRun):
  """
  SPL-31724.  Backup passwd file if it has the old school password fields, which
  only have 2 $s instead of 3.
  Warns as well, once upon migration, and once upon each FTR afterwards, if the
  backup file exists.
  """
  backupPath = path + "-formatchange.bak"
  if os.path.exists(backupPath):
    logger.warn("\nThe password backup file at '%s' contains insecure passwords.  This file exists solely"
                " to preserve the ability to downgrade from 4.1.4+ to 4.1.3 and below, if necessary.  If"
                " you have no need to downgrade, please consider removing or archiving this insecure file.\n"
                % backupPath)
  if not os.path.exists(path) or os.stat(path).st_size == 0:
    return # fresh install, or passwd file has already been wiped by migLDAP_4_1 during prior upgrade.
  # old passwd files begin w/ uid, new ones don't have it - thus * instead of +.
  if len(comm.grep(r"^[^:]*:[^:]+:\$[^:]+\$[^:]+\$", path)) > 0:
    return # already have lines w/ 3 $s in them.
  comm.copyItem(path, backupPath, dryRun)
  logger.warn("\nSplunk will convert '%s' to a more secure format.  The existing password file has been"
              " backed up at '%s'.  This backup still contains weak passwords, and exists only to"
              " preserve the ability to downgrade to versions 4.1.3 and below.  Please consider removing"
              " or archiving this backup, to increase the security of your users' passwords.\n"
              % (path, backupPath))


def removeListtails_4_1_4(dryRun):
  """
  SPL-31603.  This thing was based on the old tailer, which no longer exists.
  """
  listtailsPath = make_splunkhome_path(["bin", "listtails"])
  if os.path.exists(listtailsPath):
    comm.removeItem(listtailsPath, dryRun)


def migDataExtractionsXml_4_1_5(dryRun):
  """
  SPL-31174.  This view was left around when migrating to 4.1, and doesn't work
  (uses old endpoints).
  """
  old_data_extractions = make_splunkhome_path(["etc", "apps", "search", "default", "data", "ui", "manager", "data_extractions.xml"])
  if os.path.exists(old_data_extractions):
    comm.removeItem(old_data_extractions, dryRun)


def removeDeployModule_ItsHammerTime(dryRun):
  """
  SPL-26055.  Deploment client/server are no longer initted from a processor.  Avoid error in logs.
  """
  tailConfigPath = make_splunkhome_path(["etc", "modules", "distributedDeployment", "config.xml"])
  tailConfigBak  = tailConfigPath + BACKUP_EXT
  if os.path.exists(tailConfigPath):
    comm.moveItem(tailConfigPath, tailConfigBak, dryRun)


def addOldSourcetypePulldowns_4_2_0(dryRun):
  """
  SPL-33819.  We're trimming the sourcetype pulldown list in the UI for 4.2.0+ fresh installs,
  but want to preserve the list for upgraders.
  """
  # ensure upgrading from pre-4.2.
  if not upgradingFromBeforeSplunk4_2():
    return
  # if legacy app is already enabled, nothing to do.
  if isAppEnabled("legacy"):
    return
  if dryRun:
    logger.info("Would enable 'legacy' app to add old sourcetypes to SplunkWeb.")
  else:
    logger.info("Enabling 'legacy' app to add old sourcetypes to SplunkWeb.")
    setStoppedSplunkd("/services/admin/localapps/legacy/enable", [])


def removeUnnecessaryApps_4_2_0(dryRun):
  """
  SPL-34487.  Windows/Unix apps are being removed from the default package, as of 4.2.  If upgrading
  from before that version, check whether the apps were enabled - if so, untar the appropriate app,
  which is preserved in the package as a tarball.
  """
  if not upgradingFromBeforeSplunk4_2():
    return
  # upgrade from pre-4.2 to >4.1.
  for app in ("unix", "windows"):
    appPath  = make_splunkhome_path(["etc", "apps", app])
    if not isAppEnabled(app):
      # though 4.0 had windows app enabled by default, which could mean
      # it shows as disabled here,
      # 4.1 required config, which made it enabled in local when in use.
      # Thus, skipping this is correct for all but 4.0 direct to 4.2 for windows
      # Skip is always correct for unix
      continue
    tarPath  = make_splunkhome_path(["share", "splunk", "migration", "app_contents_%s.tar.gz" % app])
    if dryRun:
      logger.info("Would extract '%s' to '%s'." % (tarPath, appPath))
    else:
      logger.info("Extracting '%s' to '%s'." % (tarPath, appPath))
      tar = tarfile.open(tarPath, "r:gz")
      tar.extractall(appPath) # extract into the app dir.
      tar.close()
  # now that tars are fixed, we dont need to do fixMismigratatedApps_4_2_1
  setMigHistory('fixed_up_unixwin_apps', 'true', dryRun)


def fixMismigratatedApps_4_2_1(dryRun):
  """
  SPL-38340 / SPL-38402.  Function above (removeUnnecessaryApps_4_2_0) is correct, but
  shipped with wrong tar files, so redo if app is still broke.
  """
  if getMigHistory('fixed_up_unixwin_apps'):
      # this thing already fired
      return
  for app in ("unix", "windows"):
    appPath  = make_splunkhome_path(["etc", "apps", app])
    # sniff for removeUnnecessaryApps_4_2_0 breakage, if not there, nothing to
    # do.  Note app.conf.in wont exist for the general case
    if (os.path.exists(os.path.join(appPath, "default", "app.conf")) or 
        not os.path.exists(os.path.join(appPath, "default", "app.conf.in"))):
      continue
    tarPath  = make_splunkhome_path(["share", "splunk", "migration", "app_contents_%s.tar.gz" % app])
    if dryRun:
      logger.info("Would extract '%s' to '%s'." % (tarPath, appPath))
    else:
      logger.info("Extracting '%s' to '%s'." % (tarPath, appPath))
      tar = tarfile.open(tarPath, "r:gz")
      tar.extractall(appPath) # extract into the app dir.
      tar.close()
  setMigHistory('fixed_up_unixwin_apps', 'true', dryRun)

def removeEchoSh(dryRun):
  """
  SPL-70250. Remove echo.sh and echo_output.txt (if present) in order to prevent vulnerability
  """

  dirpath = make_splunkhome_path(["bin", "scripts", EXT_DEPRECATED])
  if os.path.exists(PATH_BIN_ECHO_SH):
     if dryRun:
       logger.info("Will remove '%s' and move to '%s' directory. If you have modified echo.sh"
                   " for some reason, please handle alert appropriately." % (PATH_BIN_ECHO_SH, dirpath))
     else:
       if not os.path.exists(dirpath):
          os.mkdir(dirpath)
       comm.moveItem(PATH_BIN_ECHO_SH, os.path.join(dirpath, "echo.sh"), dryRun)

  if os.path.exists(PATH_BIN_ECHO_OUTPUT_TXT):
     if dryRun:
       logger.info("Will remove '%s' and move to '%s' directory, since echo_output.txt is insecure"
                   % (PATH_BIN_ECHO_OUTPUT_TXT, dirpath))
     else:
       if not os.path.exists(dirpath):
          os.mkdir(dirpath)
       comm.moveItem(PATH_BIN_ECHO_OUTPUT_TXT, os.path.join(dirpath, "echo_output.txt"), dryRun)

def removeUnnecessaryApp_5_0(dryRun):
  """
  SPL-49155. Similar to removeUnnecessaryApps_4_2_[01], the SplunkDeploymentMonitor app is being
  removed from the default package in 5.0.  If upgrading from before that version, check whether the
  app is enabled - if so, untar the appropriate app, which is preserved in the package as a tarball.
  """
  if getMigHistory('fixed_up_deployment_app'):
      # this thing already fired
      return
  app = "SplunkDeploymentMonitor"
  appPath = make_splunkhome_path(["etc", "apps", app])
  if isAppEnabled(app):
    tarPath  = os.path.join(comm.splunk_home, "share", "splunk",
      "migration", "app_contents_%s.tar.gz" % app) 
    if dryRun:
      logger.info("Would extract '%s' to '%s'." % (tarPath, appPath))
    else:  
      logger.info("Extracting '%s' to '%s'." % (tarPath, appPath))
      tar = tarfile.open(tarPath, "r:gz", errorlevel=1)

      # extract the files themselves.  unlike extractall(), this doesn't do perms/etc.
      for a_file in tar:
          try:
              tar.extract(a_file, appPath)
          except IOError:
              os.remove(os.path.join(appPath, a_file.name))
              tar.extract(a_file, appPath)

      # do a 2nd pass and fix modes.  this is the same way extractall() works, to avoid
      # issues like creating a dir w/ no write bit, then trying to create files in it.
      for a_file in tar:
          os.chmod(os.path.join(appPath, a_file.name), a_file.mode)

      tar.close()
  # now that tars are fixed, we dont need to do fixMismigratatedApps_4_2_1
  setMigHistory('fixed_up_deployment_app', 'true', dryRun)

def replaceLocalNavXml_6_0_0(srcPath, dstPath, dryRun):
  """
  SPL-69041. If there is an existing local/data/ui/nav/default.xml in the Search app move
  it to local/data/ui/nav/old_default.xml. This way the default nav xml will be used but
  the users local nav xml will not be destroyed.
  """
  if os.path.exists(srcPath):
    comm.moveItem(srcPath, dstPath, dryRun)

def relocateSplunkwebSSLCerts_4_2_0(webConfPath, isDryRun):
  """
  SPL-34397.  Relocate splunkweb's SSL certificates from $SPLUNK_HOME/share/splunk/certs
  to $SPLUNK_HOME/etc/auth/splunkweb if the user hasn't specified a custom path for certs
  Else update cert paths in web.conf to make relative to $SPLUNK_HOME
  """
  oldCertDir = make_splunkhome_path(['share', 'splunk', 'certs'])
  newCertDir = make_splunkhome_path(['etc', 'auth', 'splunkweb'])
  oldPrivKeyPath = os.path.join(oldCertDir, 'privkey.pem')
  newPrivKeyPath = os.path.join(newCertDir, 'privkey.pem')
  oldCertPath = os.path.join(oldCertDir, 'cert.pem')
  newCertPath = os.path.join(newCertDir, 'cert.pem')

  if os.path.exists(newCertDir) or not os.path.exists(oldPrivKeyPath) or not os.path.exists(oldCertPath):
    return

  # First create the new certificate directory
  if isDryRun:
    logger.info("Would create %s" % newCertDir)
  else:
    os.mkdir(newCertDir)

  # next determine if there's a local setting for privKeyPath/caCertKey
  # if so, we don't relocate the files to the new directory
  # but we do update the paths to make them relative in the .conf file
  if os.path.exists(webConfPath):
    modified = False
    newFile = []
    with open(webConfPath, 'rt') as f:
      for line in f:
        if '=' in line and not line.startswith('#'):
          key, val = [x.strip() for x in line.split('=', 1)]
          if key=='privKeyPath' or key=='caCertPath':
            modified = True
            # make sure we have the correct path separators for this os first
            val = os.path.normpath(val)
            line = "%s = %s\n" % (key, os.path.join('share', 'splunk',  val.lstrip(os.sep)))
        newFile.append(line)
    if modified:
      logger.info("Updating %s" % webConfPath)
      with open(webConfPath, 'wt') as f:
        f.write(''.join(newFile))
      # dont relocate the cert files if the user has specified a cert path
      return

  try:
    comm.moveItem(oldPrivKeyPath, newPrivKeyPath, isDryRun)
    comm.moveItem(oldCertPath, newCertPath, isDryRun)
  except IOError as e:
    logger.info("Failed to relocate existing certificate files: %s" % (e,))
    return

  if not isDryRun:
    try:
      logger.info("Removing old cert dir %s" % oldCertDir)
      os.rmdir(oldCertDir)
    except OSError as e:
      logger.warn("Failed to remove old certificate directory %s: %s" % (oldCertDir, e))


def removeOldManagerLicensing_4_2_0(dryRun):
  """
  SPL-33809: Weywey replaced the old licensing pages in manager with stuff suitable
  for the new licensing features, but the old files still stick around in tar upgrades.
  """
  files = ("admin_licenseNG.xml", "admin_license.xml")
  for file in files:
    filePath = make_splunkhome_path(["etc", "apps", "search", "default", "data", "ui", "manager", file])
    if os.path.exists(filePath):
      comm.removeItem(filePath, dryRun)


def migIndexes_4_2_0(indexes_conf_path, isDryRun):
  """
  SPL-34459 changing the default maxHotBuckets from 1 to 3: we are not really
  migrating anything here, just printing a warning that the default has changed
  """
  if not upgradingFromBeforeSplunk4_2():
    return
  logger.info("WARNING: The default maxHotBuckets value in indexes.conf has changed from 1 to 3.")
  logger.info("If you have added new indexes and you have not explicitly set this value, this new default may result in greater disk space requirement for maintaining your hot buckets.")
  logger.info("Note that the defaults for hot buckets settings maxHotBuckets and maxDataSize are 3 and \"auto\" respectively, where \"auto\" means 750MB.")
  logger.info("Increasing this default means that there may be 2 additional buckets per index (for indexes that rely on the implicit default), each bucket with size of up to maxDataSize.")
  logger.info("Also, note that the main default index's maxHotBuckets value remains unchanged at 10, and hence would incur no additional disk usage.")
  logger.info("Please verify your indexes settings if you believe this potential increase in disk usage to be an issue.")


def createUIlogin(dryRun):
  """
  Drop the ".ui_login" file into /etc for existing installs. That way all upgrades will bypass changepassword screen. 
  """
  if not dryRun:
    filePath = make_splunkhome_path(["etc", ".ui_login"])
    comm.touch(filePath)


def warnOnConflictingViews(dryRun):
  '''
  SPL-36190 -- notify the administrator that there are locally generated view
  files that are overriding the deafult set of views that ship and are upgdaded
  by Splunk Inc.
  '''

  logger.info('\nChecking for possible UI view conflicts...')

  skipCheckPath = make_splunkhome_path(["mig-no-viewconflictcheck"])
  if os.path.exists(skipCheckPath):
      logger.info("    ...skipping check due to existence of file=\"%s\"." % skipCheckPath)
      comm.removeItem(skipCheckPath, dryRun)
      return

  SYSTEM_BUNDLE_NAMES = ['system', 'search']
  VIEWS_PATH_SEGMENT = ['data', 'ui', 'views']
  VIEW_EXTENSION = '.xml'

  system_view_names = set()

  # get list of stock shipping view names
  for app in SYSTEM_BUNDLE_NAMES:
    bun = bundle_paths.get_bundle(app, unmanaged=True)
    if bun is None:
      continue
    view_dir = os.path.join(bun.location(), 'default', *VIEWS_PATH_SEGMENT)
    if os.path.isdir(view_dir):
      system_view_names.update([f for f in os.listdir(view_dir) if f.endswith(VIEW_EXTENSION)])
  if len(system_view_names) == 0:
    logger.warn('Did not find any system views installed; UI may not function correctly!')

  # check all other managed bundles for conflicts
  for bundle in bundle_paths.bundles_iterator():
    if bundle.name() in SYSTEM_BUNDLE_NAMES:
      continue
    for bundle_view_dir in (
        os.path.join(bundle.location(), 'default', *VIEWS_PATH_SEGMENT),
        os.path.join(bundle.location(), 'local', *VIEWS_PATH_SEGMENT)
      ):
      if os.path.isdir(bundle_view_dir):
        bundle_view_names = set([f for f in os.listdir(bundle_view_dir) if f.endswith(VIEW_EXTENSION)])
        for name in (system_view_names & bundle_view_names):
          logger.info(' App "%s" has an overriding copy of the "%s" view, thus the new version may not be in effect. location=%s' % (bundle.name(), name, bundle_view_dir))

  # check user directories for conflicts
  for username in [d for d in os.listdir(PATH_ETC_USERS) if os.path.isdir(os.path.join(PATH_ETC_USERS, d))]:
    for app in os.listdir(os.path.join(PATH_ETC_USERS, username)):
      user_view_dir = os.path.join(PATH_ETC_USERS, username, app, 'local', *VIEWS_PATH_SEGMENT)
      if os.path.isdir(user_view_dir):
        user_view_names = set([f for f in os.listdir(user_view_dir) if f.endswith(VIEW_EXTENSION)])
        for name in (system_view_names & user_view_names):
          logger.info(' User "%s" has an overriding copy of the "%s" view, thus the new version may not be in effect. location=%s' % (username, name, user_view_dir))
        

def checkAlertActionsSendemailCommand(path, dryRun = False):
  """
  SPL-69407 5.x integrated pdf generation requires invoking sendemail with a ssname value.
  If there is an old custom sendemail command in alert_actions.conf, add ssname if necessary. 
  On dryRun, the path we get is the *.migratePreview version so just update it as normal and 
  preview migration will notice and add this file to the list of those requiring changes.
  """

  # is there a command key in the alert_actions [email] stanza?
  if not os.path.exists(path):
    return
  confDict = comm.readConfFile(path)
  if not 'email' in confDict:
    return
  if not 'command' in confDict['email']:
    return

  # is it a sendemail command? 
  value = confDict['email']['command']
  if value.startswith('sendemail') and not 'ssname' in value.lower():
    # append an ssname arg to the command

    if dryRun:
      logger.info("Would add required ssname argument to custom sendemail command in %s" % path)
    else:
      logger.info("Adding required ssname argument to custom sendemail command in %s" % path)

    confDict['email']['command'] += ' "ssname=$name$"'
    comm.writeConfFile(path, confDict)

def migrateDMCAppFolder(isDryRun):
  def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(src):
        return
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                shutil.copy2(s, d)
  try: 
    new_dmc_root = bundle_paths.get_bundle("splunk_monitoring_console").location()
    # if this file presents, migration occured in previous install, so just skip. 
    marker_file = os.path.join(new_dmc_root, 'splunk_migrated')
    if os.path.exists(marker_file): 
      return

    old_dmc_bundle = bundle_paths.get_bundle("splunk_management_console")

    if not old_dmc_bundle:
      # no old dmc folder, no need to do migration
      return
    
    old_dmc_root = old_dmc_bundle.location()

    if isDryRun:
      logger.info('will copy all local changes in splunk_management_console to splunk_monitoring_console')
      return

    old_local_folder = os.path.join(old_dmc_root, 'local')
    new_local_folder = os.path.join(new_dmc_root, 'local')
    # copy the local folder from old to new place
    copytree(old_local_folder, new_local_folder)
    # rename splunk_management_console_assets.conf
    old_assets_conf_name = os.path.join(new_local_folder, 'splunk_management_console_assets.conf')
    new_assets_conf_name = os.path.join(new_local_folder, 'splunk_monitoring_console_assets.conf')
    if os.path.exists(old_assets_conf_name):
      os.rename(old_assets_conf_name, new_assets_conf_name)
    # copy lookups 
    old_lookup_folder = os.path.join(old_dmc_root, 'lookups')
    new_lookup_folder = os.path.join(new_dmc_root, 'lookups')
    copytree(old_lookup_folder, new_lookup_folder)
    # copy local.meta file
    old_localmeta_file = os.path.join(old_dmc_root, 'metadata/local.meta')
    new_localmeta_file = os.path.join(new_dmc_root, 'metadata/local.meta')
    if os.path.exists(old_localmeta_file):
      shutil.copy2(old_localmeta_file, new_localmeta_file)
    # delete old folder since it is not used anymore
    shutil.rmtree(old_dmc_root)
    # create marker file to indicate migration completed. 
    open(marker_file, 'w').close()
  except Exception as e:
    logger.warn('Cannot migrate splunk_management_console to splunk_monitoring_console. %s', e)
    return

def migrateDMCNavBar(isDryRun):
  """
  During splunk upgrade, the old version of default.xml remains in the DMC local directory.
  This causes the DMC to use the old version of default.xml instead of the new version of default.xml.
  Ref: SPL-101514, SPL-109047
  """

  old_dmc_bundle = bundle_paths.get_bundle("splunk_monitoring_console")
  if not old_dmc_bundle:
    # no need to migrate
    return

  dmc_root = old_dmc_bundle.location()
  local_nav_xml_path = os.path.join(dmc_root, 'local/data/ui/nav/default.xml')
  # in /default/data/ui/nav, default.xml is the same as default.single.xml
  standalone_nav_xml_path = os.path.join(dmc_root, 'default/data/ui/nav/default.xml')
  distributed_nav_xml_path = os.path.join(dmc_root, 'default/data/ui/nav/default.distributed.xml')

  """
  three cases and corresponding actions:
     old version            new version
  1) not set up         ->  do nothing
  2) set up standalone  ->  copy default.single.xml
  3) set up distributed ->  copy default.distributed.xml
  """

  if not os.path.exists(local_nav_xml_path):
    # not set up
    logger.info("DMC is not set up, no need to migrate nav bar.")
  else:
    # have set up
    is_distributed = False
    try:
      local_app_conf = comm.readConfFile(os.path.join(dmc_root, 'local/app.conf'))
      is_distributed = splunk.util.normalizeBoolean(local_app_conf['install']['is_configured'])
    except:
      logger.warn('Cannot read local app.conf, DMC must be in standalone mode')

    if isDryRun:
      logger.info('Update DMC nav bar.')
      return

    try:
      if is_distributed:
        # case 3)
        shutil.copyfile(distributed_nav_xml_path, local_nav_xml_path)
        logger.info("DMC is in distributed mode. Nav bar updated.")
      else:
        # case 2)
        shutil.copyfile(standalone_nav_xml_path, local_nav_xml_path)
        logger.info("DMC is in standalone mode. Nav bar updated.")
    except:
      logger.error('Cannot complete the migration of DMC nav bar because of an error.')
      logger.error(traceback.format_exc())

def migrateDMCUsers(isDryRun):
  """
  This function renames the splunk_management_console directories for each user in etc/users to
  splunk_monitoring_console
  """
  if isDryRun:
    logger.info('Renaming splunk_management_console to splunk_monitoring_console')
    return

  try:
    for user in os.listdir(PATH_ETC_USERS):
      user_path = os.path.join(PATH_ETC_USERS, user)
      if os.path.isdir(os.path.join(user_path, 'splunk_management_console')):
        os.rename(os.path.join(user_path, 'splunk_management_console'), os.path.join(user_path, 'splunk_monitoring_console'))
        logger.info('Renamed splunk_management_console directory for user: ' + user + ' to splunk_monitoring_console')
  except Exception as e:
    logger.warn('Cannot rename splunk_management_console to splunk_monitoring_console because that directory already exists. %s', e)
    return

def migrateDMC_6_5_0(dryRun):
  migrateDMCAppFolder(dryRun)
  migrateDMCUsers(dryRun)

def addUriSchemeToServerList( conf_string, uri_scheme ):
  result = ""
  for uri_string in conf_string.split(','):
    uri_string = uri_string.strip()
    if not uri_string:
      continue
    if not uri_string.startswith('http://') and not uri_string.startswith('https://'):
      uri_string = uri_scheme + '://' + uri_string
    result = result + uri_string + ','
  return result[:-1]

# SPL-117689 
# If server.conf has disabled SSL on splunkd's port then we probably
# need to be using http to talk to the peers.
def serverConfDisabledSSL():
  if not PATH_SERVER_CONF:
    return False

  server_conf = comm.readConfFile( PATH_SERVER_CONF )
  if not ( 'sslConfig' in server_conf ):
    return False

  if not ( 'enableSplunkdSSL' in server_conf['sslConfig'] ):
    return False

  return not( splunk.util.normalizeBoolean(server_conf['sslConfig']['enableSplunkdSSL']) )

def migrateToStopFlippingUriSchemeInGalaxy(dryRun = False):
  """
  SPL-105589: In Galaxy we will stop trying to auto-guess the URI Scheme to contact search
  peers using trial and error. In an attempt to not break distributed search we will try
  to guess what Scheme the peers are using one last time and set the default communication
  scheme accordingly
  """
  if not PATH_DISTSEARCH_CONF:
    logger.info("Distributed Search is not configured on this instance")
    return

  distsearch_conf = comm.readConfFile( PATH_DISTSEARCH_CONF )
  if not ('distributedSearch' in distsearch_conf ):
    logger.info("Distributed Search is not configured on this instance")
    return

  uri_scheme = 'https'
  if 'trySSLFirst' in distsearch_conf['distributedSearch']:
    if not splunk.util.normalizeBoolean(distsearch_conf['distributedSearch']['trySSLFirst']):
      uri_scheme = 'http'
  elif serverConfDisabledSSL():
    uri_scheme = 'http'

  if uri_scheme == 'http':
    distsearch_conf['distributedSearch']['defaultUriScheme'] = uri_scheme

  prop_list = ['servers', 'disabled_servers', 'quarantined_servers']
  for prop in prop_list:
    if prop in distsearch_conf['distributedSearch']:
      distsearch_conf['distributedSearch'][prop] = addUriSchemeToServerList( distsearch_conf['distributedSearch'][prop], uri_scheme )

  if 'trySSLFirst' in distsearch_conf['distributedSearch']:
    distsearch_conf['distributedSearch'].pop('trySSLFirst')

  if not dryRun:
    comm.writeConfFile(PATH_DISTSEARCH_CONF, distsearch_conf)
  else:
    logger.info("uri scheme for all search peers will be set to " + uri_scheme)

def remove_legacy_manager_xml_files(dryRun):
  '''
  SPL-109236: Remove unused manager XML files.
  '''
  logger.info('Removing legacy manager XML files...')
  files = [
    'data_inputs_tcp_cooked.env_cloud.xml', 
    'data_inputs_tcp_cooked.prod_lite.env_cloud.xml',
    'data_inputs_monitor.env_cloud.xml',
    'data_inputs_monitor.prod_lite.env_cloud.xml',
    'deployment_server.xml',
    'deployment_serverclass_status.xml',
    'admin_fvtags.prod_lite.xml',
    'admin_ntags.prod_lite.xml',
    'admin_ntags.prod_lite.xml',
    'data_inputs_monitor.prod_lite.xml',
    'data_inputs_script.prod_lite.xml',
    'data_props_calc_fields.prod_lite.xml',
    'data_props_extractions.prod_lite.xml',
    'data_props_field_aliases.prod_lite.xml',
    'data_props_sourcetype_rename.prod_lite.xml',
    'data_transforms_extractions.prod_lite.xml',
    'saved_eventtypes.prod_lite.xml',
    'saved_searches.prod_lite.xml'
  ]
  
  for file_name in files:
      xml_path = os.path.join(comm.splunk_home, 'etc', 'apps', 'search', 'default', 'data', 'ui', 'manager', file_name)
      if os.path.exists(xml_path):
          comm.removeItem(xml_path, dryRun)

def remove_legacy_nav_xml_files(dryRun):
  """
  LIGHT-2425. To support Pivot in Light, the prod_lite.xml version of the nav xml needs
  to be removed from the search app.
  """
  logger.info('Removing legacy nav XML files...')
  files = [
    'default.prod_lite.xml'
  ]

  for file_name in files:
      xml_path = os.path.join(comm.splunk_home, 'etc', 'apps', 'search', 'default', 'data', 'ui', 'nav', file_name)
      if os.path.exists(xml_path):
          comm.removeItem(xml_path, dryRun)

def remove_splunkclouduf_manager_file(dryRun):
  '''
  LIGHT-2109: Remove unused manager XML files.
  '''
  logger.info('Removing splunkclouduf XML file...')
  filename = 'splunkclouduf.prod_lite.env_cloud.xml'
  xml_path = os.path.join(comm.splunk_home, 'etc', 'apps', 'search', 'default', 'data', 'ui', 'manager', filename)
  if os.path.exists(xml_path):
      comm.removeItem(xml_path, dryRun)

def remove_splunkclouduf_view_files(dryRun):
  '''
  LIGHT-2109: Remove unused view XML files.
  '''
  logger.info('Removing splunkclouduf view XML files...')
  files = [
    'splunkclouduf.prod_lite.env_cloud.xml', 
    'splunkclouduf.env_cloud.xml',
    'splunkclouduf.xml'
  ]

  for file_name in files:
      xml_path = os.path.join(comm.splunk_home, 'etc', 'apps', 'search', 'default', 'data', 'ui', 'views', file_name)
      if os.path.exists(xml_path):
          comm.removeItem(xml_path, dryRun)

def remove_system_activity_dashboards(isDryRun):
  '''
  SPL-103198: Remove System Activity Views from Splunk Enterprise
  '''
  logger.info('Removing System Activity dashboards...')
  files = [
    'internal_messages.xml', 
    'scheduler_savedsearch.xml',
    'scheduler_status.xml',
    'scheduler_status_errors.xml',
    'scheduler_user_app.prod_lite.xml',
    'scheduler_user_app.xml',
    'search_activity_by_user.xml',
    'search_detail_activity.xml',
    'search_status.xml',
    'status_index.xml'
  ]
  
  if not isDryRun:
    for file_name in files:
      xml_path = os.path.join(comm.splunk_home, 'etc', 'apps', 'search', 'default', 'data', 'ui', 'views', file_name)
      if os.path.exists(xml_path):
          comm.removeItem(xml_path, isDryRun)

# SPL-113029: Migration for ui-prefs needs be removed after Galaxy is released.
def migUserUIPrefsConf_6_4_0(dryRun, isAfterBundleMove):
  candidate_files = glob.glob(os.path.join(PATH_ETC_USERS, '*', 'search', 'local', 'ui-prefs.conf'))
  maybe_preview_files = [ chooseFile(f, dryRun, isAfterBundleMove) for f in candidate_files ]
  for f in maybe_preview_files:
    migUIPrefsConf_6_4_0(f)

def migUIPrefsConf_6_4_0(path):
  """
  Clear up ambiguities in ui-prefs.conf:
    display.prefs.defaultSampleRatio -> display.prefs.customSampleRatio
  """
  if not os.path.exists(path):
    return

  STANZA_SEARCH  = "search"
  KEY_SAMPLE_RATIO_OLD  = "display.prefs.defaultSampleRatio"
  KEY_SAMPLE_RATIO_NEW  = "display.prefs.customSampleRatio"

  setts_dict = comm.readConfFile(path)
  if STANZA_SEARCH in setts_dict and KEY_SAMPLE_RATIO_OLD in setts_dict[STANZA_SEARCH]:
    setts_dict[STANZA_SEARCH][KEY_SAMPLE_RATIO_NEW]  = setts_dict[STANZA_SEARCH].pop(KEY_SAMPLE_RATIO_OLD)
    comm.writeConfFile(path, setts_dict)

def migUserPrefsConf_6_6(dryRun, isAfterBundleMove):
    candidate_files = glob.glob(os.path.join(PATH_ETC_USERS, '*', 'user-prefs', 'local', 'user-prefs.conf'))
    maybe_preview_files = [ chooseFile(f, dryRun, isAfterBundleMove) for f in candidate_files ]
    for f in maybe_preview_files:
        migSearchSyntaxHighlightingValue_6_6(f)

def migSearchSyntaxHighlightingValue_6_6(path):
  """
    convert value from boolean to string"
    0 -> "black-white"
    1 -> "light"
  """
  if not os.path.exists(path):
    return

  STANZA = "general"
  KEY_SYNTAX_HI  = "search_syntax_highlighting"
  BLACK_WHITE = "black-white"
  LIGHT = "light"

  setts_dict = comm.readConfFile(path)
  if STANZA in setts_dict and KEY_SYNTAX_HI in setts_dict[STANZA]:
    try:
      is_highlighting_on = splunk.util.normalizeBoolean(setts_dict[STANZA][KEY_SYNTAX_HI], True)
      setts_dict[STANZA][KEY_SYNTAX_HI] = LIGHT if is_highlighting_on else BLACK_WHITE
      comm.writeConfFile(path, setts_dict)
    except:
      return

def remove_splunk_instrumentation_search_xml(dryRun):
  '''
  SPL-153076: Remove legacy search XML file from splunk_instrumentation.
  '''
  logger.info('Removing legacy search.xml file from splunk_instrumentation...')

  app_dir = None

  try:
    bundle = bundle_paths.get_bundle('splunk_instrumentation')

    if not bundle:
      return

    app_dir = bundle.location()

    xml_path = os.path.join(app_dir, 'default', 'data', 'ui', 'views', 'search.xml')
    if os.path.exists(xml_path):
      comm.removeItem(xml_path, dryRun)
  except Exception as ex:
    # It would be unfortunate to fail here, but not critical.
    # Lets suppress any exceptions so the migration can continue.
    logger.error('Failed to remove %s file: %s' % (xml_path, str(ex)))


def autoMigrate(logPath, dryRun = False):
  """
  The central migration control function.  This should automagically migrate an old Splunk's configs
  to an uptodate set of configuration files.
  """

  if comm.isLocalSplunkdUp():
    raise cex.ServerState("In order to migrate, Splunkd must not be running.")

  #
  # setup logging.  all migration stuff will go to file (as well as stdout/stderr).
  # at the end of this function, we'll remove the file-logging of all logger messages.
  # otherwise all subsequent pcl messages would get logged to file as well.
  #

  migLogFile  = open(logPath, "a") # a: remember, C logs here as well.
  migLogFileHandler = comm.newLogHandler(migLogFile, comm.debugMode, normal = False, filter = False)
  logger.getLogger().addHandler(migLogFileHandler)
  logger.getLogger().setLevel(logger.INFO)

  #
  # if this is false, that means we need to move our bundles to the new
  # location.  this file gets created by one of our migration calls.
  # for fresh installs post-move, check for bundles/default/ as well...
  #
  isAfterBundleMove = os.path.exists(PATH_MIGRATION_CONF) or not os.path.exists(PATH_OLD_DEF_BUNDLES)

  # start by ensuring that everything we want to migrate is in etc/system/...
  if not isAfterBundleMove:
    # while we're in here, delete the old 'default' bundle, or there's gonna
    # be some confused customers.  migrate_bundles will to the right thing,
    # ie delete, with the default bundle when asked.  all other bundles will
    # remain.
    for bundle in ('local', 'default'):
      if os.path.exists(bundle_paths.make_legacy_bundle_install_path(bundle)):
        bundle_paths.migrate_bundles({'dry-run' : dryRun, 'name' : bundle}, fromCLI = True)
  if not dryRun:
    isAfterBundleMove = True


  # these rely on splunkd.xml - be sure to run this before that's upgraded for 4.0.0!
  replaceLicense(dryRun)
  warnOutdatedApps()
  warnUnmigratableFiles(dryRun)

  #
  #
  # choose which files to edit (based on whether we're previewing migration or not).
  #
  #

  migAuthConf      = chooseFile(PATH_AUTHEN_CONF_NEW,  dryRun, isAfterBundleMove)
  migInputsConf    = chooseFile(PATH_INPUTS_CONF,      dryRun, isAfterBundleMove)
  migSplunkdXml    = chooseFile(PATH_SPLUNKD_XML,      dryRun, isAfterBundleMove)
  migSavedConf     = chooseFile(PATH_SAVSRCH_CONF,     dryRun, isAfterBundleMove)
  migEvttypeConf   = chooseFile(PATH_EVTTYPE_CONF,     dryRun, isAfterBundleMove)
  migSrvConf       = chooseFile(PATH_SERVER_CONF,      dryRun, isAfterBundleMove)
  migServerclassConf = \
      chooseFile(               PATH_SERVERCLASS_CONF, dryRun, isAfterBundleMove)
  migWebConf       = chooseFile(PATH_WEB_CONF,         dryRun, isAfterBundleMove)
  migIndexesConf   = chooseFile(PATH_INDEXES_CONF,     dryRun, isAfterBundleMove)
  migTagsConf      = chooseFile(PATH_TAGS_CONF,        dryRun, isAfterBundleMove)
  migPropsConf     = chooseFile(PATH_PROPS_CONF,       dryRun, isAfterBundleMove)

  migTxnTypesConf  = chooseFile(PATH_TXN_TYPES_CONF,   dryRun, isAfterBundleMove)
  migLocalMeta     = chooseFile(PATH_LOCALMETA_CONF,   dryRun, isAfterBundleMove)

  
  migWmiConf          = chooseFile(PATH_WMI_CONF,                dryRun, isAfterBundleMove)
  migSearchLocalMeta  = chooseFile(PATH_SEARCH_LOCALMETA_CONF,   dryRun, isAfterBundleMove)
  migSearchSavedConf  = chooseFile(PATH_SEARCH_SAVSRCH_CONF,     dryRun, isAfterBundleMove)
  
  migFieldActionsConf = chooseFile(PATH_FIELD_ACTIONS, dryRun, isAfterBundleMove)
  migFieldActionsConfNew = chooseFile(PATH_FIELD_ACTIONS_NEW, dryRun, isAfterBundleMove)

  migUserPrefsConf = chooseFile(PATH_USER_PREFS_CONF,  dryRun, isAfterBundleMove)
  migAlertActionsConf = chooseFile(PATH_ALERT_ACTIONS_CONF,  dryRun, isAfterBundleMove)

  #
  #
  # do the actual migration steps...
  # this section should basically be in order from oldest migration functions
  # to newest migration functions (for the most part...).
  #
  #

  # make a backup of splunkd.xml.
  comm.copyItem(PATH_SPLUNKD_XML, PATH_SPLUNKD_XML_BAK, dryRun)

  removeDirMon(dryRun)

  # this one has to happen eaerly, since other migrations fail without  the
  # change
  migSampleIndex_4_2_1(migIndexesConf, dryRun)

  checkSavedSearches(CONF_SAVEDSEARCHES)
  checkTimezones(CONF_PROPS, dryRun)
  migrateAuth_3_2_0(migAuthConf, dryRun)
  migrateSavedSearches(migSavedConf)
  migrateWebSSL(migSrvConf, migWebConf)
  migrateWebPollerTimeoutInterval_4_1(migWebConf)
  removeDeprecated(dryRun)

  # we run this even though we've previously moved everything out of
  # bundles/local, as it can still produce valid warnings depending upon what
  # the user has done.
  bundle_paths.warn_about_legacy_bundles(dryRun)

  # continue on with migration functions that don't depend on the old dir structure.
  checkCommandsConfig(CONF_COMMANDS)
  fixPasswdPermissions(PATH_PASSWD_FILE, dryRun)
  migInputs_3_3_0(migInputsConf, dryRun)
  migQueryToSearch_3_3_0(migSavedConf, migEvttypeConf)
  migCapabilities_3_3_0(PATH_AUTHORIZE_CONF)


  migIndexes_4_0_0(migIndexesConf, dryRun)
  migEventTypeTags_4_0_0(migEvttypeConf, migTagsConf, dryRun)
  migSplunkdXml_4_0_0(migSplunkdXml, migSrvConf)
  migSSLConf_4_0_0(migSrvConf)
  migSavedsearches_4_0_0(migSavedConf, migSearchSavedConf, migSearchLocalMeta, dryRun)
  migAuthConf_4_0_0(migAuthConf)
  migTranactionTypes_4_0_0(migTxnTypesConf, dryRun)
  migSourcetypeAliases_4_0_0(migTagsConf, migPropsConf, dryRun)
  migWmi_4_0_0(migWmiConf, dryRun)
  migWinScriptedInputs_4_1(dryRun, isAfterBundleMove)

  migEtcUsers_4_0_5(PATH_ETC_USERS, dryRun)
  replaceSplunkdXml_4_0_7(PATH_SPLUNKD_XML_DEF, PATH_SPLUNKD_XML, dryRun)

  migTags_4_1(migTagsConf, migTagsConf, dryRun)
  field_actions.migFieldActions_4_1(migFieldActionsConf, migFieldActionsConfNew, dryRun)

  # run this before migLDAP_4_1, which moves the passwd file.
  backupPasswdIfPre_4_1_4(PATH_PASSWD_FILE, dryRun)
  migLDAP_4_1(migAuthConf, dryRun)
  migPAM_Scripted_4_1(migAuthConf, dryRun)
  suggestGlobalExports_4_1()
  migGlobalDefaultApp_4_1(migUserPrefsConf)
  migMANIFESTtoAppConf_4_1(dryRun)
  migUserDefaultApp_4_1(dryRun, isAfterBundleMove)
  removeListtails_4_1_4(dryRun)
  migViewstatesGlobalExport_4_1_5(dryRun, isAfterBundleMove)
  migDataExtractionsXml_4_1_5(dryRun)

  removeDeployModule_ItsHammerTime(dryRun)
  addOldSourcetypePulldowns_4_2_0(dryRun)
  removeUnnecessaryApps_4_2_0(dryRun)
  relocateSplunkwebSSLCerts_4_2_0(migWebConf, dryRun)
  removeOldManagerLicensing_4_2_0(dryRun)
  migIndexes_4_2_0(migIndexesConf, dryRun)

  fixMismigratatedApps_4_2_1(dryRun)

  migLDAP_4_3(migAuthConf, dryRun)
  
  removeUnnecessaryApp_5_0(dryRun)
  replaceLocalNavXml_6_0_0(PATH_SEARCH_NAV_XML_OLD, PATH_SEARCH_NAV_XML_NEW, dryRun)

  removeEchoSh(dryRun)

  createUIlogin(dryRun)

  lastVersion = getMigHistory(KEY_LAST_MIG_VERSION)
  # If version before migration is less than 6.5.0
  # lets give a warning to stdout
  # if any role has indexer_edit capability enabled.
  if lastVersion is not None and lastVersion < (6, 5):
      checkForEnabledIndexesEditCapAndWarn(PATH_AUTHORIZE_CONF)
      checkForEnabledIndexesEditCapAndWarn_AllApps()
  #
  # !!! WARNING FOR MIGRATION AUTHORS !!!
  #
  # DO NOT access apps directly by doing things like:
  #
  #     os.path.join(comm.splunk_home, 'etc', 'apps') # WRONG!
  #
  # This means you should not use the global variables defined at the top of
  # this file to access apps. For example, do not use PATH_APPS_DIR!
  #
  # Instead, use the methods in the bundle_paths module.
  #
  # - To iterate over all apps: bundle_paths.bundles_iterator()
  # - To find a particular app: bundle_paths.get_bundle('appname')
  # - To access the apps directory directly: bundle_paths.get_base_path()
  #
  # If this doesn't make sense to you, talk to ewoo.
  #

  warnOnConflictingViews(dryRun)
  checkAlertActionsSendemailCommand(migAlertActionsConf, dryRun)
  remove_legacy_manager_xml_files(dryRun)
  remove_legacy_nav_xml_files(dryRun)
  # make sure migrateDMC_6_5_0 (specifically migrateDMCAppFolder) is called before calling migrateDMCNavBar
  migrateDMC_6_5_0(dryRun)
  migrateDMCNavBar(dryRun)
  remove_system_activity_dashboards(dryRun)
  remove_splunkclouduf_manager_file(dryRun)
  remove_splunkclouduf_view_files(dryRun)
  migrateToStopFlippingUriSchemeInGalaxy(dryRun)
  migUserUIPrefsConf_6_4_0(dryRun, isAfterBundleMove)
  migUserPrefsConf_6_6(dryRun, isAfterBundleMove)
  remove_splunk_instrumentation_search_xml(dryRun)

  #
  # migrate known third party apps
  #
  app_maps.migrate_maps_41x_420(dryRun)

  migrateWeb_SSOMode_4_2_5(migSrvConf, migWebConf)

  warnOfNowInvalid_serverclassConf_6_0(migServerclassConf) # SPL-63066
  warnOfNowUnsupportedAttributes_serverclassConf_6_0(migServerclassConf) # SPL-67765
  replace_ui_modules_8_0_0(dryRun) # SPL-173474

  # SPL-173477 - Removed Apps, AXML and Modules should not be present after upgrade to Quake 8.0.0
  remove_exposed_content_8_0_0(dryRun)
  remove_axml_8_0_0(dryRun)
  remove_axml_apps_8_0_0(dryRun)
  
  #
  #
  # finished w/ migration (or dry run).
  #
  #

  # store a marker of what version we've upgraded to.
  setMigHistory(KEY_LAST_MIG_VERSION, splunk.getReleaseVersion(), dryRun)

  # find all files in splunkhome that we may have created during migration preview/dry run.
  previewFiles = findPreviewFiles()
  if dryRun:
    showPreviewFiles(previewFiles)
    raise cex.SuccessException("Migration is continuing...")
  # if it's not a dry run, go through and try to delete all our .migratePreview files from any prior runs!
  # this is so they don't get detected in subsequent upgrades, and accidentally get displayed.
  else:
    for macLikeFile in previewFiles:
      os.unlink(macLikeFile) # delete useless files.
  
  #
  # revert logging.  we don't want all subsequent logging calls to keep going to the mig log file.
  # in the case of an exception above here, we'll be exiting anyway - so no worries about this
  # not getting called in those cases.
  # 

  logger.getLogger().removeHandler(migLogFileHandler)
