"""
This script is called by splunkd's ScriptRunner.

The following args will be checked for:
  <script> <communication token> <args for script>

The following input data is expected, possibly via stdin:
  ScriptPath: <path to script to exec>
  SessionKey: <splunkd session key>
  ProductType: <string>
  <actual stdin data>

SessionKey will be parsed out and set as the global "___sessionKey".  Once
ScriptName is read in, the provided string is called via execfile(), allowing
the remaining stdin to still be handled by the script being called.
"""

import os, sys
import logging
import traceback

# Allows logging to work on any OS
PYTHON_LOG_PATH = os.path.join('var', 'log', 'splunk', 'python.log')

#SPL-28166
logging.basicConfig(level=("UNIT_TEST_EXTRA_LOGGING" in os.environ) and logging.INFO or logging.ERROR,
                   format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'], PYTHON_LOG_PATH),
                   filemode='a')
                   
logger = logging.getLogger(__name__)

def read_stdin_line():
    if sys.version_info >= (3, 0):
        # We don't want to read data directly from sys.stdin since that
        # will mean its internal buffers will get populated with decoded
        # UTF-8 data.  That means that any code that later tries to read
        # from sys.stdin.buffer will be missing part or all of their stream!
        # Instead read a line as bytes directly from I/O and decode it ourselves.
        return sys.stdin.buffer.readline().decode()
    return sys.stdin.readline()
        

# read in first line, script name.
tmpStr = read_stdin_line()
if not tmpStr.startswith("ScriptPath:"):
  raise Exception("Expected script path line (got: %s)." % tmpStr)
tmpStr = tmpStr.replace("ScriptPath:", "", 1)
REAL_SCRIPT_NAME = tmpStr.strip()
# empty script name is invalid.
if (len(REAL_SCRIPT_NAME) == 0):
  raise Exception("Script path is empty.")

# read in second line, session key.
tmpStr = read_stdin_line()
if not tmpStr.startswith("SessionKey:"):
  raise Exception("Expected session key line (got: %s)." % tmpStr)
tmpStr = tmpStr.replace("SessionKey:", "", 1)
# empty session key is not invalid.
___sessionKey = tmpStr.strip()

# read in 3rd line (added in 6.2/dash), product type.
tmpStr = read_stdin_line()
if not tmpStr.startswith("ProductType:"):
  raise Exception("Expected product type line (got: %s)." % tmpStr)
tmpStr = tmpStr.replace("ProductType:", "", 1)
# empty product type is invalid.
___productType = tmpStr.strip()

scriptDir = os.path.dirname(REAL_SCRIPT_NAME)
sys.path.append(scriptDir)
os.chdir(scriptDir)
# Can turn on debugging if imports get messed up.
logger.debug("Running script with imported path=" + scriptDir)

# the rest of stdin is preserved - exec the real script now.
__file__ = REAL_SCRIPT_NAME
try:
    if sys.version_info < (3, 0):
        execfile(REAL_SCRIPT_NAME)
    else:
        exec(open(REAL_SCRIPT_NAME).read())
except Exception as exc:
    tb = traceback.format_exc()
    err_string = "The script at path=" + REAL_SCRIPT_NAME + " has thrown an exception=" + tb
    logger.error(err_string)
    # This allows it to also go to splunkd.log, which it was not in before.
    sys.stderr.write(err_string + "\n")
    raise
