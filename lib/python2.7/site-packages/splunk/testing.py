from __future__ import absolute_import
from __future__ import print_function
from builtins import object

import os, re, time, sys, glob, shutil
import unittest, httplib2, cgi

from future.moves.urllib import parse as urllib_parse

import lxml.etree
import logging as logger
import splunk.rest.format

import base64

# Define the level of unit test logging
# 0 - sparse
# 1 - test names
# 2 - test name with subtasks
# 3 - everything
LOG_LEVEL = 3

# define max number of characters to show when asserts fail
TRUNCATE_LENGTH = 500

# number of times to retry an HTTP request, at a delay interval
# used for <status retryUntilTrue="true">
HTTP_RETRY_COUNT = 10
HTTP_RETRY_DELAY = .5

splunkhome = os.getenv("SPLUNK_HOME")

def time_str():
    return time.strftime('%m/%d/%Y %H:%M:%S', time.localtime())

def runLocalRestTests():
    '''
    Looks in the current directory and attempts to load and execute REST tests
    that are contained in *.xml files.  See the spec at:
        //splunk/current/python-site/splunk/simpleRestTester.xml.spec
    '''
    s = SimpleRestTester()
    if sys.argv:
        isPassed = s.run(*sys.argv[1:])
    else:
        isPassed = s.run()
    if isPassed: sys.exit(0)
    else: sys.exit(-1)


class TestSkipped(Exception):
    '''
    This class is used to exit a test without affecting the pass or fail count
    '''
    pass

