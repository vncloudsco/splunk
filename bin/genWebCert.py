import subprocess, sys

sys.stderr.write("NOTE: This script is deprecated.  Instead, use \"splunk createssl web-cert\".\n\n");
sys.exit(subprocess.call(["splunk", "createssl", "web-cert"] + sys.argv[1:]))
