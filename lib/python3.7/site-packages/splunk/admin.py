from __future__ import print_function
from builtins import object
import os
import struct
import sys
import types
import traceback
import lxml.etree as et
import defusedxml.lxml as safe_lxml
import splunk
import splunk.util
from splunk.persistconn.packet import PersistentServerConnectionPacketParser
import __main__

def usage():
    raise UsageException("Usage: %s [%s].  (Got: %s)" % (sys.argv[0], str.join(str(" | "), ARGS_LIST), sys.argv))

############################## Constants ##

ACTION_CREATE  = 1
ACTION_LIST    = 2
ACTION_EDIT    = 4
ACTION_REMOVE  = 8
ACTION_MEMBERS = 16
ACTION_RELOAD  = 32

CONTEXT_NONE         = 1
CONTEXT_APP_ONLY     = 2
CONTEXT_APP_AND_USER = 3

ARG_EXECUTE = "execute"
ARG_PERSISTENT = "persistent"
ARG_SETUP   = "setup"
ARGS_LIST   = (ARG_SETUP, ARG_EXECUTE, ARG_PERSISTENT)

# TODO: macro this.
EAI_META_PREFIX   = "eai:"
EAI_ENTRY_ACL     = "eai:acl"

CAP_BYPASS        = "bypass_capability_check"
CAP_NONE          = "allow_access_to_all"
ADMIN_ALL_OBJECTS = "admin_all_objects"

ATTR_DATATYPE         = "datatype"

ATOMTYPE_UNSET        = "unset"
ATOMTYPE_STRING       = "string"
ATOMTYPE_BOOL         = "boolean"
ATOMTYPE_NUMBER       = "number"
ATOMTYPE_NULL         = "null"

def stdout_write(payload):

  if sys.version_info > (3, 0) and isinstance(payload, bytes):
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.write(b'\n')

  else:
    sys.stdout.write(payload)
    sys.stdout.write('\n')

############################## Exceptions ##

class AdminManagerException(Exception):
  def __init__(self, msg):
    Exception.__init__(self, msg)

# NOTE: if you add something here, also add it to AdminManager.cpp's rethrow_python_exception().
class AlreadyExistsException(     AdminManagerException): pass
class NotFoundException(          AdminManagerException): pass
class ArgValidationException(     AdminManagerException): pass
class BadActionException(         AdminManagerException): pass
class BadProgrammerException(     AdminManagerException): pass
class HandlerSetupException(      AdminManagerException): pass
class InternalException(          AdminManagerException): pass
class UsageException(             AdminManagerException): pass
class ServiceUnavailableException(AdminManagerException): pass


############################## Entry point ##
def handleException(e, exc_info, traceback):
    exType, exMsg, exBT = exc_info
    # <eai_error>
    root            = et.Element("eai_error");
    #   <recognized>[true|false]</recognized>
    knownNode       = et.SubElement(root, "recognized")
    knownNode.text  = isinstance(e, AdminManagerException) and "true" or "false"
    #   <type>[exception class]</type>
    typeNode        = et.SubElement(root, "type");
    typeNode.text   = splunk.util.unicode(exType)
    #   <message>[exception value]</message>
    msgNode         = et.SubElement(root, "message");
    msgNode.text    = splunk.util.unicode(exMsg)
    #   <stacktrace>[bt]</stacktrace>
    stackNode       = et.SubElement(root, "stacktrace");
    stackNode.text  = traceback

    # </eai_error>
    return et.tostring(root)

def init_persistent(handler, ctxInfo, data):
  mode = ARG_PERSISTENT

  try:
    hand = handler(mode, ctxInfo, data)
    if hand.isSetup():
        hand.setup()
        return hand.toXml(ConfigInfo())
    else:
      info = ConfigInfo()
      hand.execute(info)
      return hand.toXml(info)
  except Exception as e:
      return handleException(e, sys.exc_info(), traceback.format_exc())


class PersistentHandler(PersistentServerConnectionPacketParser):
    def __init__(self, handler, ctxInfo):
        self._handler = handler
        self._ctxInfo = ctxInfo

        super(PersistentHandler, self).__init__()

    def handle_packet(self, in_packet):
        if in_packet.is_first():
            self.write("")	# Empty error string indicates success

        if in_packet.has_block():
            reply =  init_persistent(self._handler, self._ctxInfo,
                                     in_packet.block)
            if reply:
                self.write(reply)

