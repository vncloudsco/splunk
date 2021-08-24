import sys, subprocess, getopt

# keys we'll be using when talking with splunk.
USERNAME    = "username"
# secure inputs configured in authentication.conf as key:value;key:value
# should be available to all functions that extract user information.
# This information is stored in a python dictionary 'args' and the 
# readInputs() function below parses these arguments.
SCRIPT_SECURE_INPUTS = "--scriptSecureArguments"
SEC_INPUTS_DELIM = ";"
SEC_INPUTS_SUB_DELIM = ":"
USERTYPE    = "role"
SUCCESS     = "--status=success"
FAILED      = "--status=fail"

# read the inputs coming in and put them in a dict for processing.
def readInputs():
   optlist, args = getopt.getopt(sys.stdin.readlines(), '', ['username=', 'password=', 'scriptSecureArguments=', 'userInfo='])

   returnDict = {}
   for name, value in optlist:
      if name == SCRIPT_SECURE_INPUTS:
        # handle all the secure script inputs configured in authentication.conf
        secInputs = value.split(SEC_INPUTS_DELIM)
        for secInput in secInputs:
            tokens = secInput.split(SEC_INPUTS_SUB_DELIM)
            returnDict[tokens[0]] = tokens[1].strip() 
      else: 
        returnDict[name[2:]] = value.strip()

   return returnDict
