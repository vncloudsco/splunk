"""
This file contains code that is used for building or running unit tests, but
is not needed for splunk run-time.  This file will not be packaged.
"""

import os

"""
Returns the build type of the current environment (typically returns "Debug" or "Release")
"""
def discover_msvc_build_type(splunk_home):
	cbt_filename = os.path.join(splunk_home, "include", "verify-contrib-build-type.h")
	if not os.path.exists(cbt_filename):
		raise Exception("File '%s' does not exist: cannot determine build type" % cbt_filename)
	cbt_handle = open(cbt_filename)
	cbt_contents = cbt_handle.readlines()
	cbt_handle.close()
	return cbt_contents[0].split(" ")[1].split("=")[1]

"""
Returns the architecture of the current environment (returns "x86" or "amd64")
"""
def discover_msvc_architecture_type(splunk_home):
	cbt_filename = os.path.join(splunk_home, "include", "verify-contrib-build-type.h")
	if not os.path.exists(cbt_filename):
		raise Exception("File '%s' does not exist: cannot determine architecture type" % cbt_filename)
	cbt_handle = open(cbt_filename)
	cbt_contents = cbt_handle.readlines()
	cbt_handle.close()
	bits_str = cbt_contents[1].split(" ")[1].split("=")[1]
	retval = "x86"
	if bits_str == "64":
		retval = "amd64"
	elif bits_str != "32":
		raise Exception("Unexpected bit string '%s' found in '%s'" % (bits_str, cbt_filename))
	return retval

