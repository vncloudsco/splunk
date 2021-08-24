#!/bin/sh
SCRIPT_LOCATION=`dirname "$0"`
eval `"$SCRIPT_LOCATION/splunk" envvars`

umask 022

exec python "$SCRIPT_LOCATION/genWebCert.py" "$@"
