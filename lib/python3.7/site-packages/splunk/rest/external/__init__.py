# /////////////////////////////////////////////////////////////////////////////
#  This stub file is a proxy for importing all the of bundled custom REST
#  endpoint handlers.  

#  The path insertion here allows all python scripts that are added in the
#  bundles to be accessible from other python modules under the following:
#       import splunk.rest.external.<module_name>
#
#  For instance, if you add the file, /etc/bundles/imap/rest/mailbox.py
#  then that module will be available at:
#       import splunk.rest.external.mailbox
#
# /////////////////////////////////////////////////////////////////////////////

import os
from splunk.clilib import bundle_paths

# locate eligible python scripts paths within the bundle system
bundleList = sorted(bundle_paths.get_bundle_subdirs("bin") +
              bundle_paths.get_bundle_subdirs("rest"))
for scriptsPath in bundleList:
    if os.access(scriptsPath, os.R_OK):

        # inject bundle path into local python module path
        __path__.insert(0, scriptsPath)
