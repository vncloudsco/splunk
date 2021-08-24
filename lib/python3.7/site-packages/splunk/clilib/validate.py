from __future__ import absolute_import
#   Version 4.0
from builtins import range
import re
from .control_exceptions import ValidationError

CRONFIELD_DESC = "Each field in a schedule must consist of only 0-9, *, /, and/or -."
CRON_NUM_DESC  = "The schedule string must consist of 5 fields, in the form '0 0 * * *'."
HOSTNAME_DESC  = "Hostnames must consist of only numbers, letters, periods, underscores, and dashes."
IP_ADDR_DESC   = "IP addresses must be in the form 'a.b.c.d'."
IP_QUAD_DESC   = "Each section of an IP address must be a number from 0 to 255."

_alphaNumIshPattern = "^[0-9a-zA-Z._-]*$" # alphanum + a bit extra..

#   given a passed in val and an regex,
#   return True or RE obj on match, raise exception otherwise
def validateInput(argVal, expr):
    if not argVal is None:
        # compile the pattern
        p = re.compile(expr, re.IGNORECASE)
        match = p.match(argVal)
        if match is None:
            return False
    else:
        return False
    
    return True 



def checkLowerAscii(name, val):
  """
  Checks to see whether all chars in agiven string are contained within ASCII 32 through
  ASCII 126. 
  """
  length = len(str(val))
  # ugh, if someone knows of an 'ord()' for a whole string, lemme know.
  for num in range(0, length):
    ascii = ord(val[num])
    if ascii < 32 or ascii > 126: # between space and tilde, inclusive.
      raise ValidationError(name, val, "Special characters are not allowed.")
  return val



def checkBase(name, val, checkCharSet = True):
  """
  Does any base checks that should be done for every check function.
  """
  if len(str(name)) < 1:
    raise ValidationError(name, val, "Arguments must not be empty.")
  if checkCharSet:
    checkLowerAscii(name, val)
  return val



def checkBool(name, val):
  """
  Checks that a given string is a boolean value (true/false).
  """
  checkBase(name, val)
  # who knows what we're passed.. just make sure it's a string first, to be safe.
  val = str(val).lower()

  if not str(val).lower() in ("true", "false", "1", "0"):
    raise ValidationError(name, val, "This value must be one of: true, false, 1, 0.")

  if val == 'true' or val == '1':
    return True
  else:
    return False



def checkPosInt(name, val):
  """
  Checks that a given string is a positive integer.
  """
  checkBase(name, val)
  # who knows what we're passed.. just make sure it's a string first, to be safe.
  if not str(val).isdigit() or int(val) < 0:
    raise ValidationError(name, val, "This value must be a positive integer.")

  val = int(val)
  return val



def checkPortNum(name, val):
  """
  Checks that a port number is valid - a positive integer less than 65536.
  """
  checkBase(name, val)
  # who knows what we're passed.. just make sure it's a string first, to be safe.
  # allow for 0 because that's how we disable ports from being opened.
  if not str(val).isdigit() or int(val) < 0 or int(val) > 65535:
    raise ValidationError(name, val, "Ports must be numbers between 0 and 65535.")
  return val



def checkIP(name, val):
  """
  Checks that an IP address is valid - dotted quad, each from 0 to 255.
  """
  checkBase(name, val)
  # who knows what we're passed.. just make sure it's a string first, to be safe.
  sections = str(val).split(".")
  if len(sections) != 4:
    raise ValidationError(name, val, IP_ADDR_DESC)

  for quad in sections:
    if not quad.isdigit() or int(quad) < 0 or int(quad) > 255: 
      raise ValidationError(name, val, IP_QUAD_DESC)
  return val



def checkHostname(name, val):
  """
  Checks that a hostname is valid - chars are 0-9, a-z, A-Z, period, underscore, dash.
  """
  checkBase(name, val)
  # who knows what we're passed.. just make sure it's a string first, to be safe.
  hostname = str(val)

  if not validateInput(hostname, _alphaNumIshPattern):
    raise ValidationError(name, hostname, HOSTNAME_DESC)
  return val


def checkHostPort(name, val):
  checkBase(name, val)
  sections = str(val).split(":")
  if len(sections) != 2:
    raise ValidationError(name, val, "Host/port must be in the form 'host:port'.")
  checkHostname(name, sections[0])
  checkPortNum(name, sections[1])
  return val



def checkIPPort(name, val):
  checkBase(name, val)
  sections = str(val).split(":")
  if len(sections) != 2:
    raise ValidationError(name, val, "IP/port must be in the form 'ip:port'.")
  checkIP(name, sections[0])
  checkPortNum(name, sections[1])
  return val



def checkIPPortOrHostPort(name, val):
  """
  Checks that the value is either a valid hostname OR IP address...
  """
  checkBase(name, val)
  lastSection = str(val).split(":")[0].split(".")[-1]
  try:
    if lastSection.isdigit():
      checkIPPort(name, val)
    else:
      checkHostPort(name, val)
  except ValidationError:
    raise ValidationError(name, val, "Host/port and IP/port must be in the form 'host-or-ip:port'.  %s  %s  %s" % (HOSTNAME_DESC, IP_ADDR_DESC, IP_QUAD_DESC))
  return val