class SimpleRestTester(object):
    '''
    Provides simple REST endpoint unit testing.

    See the test XML spec file in:
        //splunk/current/python-site/splunk/simpleRestTester.xml.spec

    >>> s = SimpleRestTester()
    >>> s.saveVariable('jv', 'johnvey')
    >>> s.saveVariable('jv2', 'nothing')
    >>> s.replaceVariables('this is a string replace')
    'this is a string replace'
    >>> s.replaceVariables('this is a string ${jv} to ${jv} replace')
    'this is a string johnvey to johnvey replace'
    >>> s.replaceVariables('this is a string ${jv} to ${jv2} replace')
    'this is a string johnvey to nothing replace'
    >>> s.replaceVariables('this is a string ${jv} to ${asdfasdf} replace')
    'this is a string johnvey to ${asdfasdf} replace'
    >>> s.replaceVariables('this is a string ${234123} to ${asdfasdf} replace')
    'this is a string ${234123} to ${asdfasdf} replace'
    >>> s.assertEqual('1234', '1234', 'this is equal')
    True
    >>> s.assertEqual('1234', '12345')
    Traceback (most recent call last):
    Exception: assertEqual failed:
        ACTUAL:   1234
        EXPECTED: 12345
    >>> s.assertEqual(False, True)
    Traceback (most recent call last):
    Exception: assertEqual failed:
        ACTUAL:   False
        EXPECTED: True
    '''

    variables = {}
    bkup_dict = {}
    backedup = False
    restored = False

    username = None
    password = None
    hostport = None
    testCount = 0

    def __init__(self):
        self.init_bkup_ds()

    def init_bkup_ds(self):
        self.bkup_dict['dirs'] = []
        self.bkup_dict['files'] = []
        self.bkup_dict['extra'] = []
        self.backedup = False
        self.restored = False

    def run(self, *filelist):

        if filelist:
            files = filelist
        else:
            files = sorted([x for x in os.listdir('.') if x.endswith('.xml')])

        self.log(0, '')
        self.log(0, 'Starting REST test suite')
        t1 = time.time()

        fileCount = len(files)
        passCount = failCount = 0
        for filePath in files:
            self.init_bkup_ds()
            res = self.executeTest(filePath)
            if res:
                passCount = passCount + 1
            else:
                failCount = failCount + 1

        self.log(0, '')
        self.log(0, '-' * 76)
        self.log(0, 'suite time: %.3f sec; %s file(s): %s pass; %s fail' % (time.time() - t1, fileCount, passCount, failCount))
        if fileCount == passCount:
            self.log(0, 'OK')
            return True
        else:
            self.log(0, 'FAIL')
            return False

    def fail(self, msg=None):
        raise Exception(msg)

    def assertTrue(self, test, msg=None):
        if not test:
            if msg:
                raise Exception('assertTrue failed: %s' % msg)
            else:
                raise Exception('assertTrue failed')
        return True

    def assertEqual(self, a, b, msg=None):
        if a != b:
            if isinstance(a, type('')) and len(a) > TRUNCATE_LENGTH: a = a[:TRUNCATE_LENGTH] + '...'
            if isinstance(b, type('')) and len(b) > TRUNCATE_LENGTH: b = b[:TRUNCATE_LENGTH] + '...'
            raise Exception('assertEqual failed: %s' % (msg or '\n    ACTUAL:   %s\n    EXPECTED: %s' % (a, b)))
        return True

    def replaceVariables(self, string):
        if not string: return string

        try:
            #self.log(1, 'replacing on string=%s' % string)
            reg = re.compile(r'\$\{([^\}]+)\}')
            i = 0
            while i < len(string):
                #self.log(1, '-> replacing on string=%s' % string)
                match = reg.search(string, i)
                if match:
                    #self.log(1, 'found match start=%s end=%s group=%s' % (match.start(1), match.end(1), match.group(1)))
                    varName = match.group(1)
                    if varName in self.variables or varName == 'SPLUNK_HOME' or varName == 'URL_ENCODED_SPLUNK_HOME':
                        #self.log(1, 'about to replace with %s' % self.variables[varName])
                        replacement = ""
                        global splunkhome
                        if varName in self.variables:
                            replacement = self.variables[varName]
                        elif varName == 'URL_ENCODED_SPLUNK_HOME':
                            # Pass safe='' to force '/' -> '%2F'.
                            replacement = urllib_parse.quote(splunkhome, safe='')
                        else:
                            # gotta escape backslashes in windows since they would be turned into special chars
                            replacement = splunkhome.replace("\\", "\\\\")
                        varNameLen = len(varName)
                        stringOrigLen = len(string)  # string len before replacement
                        string = reg.sub(replacement, string, 1)
                        # Start over from beginning of replacement, in case
                        # the replacement itself contains text-to-replace.
                        i = match.start(1) - 2
                    else:
                        i = match.end(1)
                else:
                    break
        except Exception as e:
            logger.debug('Error trying to replaceVariables: %s' % e)

        return string

    def saveVariable(self, key, value):
        #self.log(1, 'saveVariable - %s=%s' % (key, value))
        self.variables[key] = value

    def getVariable(self, key):
        #print('getVariable - key=%s' % key)
        if key in self.variables:
            return self.variables[key]
        else:
            return None

    def log(self, level, msg):
        if level <= LOG_LEVEL:
            sys.stderr.write('%s\n' % msg)

    def executeTest(self, filepath):
      try:
        t1 = time.time()

        # read in test script
        script = lxml.etree.parse(filepath)
        root = script.getroot()

        self.log(1, '')
        self.log(1, '=' * 76)
        if root.findtext('desc'):
            self.log(1, self.replaceVariables(root.findtext('desc')))
            self.log(1, os.sep.join(os.path.abspath(filepath).split(os.sep)[-3:]))
        else:
            self.log(1, 'Parsing XML test "%s"' % filepath)
        self.log(1, '-' * 76)

        # get host info
        hostname = root.findtext('hostname')
        port = root.findtext('port')
        self.hostport = 'https://%s:%s' % (hostname, port)

        # if not in XML, then get host info from server
        if not hostname or not port:
            self.hostport = splunk.getLocalServerInfo()

        self.log(2, 'Connecting to %s' % (self.hostport))

        # look for HTTP digest auth info
        self.username = self.password = None
        authInfo = root.find('auth')
        if authInfo is not None:
            self.username = self.replaceVariables(authInfo.findtext('username'))
            self.password = self.replaceVariables(authInfo.findtext('password'))
            self.log(2, 'Using credentials: %s/%s' % (self.username, self.password))

        backup_restore_node = root.find('backup_restore')
        if backup_restore_node:
           self.backup(backup_restore_node)

        logBuffer = []
        self.testCount = len(root.xpath('//test'))
        passCount = failCount = 0
        for test in root.xpath('//test|//comment|//code'):
            try:
                retry_count = 1
                retry_sleep = 0


                tmp = test.findtext('retry')
                if tmp != None and len(tmp) != 0:
                     retry_count = int(tmp)

                tmp = test.findtext('retry_sleep')
                if tmp != None and len(tmp) != 0:
                     retry_sleep = float(tmp)

                if retry_count > 1:
                    self.log(2, 'retry_count=%d, retry_sleep=%d' % (retry_count, retry_sleep))

                while retry_count > 0:
                    retry_count -= 1
                    if self.execute_test_case(test):
                        passCount += 1
                        break

                    if retry_count > 0:
                       self.log(1, 'retrying in %.3f seconds' % (retry_sleep))
                       time.sleep(retry_sleep)
                    else:
                       failCount += 1
            except TestSkipped as e:
                continue
        self.restore()
        delta = time.time() - t1
        self.log(1, '')
        self.log(1, 'time: %.3f sec; %s test(s): %s pass; %s fail' % (delta, self.testCount, passCount, failCount))
        if self.testCount == passCount:
            return True
        else:
            return False
      finally:
        if self.backedup and not self.restored:
           self.restore()

    def create_test_generator(self, filepath):
        '''
        Takes in a file path, forms an XML object from the content, and gets test suite information
        defined in the file

        Uses yield so the return value can be iterable
        '''
        script = lxml.etree.parse(filepath)
        root = script.getroot()

        # get host info
        hostname = root.findtext('hostname')
        port = root.findtext('port')
        self.hostport = 'https://%s:%s' % (hostname, port)

        if not hostname or not port:
            self.hostport = splunk.getLocalServerInfo()

        authInfo = root.find('auth')
        if authInfo is not None:
            self.username = self.replaceVariables(authInfo.findtext('username'))
            self.password = self.replaceVariables(authInfo.findtext('password'))

        self.testCount = len(root.xpath('//test'))
        for test in root.xpath('//test|//comment|//code'):
            yield test

    def execute_test_case(self, test):
        '''
        Takes in the "test" xml element (etree Element object) and get information to form the REST
        request and also to get information on how to verify the response

        Returns: bool
        '''
        if test.tag == 'comment':
            self.log(2, '%s - # %s' % (time_str(), self.replaceVariables(test.text)))
            raise TestSkipped("Test skipped")

        if test.tag == 'code':
            code = self.replaceVariables(test.text)
            result = eval(code)
            self.log(2, '%s - eval(%s) -> %s' % (time_str(), code, result))
            raise TestSkipped("Test skipped")

        # handle artificial test pauses
        pauseInterval = test.findtext('pause')
        if pauseInterval:
            self.log(2, '- Pausing for %ss -' % pauseInterval)
            self.testCount = self.testCount - 1
            time.sleep(float(pauseInterval))
            raise TestSkipped("Test skipped")

        logBuffer = [(2, '%s - %s' % (time_str(), self.replaceVariables(test.findtext('desc'))))]

        # look for HTTP digest auth info for this specific test case
        tmpUsername = tmpPassword = None
        tmpAuthInfo = test.find('auth')
        if tmpAuthInfo is not None:
            tmpUsername = self.replaceVariables(tmpAuthInfo.findtext('username'))
            tmpPassword = self.replaceVariables(tmpAuthInfo.findtext('password'))

        # define request
        requestParams = test.find('request')

        tmpHostport = self.hostport
        if test.find('use_splunkweb_uri_instead_of_splunkd_uri') is not None:
            tmpHostport = splunk.getWebServerInfo()

        method = requestParams.findtext('method')
        path = self.replaceVariables(requestParams.findtext('path'))
        uri = '%s%s' % (tmpHostport, path)

        querystring = []
        for arg in requestParams.findall('query/arg'):
            querystring.append((arg.get('name'), self.replaceVariables(arg.text)))
            if arg.get('save'):
                self.saveVariable(arg.get('save'), self.replaceVariables(arg.text))
        if len(querystring) > 0:
            logger.debug(querystring)

        headers = {}
        for header in requestParams.findall('headers/header'):
            headers[header.get('name')] = self.replaceVariables(header.text)
            if header.get('save'):
                self.saveVariable(header.get('save'), self.replaceVariables(header.text))

        payload = requestParams.findtext('payload')
        orig_payload = payload
        is_base64 = False
        formList = []
        if not payload:
            for arg in requestParams.findall('form/arg'):
                t = self.replaceVariables(arg.text)
                if t is None:
                    t = ''
                formList.append((self.replaceVariables(arg.get('name')), t))
                if arg.get('save'):
                    self.saveVariable(arg.get('save'), self.replaceVariables(arg.text))
            payload = urllib_parse.urlencode(formList)
            if len(formList) > 0:
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
                logger.debug(formList)
                logger.debug(payload)
        else:
            payloadParams = requestParams.find('payload')
            if payloadParams is not None:
                encodingParams = payloadParams.get('encoding')
                if encodingParams is not None and encodingParams == 'base64':
                    is_base64 = True
                    payload = base64.standard_b64decode(payload)

        # define expected response
        responseParams = test.find('response')

        # get expected status; if waitForStatus, tester will retry request
        # for X seconds until true
        waitForStatus = False
        statusNode = responseParams.find('status')
        statusCode = None

        if statusNode is not None:
            statusCode = self.replaceVariables(statusNode.text)
            if statusNode.get('retryUntilTrue') and statusNode.get('retryUntilTrue').lower() == 'true':
                waitForStatus = True
                retriesRemaining = int(statusNode.text)

        responseParamHeaders = {}
        responseParamHeadersSave = {}
        for header in responseParams.findall('headers/header'):
            responseParamHeaders[header.get('name').lower()] = header.text
            if header.get('save'):
                responseParamHeadersSave[header.get('name').lower()] = header.get('save')

        serverContent = None
        try:
            # make call
            h = httplib2.Http(disable_ssl_certificate_validation = True, proxy_info=None)
            h.follow_redirects = False

            if tmpUsername:
                # use testcase-specific credentials
                h.add_credentials(tmpUsername, tmpPassword)
                logBuffer.append((3, 'Auth: %s/%s' % (tmpUsername, tmpPassword)))
            elif self.username:
                # else: use suite-wide credentials
                h.add_credentials(self.username, self.password)

            if querystring:
                uri += '?' + urllib_parse.urlencode(querystring)

            logBuffer.append((3, 'URI: %s %s' % (method, uri)))
            logger.debug('URI: %s %s' % (method, uri))
            if payload:
                if is_base64:
                    logBuffer.append((3, 'Payload (base64 encoded):\n\t%s' % orig_payload))
                else:
                    payloadOutput = cgi.parse_qsl(payload)
                    logBuffer.append((3, 'Payload:\n\t%s' % '\n\t'.join(['%s: %s' % (x[0], x[1]) for x in payloadOutput])))

            # retry request if test specifies that we should wait until the
            # HTTP status is what we want; poll interval is .5 seconds
            retryRequest = True
            if not waitForStatus:
               #if we don't wish to wait, assign the default value
               retriesRemaining = HTTP_RETRY_COUNT
            retryNotified = False
            while retryRequest:
                serverResponse, serverContent = h.request(uri, method, headers=headers, body=payload)

                # normalize header case
                serverResponse = dict([(x.lower(), serverResponse[x]) for x in serverResponse])

                if not statusCode:
                    retryRequest = False
                elif serverResponse['status'] == statusCode:
                    retryRequest = False
                elif not retriesRemaining:
                    retryRequest = False
                elif waitForStatus:
                    #print('waiting for statusCode...got %s' % serverResponse['status'])

                    #not sure why this is here, commenting out - JJ
                    #if not retryNotified:

                    logBuffer.append((3, 'waiting for statusCode (%s sec)' % ((retriesRemaining) * HTTP_RETRY_DELAY)))
                    #if running from the command line also, show the message
                    self.log(2, 'waiting for statusCode for (%s sec)' % ((retriesRemaining) * HTTP_RETRY_DELAY))
                    #retryNotified = True
                    retriesRemaining = retriesRemaining - 1
                    time.sleep(HTTP_RETRY_DELAY)
                    continue
                else:
                    retryRequest = False

            # assert http status
            logBuffer.append((3, 'checking statusCode'))
            if statusCode:
                self.assertEqual(serverResponse['status'], statusCode)

            serverContent = serverContent.strip()

