from __future__ import absolute_import
#   Version 4.0
import logging as logger
import splunk.clilib.cli_common as comm
import os, re, subprocess

DB_MANIP   = os.path.join(comm.splunk_home, "bin", "dbmanipulator.py")

EXPORT_FILE    = "export.csv"
EXPORT_GZ_FILE = "export.csv.gz"

def getDef(args, fromCLI):
  """
  Show the default index.
  """
  paramsReq = ()
  paramsOpt = ()

  comm.validateArgs(paramsReq, paramsOpt, args)
  comm.requireSplunkdDown()

  #
  # No errors found, continue.
  #

  logger.info("Default index: ")
  os.system("python \"%s\" --showdefault" % DB_MANIP)


def setDef(args, fromCLI):
  """
  Set the new default index.
  """
  paramsReq = ("value",)
  paramsOpt = ()

  comm.validateArgs(paramsReq, paramsOpt, args)
  comm.requireSplunkdDown()

  #
  # No errors found, continue.
  #

  os.system("python \"%s\" --default \"%s\"" % (DB_MANIP, args["value"]))


def do_import(bucket, export_file):
  logger.info("importing %s" % bucket)
  if os.system("importtool \"%s\" \"%s\"" % (bucket, export_file)) == 0:
    os.remove(export_file)
  else:
    logger.error("error importing %s" % bucket)