def init(handler, ctxInfo):
  try:
    # TODO: handle dependence on sys.argv intelligently for testing/etc imports.
    mode = ((len(sys.argv) > 1) and sys.argv[1] in ARGS_LIST) and sys.argv[1] or usage()

    if mode == ARG_PERSISTENT:
        h = PersistentHandler(handler, ctxInfo)
        h.run()
        return

    isSetup = False
    if ARG_EXECUTE == mode:
      hand = handler(mode, ctxInfo)
      info = ConfigInfo()
      hand.execute(info)
      stdout_write(hand.toXml(info))
    elif ARG_SETUP == mode:
      hand = handler(mode, ctxInfo)
      hand.setup()
      stdout_write(hand.toXml(ConfigInfo()))
    else:
      raise InternalException("Can't get here, boss (%s)." % mode)
  except Exception as e:
      stdout_write(handleException(e, sys.exc_info(), traceback.format_exc()))

############################## Helpers ##

class AdminTyper(object):
    types = {}
    def add(self, key, itemType):
        self.types[key] = itemType
    def get(self, key):
        if key in self.types:
            return self.types[key]
        return str

class ArgsList(object):
  def __init__(self):
    self.data = {}
    for member in dir(self.data):
      if not member in ("__class__", "__getitem__", "__setitem__"):
        setattr(self, member, getattr(self.data, member))
  def __iter__(self):
    return iter(self.data)
  def __getitem__(self, key):
    return self.data[key]
  def __contains__(self, key):
    return key in self.data
  def __len__(self):
    return len(self.data)
  def __setitem__(self, key, val):
    if key in self.data:
      del(self.data[key])
    self.append(key, val)
  def append(self, key, val):
    if isinstance(val, list):
      if not key in self.data:
        self.data[key] = val
      else:
        self.data[key] += val
    else:
      self.data[key] = val
  def datatypeFromNative(self, item):
    """Return a datatype string based on item's Python datatype.  Our datatypes follow
       the JSON model and are thus restricted to string/boolean/number/null."""
    if item == None:
      return ATOMTYPE_NULL
    # basestring to also support unicode (SPL-60776).
    if isinstance(item, splunk.util.string_type):
      return ATOMTYPE_STRING
    # SPL-140511 - Fundamentally, JSON bool type was never interpreted correctly, since integer eval
    # happened before... this change just sets evaluating bool before int.
    if isinstance(item, bool):
      return ATOMTYPE_BOOL
    if isinstance(item, (int, float)):
      return ATOMTYPE_NUMBER
    if sys.version_info < (3, 0) and isinstance(item, long):
      return ATOMTYPE_NUMBER
    return ATOMTYPE_UNSET
  def toXml(self, parent):
    for k, v in list(self.data.items()):
      if isinstance(v, list):
        # ex1: <attrib name="key" type="list" datatype="num"><item>val1</item><item>val2</item></attrib>
        # ex2: empty list: <attrib type="list"></attrib>  ...note absence of datatype.
        itemList = et.SubElement(parent, "attrib", type = "list")
        itemList.attrib["name"] = k

        # peek at the first item and get the datatype for this list.  the datatype is
        # per-list, not per-item, so we base it on the first one.
        if (0 != len(v)):
          itemList.attrib[ATTR_DATATYPE] = self.datatypeFromNative(v[0])

        for oneV in v:
          item = et.SubElement(itemList, "item")
          item.text = splunk.util.unicode(oneV)
      else:
        # ex: <attrib name="key" type="item" dataty="bool">value</attrib>
        item = et.SubElement(parent, "attrib", type = "item")
        item.attrib["name"] = k
        item.attrib[ATTR_DATATYPE] = self.datatypeFromNative(v)
        item.text = splunk.util.unicode(v)

class ArgsInfo(ArgsList):
  def __init__(self):
    self.id = ""
    ArgsList.__init__(self)
  def toXml(self, parent):
    id = et.SubElement(parent, "id")
    id.text = self.id
    args = et.SubElement(parent, "args")
    ArgsList.toXml(self, args)

