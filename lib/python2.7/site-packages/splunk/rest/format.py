# /////////////////////////////////////////////////////////////////////////////
#  Syndication Formats
# /////////////////////////////////////////////////////////////////////////////

from builtins import object
from builtins import map
import xml.sax.saxutils as su
import lxml.etree as etree
import logging
import time
import splunk
import splunk.util as util
import sys
from splunk.util import format_local_tzoffset

logger = logging.getLogger('splunk.rest.format')

XML_MANIFEST    = '<?xml version="1.0" encoding="UTF-8" ?>'
ATOM_NS         = 'http://www.w3.org/2005/Atom'
SPLUNK_NS       = 'http://dev.splunk.com/ns/rest'
OPENSEARCH_NS   = 'http://a9.com/-/spec/opensearch/1.1/'

# format strings to use with lxml for namespaced tags
ATOM_TAGF       = '{%s}%%s' % ATOM_NS
SPLUNK_TAGF     = '{%s}%%s' % SPLUNK_NS
OPENSEARCH_TAGF = '{%s}%%s' % OPENSEARCH_NS

# define node value constants
FEED_LAYOUT_PROPS = 'props'
FEED_LAYOUT_TABLE = 'table'

# helper functions to escape/unescape XML contents
# handling the fact that in Python 3 the XML escaping utils will error out if passed a bytes string
def unescapeContents(contents):
    if sys.version_info >= (3, 0) and isinstance(contents, (bytearray, bytes)):
        return su.unescape(contents.decode()).encode()
    return su.unescape(contents)

def escapeContents(contents):
    if sys.version_info >= (3, 0) and isinstance(contents, (bytearray, bytes)):
        return su.escape(contents.decode()).encode()
    return su.escape(contents)

def parseFeedDocument(inputContents, contentsAreEscaped=False):
    '''
    Parses input content from known XML format into specific feed class objects;
    unknown formats are passed on as string
    
    contentsAreEscaped - indicates if the entirety of inputContents
        is escaped XML, and not just the interior node values.  This
        is a special accomodation of the interface between the splunk
        HTTP environment and the python handler
    '''
    if contentsAreEscaped: inputContents = unescapeContents(inputContents)
    

    # parse XML
    try:
        safeparser = etree.XMLParser(resolve_entities=False, huge_tree=True)
        etree.set_default_parser(safeparser)
        rootNode = etree.fromstring(inputContents)
    except Exception as e:
        logger.debug('There was an error parsing the feed document. Error: %s' % e.args[0])
        logger.debug('parseFeedDocument inputContents = %s', inputContents) 

        if contentsAreEscaped:
            return escapeContents(inputContents)
        else:
            return inputContents

    # check document type
    try:
        baseNS = rootNode.nsmap[None]
    except KeyError:
        return inputContents
        
    if baseNS == ATOM_NS:
        if rootNode.tag == ATOM_TAGF % 'feed':
            output = toAtomFeed(rootNode)
        elif rootNode.tag == ATOM_TAGF % 'entry':
            output = toAtomEntry(rootNode)
        else:
            logger.warn("parseFeedDocument - Found Atom document, but no <feed> or <entry> node")

        ## comment out: we aren't going to reach all the way into the s:dict tag to fetch the dictionary
        ## just return an AtomFeed object and let anyone who needs the dictionary call the to.Primitive
        #try:
        #    output = output.toPrimitive()
        #except Exception as e:
        #    logger.debug('parseFeedDocument - unable to cast content to primitive')
        #    logger.exception(e) 
        return output
        
    else:
        logger.debug('parseFeedDocument - no parseable feed doc found')
    
    if contentsAreEscaped: return escapeContents(inputContents)
    else: return inputContents
    
def getAttributeFromXMLString(xmlString, attrib): 
    '''
    Takes an xml string and searches for the given attribute.  Returns the attribute's value if found or returns None if the attribute is not found.
    '''


    rootNode = etree.fromstring(xmlString)
    return searchForAttribute(rootNode, attrib)