#            if False:
#                logger.debug('=' * 80)
#                logger.debug(uri)
#                logger.debug('-' * 80)
#                logger.debug(serverContent)
#                logger.debug('=' * 80)

            # assert headers
            for header in responseParamHeaders:
                logBuffer.append((3, 'checking header=%s' % header))
                self.assertTrue(header in serverResponse, 'header not found')
                if responseParamHeaders[header]:
                    self.assertEqual(serverResponse[header], responseParamHeaders[header])
                if header in responseParamHeadersSave:
                    self.saveVariable(responseParamHeadersSave[header], serverResponse[header])

            # assert plain text content
            bodyNode = responseParams.find('body')
            if bodyNode:
                bodyText = bodyNode.text
                if bodyText:
                    logBuffer.append((3, 'checking body'))
                    self.assertEqual(serverContent, self.replaceVariables(bodyText))
                if bodyNode.get('save'):
                    self.saveVariable(bodyNode.get('save'), bodyText)

            # assert plain text substring content
            substringTest = self.replaceVariables(responseParams.findtext('substring'))
            if substringTest:
                logBuffer.append((3, 'checking body for text=%s' % substringTest))
                self.assertTrue(serverContent.find(substringTest) > -1, 'string not found')

            # assert plain text substring content
            regexTests = self.replaceVariables(responseParams.findall('regex/pattern'))
            if regexTests:
                for test in regexTests:
                    logBuffer.append((3, 'checking body for regex=%s' % test.text))
                    pattern = re.compile(test.text)
                    self.assertTrue(pattern.search(serverContent), 'regex pattern not found')

            # assert XML stuff
            xmlTests = responseParams.findall('xml/xpath')
            if xmlTests:

                try:
                    doc = lxml.etree.fromstring(serverContent)
                except lxml.etree.XMLSyntaxError as e:
                    self.fail('Test requires XML response; received unparsable XML:\n%s' % serverContent)

                baseNS = None
                if None in doc.nsmap:
                    baseNS = doc.nsmap[None]
                xpathNS = {}
                if baseNS == splunk.rest.format.ATOM_NS:
                    xpathNS['atom'] = splunk.rest.format.ATOM_NS
                    xpathNS['opensearch'] = splunk.rest.format.OPENSEARCH_NS
                    xpathNS['s'] = splunk.rest.format.SPLUNK_NS

                for axis in responseParams.findall('xml/xpath'):
                    logBuffer.append((3, 'checking xpath=%s' % axis.get('selector')))
                    matchedNodes = doc.xpath(axis.get('selector'), namespaces = xpathNS)
                    if isinstance(matchedNodes, bool):
                        self.assertTrue(matchedNodes, 'xpath boolean expression failed')
                    else:
                        if axis.get('length'):
                           self.assertTrue(len(matchedNodes) == int(axis.get('length')), 'selected nodes length criteria not met: %s != %s' % (str(len(matchedNodes)), str(axis.get('length'))))
                        else:
                           self.assertTrue(len(matchedNodes) > 0, 'selected node not found %s' % str(axis.get('selector')))
                        if axis.get('save'):
                            self.saveVariable(axis.get('save'), matchedNodes[0].text)
                        if axis.text :
                            self.assertEqual(matchedNodes[0].text, self.replaceVariables(axis.text))
        except Exception as e:
            self.log(0, logBuffer[0][1] + '...FAIL')
            logBuffer.pop(0)
            for msg in logBuffer:
                self.log(msg[0], '    %s' % msg[1])
                logger.debug(msg[0], '    %s' % msg[1])
            self.log(0, '    ==> %s' % e)
            logger.debug('    ==> %s' % e)
            if serverContent:
                self.log(0, '-' * 76)
                logger.debug(('-' * 46) + " first 5000 characters of response content:")
                if len(serverContent) > 5000:
                    self.log(0, serverContent[:5000])
                    logger.debug(serverContent[:5000])
                else:
                    self.log(0, serverContent)
                    logger.debug(serverContent)
                self.log(0, '-' * 76)
            return False

        self.log(logBuffer[0][0], logBuffer[0][1] + '...OK')
        return True

    def make_win_compatable(self, data):
       if os.name == 'nt':
          data = '\\'.join(data.split('/'))
       return data


    # ---------------------------
    def backup(self, bkup_node):
        """
        determines if we have to backup an entire dir or individual files within that dir
        it then calls the perform_backup function to do the actual work
        """
        global splunkhome
        for dir in bkup_node.findall('dir'):

           dir_name = dir.get('name')

           if dir_name and dir_name.find('{\$SPLUNK_HOME}') and not splunkhome:
              raise Exception("Splunk home must be set.")

           if dir_name:
              dir_name = self.make_win_compatable(dir_name)

              #individual files to backup within this dir
              file_list = []
              for file in dir.findall('file'):
                 file_list.append(self.make_win_compatable(file.text))
              self.perform_backup(dir_name, file_list)
           else:
              if dir.text and dir.text.find('{\$SPLUNK_HOME}') and not splunkhome:
                 raise Exception("Splunk home must be set.")
              #backup the entire dir
              self.perform_backup(self.make_win_compatable(dir.text))

    # --------------------------------------------
    def perform_backup(self, dir, file_list=[]):
        """
        move the entire dir or specified files within the dir to a backup dir
        """

        dir = re.sub('{\$SPLUNK_HOME}', splunkhome, dir)
        bkup_dir = os.path.join(os.path.dirname(dir), "backup_%s" % os.path.split(dir)[1])
        if not os.path.isdir(dir):
           print('Warning: dir %s does not exists. Possibly incorrect config file, hence ignoring it' % dir)
        elif os.path.isdir(bkup_dir):
             print("Warning: Backup dir %s already exists.  Not backing up." % bkup_dir)
        else:
           #global bkup_dict

           os.makedirs(bkup_dir)
           print('Created dir %s' % bkup_dir)

           if not file_list:
              self.bkup_dict['dirs'].append((bkup_dir, dir))
              print('expanded dir: %s' % dir)
              for f in glob.glob(os.path.join(dir, "*")):
                 shutil.move(f, bkup_dir)
                 print('Moved file %s to %s' % (f, bkup_dir))
           else:
              print('in dir %s backing up files %s' % (dir, str(file_list)))
              for f in file_list:
                 if not os.path.isfile(os.path.join(dir, f)):
                    print('Warning: file %s does not exist. Check config file.' % os.path.join(dir, f))
                    continue
                 #if the included file contains a path to a subdir, create the subdirs in the backup dir as well
                 if os.path.split(f)[0]:
                    new_dir = os.path.split(os.path.join(bkup_dir, f))[0]
                    print('Creating dir %s ' % new_dir)
                    os.makedirs(new_dir)
                    shutil.move(os.path.join(dir, f), new_dir)
                 else:
                    shutil.move(os.path.join(dir, f), bkup_dir)

                 self.bkup_dict['files'].append((os.path.join(bkup_dir, f), os.path.join(dir, f)))

           self.bkup_dict['extra'].append(bkup_dir)
           self.backedup = True

    # -----------------
    def restore(self):
        """
        """
        for t in self.bkup_dict['dirs']:
           print('restoring %s to %s' % (t[0], t[1]))
           shutil.rmtree(t[1])
           shutil.copytree(t[0], t[1])
        for t in self.bkup_dict['files']:
           print('restoring %s to %s' % (t[0], t[1]))
           shutil.copy(t[0], t[1])
        for dir in self.bkup_dict['extra']:
           shutil.rmtree(dir)
        self.restored = True

# --------------------------
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    s = SimpleRestTester()
    if sys.argv:
        isPassed = s.run(*sys.argv[1:])
    else:
        isPassed = s.run()

    if isPassed: sys.exit(0)
    else: sys.exit(-1)
