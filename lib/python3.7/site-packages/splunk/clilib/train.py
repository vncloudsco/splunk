from __future__ import absolute_import
import logging as logger
import os
import splunk.clilib.cli_common as comm
from splunk.clilib import control_exceptions as cex

PYTHON_CMD     = "python"

def makeScriptCmd(script):
  # 2nd arg is quoted in case $SPLUNK_HOME has spaces in it.
  return "%s \"%s\"" % (PYTHON_CMD, os.path.join(comm.SPLUNK_PY_PATH, "mining", script))

def trainFields(args, fromCLI):
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  os.system(makeScriptCmd("interactiveLearner.py"))

def trainDates(args, fromCLI):
  paramsReq = ()
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  os.system(makeScriptCmd("interactivedates.py"))