def searchForAttribute(node, attrib):
    '''
    Recursive function.  Searches through a node and then its children until it finds the given attribute.
    '''
     
    nodeAttrib = node.attrib.get('name', '')


    # Found the attribute
    if nodeAttrib == attrib:
        return node.text

    children = node.getchildren()
    if len(children) == 0:
        return None 
    for e in children: 
        match = searchForAttribute(e, attrib)
        if match is not None: 
            return match

          
def toAtomFeed(lxmlNode):
    '''
    Converts an lxml node into an AtomFeed object
    '''

    root = lxmlNode
    output = AtomFeed()

    # extract props
    output.id = root.findtext(ATOM_TAGF % 'id')
    output.title = root.findtext(ATOM_TAGF % 'title')
    output.updated = util.parseISO(root.findtext(ATOM_TAGF % 'updated', ''))

    # extract OpenSearch props
    output.os_totalResults = root.findtext(OPENSEARCH_TAGF % 'totalResults')
    output.os_itemsPerPage = root.findtext(OPENSEARCH_TAGF % 'itemsPerPage')
    output.os_startIndex   = root.findtext(OPENSEARCH_TAGF % 'startIndex')

    # extract messages
    for msg in root.xpath('//s:msg', namespaces={'s': SPLUNK_NS}):
        output.messages.append({'type': msg.get('type', 'error').lower(), 'text': msg.text})
    
    # extract links
    try: 
        output.links = list(map((lambda link: (link.attrib['rel'], link.attrib['href'])), root.findall(ATOM_TAGF % 'link')))
    except KeyError:
        pass # SPL-21884
                        
    # iterate over entries
    output.entries = list(map(toAtomEntry, root.xpath('//a:entry', namespaces={'a': ATOM_NS})))

    return output
    
    
def toAtomEntry(lxmlNode):
    '''
    Converts an lxml node into an AtomEntry object
    '''
    
    root = lxmlNode

    #SPL-20024
    link_nodes = root.findall(ATOM_TAGF % 'link')
    link = []
    for ln in link_nodes:
       link.append((ln.attrib['rel'], ln.attrib['href']))

    # extract props
    params = {
        'id': root.findtext(ATOM_TAGF % 'id'),
        'title': root.findtext(ATOM_TAGF % 'title'),
        'published': util.parseISO(root.findtext(ATOM_TAGF % 'published', '')),
        'updated': util.parseISO(root.findtext(ATOM_TAGF % 'updated', '')),
        'summary': root.findtext(ATOM_TAGF % 'summary'),
        'author': root.findtext('/'.join([ATOM_TAGF % 'author', ATOM_TAGF % 'name'])),
        #SPL-20024
        'link': link,
    }

    output = AtomEntry(**params)

    contentNodes = root.xpath('a:content', namespaces={'a': ATOM_NS})
    
    if contentNodes:
        
        output.contentType = contentNodes[0].get('type')
        
        if output.contentType == 'text':
            output.rawcontents = contentNodes[0].text.strip()
        elif len(contentNodes[0]) > 0:
            #logger.debug('toAtomEntry - content is of type: %s' % contentNodes[0][0])
            output.rawcontents = contentNodes[0][0]
        elif contentNodes[0].text:
            #logger.debug('toAtomEntry - content is text')
            output.rawcontents = contentNodes[0].text.strip()
        else:
            raise Exception("No idea what content type is")

    return output
    
def strftime(t=None):
    '''
    Generates a strftime string for use in AtomFeed and AtomEntry objects.
    '''
    correct_tz_time = format_local_tzoffset(t)
    if t is None:
        return time.strftime('%Y-%m-%dT%H:%M:%S') + correct_tz_time
    else:
        return time.strftime('%Y-%m-%dT%H:%M:%S', t) + correct_tz_time
    

def getAtomStyleNodes():
    '''
    Returns stylesheet processing instruction nodes to include at the beginning of
    Atom feeds.
    '''
    output = [etree.Comment('500B block to defeat firefox formatting. %s' % ('. ' * 500))]
    output.append(etree.PI('xml-stylesheet', 'type="text/xml" href="/static/atom.xsl"'))

    return output

