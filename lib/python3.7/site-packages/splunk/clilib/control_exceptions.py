#   Version 4.0
# ====================
# Module for Exceptions related to ControlAPI
# ====================

class PCLException(Exception):
  def __init__(self, msgVal):
    Exception.__init__(self, msgVal)
  def __str__(self):
    return repr(self.args)

class ArgError(PCLException):
  pass

class AuthError(PCLException):
  pass

class ConfigError(PCLException):
  pass

class FileAccess(PCLException):
  pass

class FilePath(PCLException):
  pass

class FileType(PCLException):
  pass

class InternalError(PCLException):
  pass

class InputError(PCLException):
  pass

class InvokeAPI(PCLException):
  pass

class ParsingError(PCLException):
  pass

class PipeIOError(PCLException):
  pass

class SearchError(PCLException):
  pass

class ServerState(PCLException):
  pass

class ServerConnectionException(PCLException):
  pass

# caller should not continue beyond here.
class StopException(PCLException):
  pass

# python is not continuing, but there was no error.
class SuccessException(PCLException):
  pass

class ValidationError(PCLException):
  def __init__(self, nameVal, argVal, descVal):
    self.arg  = argVal
    self.desc = descVal
    self.name = nameVal
    message = "%s (parameter: \"%s\", value: \"%s\")" % (self.desc, self.name, self.arg)
    PCLException.__init__(self, message)
  def getDesc(self):
    return repr(self.desc)
  def getName(self):
    return repr(self.name)
  def getArg(self):
    return repr(self.arg)

class VersionError(PCLException):
  pass
