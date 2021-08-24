"""
    Provides utilities to make secure network connections using the Python ssl
    module. When run in Common Criteria mode, we perform additional certificate
    verification steps.

    The main function is SSLHelper.createSSLContext. This function creates an
    ssl.SSLContext instance and applies parameterized ssl settings to it.

    SSLHelper.createSSLContextFromSettings takes the content of the passed in
    conf file settings and maps them to a call to SSLHelper.createSSLContext.
    Most callees will be using this function.

    The SecureSMTP module uses this class to make secure smtp connections.

    The preferred way to make a secure HTTP request is to use this module along
    with the urllib2 module. Here's an example usage:


        import splunk.ssl_context as ssl_context
        from future.moves.urllib.request import urlopen

        sslHelper = ssl_context.SSLHelper()
        ctx = sslHelper.createSSLContextFromSettings(
                sslConfJSON=myConfFileJSON,
                serverConfJSON=serverConfJSON,
                isClientContext=True)
        res = urlopen('https://www.splunk.com', context=ctx)

"""
from builtins import object
import glob
import os
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.entity as entity
import splunk.mining.dcutils as dcu
import splunk.util as util
import ssl

__all__ = ('SSLHelper')

# Bitmap for SSL versions
SSLVERSION_SSL2 = 0x01
SSLVERSION_SSL3 = 0x02
SSLVERSION_TLS1_0 = 0x04
SSLVERSION_TLS1_1 = 0x08
SSLVERSION_TLS1_2 = 0x10
ALL_SSL_VERSIONS = (SSLVERSION_SSL3 | SSLVERSION_TLS1_0
                   | SSLVERSION_TLS1_1 | SSLVERSION_TLS1_2)

# Validate Server/Client
VALIDATE_NONE           = 0
VALIDATE_CLIENT         = 1
VALIDATE_SERVER         = 2
VALIDATE_CLIENT_SERVER  = VALIDATE_CLIENT | VALIDATE_SERVER

X509_MIN_VERSION = 3

X509_V_ERR_UNABLE_TO_GET_CRL = 3
X509_V_ERR_CRL_HAS_EXPIRED = 12

# Hard coded path to location of the CRLs. Eventually we will expose this as a
# conf file setting
PATH_CRL_DIR         = make_splunkhome_path(["etc", "auth", "crl"])

logger = dcu.getLogger()

def verifyName(certDict, subjectAltNamesToCheck=None,
               commonNamesToCheck=None):
    """
        Called internally by createSSLContext to perform certificate
        SAN(Subject Alternate Name) and CN(Common Name) verification checks.

        If alternate names exist, they have to match in common criteria mode
        SPL-105519, SAN(Subject Alternate Name) check takes priority over
        CN(Common Name) check. Note we do not do any wildcard checking. The
        spelling must be exact. We do trim leading and trailing whitespace
        before performing the check
    """

    verificationError = ""
    # Typically a tuple of tuples
    subjectAltName = certDict.get('subjectAltName')

    if subjectAltNamesToCheck:
        # Pluck out the DNS names, trim the whitespace and put them into a set
        if subjectAltName:
            sanAsSet = set(name[1].strip() for name in subjectAltName)
        else:
            sanAsSet = set()
        # Convert the comma delimited string into a set with trimmed whitespace
        altNameAsSet = set(
            name.strip() for name in subjectAltNamesToCheck.split(","))
        # Find all of the common items in the two sets
        altNameIntersection = altNameAsSet.intersection(sanAsSet)
        # If there are any matches, then the SAN check has passed
        sanCheckPassed = len(altNameIntersection) > 0
        if not sanCheckPassed:
            verificationError = (("The certificate's Subject Alternative Name "
                                  "%s did not match any allowed names [%s]")
                                % (list(sanAsSet), subjectAltNamesToCheck))
        return sanCheckPassed, verificationError

    # Format is a tuple of tuples of tuples
    # eg. ((('countryName', u'US'),), (('stateOrProvinceName', u'California'),),
    # (('localityName', u'San Francisco'),),
    # (('organizationName', u'Splunk, Inc.'),),
    # (('commonName', u'*.splunk.com'),))
    # Put the subject into a dictionary

    if commonNamesToCheck:
        commonName = getSubjectFromCertDict(certDict)
        # Convert the comma delimited string into a set with trimmed whitespace
        commonNamesAsSet = set(
            name.strip() for name in commonNamesToCheck.split(","))
        # If the common name is in the whitelist of common names, then the CN
        # has passed
        cnCheckPassed = commonName in commonNamesAsSet
        if not cnCheckPassed:
            verificationError = (("The certificate's common name [%s] did not "
                                  "match any allowed names [%s]")
                                % (commonName, commonNamesToCheck))
        return (cnCheckPassed, verificationError)

    # If we have no names to check, then verification passes
    return (True, verificationError)

