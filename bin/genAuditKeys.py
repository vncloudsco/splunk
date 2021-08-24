# This script will generate a public and private key and place them
# in the directory $SPLUNK_HOME/etc/auth/audit/private.pem|public.pem

import subprocess, sys

sys.stderr.write("NOTE: This script is deprecated.  Instead, use \"splunk createssl audit-keys\".\n\n");
sys.exit(subprocess.call(["splunk", "createssl", "audit-keys"] + sys.argv[1:]))