def nodeToString(node):
    '''
    Returns the etree node in the Python 2 or 3 default string class.
    '''
    return util.toDefaultStrings(etree.tostring(node))

def primitiveToAtomFeed(hostUri, basePath, objToConvert):
    '''
    Converts a python primitive object (list, dict, str) into an AtomFeed class
    
    @param hostUri - The absolute URI to prepend to all entries (not prepended to links)

    @param basePath - The base URI path from which to build the child
        elements
        
    @param objToConvert - The python primitive to cast into Atom entries
    
    '''
    
    # otherwise, methods that return dictionaries or lists or strings get their
    # contents auto-converted into individual entries
    feed = AtomFeed()
    feed.id = hostUri + basePath
    feed.title = basePath.split('/')[-1]
   
    # dictionaries get each converted into an atom entry
    if isinstance(objToConvert, dict) or isinstance(objToConvert, util.OrderedDict):
        for key in objToConvert:
            feed.addEntry(
                    id=hostUri + '%s/%s' % (basePath, key),
                    link='%s/%s' % (basePath, key),
                    title=key,
                    rawcontents=objToConvert[key])
                    
    # list elements are treated as table rows
    elif isinstance(objToConvert, list) and len(objToConvert) and isinstance(objToConvert[0], list):
        for item in objToConvert:
            feed.addEntry(
                    id=hostUri + '%s/%s' % (basePath, item[0]),
                    link='%s/%s' % (basePath, item[0]),
                    title=str(item[0]),
                    rawcontents=item)
            
    # everything else get converted into a single entry
    elif objToConvert:
        logger.debug('treating output as plain string')
        feed.addEntry(
                id=(basePath + '#contents'), 
                link=(basePath + '#contents'), 
                title='List', 
                rawcontents=objToConvert)
                        
    return feed
    
    
    
# /////////////////////////////////////////////////////////////////////////////
#  Atom syndication format helper classes
#  See the RFC: http://atompub.org/rfc4287.html
# /////////////////////////////////////////////////////////////////////////////

class AtomFeed(object):
    '''Represents the top level Atom collection'''
    
    def __init__(self):
        self.id = 'ID'
        self.title = 'TITLE'
        self.updated = strftime()
        self.author = 'Splunk'
        self.entries = []
        self.isEditable = False
        self.isMultiSelect = False
        self.layout = FEED_LAYOUT_PROPS
        self.specUri = ''
        self.messages = []
        
        # opensearch properties
        self.os_totalResults = None
        self.os_itemsPerPage = None
        self.os_startIndex = None

        # links
        self.links = []
        
    def addEntry(self, id, title, updated=None, link=None, contentType='text', rawcontents='', summary='', author=None, published=None):
        if not published: published = self.updated
        if not updated: updated = self.updated
        if not link: link = id
        self.entries.append(AtomEntry(id, title, updated, link, contentType, rawcontents, summary, author, published))
        
    def toXml(self):
        
        output = [XML_MANIFEST]
        output.append('\n'.join([nodeToString(x) for x in getAtomStyleNodes()]))
        output.append('<feed xmlns="%s" xmlns:s="%s">' % (ATOM_NS, SPLUNK_NS))
        output.append('<title>%s</title>' % su.escape(self.title))
        output.append('<id>%s</id>' % su.escape(self.id))
        output.append('<updated>%s</updated>' % su.escape(self.updated))
        output.append('<author><name>%s</name></author>' % su.escape(self.author))
        output.append('<s:layout>%s</s:layout>' % self.layout)
        
        if self.messages:
            output.append('<s:messages>')
            for msg in self.messages:
                if msg['errorCode']:
                    output.append('<s:msg type="%s" code="%s">' % (msg['type'], msg['errorCode']))
                else:
                    output.append('<s:msg type="%s">' % msg['type'])
                if msg['text']:
                    output.append(su.escape(msg['text']))
                output.append('</s:msg>')
            output.append('</s:messages>')
            
        if self.specUri:
            output.append('<link rel="spec" href="%s" />' % self.specUri)
        if self.isEditable:
            output.append('<s:editable>true</s:editable>')
        if self.isMultiSelect:
            output.append('<s:multiSelect>true</s:multiSelect>')
        for entry in self.entries:
            output.append(entry.toXml(False))
        output.append('</feed>')
        return '\n'.join(output)

    def asJsonStruct(self):
        output = {}
        output["updated"]       = self.updated
        output["author"]        = self.author
        output["layout"]        = self.layout
        if self.messages:
            output["messages"]      = []
            for msg in self.messages:
                newMsg = {}
                newMsg["type"] = msg["type"]
                if msg["errorCode"]:
                    newMsg["code"] = msg["errorCode"]
                if msg["text"]:
                    newMsg["text"] = msg["text"]
                output["messages"].append(newMsg)

        if self.specUri:
            output["spec"] = self.specUri
        if self.isEditable:
            output["editable"] = True
        if self.isMultiSelect:
            output["multiSelect"] = True
        if len(self.entries) > 0:
            output["entry"] = []
        for entry in self.entries:
            output["entry"].append(entry.asJsonStruct())
        return output

    def toPrimitive(self):
        
        output = util.OrderedDict()
        for entry in self.entries:
            output[entry.title] = entry.toPrimitive()
        return output
            
    def __iter__(self):
        return self.entries.__iter__()
       
    def __contains__(self, key):
        return self.entries.__contains__(key)
        
    def __len__(self):
        return self.entries.__len__()
        

    def __getitem__(self, idx):
        return self.entries.__getitem__(idx)
        