def getHostFromSocket(sock):
    if sock is None:
        return None
    return sock.getpeername()[0]

def getSubjectFromCertDict(certDict):

    subject = certDict.get('subject')
    if subject:
        subjectDict = dict(x[0] for x in subject)
        if subjectDict:
            return subjectDict.get('commonName')

    return None

class SSLHelper(object):
    """
        Author: Jason Szeto
        Date: December 10, 2015

        Helper class used for setting up secure network connections using
        PyOpenSSL.
    """
    sessionKey = None
    ccMode = None
    fipsMode = None

    def isCCMode(self):
        if self.ccMode == None:
            ccBoolVal = os.getenv('SPLUNK_COMMON_CRITERIA')
            if ccBoolVal == None:
                self.ccMode = False
            else:
                self.ccMode = util.normalizeBoolean(ccBoolVal)
        return self.ccMode

    def isFipsMode(self):
        if self.fipsMode == None:
            fipsBoolVal = os.getenv('SPLUNK_FIPS')
            if fipsBoolVal == None:
                self.fipsMode = False
            else:
                self.fipsMode = util.normalizeBoolean(fipsBoolVal)
        return self.fipsMode

    def parseOneSslVersion(self, version):
        table = [
            # A few special strings that describe multiple versions
            [ "*",		ALL_SSL_VERSIONS ],
            [ "all",	ALL_SSL_VERSIONS ],
            [ "tls",	SSLVERSION_TLS1_0 | SSLVERSION_TLS1_1 | SSLVERSION_TLS1_2 ],

            # Then the particular ones, including some aliases
            [ "ssl3",	SSLVERSION_SSL3 ],
            [ "sslv3",	SSLVERSION_SSL3 ],
            [ "ssl-3",	SSLVERSION_SSL3 ],

            [ "tls10",	SSLVERSION_TLS1_0 ],
            [ "tls1.0",	SSLVERSION_TLS1_0 ],
            [ "tls-1.0",	SSLVERSION_TLS1_0 ],

            [ "tls11",	SSLVERSION_TLS1_1 ],
            [ "tls1.1",	SSLVERSION_TLS1_1 ],
            [ "tls-1.1",	SSLVERSION_TLS1_1 ],

            [ "tls12",	SSLVERSION_TLS1_2 ],
            [ "tls1.2",	SSLVERSION_TLS1_2 ],
            [ "tls-1.2",	SSLVERSION_TLS1_2 ],

            # SSLv2 isn't supported at all anymore by OpenSSL, but  we still
            # need to recognize the tokens so that settings like "*,-ssl2" parse
            ["ssl2", SSLVERSION_SSL2],
            ["sslv2", SSLVERSION_SSL2],
            ["ssl-2", SSLVERSION_SSL2]
        ]

        for entry in table:
            if (len(version) == len(entry[0]) and
               version.lower() == entry[0].lower()):
                return entry[1];
        return 0

    def parseSSLVersions(self, sslVersionString):
        """
            Parse SSL versions string into its bit-map presentation.
            Check SSLVERSION_* constants for mapping info.
        """
        if sslVersionString == None:
            return 0

        # strip whitespaces and tabs.
        sslVersionString = sslVersionString.replace(' ', '').replace('\t', '')
        words = sslVersionString.split(',')
        gotOne = False
        retval = 0
        for word in words:
            negate = False
            if word.startswith('-') or word.startswith('!'):
                if not gotOne:
                    retval = ALL_SSL_VERSIONS
                # remove first char
                word = word[1:]
                negate = True
            elif word.startswith('+'):
                # remove first char
                word = word[1:]
            # convert into the SSL version bitmap
            bits = self.parseOneSslVersion(word)

            # 0 indicates a bad version-string; fall-back to a secure default.
            if bits == 0:
                return 0

            if negate:
                retval = retval & ~bits
            else:
                retval = retval | bits
            gotOne = True

        return retval

    def verifyCallback(self, sock, isOK, certDict, errorNum, certDepth):
        """
            Callback function called by an ssl connection when verifying
            a certificate chain. The function is called once for each
            certificate in the chain. This implementation performs additional
            verification steps required for Common Criteria compliance.

            The callback is not natively part of the ssl module. We have patched
            the module to expose the callback. The callback takes 5 arguments:
            a socket, openssl flag for verification success, the certificate as
            a dictonary, the openssl error number, and the certificate depth
            callback should return true if verification passes and false
            otherwise.

            Common Criteria verification steps

            From [src/framework/X509Verify.cpp]:
            * If depth == 0, check that Extended Key Usage is for server usage
            (if we are client) or client usage (if we are server)
            Check if there is a Purpose == "Server Authentication" or "Client
            Authentication"
            * If depth > 0, check that Basic Constraints -> Certificate
            Authority is true
            * Check Version >= 3

            From [src/util/X509.cpp:x509CheckCommonAlternateNames]:
            If alternate names exist, they have to match in common criteria
            mode
            SPL-105519, SAN(Subject Alternate Name) check takes priority over
            CN(Common Name) check. Check that the Subject Alternative Name and
            the sslAltNameToCheck lists contain a match. Check that the Common
            Name and the sslCommonNameToCheck lists contain a match

            Do we need to do wildcard checking (eg. *.splunk.com)
            Currently only do DNS checking
            Only do the CC case (check SAN first, then CN).

           CRL check
                - C++ side passes verification if CRL expired and prints warning
                - C++ side passes verification if CRL is missing
                - Instead of passing caPath to load_verify_locations, read in
                the files in caPath and pass those into load_verify_locations
                individually
                - Check if python ssl will throw an exception if you pass in a
                non-PEM


        """

        logger.debug('SSLHelper.verifyCallback errorNum: [%d] certDepth [%d] '
                     'isOK [%d] cert %s'
                     % (errorNum, certDepth, isOK, certDict))

        # If we get one of the following errors,
        # X509_V_ERR_UNABLE_TO_GET_CRL (3) or X509_V_ERR_CRL_HAS_EXPIRED (12),
        # we override the error. We want the CRL check to be more loose.
        # SPL-94905: We make the selection of "accept the certificate" for
        # an expired CRL. The check itself will log the warning and it is
        # the user's responsibility to download/update a valid CRL. This is
        # consistent with our behavior while loading CRLs at startup
        # where we ignore any expired CRLs.
        if not isOK:
            if errorNum == X509_V_ERR_UNABLE_TO_GET_CRL:
                logger.warning("A request to %s is missing a CRL file for "
                               "the certificate at depth %d. We are "
                               "overriding this OpenSSL error [%d], but we "
                               "recommend that you install the missing CRL "
                               "file. Certificate = %s"
                               % (getHostFromSocket(sock), certDepth,
                                  errorNum, certDict))
            elif errorNum == X509_V_ERR_CRL_HAS_EXPIRED:
                logger.warning("A request to %s has an expired CRL file for "
                               "the certificate at depth %d. We are "
                               "overriding this OpenSSL error [%d], but we "
                               "recommend that you update the expired CRL "
                               "file. Certificate = %s"
                               % (getHostFromSocket(sock), certDepth,
                                  errorNum, certDict))
            else:
                logger.error("A request to %s has an invalid certificate at "
                             "depth %d. OpenSSL error number = [%d]. "
                             "Certificate = %s"
                             % (getHostFromSocket(sock), certDepth,
                                errorNum, certDict))
                return False

        verificationError = ""

        if self.isCCMode():
            if certDepth == 0:
                """
                    SPL-94899: "The application shall validate the
                    extendedKeyUsage field according to the following rules:

                    * Server certificates presented for TLS shall have the
                      Server Authentication purpose ... in the extendedKeyUsage
                      field.

                    * Client certificates presented for TLS shall have the
                      Client Authentication purpose ... in the extendedKeyUsage
                      field."
                """
                extendedKeyUsage = certDict['extendedKeyUsage']
                if not (extendedKeyUsage & ssl._ssl.XKU_SSL_SERVER):
                    verificationError = ("The certificate extendedKeyUsage does "
                                         "not support server authentication")
            elif certDepth > 0:
                """
                    SPL-94900: "The application shall only treat a certificate
                    as a CA certificate if the basicConstraints extension is
                    present and the CA flag is set to TRUE."
                """

                exFlags = certDict['ex_flags']
                if not (exFlags & ssl._ssl.EXFLAG_CA):
                    verificationError = ("The certificate is not a certificate "
                                         "authority.")

            # SPL-94904: "The application shall use X.509v3 certificates as
            # defined by RFC 5280 to support authentication...."
            version = certDict['version']
            if version < X509_MIN_VERSION:
                # From x509_txt.c - application verification failure
                verificationError = (("The certificate version is too old. "
                                      "Certificate version = [%d] Expected version "
                                      "= [%d]") % (version, X509_MIN_VERSION))

        if verificationError == "" and certDepth == 0:
            passesVerify, verificationError = verifyName(certDict,
                                                         self.altNameList,
                                                         self.commonNameList)

        if verificationError != "":
            logger.error("The certificate for [%s] at depth [%d] failed "
                         "verification for the reason [%s]. Certificate = %s"
                         % (getSubjectFromCertDict(certDict), certDepth,
                            verificationError, certDict))
            return False

        return True

    def createSSLContext(self,
                             sslVersions=0,
                             commonNameList=None,
                             altNameList=None,
                             cipherSuite=None,
                             validatePeerCert=VALIDATE_NONE,
                             rootCAPath=None,
                             isClientContext=True):

        """
            Creates a ssl.SSLContext instance to be used for making a secure
            connection.

            Arguments:
                sslVersions (int) - bitmap flag that contains all of the
                supported ssl versions. Use the bitmap constants to specify the
                version(s). SSLVERSION_SSL2, SSLVERSION_SSL3, SSLVERSION_TLS1_0,
                SSLVERSION_TLS1_1, SSLVERSION_TLS1_2, ALL_SSL_VERSIONS. Can
                also use SSLHelper.parseSSLVersions to map the string list from
                a conf file attribute to the bitmap flag value

                commonNameList (string) - a comma delimited string of
                whitelisted host names to compare against a certificate's Common
                Name. (eg. 'splunk.com, *.splunk.com'). The certificate will
                pass the CN (Common Name) check if it's common name matches a
                host on this list

                altNameList (string) - a comma delimited string of
                whitelisted host names to compare against a certificate's
                Subject Alternative Name. (eg. 'splunk.com, *.splunk.com').
                The certificate will pass the SAN check if any of the names in
                its Subject Alternative Name matches any host on this list

                cipherSuite (string) - The TLS cipher suite string to use for
                the secure connection (eg. ECDHE-RSA-AES256-SHA)

                validatePeerCert (int) - bitmap flag that determines which
                combination of client and server to perform verification upon.
                Can contain any combination of the following values:
                VALIDATE_NONE, VALIDATE_CLIENT, VALIDATE_SERVER,
                VALIDATE_CLIENT_SERVER

                rootCAPath (string) - path to the certificate file in PEM format
                that contains the root CA (Certificate Authority) certificate
                store.

                isClientContext (boolean) - set to true if the calling code is
                the client of the connection. Set to false if it is the server.
                This value is used in conjunction with the validatePeerCert
                parameter to determine if certificate verification should occur

        """
        self.commonNameList = commonNameList
        self.altNameList = altNameList

        logger.debug("createSSLContext sslVersions [%s] commonNameList [%s] "
                     "altNameList [%s] validatePeerCert [%s] rootCAPath [%s] "
                     "isClientContext [%s] cipherSuite [%s]" %
                     (sslVersions, commonNameList, altNameList, validatePeerCert,
                      rootCAPath, isClientContext, cipherSuite))

        # if bad string or missing parameter, use tls1.0 and above.
        if sslVersions == 0:
            sslVersions = SSLVERSION_TLS1_0 \
                          | SSLVERSION_TLS1_1 \
                          | SSLVERSION_TLS1_2

        # FIPS mode allows only TLS1.0 or higher
        if self.isFipsMode():
            sslVersions = sslVersions & ~(SSLVERSION_SSL2 | SSLVERSION_SSL3)
        else:
            # SSLv2 isn't supported at all, so never let that bit appear
            sslVersions = sslVersions & ~SSLVERSION_SSL2


        if sslVersions == 0:
            raise Exception("No compatible SSL versions requested.")

        # Create the context using the sslVersions
        # If sslVersions is a single protocol version, then create that specific
        # SSL context. If there are multiple versions specified, then allow all
        # versions (SSL.SSLv23_METHOD) and then turn off unneeded versions via
        # set_options

        filterVersions = False
        sslProtocol = None

        if sslVersions == SSLVERSION_SSL3:
            sslProtocol = ssl.PROTOCOL_SSLv3
        elif sslVersions == SSLVERSION_TLS1_0:
            sslProtocol = ssl.PROTOCOL_TLSv1
        elif sslVersions == SSLVERSION_TLS1_1:
            sslProtocol = ssl.PROTOCOL_TLSv1_1
        elif sslVersions == SSLVERSION_TLS1_2:
            sslProtocol = ssl.PROTOCOL_TLSv1_2
        else:
            sslProtocol = ssl.PROTOCOL_SSLv23
            filterVersions = True

        ctx = ssl.SSLContext(sslProtocol)

        if ctx == None:
            raise Exception("SSL Context creation failed.")

        # if SSLv23_METHOD used, eliminate SSL versions that the user explicitly
        # disallowed.
        table = [
            [SSLVERSION_SSL3, ssl.OP_NO_SSLv3],
            [SSLVERSION_TLS1_0, ssl.OP_NO_TLSv1],
            [SSLVERSION_TLS1_1, ssl.OP_NO_TLSv1_1],
            [SSLVERSION_TLS1_2, ssl.OP_NO_TLSv1_2]
        ]

        set_ops = ssl.OP_NO_SSLv2 # should be off by default, but just in case
        if filterVersions:
            for entry in table:
                if (sslVersions & entry[0]) == 0:  # SSL version is not present
                    set_ops = set_ops | entry[1]

        # set the options to eliminate SSL versions
        if set_ops != 0:
            ctx.options |= set_ops

        verifyOptions = ssl.CERT_NONE
        verifyCallback = None

        # Decide on flags for peer-validation
        if validatePeerCert != VALIDATE_NONE:
            if isClientContext and (
                    (validatePeerCert & VALIDATE_SERVER) != VALIDATE_NONE):
                verifyOptions = ssl.CERT_REQUIRED
            elif not isClientContext and (
                    (validatePeerCert & VALIDATE_CLIENT) != VALIDATE_NONE):
                verifyOptions = ssl.CERT_REQUIRED
            verifyCallback = self.verifyCallback

        ctx.verify_mode = verifyOptions
        if verifyCallback and ctx.verify_mode != ssl.CERT_NONE:
            # Set verification callback here
            ctx.set_verify_callback(verifyCallback)

        # Specify the location of the root CA
        if rootCAPath != None:
            ctx.load_verify_locations(os.path.expandvars(rootCAPath))  # make more generic.

        if self.isCCMode():
            ctx.verify_flags = ssl.VERIFY_CRL_CHECK_CHAIN
            # Iterate over PEM files in the CRL directory (hard-coded in galaxy)
            for filename in glob.glob(os.path.join(PATH_CRL_DIR, '*.pem')):
                ctx.load_verify_locations(filename)
                logger.debug('Adding CRL PEM file for CRL check [%s]' % filename)

        # Specify the cipher suite
        if cipherSuite:
            ctx.set_ciphers(cipherSuite)

        # NOTE: the context created does not load a cert-chain and has no
        # private key. If we have a use-case which requires
        # client-authentication, we need to add support here.

        return ctx

    def createSSLContextFromSettings(self, sslConfJSON=None,
                                     serverConfJSON=None,
                                     isClientContext=True):
        """
            Helper function to wrap two calls together. First retrieves the
            ssl specific conf file settings for a passed in conf file name
            and stanza. Second, calls createSSLContext with those conf file
            settings.

            Arguments:

                sslConfJSON (Dict) - the contents of the conf file stanza
                that contains the ssl settings. Can use entity.getEntity()
                to obtain this dict.

                serverConfJSON (Dict) - the contents of the server.conf
                sslConfig stanza. Can use SSLHelper.getServerSettings() to
                obtain this dict.

                isClientContext (boolean) - set to true if the calling code
                is the client of the connection. Set to false if it is the
                server.

        """
        if sslConfJSON == None or not sslConfJSON:
            return self.createSSLContext(isClientContext=isClientContext)

        sslSettings = self.getSSLConfSettings(sslConfJSON, serverConfJSON, isClientContext)

        return self.createSSLContext(sslVersions=sslSettings['sslVersions'],
                                     commonNameList=sslSettings[
                                         'sslCommonNameToCheck'],
                                     altNameList=sslSettings[
                                         'sslAltNameToCheck'],
                                     cipherSuite=sslSettings['cipherSuite'],
                                     validatePeerCert=sslSettings[
                                         'validatePeerCert'],
                                     rootCAPath=sslSettings['rootCAPath'],
                                     isClientContext=isClientContext)

    def getSSLConfSettings(self, sslConfJSON, serverConfJSON, isClientContext=True):
        """
            Retrieve SSL specific conf file settings from a given conf file and
            return an object containing those settings
        """

        settings = {}

        # bitmap of SSL versions
        if isClientContext:
            sslVersions = sslConfJSON.get('sslVersionsForClient')
            if not sslVersions:
                sslVersions = sslConfJSON.get('sslVersions')
        else:
            sslVersions = sslConfJSON.get('sslVersions')

        settings['sslVersions'] = self.parseSSLVersions(sslVersions)
        settings['sslCommonNameToCheck'] = sslConfJSON.get('sslCommonNameToCheck')
        settings['sslAltNameToCheck'] = sslConfJSON.get('sslAltNameToCheck')
        settings['cipherSuite'] = sslConfJSON.get('cipherSuite')

        validatePeerCert = VALIDATE_NONE
        verifyServerBool = sslConfJSON.get('sslVerifyServerCert')
        if verifyServerBool != None \
                and util.normalizeBoolean(verifyServerBool):
            validatePeerCert = validatePeerCert | VALIDATE_SERVER
        settings['validatePeerCert'] = validatePeerCert

        # We fetch sslRootCAPath from server.conf
        if serverConfJSON:
            settings['rootCAPath'] = serverConfJSON.get('sslRootCAPath')

        logger.debug("SSLHelper.getSSLConfSettings settings=%s" % (settings))

        return settings


    def getServerSettings(self, sessionKey):
        '''
            Gets the settings in the sslConfig stanza in server.conf
        '''
        settings = None
        try:
            settings = entity.getEntity('/configs/conf-server',
                                        'sslConfig',
                                        sessionKey=sessionKey)

            logger.debug('SSLHelper.getServerSettings %s' % settings)
        except Exception as e:
            logger.error("SSLHelper.getServerSettings Could not access or "
                         "parse sslConfig stanza of server.conf. Error=%s"
                         % str(e))

        return settings
