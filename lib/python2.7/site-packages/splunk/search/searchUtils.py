import lxml.etree as et

import splunk
import splunk.rest as rest
import splunk.entity as entity

def getFormattedTimeForUser(sessionKey, now=None, timeFormat=None):
    getargs = {'time': 'now',
               'time_format': timeFormat if timeFormat else '%F %T'}

    if now:
        getargs['now'] = now

    serverStatus, serverResp = rest.simpleRequest('/search/timeparser', getargs=getargs, sessionKey=sessionKey)

    root = et.fromstring(serverResp)

    if root.find('messages/msg'):
        raise splunk.SplunkdException(root.findtext('messages/msg'))

    return root.xpath("//dict/key[@name='now']/text()")[0]

if __name__ == '__main__':
    import unittest
    import uuid
    import datetime
    import splunk.auth as auth
    import splunk.entity as entity

    def createTestUser(tz, sessionKey):
        uri = entity.buildEndpoint('authentication', 'users')
        userName = str(uuid.uuid1())
        postargs = {
            "name": userName,
            "password": "changeme",
            "roles": "user",
            "tz": tz
            }
        (response, content) = rest.simpleRequest(uri, postargs=postargs, sessionKey=sessionKey)        
        return userName

    def deleteTestUser(userName, sessionKey):
        uri = entity.buildEndpoint(['authentication', 'users'], userName)
        (response, content) = rest.simpleRequest(uri, sessionKey=sessionKey, method="DELETE")        

    class GetTimeTest(unittest.TestCase):
        
        def setUp(self):
            self.adminSessionKey = auth.getSessionKey("admin", "changeme")
            self.userName = createTestUser(tz="Chile/EasterIsland", sessionKey=self.adminSessionKey)
            self.sessionKey = auth.getSessionKey(self.userName, "changeme")
 
        def tearDown(self):
            deleteTestUser(self.userName, sessionKey=self.adminSessionKey)

        def testChileEasterIsland(self):
            val = getFormattedTimeForUser(self.sessionKey, now=1342123200, timeFormat="%F %T %Z")
            self.assertEquals(val, u'2012-07-12 14:00:00 EAST')

    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(GetTimeTest))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