class AtomEntry(object):
    '''Represents an Atom entry'''
    
    def __init__(self, id, title, updated, link=None, contentType=None, rawcontents=None, summary='', author='', published=''):
        self.id = id
        self.title = title
        self.updated = updated
        self.published = published
        self.author = author
        self.summary = summary
        self.rawcontents = rawcontents
        self.contentType = contentType
        self.actions = []
        #SPL-20024
        if isinstance(link, list) and link:
           self.links = link
        else:
           self.links = [('alternate', su.escape(link or id))]
        

    def toXml(self, outputManifest=True):
        '''
        Returns a string version of the XML representation of this entry
        '''
        
        output = []
        if outputManifest:
            output.append(XML_MANIFEST)
            output.append('\n'.join([nodeToString(x) for x in getAtomStyleNodes()]))
            output.append('<entry xmlns="%s" xmlns:s="%s">' % (ATOM_NS, SPLUNK_NS))
            
        else:
            output.append('<entry>')
        output.append('<title>%s</title>' % su.escape(self.title))
        output.append('<id>%s</id>' % su.escape(self.id))
        output.append(self._generateLinkXml())
        output.append('<published>%s</published>' % su.escape(self.published))
        output.append('<updated>%s</updated>' % su.escape(self.updated))
        
        output.append('<s:actions>')
        for item in self.actions:
            output.append('<s:action>%s</s:action>' % item)
        output.append('</s:actions>')
        
        if self.summary:
            output.append('<summary>%s</summary>' % su.escape(self.summary))
            
        contentType, contentValue = self._xmlSerializeContents(self.rawcontents)
        output.append('<content type="%s">%s</content>' % (su.escape(contentType), contentValue))
        
        output.append('</entry>')
        
        return '\n'.join(output)

    def asJsonStruct(self):
        output = {}
        output["title"]         = self.title
        output["id"]            = self.id
        output["updated"]       = self.updated

        output["links"] = self._generateLinkJsonStruct()
        
        if len(self.actions) > 0:
            output["actions"] = []
            for action in self.actions:
                output["actions"].append(action)
        
        if self.summary:
            output["summary"] = self.summary
            
        output["content"] = self.rawcontents
        return output


    def _generateLinkXml(self):
        output = []
        for link in self.links:
            if len(link) == 3:
                pattern = '<link rel="%s" href="%s" type="%s" />'
            else:
                pattern = '<link rel="%s" href="%s" />'
            output.append(pattern % link)
        return '\n'.join(output)
        
    def _generateLinkJsonStruct(self):
        output = {}
        for link in self.links:
            newLink = {"href" : link[1]}
            if len(link) == 3:
                newLink["type"] = link[2]
            output[link[0]] = newLink
        return output
        
    def _xmlSerializeContents(self, inputvalue):
        
        contentType = 'text/xml'
        if isinstance(inputvalue, dict) or isinstance(inputvalue, util.OrderedDict) or isinstance(inputvalue, list):
            output = primitiveToXml(inputvalue)
        elif isinstance(inputvalue, etree._Element):
            output = etree.tostring(inputvalue)
        elif inputvalue == None:
            contentType = 'text'
            output = ''
        else:
            contentType = 'text'
            output = su.escape(str(inputvalue))
            
        return (contentType, output)
        
    def toPrimitive(self):

        # this basic check is to prevent XML-as-string values from being
        # doubly escaped when being returned; this check assumes that the raw
        # XML string value is properly stripped
        if isinstance(self.rawcontents, util.string_type):
            cleanString = self.rawcontents.strip(' \t\n')
            if cleanString.startswith('<') and cleanString.endswith('>'):
                return self.rawcontents

        # otherwise auto-convert to primitives
        return nodeToPrimitive(self.rawcontents, False)
        
        