class ConfigItem(ArgsList):
  def __init__(self):
    self.actions       = ~ACTION_CREATE & ~ACTION_MEMBERS # default: all but create/members.
    self.atomId        = ""
    self.author        = ""
    self._customActions = []
    self._metadata     = {}
    self.timePublished = 0
    self.timeUpdated   = 0
    ArgsList.__init__(self)

  # whether to show 'members' link in results.
  def hasMembers(self):
    return self.actions & ACTION_MEMBERS
  def setHasMembers(self, canHas):
    if canHas:
      self.actions |= ACTION_MEMBERS
    else:
      self.actions &= ~ACTION_MEMBERS
  def copyMetadata(self, src):
      for k, v in list(src.items()):
        if k.startswith(EAI_META_PREFIX):
          self.setMetadata(k, v)
  def setMetadata(self, key, value):
    self._metadata[key] = value
  def removeAllActions(self):
    self.actions = 0
  def addCustomAction(self, ca):
    self._customActions.append(ca)

  def toXml(self, parent):
    metadataNode = et.SubElement(parent, "metadata")

    # serialize acl & related metadata.
    if EAI_ENTRY_ACL in self._metadata:
      # {'eai:acl': {'sharing': 'app', 'perms': {'read': ['*'], 'write': ['*']}, 'app': 'windows',
      #              'modifiable': 'true', 'can_write': 'true', 'owner': 'nobody'},
      #              'eai:userName': 'nobody', 'eai:appName': 'windows'}
      aclNode = et.SubElement(metadataNode, "acl")
      settings = self._metadata[EAI_ENTRY_ACL]
      for item in ("sharing", "app", "modifiable", "owner", "removable"):
        if not item in settings:
          continue
        tmpNode = et.SubElement(aclNode, item)
        tmpNode.text = splunk.util.unicode(settings[item])
      # TODO: this could be a little more resilient?  unlikely to fail, though.
      if "perms" in settings:
        permsListNode = et.SubElement(aclNode, "perms")
        if settings["perms"] is not None:
          for perm, permRoles in list(settings["perms"].items()):
            permNode = et.SubElement(permsListNode, "perm")
            permNode.attrib["name"] = perm
            for role in permRoles:
              roleNode = et.SubElement(permNode, "role")
              roleNode.text = role

    # serialize custom actions.
    if len(self._customActions) > 0:
        caRootNode = et.SubElement(parent, "customActions")
        for actName in self._customActions:
            actNode = et.SubElement(caRootNode, "action")
            actNameNode = et.SubElement(actNode, "name")
            actNameNode.text = splunk.util.unicode(actName)

    #add actions
    actionNode = et.SubElement(parent, "actions")
    actionNode.text = str(self.actions)

    # serialize remaining (non-underscore fields).
    memberList = dir(self)
    dataNode = et.SubElement(parent, "data")
    ArgsList.toXml(self, dataNode)
    memberList.remove("data")
    for item in memberList:
      if not item.startswith("_"):
        member = getattr(self, item)
        if not type(member) in (types.BuiltinMethodType, types.MethodType):
          tmp = et.SubElement(parent, "attrib")
          tmp.attrib["name"] = item
          tmp.text = splunk.util.unicode(getattr(self, item))

