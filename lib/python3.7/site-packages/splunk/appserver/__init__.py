# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

#
# locate and insert any registered custom web bundle python scripts
#
# the expected format is that any bundle directory have a 'web' subdirectory
# that contains python methods
#

import os, sys
from splunk.clilib import bundle_paths

# locate scripts directory
bundleList = sorted(bundle_paths.get_bundle_subdirs("bin") +
              bundle_paths.get_bundle_subdirs("web"))
for scriptsPath in bundleList:
    if os.access(scriptsPath, os.F_OK):
        # inject the bundle path into pythonpath
        sys.path.append(scriptsPath)
        #print("Loading appserver path: %s" % scriptsPath)
