#!/bin/sh

SCRIPT_LOCATION=`dirname "$0"`
eval `"$SCRIPT_LOCATION/splunk" envvars`


usage() {
    echo "Usage: getSignedServerCert.sh "
    echo ""
    echo "  -d <CERT_DIR> Where to store the root CA. /opt/splunk/etc/certs  REQUIRED" 
    echo ""
    echo "  -l <KEYLEN> Length of RSA key to generate. OPTIONAL" 
    echo ""
    echo ""
    exit 1
}


PROMPT=1
KEYLEN=2048

while getopts d:l:p OPTION
do
  case "${OPTION}" in
      d) CERTDIR="$OPTARG";;
      l) KEYLEN="$OPTARG";;
      p) PROMPT=0;;
      \?) usage;;
  esac
done

if [ "x$CERTDIR" = "x" ]; then
    echo "You must specify where your certificates are to be stored"
    echo ""
    usage
fi

cd "$CERTDIR"

if [ -f ca.pem ]; then
    echo "There is ca.pem in this directory. If you choose to replace the CA then splunk servers will require "
    echo "new certs signed by this CA before they can interact with it."
    echo "Do you wish to replace the CA ? [y/N]"
    read CONTINUE
    
    if [ "$CONTINUE" = "y" -o "$CONTINUE" = "Y" ]; then
        rm cacert.pem
        rm ca.pem
    else
        echo "Opted not to replace ca. Aborting."
        exit
    fi
fi 


echo "This script will create a root CA"
echo "It will output two files. ca.pem cacert.pem"
echo "Distribute the cacert.pem to all clients you wish to connect to you."
echo "Keep ca.pem for safe keeping for signing other clients certs"
echo "Remember your password for the ca.pem you will need to later to sign other client certs"
echo "Your root CA will expire in 10 years"

#generate the root key.
if [ $PROMPT = 0 ]; then
    # Create a certificate and signing request
    openssl req -newkey rsa:$KEYLEN -sha256 -keyout cakey.pem -out careq.pem
    openssl x509 -req -in careq.pem -sha256 -extensions v3_ca -signkey cakey.pem -out cacert.pem -days 3650
else
    openssl req -newkey rsa:$KEYLEN -passout pass:password -subj /countryName=US/stateOrProvinceName=CA/localityName=SanFrancisco/organizationName=SplunkInc/commonName=SplunkCA/organizationName=SplunkUser/ -sha256 -keyout cakey.pem -out careq.pem
    openssl x509 -req -in careq.pem -passin pass:password -sha256 -extensions v3_ca -signkey cakey.pem -out cacert.pem -days 3650

fi    

#generate cacert.pem

# create root cert cacert.pen + rootKey.pem
cat cacert.pem cakey.pem > ca.pem
    
# wrap it all in a X509 cert
openssl x509 -subject -issuer -dates -noout -in ca.pem
