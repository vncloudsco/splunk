#
# Sample testing REST handler class, for use with the selftest module in this
# directory
#

import sys
import lxml.etree as etree
import unittest
import xml.sax.saxutils as su
import splunk.rest
import splunk.rest.format as srf



# /////////////////////////////////////////////////////////////////////////////
#  data definitions that are to be used in the REST/HTTP <-> python wrappers     
# /////////////////////////////////////////////////////////////////////////////

# define primitive types to test
testData = {
    'dict': {'k1':'v1', 'k2':'v2', 'k3':'<tagname />', 'k4':'something & else', 'k5': None},
    'list': ['L1', 'L2', '<tagname />', 'something & else', None],
    'dictList': {'kl1': ['kl11', 'kl12', 'kl13'], 'k2':'v2', 'k3':'v3'},
    'listDict': [{'ld1':'v1','ld2':'v2','ld3':'v3'}, 'L2', 'L3']
}

# define atom feeds that correspond to the testData
testFeeds = {
    'list': '''%s
        <feed xmlns="%s" xmlns:s="%s">
            <title>THE_TITLE</title>
            <id>THE_ID</id>
            <link href="/THE_LINK" />
            <updated>UPDATED_NOW</updated>
            <entry>
                <title>ENTRY1</title>
                <id>ENTRYID1</id>
                <content type="text/xml">
                    <s:list>
                        <s:item>L1</s:item>
                        <s:item>L2</s:item>
                        <s:item>&lt;tagname /&gt;</s:item>
                        <s:item>something &amp; else</s:item>
                        <s:item></s:item>
                    </s:list>
                </content>
            </entry>
        </feed>''' % (srf.XML_MANIFEST, srf.ATOM_NS, srf.SPLUNK_NS)
    ,
    'dict': '''%s
        <feed xmlns="%s" xmlns:s="%s">
            <title>THE_TITLE</title>
            <id>THE_ID</id>
            <link href="/THE_LINK" />
            <updated>UPDATED_NOW</updated>
            <entry>
                <title>ENTRY1</title>
                <id>ENTRYID1</id>
                <content type="text/xml">
                    <s:dict>
                        <s:key name="k1">v1</s:key>
                        <s:key name="k2">v2</s:key>
                        <s:key name="k3">&lt;tagname /&gt;</s:key>
                        <s:key name="k4">something &amp; else</s:key>
                        <s:key name="k5"></s:key>
                    </s:dict>
                </content>
            </entry>
        </feed>''' % (srf.XML_MANIFEST, srf.ATOM_NS, srf.SPLUNK_NS)
    ,
    'dictList': '''%s
        <feed xmlns="%s" xmlns:s="%s">
            <title>THE_TITLE</title>
            <id>THE_ID</id>
            <link href="/THE_LINK" />
            <updated>UPDATED_NOW</updated>
            <entry>
                <title>k1</title>
                <id>ENTRYID1</id>
                <content type="text/">
                    <s:dict>
                        <s:key name="k1">v1</s:key>
                        <s:key name="k2">v2</s:key>
                        <s:key name="k3">v3</s:key>
                        <s:key name="k4">v4</s:key>
                    </s:dict>
                </content>
            </entry>
        </feed>''' % (srf.XML_MANIFEST, srf.ATOM_NS, srf.SPLUNK_NS)
}

if sys.version_info >= (3, 0):
    for feedName in testFeeds:
        testFeeds[feedName] = testFeeds[feedName].encode()

# /////////////////////////////////////////////////////////////////////////////
#  format.py tests
# /////////////////////////////////////////////////////////////////////////////

class TestPrimitives(unittest.TestCase):

    def testDictNodeToPrimitive(self):

        # generate the XML
        root = etree.Element('{%s}dict' % srf.SPLUNK_NS)
        for k, v in testData['dict'].items():
            el = etree.SubElement(root, '{%s}key' % srf.SPLUNK_NS)
            el.set('name', k)
            el.text = v

        converted = srf.nodeToPrimitive(root)

        self.assertEqual(converted, testData['dict'])

    def testListNodeToPrimitive(self):

        # generate the XML
        root = etree.Element('{%s}list' % srf.SPLUNK_NS)
        for i in testData['list']:
            el = etree.SubElement(root, '{%s}item' % srf.SPLUNK_NS)
            el.text = i

        converted = srf.nodeToPrimitive(root)

        self.assertEqual(converted, testData['list'])


class TestParser(unittest.TestCase):

    def testFeedListUnescaped(self):
        parsed = srf.parseFeedDocument(testFeeds['list'])
        self.assertEqual(parsed.toPrimitive()['ENTRY1'], testData['list'])

    def testFeedListEscaped(self):
        parsed = srf.parseFeedDocument(srf.escapeContents(testFeeds['list']), True)
        self.assertEqual(parsed.toPrimitive()['ENTRY1'], testData['list'])

    def testFeedDict(self):
        parsed = srf.parseFeedDocument(testFeeds['dict'])
        self.assertEqual(parsed.toPrimitive()['ENTRY1'], testData['dict'])




if __name__ == '__main__':
    
    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(TestPrimitives))
    suites.append(loader.loadTestsFromTestCase(TestParser))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    
