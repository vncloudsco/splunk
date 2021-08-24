#!/usr/bin/python

#
# Python binding for HTTP REST server script dispatch
#
# REST endpoints that have been assigned a python script handler will invoke
# this script by default, unless otherwise specified in the restmap.conf
# file.
#
# This handler is invoked as a standard program:
#
#   python rest_handler.py <handlerClassName> <requestXml> <authInfo>
#
# handlerClassName: The name of the python class to dispatch. This is generally
#                   of the form: <module_name>.<class_name>
#
# requestInfo: String version of request XML document; see splunk/rest/selftest.py
#
# sessionKey: The current session key used by the client
#
#
# This script must be run in the Splunk python context (python2.5, PYTHONPATH)

import os, sys
import splunk
import splunk.rest
import splunk.Intersplunk
import splunk.mining.dcutils as dcu
import logging
import traceback
import datetime 
import time
from splunk.clilib.bundle_paths import make_splunkhome_path

#SPL-18630
import __main__

#
# setup logging
#

# logging settings
BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
PYTHON_LOG_FILENAME = 'python.log'
#PYTHON_LOG_LEVEL = logging.INFO
PYTHON_LOG_LEVEL = logging.ERROR
LOGGING_DEFAULT_CONFIG_FILE = make_splunkhome_path(['etc', 'log.cfg'])
LOGGING_LOCAL_CONFIG_FILE = make_splunkhome_path(['etc', 'log-local.cfg'])
LOGGING_STANZA_NAME = 'python'
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
logger = dcu.getLogger()

#
# read in argv's
#

#assert(len(sys.argv) > 2)
assert(len(sys.argv) > 1)

handlerClassName = sys.argv[1]
#SPL-18630
#make this backwards comp.
try:
    sessionKey = getattr(__main__, "___sessionKey")
except AttributeError:
    #fall back to the old behaviour
    assert(len(sys.argv) > 2)
    sessionKey = sys.argv[2]

if sys.version_info >= (3, 0):
    request = sys.stdin.buffer.read()
    def stdout_print(s):
        if isinstance(s, str):
            s = s.encode()
        sys.stdout.buffer.write(s + b"\n")
else:
    request = sys.stdin.read()
    def stdout_print(s):
        sys.stdout.write(s + "\n")

params = {
    'handlerClassName': handlerClassName,
    'requestInfo': request,
    'sessionKey': sessionKey
}

try:
    stdout_print(splunk.rest.dispatch(**params))
except Exception as e:
    logger.exception(e)
    # SPL-160673 - Print a user appropriate message.
    #stdout_print("An exception was thrown while dispatching the python script handler." + str(e) + traceback.format_exc())
    stdout_print("An exception was thrown while dispatching the python script handler.")
