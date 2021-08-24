from __future__ import absolute_import
#   Version 4.0
import logging as logger
import os

from splunk.clilib import cli_common as comm


ARG_NAME    = "name"
ARG_UPGRADE = "upgrade"

BUNDLE_EXTENSIONS = ('.conf', '.bundle')

# Bundles that should not be shown to users
BUNDLES_IGNORE = ('default', 'local', 'README')

def showConfig(args, fromCLI):
  paramsReq = (ARG_NAME,)
  paramsOpt = ()
  comm.validateArgs(paramsReq, paramsOpt, args)
  logger.info(comm.getMergedConfRaw(args[ARG_NAME]))

##############################################################################
# Internally used functions
##############################################################################

def getBundleTuples(path):
  """Return dictionary of tuples describing bundles in a path
  
  key - name of bundle (e.g. default)
  0 - absolute path to bundle (e.g. /etc/bundles/default.conf)
  1 - bundle base file name
  """
  bundles = {}

  try:
    for bundleFileName in os.listdir(path):

      # Construct full, absolute path to bundle
      bundlePath = os.path.join(path, bundleFileName)

      # Files
      for extension in BUNDLE_EXTENSIONS:
        if bundleFileName.endswith(extension):
          # Remove extension from name
          bundleName = bundleFileName[0:bundleFileName.rfind(extension)]

          # Ignore certain bundles
          if bundleName in BUNDLES_IGNORE:
            continue

          bundles[bundleName] = (bundlePath, bundleFileName)
          continue

      # Directories
      bundleName = bundleFileName
      if os.path.isdir(bundlePath):
        # Ignore certain bundles
        if bundleName in BUNDLES_IGNORE:
          continue

        bundles[bundleName] = (bundlePath, bundleFileName)
  except OSError:
    bundles = {}

  return bundles