# /////////////////////////////////////////////////////////////////////////////
#  Utilities
# /////////////////////////////////////////////////////////////////////////////

def unesc(str):
    if not str: return str    
    return su.unescape(str, {'&quot;': '"', '&apos;': "'"})
    
def nodeToPrimitive(N, failOnNonNode=False):
    if N == None: return None
    if isinstance(N, etree._Element):
        if N.tag in (SPLUNK_TAGF % 'dict', 'dict'):
            return _dictNodeToPrimitive(N)
        elif N.tag in (SPLUNK_TAGF % 'list', 'list'):
            return _listNodeToPrimitive(N)
    if failOnNonNode:
        raise Exception('Expected Element object type; got %s' % N)
    return unesc(str(N))
                   
def _dictNodeToPrimitive(N):
    output = {}
    for child in N:
        if child.text and (len(child.text.strip()) > 0):
            output[child.get('name')] = child.text
        elif len(child) > 0:
            output[child.get('name')] = nodeToPrimitive(child[0])
        else:
            output[child.get('name')] = unesc(child.text)
    return output
    
def _listNodeToPrimitive(N):
    output = []
    for child in N:
        if child.text:
            output.append(child.text)
        elif len(child) > 0:
            output.append(nodeToPrimitive(child[0]))
        else:
            output.append(None)
    return output
            
            

def primitiveToXml(P):
    if isinstance(P, dict) or isinstance(P, util.OrderedDict): return _dictToXml(P)
    elif isinstance(P, list): return _listToXml(P)
    elif isinstance(P, util.unicode): return su.escape(P)
    else: return su.escape(str(P))

def _dictToXml(D):
    output = ['<s:dict>']
    for k in D:
        output.append('<s:key name=%s>' % su.quoteattr(k))
        output.append(primitiveToXml(D[k]))
        output.append('</s:key>')
    output.append('</s:dict>')
    return ''.join(output)

def _listToXml(L):
    output = ['<s:list>']
    for x in L:
        output.append('<s:item>')
        output.append(primitiveToXml(x))
        output.append('</s:item>')
    output.append('</s:list>')
    return ''.join(output)

                
                
