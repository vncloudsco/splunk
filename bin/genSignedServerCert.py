import subprocess, sys

sys.stderr.write("NOTE: This script is deprecated.  Instead, use \"splunk createssl server-cert\".\n\n");
sys.exit(subprocess.call(["splunk", "createssl", "server-cert"] + sys.argv[1:]))