class ConfigInfo(object):
  def __init__(self):
    self.feed_name     = ""
    self.data          = {}
    for member in dir(self.data):
      if not member in ("__class__", "__getitem__", "__setitem__"):
        setattr(self, member, getattr(self.data, member))
    self.messages = []
  def __iter__(self):
    return iter(self.data)
  def __getitem__(self, key):
    if not key in self.data:
      self.data[key] = ConfigItem()
    return self.data[key]
  def __contains__(self, key):
    return key in self.data
  def __len__(self):
    return len(self.data)
  def __setitem__(self, item, keyValPair):
    if 2 != len(keyValPair):
      raise BadProgrammerException("Value of ConfigInfo key should be key/value tuple (is: %s)." % splunk.util.unicode(keyValPair))
    self.data[item] = ConfigItem()
    self.data[item].append(keyValPair[0], keyValPair[1])
  def copyMetadata(self, src, transformer = None):
    """
    Copy EAI metadata from a dictionary in the format:
      {"item1": {"foo"       : bar,
                 "eai:data1" : "val",
                 "eai:foo2"  : "val"},
       "item2": ...}
    """
    for name, settings in list(src.items()):
      if transformer:
        name = transformer(name)
      # only copy metadata for items we have?
      if not name in self.data:
        continue
      self[name].copyMetadata(settings)
  def mergeFrom(self, srcConfInfo):
    self.data.update(srcConfInfo.data)

  def addInfoMsg(self, msg):
    self.messages.append({"text": msg, "type": "INFO"})

  def addWarnMsg(self, msg):
    self.messages.append({"text": msg, "type": "WARN"})

  def addErrorMsg(self, msg):
    self.messages.append({"text": msg, "type": "ERROR"})

  def addDeprecationMsg(self):
      self.addWarnMsg("This endpoint has been deprecated")

  def toXml(self, parent):
    feedNode = et.SubElement(parent, "feed_name")
    feedNode.text = self.feed_name

    if len(self.messages) > 0:
      for msg in self.messages:
        msgNode = et.SubElement(parent, "message")
        msgNode.attrib["text"] = msg["text"]
        msgNode.attrib["type"] = msg["type"]

    for k, v in list(self.data.items()):
      tmpNode = et.SubElement(parent, "item")
      tmpNode.attrib["name"] = k
      v.toXml(tmpNode) # calls ArgsList.toXml().

class ArgSpecList(object):
  def __init__(self):
    self.args = []
  def addOptArg(self, argName):
    if argName.startswith("_"):
      raise HandlerSetupException("Parameters beginning with '_' are reserved for EAI's usage.")
    arg = self.ArgSpec()
    arg.argName = argName
    arg.isRequired = False
    self.args.append(arg)
    return arg
  def addReqArg(self, argName):
    if argName.startswith("_"):
      raise HandlerSetupException("Parameters beginning with '_' are reserved for EAI's usage.")
    arg = self.ArgSpec()
    arg.argName = argName
    arg.isRequired = True
    self.args.append(arg)
    return arg
  class ArgSpec(object):
    argsDependedOn = []
    argName        = []
    isRequired     = False
    def dependsOn(self, argName):
      self.argsDependedOn.append(argName);
    def isWildcarded(self):
      return self.argName.contains('*');
  def toXml(self, parent):
    for spec in self.args:
      # can't have * in xml tag names...
      tmp = et.SubElement(parent, "arg")
      tmp.attrib["name"] = spec.argName
      isReq = et.SubElement(tmp, "isRequired")
      isReq.text = splunk.util.unicode(spec.isRequired)
      if len(spec.argsDependedOn) > 0:
        dependsOn = et.SubElement(tmp, "argsDependedOn");
        for oneDep in spec.argsDependedOn:
          dep = et.SubElement(dependsOn, "dep")
          dep.text = oneDep

############################## Handler base class ##