if __name__ == '__main__':
    
    import unittest
    
    class MainTest(unittest.TestCase):
        
        #
        # the decoded string: 
        #   'abc_\xce\xa0\xce\xa3\xce\xa9'
        # is equivalent to:
        #   u'abc_\u03a0\u03a3\u03a9'
        #
        
        def testStringToXml(self):
            self.assertEqual(primitiveToXml('asdf'), 'asdf')
            self.assertEqual(
                primitiveToXml(b'abc_\xce\xa0\xce\xa3\xce\xa9'.decode('UTF-8')), 
                u'abc_\u03a0\u03a3\u03a9')
            self.assertEqual(
                primitiveToXml(u'abc_\u03a0\u03a3\u03a9'), 
                u'abc_\u03a0\u03a3\u03a9')
            self.assertNotEqual(
                primitiveToXml(u'abc_\u03a0\u03a3\u03a9'), 
                b'abc_\u03a0\u03a3\u03a9')
            
        def testListToXml(self):
            self.assertEqual(primitiveToXml(['asdf']), '<s:list><s:item>asdf</s:item></s:list>')
            self.assertEqual(
                primitiveToXml([u'abc_\u03a0\u03a3\u03a9'.encode('UTF-8')]), 
                u'<s:list><s:item>abc_\u03a0\u03a3\u03a9</s:item></s:list>'.encode('UTF-8'))
    

        def testXmltoPrimitive(self):
            self.assertEqual(nodeToPrimitive(
                etree.fromstring(u'<list><item>item1</item><item>item2</item><item>item3</item></list>')), 
                [u'item1', u'item2', u'item3'])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring(u'<dict><key name="k1">v1</key><key name="k2">v2</key><key name="k3">v3</key></dict>')), 
                {'k1': 'v1','k2': 'v2','k3': 'v3'})
            self.assertEqual(nodeToPrimitive(
                etree.fromstring(u'<list><item>item1</item><item>item2</item><item><dict><key name="k1">v1</key><key name="k2">v2</key><key name="k3">v3</key></dict></item></list>')), 
                [u'item1', u'item2', {'k1': 'v1','k2': 'v2','k3': 'v3'}])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring(u'<list><item>abc_\u03a0\u03a3\u03a9</item></list>')), 
                [u'abc_\u03a0\u03a3\u03a9'])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<list><item>abc_\xce\xa0\xce\xa3\xce\xa9</item></list>').decode('UTF-8'))), 
                [u'abc_\u03a0\u03a3\u03a9'])

            # test empty nodes
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<list><item></item></list>').decode('UTF-8'))), 
                [None])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<list><item/></list>').decode('UTF-8'))), 
                [None])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<dict><key name="emptyme"></key></dict>').decode('UTF-8'))), 
                {'emptyme': None})
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<dict><key name="emptyme"/></dict>').decode('UTF-8'))), 
                {'emptyme': None})


        def testXmltoPrimitiveNS(self):
            self.assertEqual(nodeToPrimitive(
                etree.fromstring(u'<s:list xmlns:s="%s"><s:item>abc_\u03a0\u03a3\u03a9</s:item></s:list>' % SPLUNK_NS)), 
                [u'abc_\u03a0\u03a3\u03a9'])
            self.assertEqual(nodeToPrimitive(
                etree.fromstring((b'<s:list xmlns:s="%s"><s:item>abc_\xce\xa0\xce\xa3\xce\xa9</s:item></s:list>' % SPLUNK_NS.encode('UTF-8')).decode('UTF-8'))), 
                [u'abc_\u03a0\u03a3\u03a9'])

            
        def testXmlToPrimitiveHtmlEntites(self):
            
            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<list><item>&lt;item1&gt;</item><item>&quot;item&apos;2</item></list>')),
                [u'<item1>', u'"item\'2']
                )


            # check the double encoding scenario
            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<dict><key name="eai:data">&lt;level1&gt;&amp;lt;level2&amp;gt;&lt;/level1&gt;</key></dict>')),
                {'eai:data': '<level1>&lt;level2&gt;</level1>'}
                )
            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<list><item>&lt;level1&gt;&amp;lt;level2&amp;gt;&lt;/level1&gt;</item></list>')),
                ['<level1>&lt;level2&gt;</level1>']
                )

                
            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<dict><key name="&lt;key1&gt;">&lt;item1&gt;</key><key name="&quot;key&apos;2">&quot;item&apos;2</key></dict>')),
                { '<key1>': '<item1>', '"key\'2': '"item\'2'}
                )
            self.assertEqual(
                nodeToPrimitive('search sourcetype=&quot;twiki&quot; edit startmonthsago=&quot;1&quot; | where date_hour&gt;20 OR date_hour&lt;5 | top twikiuser'),
                'search sourcetype="twiki" edit startmonthsago="1" | where date_hour>20 OR date_hour<5 | top twikiuser'
                )


            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<dict><key name="eai:data">sourcetype=&quot;&lt;twiki&gt;&quot;</key></dict>')),
                {'eai:data': 'sourcetype="<twiki>"'}
                )
            self.assertEqual(
                nodeToPrimitive(etree.fromstring(u'<list><item>sourcetype=&quot;&lt;twiki&gt;&quot;</item></list>')),
                ['sourcetype="<twiki>"']
                )


        def testPrimitiveToXmlHtmlEntites(self):

            self.assertEqual(
                primitiveToXml(['<item1>', '"item\'2']),
                '<s:list><s:item>&lt;item1&gt;</s:item><s:item>"item\'2</s:item></s:list>',
                )

            self.assertEqual(
                primitiveToXml({'<key1>': '<item1>'}),
                '<s:dict><s:key name="&lt;key1&gt;">&lt;item1&gt;</s:key></s:dict>'
                )

            self.assertEqual(
                primitiveToXml({'"key\'2': '"item\'2'}),
                '<s:dict><s:key name="&quot;key\'2">"item\'2</s:key></s:dict>'
                )

            self.assertEqual(
                primitiveToXml({"'key\"2": "'item\"2"}),
                '<s:dict><s:key name="\'key&quot;2">\'item"2</s:key></s:dict>'
                )
                
                
                
        def testAtomFeed(self):
            
            feed = AtomFeed()
            feed.addEntry('ID_STRING', 'entrytitle', strftime(), rawcontents='this is the raw content')
            self.assertEqual(feed[0].id, 'ID_STRING')
            self.assertEqual(feed[0].title, 'entrytitle')
            self.assertEqual(feed[0].rawcontents, 'this is the raw content')
            
            feed.toXml()

        def testPrimitiveToAtomFeed(self):
            
            # test empties
            feed = primitiveToAtomFeed('hostpath', 'basepath', {})
            self.assertEqual(len(feed), 0)
            self.assertEqual(feed.id, 'hostpathbasepath')
            feed.toXml()

            feed = primitiveToAtomFeed('hostpath', 'basepath', [])
            self.assertEqual(len(feed), 0)
            self.assertEqual(feed.id, 'hostpathbasepath')
            feed.toXml()
            
            # test 1 item
            feed = primitiveToAtomFeed('hostpath', 'basepath', {'entry1':'value1'})
            self.assertEqual(len(feed), 1)
            self.assertEqual(feed.id, 'hostpathbasepath')

            feed = primitiveToAtomFeed('hostpath', 'basepath', ['value1'])
            self.assertEqual(len(feed), 1)
            self.assertEqual(feed.id, 'hostpathbasepath')

            # test 3 items
            d = util.OrderedDict()
            d['entry1'] = 'value1'
            d['entry2'] = 'value2'
            d['entry3'] = 'value3'
            feed = primitiveToAtomFeed('hostpath', 'basepath', d)
            self.assertEqual(len(feed), 3)
            self.assertEqual(feed[0], feed.entries[0])
            self.assertEqual(feed[2], feed.entries[2])
            self.assertEqual(feed[0].rawcontents, 'value1')
            self.assertEqual(feed[1].rawcontents, 'value2')
            self.assertEqual(feed[2].rawcontents, 'value3')

                   
        def testAtomEntryToPrimitive(self):
            '''
            checks that the AtomEntry.toPrimitive() method properly converts
            the known Splunk XML format into primitives and leaves string values
            untouched, and unescaped
            '''
            
            xmlstring = '<root xmlns="%s" xmlns:s="%s"><s:dict><s:key name="&quot;key\'2">"item\'2 is &lt; 42</s:key></s:dict></root>' % (ATOM_NS, SPLUNK_NS)
            xmlelement = etree.fromstring(xmlstring)
                       
            ae = AtomEntry(id='foo', title='title', updated='now', rawcontents=xmlstring)
            self.assertEqual(ae.toPrimitive(), xmlstring)
            
            ae = AtomEntry(id='foo', title='title', updated='now', rawcontents=xmlelement)
            self.assertEqual(ae.toPrimitive(), nodeToPrimitive(xmlelement))
            
            

            
            
    suite = unittest.TestLoader().loadTestsFromTestCase(MainTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
