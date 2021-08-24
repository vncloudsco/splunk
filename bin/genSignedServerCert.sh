#!/bin/sh
SCRIPT_LOCATION=`dirname "$0"`
eval `"$SCRIPT_LOCATION/splunk" envvars`

echo ++python "$SCRIPT_LOCATION/genSignedServerCert.py" "$@"
python "$SCRIPT_LOCATION/genSignedServerCert.py" "$@"
exit $?