class MConfigHandler(object):
  """
  Base class for all EAI handlers to implement.
  """
  def __init__(self, scriptMode, ctxInfo, request=None):
    self.appName                    = ""               # useful for external handlers to save data.
    self.callerArgs                 = ArgsInfo()       # args passed in from caller.
    self.customAction               = ""               # set if /handler/<entry>/<action> was hit.
    self.customActionCap            = ""               # required capability for current custAct, if any.
    self.didFilter                  = False            # did the handler filter on its own?
    self.didPaginate                = False            # did the handler paginate on its own?
    self.docShowEntry               = True             # whether to gen docs for this action ctxt.
    self.maxCount                   = 0                # max items to return to caller.
    self.posOffset                  = 0                # offset from beginning of results.
    self.requestedAction            = 0                # action requested by the caller.
    self.requestedFilters           = None             # any number of filters specified by caller.
    self.restartRequired            = False            # should server be restarted once handler is done?
    self.shouldAutoList             = True             # should handleList be called after create/edit?
    self.shouldFilter               = False            # did caller request filtering?
    self.sortAscending              = True             # false == sort descending.
    self.sortByKey                  = ""               # in a given set of config objects, which key to sort by.
    self.supportedArgs              = ArgSpecList()    # args supported by this particular handler.

    self.shouldReload               = False            # call handleReload after handler finishes?
    self.userName                   = ""               # useful for external handlers to save data.

    self.capabilityRead             = ""
    self.capabilityWrite            = ""

    self.context = ctxInfo
    self._mode = scriptMode

    #pylint: disable=E1103
    if sys.stdin.closed:
      return; # hope you know what you're doing - this better be for testing or something!

    if sys.version_info >= (3, 0):
      if request is None:
        dataFromSplunkd = sys.stdin.buffer.read()
      elif isinstance(request, str):
        dataFromSplunkd = request.encode()
      else:
        dataFromSplunkd = request
    elif request is None:
      dataFromSplunkd = sys.stdin.read()
    else:
      dataFromSplunkd = request

    if 0 == len(dataFromSplunkd):
      raise UsageException("Received no serialized data via stdin (mode: %s).  Will not continue." % self._mode)
    ### open("/tmp/lolwut", "w").write("""
    ###   "------------------data from splunkd---------------------"
    ###   %s
    ###   "--------------------------------------------------------"
    ###   """ % dataFromSplunkd)
    # TODO: could compare dir() output before and after the following, and show
    #       a warning if the count changes (unexpected members).
    xmlData = safe_lxml.fromstring(dataFromSplunkd)

    for item in xmlData.find("eai_settings"):
      if (None != item.text):
        setattr(self, item.tag, item.text)
    # convert these guys to nums.
    self.maxCount         = int(self.maxCount)
    self.posOffset        = int(self.posOffset)
    self.requestedAction  = int(self.requestedAction)
    #for (k, v) in parsedData["eai_settings"].items():
      #setattr(self, k, v)
    # bleh, workarounds.  need slightly smarter deserialization (TODO).
    tmp = xmlData.find("callerArgs")
    self.callerArgs = ArgsInfo()
    for item in tmp.find("args"):
      if item.tag == "item" and "name" in item.attrib:
        # TODO: should this just work as self.callerArgs[item.getAttribute("name")].append(item.text)?
        if not item.attrib["name"] in self.callerArgs.data:
          self.callerArgs.data[item.attrib["name"]] = [item.text]
        else:
          self.callerArgs.data[item.attrib["name"]].append(item.text)
    self.callerArgs.id = tmp.find("id").text
    # TODO BUG: requestedFilters is not deserialized!

    isSetup = xmlData.find("setup")
    sessionKey = xmlData.find("sessionKey")
    productType = xmlData.find("productType")

    self._setup = isSetup is not None
    if sessionKey is not None:
        setattr(__main__, '___sessionKey', sessionKey.text)
    if productType is not None:
        setattr(__main__, '___productType', productType.text)


  def isSetup(self):
    return self._setup

  def readConf(self, confName, typer = None):
    import splunk.bundle as bundle
    app  = self.context != CONTEXT_NONE         and self.appName  or "-"
    user = self.context == CONTEXT_APP_AND_USER and self.userName or "-"
    retDict = {}
    try:
      thing=bundle.getConf(confName, sessionKey=self.getSessionKey(), namespace=app, owner=user)
      for s in thing:
        retDict[s] = {}
        if typer:
            for k, v in list(thing[s].items()):
                retDict[s][k] = typer.get(k)(v) # apply native datatypes.
        else:
            retDict[s].update(list(thing[s].items()))
    # it's not "wrong" to request a conf file that doesn't exist, just like with PropertyPages.
    except splunk.ResourceNotFound:
      pass
    return retDict

  def readConfCtx(self, confName):
    """
    This version of readConf should only be used when you're sure there's an
    appropriate handler for it.  Basically, something at /configs/conf-<name>.
    """
    app  = self.context != CONTEXT_NONE         and self.appName  or "-"
    user = self.context == CONTEXT_APP_AND_USER and self.userName or "-"
    retDict = {}
    path = "configs/conf-%s" % confName
    import splunk.entity as en
    thing=en.getEntities(path, sessionKey=self.getSessionKey(), namespace=app, owner=user, count=-1)
    for s in thing:
      retDict[s] = {}
      retDict[s].update(list(thing[s].items()))
    return retDict


  def writeConf(self, confName, stanzaName, settingsDict):
    import splunk.bundle as bundle
    app  = self.appName # always save things to SOME app context.
    user = self.context == CONTEXT_APP_AND_USER and self.userName or "-"
    overwriteStanzas = not (self.requestedAction == ACTION_EDIT or self.requestedAction == ACTION_REMOVE)

    try:
      confObj = bundle.getConf(   confName, sessionKey=self.getSessionKey(), namespace=app, owner=user,
                               overwriteStanzas=overwriteStanzas)
    except splunk.ResourceNotFound:
      confObj = bundle.createConf(confName, sessionKey=self.getSessionKey(), namespace=app, owner=user)

    confObj.beginBatch()
    for k, v in list(settingsDict.items()):
      if isinstance(v, list):
        confObj[stanzaName][k] = str.join(str(","), v)
      else:
        confObj[stanzaName][k] = v
    confObj.commitBatch()

  def setReadCapability(self, capability):
    self.capabilityRead = capability

  def setWriteCapability(self, capability):
    self.capabilityWrite = capability

  def getSessionKey(self):
    if hasattr(__main__, "___sessionKey"):
      return getattr(__main__, "___sessionKey")
    raise UsageException("Session key not provided in __main__.")

  def toXml(self, confInfo):
    root  = et.Element("eai")
    setts = et.SubElement(root, "eai_settings")
    info  = et.SubElement(root, "config_info")
    confInfo.toXml(info)
    for memberName in dir(self):
      member = getattr(self, memberName)
      if (not isinstance(member, types.MethodType) and not memberName.startswith("_")):
        if "toXml" in dir(member):
          tmp = et.SubElement(setts, memberName)
          member.toXml(tmp)
        elif isinstance(member, list):
          for oneItem in member:
            tmp = et.SubElement(setts, memberName)
            tmp.text = None != member and splunk.util.unicode(member) or u""
        else:
          tmp = et.SubElement(setts, memberName)
          tmp.text = None != member and splunk.util.unicode(member) or u""
    return et.tostring(root)

  def setup(self):
    """
    Must be implemented by the derived class.  Defines arguments and validation
    info.  Called before the handle*() functions.
    Should:
     - inspect self.requestedAction.
     - populate self.supportedArgs via addReqArg() and addOptarg().
     - set pipelineName and processorName if appropriate.
    """
    raise BadProgrammerException("This python handler has not implemented a setup function.  Aborting.")
  def execute(self, confInfo):
    if 0 != len(self.customAction):
      self.handleCustom(confInfo)
    else:
      if self.requestedAction == ACTION_CREATE:   self.handleCreate(confInfo)
      if self.requestedAction == ACTION_LIST:     self.handleList(confInfo)
      if self.requestedAction == ACTION_EDIT:     self.handleEdit(confInfo)
      if self.requestedAction == ACTION_REMOVE:   self.handleRemove(confInfo)
      if self.requestedAction == ACTION_MEMBERS:  self.handleMembers(confInfo)
      if self.requestedAction == ACTION_RELOAD:   self.handleReload(confInfo)
  def handleCreate(self, confInfo):
    """Called when user invokes the "create" action."""
    self.actionNotImplemented()
  def handleEdit(self, confInfo):
    """Called when user invokes the "edit" action."""
    self.actionNotImplemented()
  def handleList(self, confInfo):
    """Called when user invokes the "list" action."""
    self.actionNotImplemented()
  def handleMembers(self, confInfo):
    """Called when user invokes the "members" action."""
    self.actionNotImplemented()
  def handleReload(self, confInfo):
    """Called when user invokes the "reload" action."""
    self.actionNotImplemented()
  def handleRemove(self, confInfo):
    """Called when user invokes the "remove" action."""
    self.actionNotImplemented()
  def handleCustom(self, confInfo):
    """
    Called when user invokes a custom action.  Implementer can find out which
    action is requested by checking self.customAction and self.requestedAction.
    The former is a string, the latter an action type (create/edit/delete/etc).
    """
    self.actionNotImplemented()

  def actionNotImplemented(self):
    raise BadProgrammerException("This handler claims to support this action (%d), but has not implemented it." % self.requestedAction)
  def invalidCustomAction(self):
    raise BadActionException("Invalid custom action for this python handler (custom action: %s, eai action: %d)." \
        % (self.customAction, self.requestedAction))
