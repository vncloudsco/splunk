from __future__ import absolute_import
#   Version 4.0
import logging as logger
import splunk.clilib.cli_common as comm
import os, shutil
from splunk.clilib import control_exceptions as ce
from splunk.clilib import bundle_paths
from splunk.clilib.bundle_paths import make_splunkhome_path

# TODO: should the server be up, down, or either for these operations?

def imUserSplunk(args, fromCLI):
  """
  Import users and splunks.
  """
  paramsReq = ("dir",)
  paramsOpt = ()

  comm.validateArgs(paramsReq, paramsOpt, args)

  bakDir = os.path.normpath(args["dir"])

  #
  # No errors found, continue.
  #

  logger.info("Restoring user data from dir: %s." % bakDir)

  PASS_NAME     = "passwd"
  PASS_FILE_BAK = os.path.join(bakDir, PASS_NAME)
  PASS_FILE     = make_splunkhome_path(["etc", PASS_NAME])

  filename, oldFilePath, newFilePath = (PASS_NAME, PASS_FILE_BAK, PASS_FILE)
  if os.path.exists(oldFilePath):
    shutil.copy(oldFilePath, newFilePath)
  else:
    if filename in (PASS_NAME,):
      logger.info("No '%s' file found in supplied backup dir '%s'. Did you supply an incorrect directory?" % (filename, bakDir))

  try:
    importer = bundle_paths.BundlesImporter()
    site = bundle_paths.BundlesImportExportSite(bakDir)
    importer.do_import(site)
  except bundle_paths.BundleException as e:
    raise ce.FilePath("Unable to import: %s.  Aborting restore." % e)
