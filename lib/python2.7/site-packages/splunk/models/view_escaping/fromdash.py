from __future__ import absolute_import
from builtins import object
from builtins import range
from builtins import object

import json
import logging
import lxml.etree as et
import re
import sys
from gettext import gettext as _

import splunk.util
from splunk.models.view_escaping import forminput
from splunk.models.view_escaping.base import POST_SEARCH_MODE, SAVED_SEARCH_MODE, TEMPLATE_SEARCH_MODE
from splunk.models.view_escaping.base import DEFAULT_SEARCH_ID
from splunk.models.view_escaping.dashboard import SimpleDashboard
from splunk.models.view_escaping.drilldown import parseDrilldown
from splunk.models.view_escaping.drilldown import parseDrilldownAction
from splunk.models.view_escaping.panel import Panel
# I am leaving the * because refactoring may have un foreseen issues. the code uses `globals().items()` :(
from splunk.models.view_escaping.panelElement import *
from splunk.models.view_escaping.panelElement import normalizeBoolean, Event, BasePanel, Chart
from splunk.models.view_escaping.row import Row
from splunk.models.view_escaping.search import Search, createSearchFromSearchXml
from splunk.models.view_escaping.tokendeps import parseTokenDeps
from splunk.models.view_escaping.validation_helper import WarningsCollector


logger = logging.getLogger('splunk.models.view_escaping')

ID_PATTERN = re.compile(r'^[a-z]\w*$', re.IGNORECASE)

def getValidationMessages(dashboardNode, viewName=None, digest=None, sourceApp=None):
    logger.info('Validating dashboard XML for view=%s', viewName)
    collector = WarningsCollector(logger=logger)
    try:
        with collector:
            createDashboardFromXml(dashboardNode, viewName, digest, sourceApp)
    except:
        pass
    return collector.getMessages()


def createDashboardFromXml(dashboardNode, viewName=None, digest=None, sourceApp=None):
    """
    @param dashboardNode: lxml node representing a dashboard or form
    @param viewName: the name of the xml file
    @param digest: boolean
    @return:
    """

    logger.debug("Parsing view: simplexml=%s" % viewName)
    dashboard = SimpleDashboard(viewName=viewName, digest=digest, sourceApp=sourceApp)

    # Parse global options
    dashboard.label = dashboardNode.findtext('./label')
    dashboard.description = dashboardNode.findtext('./description')

    dashboard.customScript = dashboardNode.get('script', None)    
    dashboard.customStylesheet = dashboardNode.get('stylesheet', None)
    dashboard.onUnloadCancelJobs = normalizeBoolean(
        dashboardNode.get('onunloadCancelJobs', dashboard.onUnloadCancelJobs))

    dashboard.matchTagName = dashboardNode.tag
    if dashboard.matchTagName not in ['form', 'dashboard']:
        raise Exception(_('Invalid root element'))

    if dashboardNode.tag == 'form':
        # update the fieldset
        fieldsetNode = dashboardNode.find('./fieldset')
        if fieldsetNode is not None:
            dashboard.autoRun = splunk.util.normalizeBoolean(
                fieldsetNode.get('autoRun', False))
            dashboard.submitButton = splunk.util.normalizeBoolean(
                fieldsetNode.get('submitButton', True))

            for item in fieldsetNode:
                logger.debug("Found new element in fieldset: form=%s item=%s" % (viewName, item.tag))
                if item.tag == 'html':
                    panelInstance = createPanelElementFromXml(item)
                    dashboard.fieldset.append(panelInstance)
                elif item.tag == 'input':
                    inputDefaults = dict()
                    if not dashboard.submitButton:
                        inputDefaults['searchWhenChanged'] = True
                    inputInstance = forminput.createInput(item.get('type'), inputDefaults)
                    inputInstance.fromXml(item, sourceApp)

                    dashboard.fieldset.append(inputInstance)

    # set core view attributes
    for k in dashboard.standardAttributeMap:
        v = dashboardNode.get(k)
        if v is not None:
            if k in dashboard.booleanAttributeKeys:
                v = splunk.util.normalizeBoolean(v)
            elif k in dashboard.integerAttributeKeys:
                try:
                    v = int(v)
                except:
                    msg = "Dashboard attribute %s should have an integer value. Value found: %s" % (k, v)
                    logger.error(msg)
                    raise Exception(msg)
            setattr(dashboard, k, v)

    # Legacy searchTemplate extraction
    search = createSearchFromXml(dashboardNode, id=DEFAULT_SEARCH_ID)
    if search:
        dashboard.searches.append(search)
    for searchNode in dashboardNode.findall('search'):
        search = createSearchFromSearchXml(searchNode)
        if search:
            logger.debug("Appending new search to view=%s" % viewName)
            dashboard.searches.append(search)

    for rowNode in dashboardNode.findall('row'):
        logger.debug("Appending new row to view=%s" % viewName)
        dashboard.rows.append(createRowFromXml(rowNode, sourceApp))

    normalizeIdentifiers(dashboard)
                                     
    def prepareEventSearch(searchObj):
        if searchObj is not None:
            if searchObj.searchMode == POST_SEARCH_MODE:
                prepareEventSearch(dashboard.get_search(searchObj.baseSearchId))
            else:
                searchObj.statusBuckets = 300

    for row in dashboard.rows:
        for panel in row.panels:
            for panelElement in panel.panelElements:
                if isinstance(panelElement, Event):
                    prepareEventSearch(panelElement.search)

    return dashboard


def verify_id(id, seen, type):
    if id is not None:
        if id in seen:
            raise Exception(_('Duplicate ID "%s" of %s' % (id, type)))
        if not ID_PATTERN.match(id):
            raise Exception(_(
                'ID "%s" for %s does not match pattern %s ' +
                '(ID has to begin with a letter and must not '
                'container characters other than letters, numbers and "_")') % (id, type, ID_PATTERN.pattern))
        seen.add(id)


class IdSeq(object):
    def __init__(self):
        self.val = 1

    def __next__(self):
        while True:
            yield self.val
            self.val += 1 

def auto_id(pattern, seen, seq):
    id = None
    for seq_no in next(seq):
        id = pattern % seq_no
        if id not in seen:
            break
    seen.add(id)
    return id


def normalizeIdentifiers(dashboard):
    """
    Ensure all dashboard elements have an unique id

    @param dashboard: Dashboard object
    @return: no return value
    """
    seen = set()
    for row in dashboard.rows:
        verify_id(row.id, seen, "row")
    for panel in dashboard.all_panels():
        verify_id(panel.id, seen, "panel")
    for el in dashboard.all_elements():
        verify_id(el.id, seen, "panel element")
    for el in dashboard.all_fields():
        verify_id(el.id, seen, "input field")
    for (search, obj) in dashboard.all_searches():
        verify_id(search.id, seen, "search")

    globalSearch = None

    search_seq = IdSeq()
    row_seq = IdSeq()
    panel_seq = IdSeq()
    element_seq = IdSeq()
    input_seq = IdSeq()
    
    for (search, obj) in dashboard.all_searches():
        if search.id is None:
            search.id = globalSearch = auto_id("search%d", seen, search_seq)

    for row in dashboard.rows:
        if row.id is None:
            row.id = auto_id("row%d", seen, row_seq)
            row.idGenerated = True
    for panel in dashboard.all_panels():
        if panel.id is None:
            panel.id = auto_id("panel%d", seen, panel_seq)
            panel.idGenerated = True
    for el in dashboard.all_elements():
        if el.id is None:
            el.id = auto_id("element%d", seen, element_seq)
        if el.context is None:
            if getattr(el, 'searchMode', None):
                el.context = auto_id("search%d", seen, search_seq)
            elif globalSearch is not None:
                el.context = globalSearch
    for field in dashboard.all_fields():
        if field.id is None:
            field.id = auto_id("input%d", seen, input_seq)
        if getattr(field, 'context', None) is None:
            if getattr(field, 'search', None) or getattr(field, 'savedSearch', None):
                field.context = auto_id("search%d", seen, search_seq)


def createSearchFromXml(searchNode, id=None):
    """
    Parses a search from search, dashboard, panel element xml nodes
    @param searchNode: Lxml representing a form or dashboard element
    @param id: and optional id to force id to
    @return:
    """

    # define search mode XML node -> object property mappings
    searchModeNodeMap = [
        ('searchString', TEMPLATE_SEARCH_MODE),
        ('searchName', SAVED_SEARCH_MODE),
        ('searchTemplate', TEMPLATE_SEARCH_MODE),
        ('searchPostProcess', POST_SEARCH_MODE)
    ]

    opt = dict()
    for pair in searchModeNodeMap:
        if searchNode.find(pair[0]) is not None:
            opt['searchMode'] = pair[1]
            opt['searchCommand'] = (
                searchNode.findtext(pair[0])).replace("\n", " ").replace("\t", " ")
            break
    else:
        return False
    for node in ['earliestTime', 'latestTime']:
        nodeVal = searchNode.findtext(node)
        if nodeVal:
            opt[node] = nodeVal
    tokenDeps = parseTokenDeps(searchNode)
    if id:
        opt['id'] = id
    if tokenDeps:
        opt['tokenDeps'] = tokenDeps
    return Search(**opt)

def createRowFromXml(rowNode, sourceApp=None):
    """
    Parses a row xml node
    @param rowNode: Lxml representing a form or dashboard element
    @return:
    """
    logger.debug("parsing dashboard row node")
    if rowNode.get('grouping'):
        rowGroupings = list(map(
            int,
            rowNode.get('grouping').replace(' ', '').strip(',').split(',')))
        logger.debug("Found row grouping=%s" % rowGroupings)
    else:
        rowGroupings = None

    row = Row(rowGroupings)
    row.tokenDeps = parseTokenDeps(rowNode)
    row.id = rowNode.get('id')

    if len(rowNode) is 0:
        logger.warn('Dashboard row is empty (line %d)', rowNode.sourceline)

    else:
        hasPanels = False
        hasVisualizations = False
        for panelElementNode in rowNode:
            if panelElementNode.tag == "panel":
                if hasVisualizations:
                    raise Exception(_('Row, on line=%s, should not combine visualizations and panels. Panel, on line=%s') % (rowNode.sourceline, panelElementNode.sourceline))
                hasPanels = True
                if rowGroupings is not None:
                    raise Exception(_('Row on line=%s specifies row grouping but has <panel> children, which is not allowed') % rowNode.sourceline)
                row.panels.append(createPanelFromXML(panelElementNode, sourceApp))
            elif panelElementNode.tag == et.Comment:
                continue
            else:
                if hasPanels:
                    raise Exception(_('Row, on line=%s, should not combine visualizations and panels. Visualization, on line=%s') % (rowNode.sourceline, panelElementNode.sourceline))
                hasVisualizations = True
                try:
                    panelElement = createPanelElementFromXml(panelElementNode)
                    if panelElement:
                        row.appendPanelElement(panelElement)
                except NotImplementedError:
                    raise Exception(_('Row, on line=%s, contains unknown node=%s on line=%s.') % (rowNode.sourceline, panelElementNode.tag, panelElementNode.sourceline))
    return row


def createPanelFromXML(panelNode, sourceApp=None):
    panel = Panel(None)
    panel.tokenDeps = parseTokenDeps(panelNode)
    panel.id = panelNode.get('id', None)

    if len(panelNode) is 0:
        logger.warn('Dashboard panel is empty (line %d)', panelNode.sourceline)

    ref = panelNode.get('ref', None)
    if ref:
        panel.ref = ref
        panel.app = panelNode.get('app', sourceApp)
    else:
        panel.title = panelNode.findtext('title')
        for panelElementNode in panelNode:
            if panelElementNode.tag == 'input':
                inputInstance = forminput.createInput(
                    panelElementNode.get('type'), dict(searchWhenChanged=True))
                inputInstance.fromXml(panelElementNode, sourceApp)
                panel.fieldset.append(inputInstance)
            elif panelElementNode.tag == 'search':
                search = createSearchFromSearchXml(panelElementNode)
                if search:
                    panel.searches.append(search)
            elif panelElementNode.tag not in ('title', 'description'):
                panelElement = createPanelElementFromXml(panelElementNode)
                if panelElement:
                    panel.appendPanelElement(panelElement)
    return panel


def extractHtmlContent(node):
    if normalizeBoolean(node.attrib.get("encoded", False)):
        return node.text
    else:
        if len(node) == 0 and node.text is None:
            return ''
        else:
            parser = et.XMLParser(resolve_entities=False)
            clone = et.XML(et.tostring(node).strip(), parser)
            # Strip attributes on outer <html> node, so we can safely strip it once serialized
            clone.attrib.clear()
            html = et.tostring(clone)
            if sys.version_info > (3, 0) and isinstance(html, bytes):
                html = html.decode()
            if html.startswith('<html>') and html.endswith('</html>'):
                return html[6:-7].strip()
            else:
                return html

def _isPrimarySearchNode(node):
    type = node.get('type')
    return type == 'primary' or type is None

def _findPrimarySearchNode(panelElementNode):
    searchNodes = panelElementNode.findall('search')
    return next((sn for sn in searchNodes if _isPrimarySearchNode(sn)), None)

def createPanelElementFromXml(panelElementNode):
    def createHtmlPanelElementFromXml(panelElementNode, panelInstance):
        """
        Override default parser and just get the text
        """
        logger.debug("parsing html panel element")
        panelInstance.options['useTokens'] = normalizeBoolean(panelElementNode.attrib.get("tokens", True))
        
        src = panelElementNode.get('src')
        if src:
            panelInstance.options['serverSideInclude'] = src
            return

        panelInstance.options['rawcontent'] = extractHtmlContent(panelElementNode)
        panelInstance.tokenDeps = parseTokenDeps(panelElementNode)

    def createChartPanelElementFromXml(node, element):
        createDefaultPanelElementFromXml(node, element)
        selectionNode = node.find('selection')
        if selectionNode:
            element.selection = []
            for actionNode in [node for node in selectionNode if et.iselement(node) and isinstance(node.tag, str)]:
                action = parseDrilldownAction(actionNode)
                if action:
                    element.selection.append(action)

    def createTablePanelElementFromXml(panelElementNode, panelInstance):
        """
        Add a format tag to provide cell formatting
        (primarily for sparklines at the current time)
        Each format tag may have some option sub-tags
        Each option may contain list or option tags generating
        lists or dictionaries respectively

        Each format tag may specify a field to filter on
        (defaults to all fields) and a type to apply (eg 'sparkline')
        """
        logger.debug("parsing table panel element")

        def parseOption(node):
            """Extract nested options/lists"""
            listNodes = node.findall('list')
            optionNodes = node.findall('option')

            if listNodes and optionNodes:
                raise ValueError("Tag cannot contain both list and option subtags")
            elif listNodes:
                result = []
                for listNode in listNodes:
                    result.append(parseOption(listNode))
                return result
            elif optionNodes:
                result = {}
                for optionNode in optionNodes:
                    result[optionNode.get('name')] = parseOption(optionNode)
                return result
            else:
                return node.text

        createDefaultPanelElementFromXml(panelElementNode, panelInstance)
        fieldFormats = {}
        for formatNode in panelElementNode.findall('format'):
            logger.debug("Parsing format view node")
            field = formatNode.get('field', '*')
            formatType = formatNode.get('type', 'text')
            options = {}
            for optionNode in formatNode.findall('option'):
                options[optionNode.get('name')] = parseOption(optionNode)
            fieldFormats.setdefault(field, []).append({
                'type': formatType,
                'options': options
            })
        panelInstance.fieldFormats = fieldFormats

    def createVizPanelElementFromXml(panelElementNode, panelInstance):
        createDefaultPanelElementFromXml(panelElementNode, panelInstance)
        panelInstance.type = panelElementNode.get('type', None)

    def createDefaultPanelElementFromXml(panelElementNode, panelInstance):
        logger.debug("Parsing default panel element options")
        title = panelElementNode.findtext('title')
        if title is not None:
            setattr(panelInstance, 'title', title)

        optionTypeMap = {}
        if hasattr(panelInstance.__class__, 'optionTypeMap'):
            optionTypeMap = getattr(panelInstance.__class__, 'optionTypeMap')

        # option params get their own container
        for node in panelElementNode.findall('option'):
            optionName = node.get('name')
            optionValue = node.text
            if optionName in optionTypeMap:
                optionValue = optionTypeMap[optionName](optionValue)
            if isinstance(optionValue, str) and optionValue != None:
                optionValue = optionValue.strip()
            if optionName not in ['id', 'el', 'managerid', 'tokenDependencies', 'resizable']:
                panelInstance.options[optionName] = optionValue

        # handle different search modes
        if getattr(panelInstance.__class__, 'hasSearch'):
            # SPL-143552: make sure the primary search is found. Other types of search nodes will be ignored for now.
            primarySearchNode = _findPrimarySearchNode(panelElementNode)
            search = createSearchFromSearchXml(primarySearchNode) if primarySearchNode is not None else None
            if search:
                panelInstance.search = search
            else:
                search = createSearchFromXml(panelElementNode)
                if search:
                    panelInstance.search = search
                else:
                    # create a default search if there is not one
                    panelInstance.search = Search(searchMode=POST_SEARCH_MODE)

        # handle field lists
        if panelElementNode.find('fields') is not None:
            fields = panelElementNode.findtext('fields').strip()
            if len(fields) and fields[0] == '[' and fields[-1] == ']':
                panelInstance.searchFieldList = json.loads(fields)
            else:
                panelInstance.searchFieldList = splunk.util.stringToFieldList(fields)

        # extract simple XML drilldown params
        panelInstance.simpleDrilldown = parseDrilldown(panelElementNode.find('drilldown'))

        panelInstance.tokenDeps = parseTokenDeps(panelElementNode)

        # extract the contents of all top-level comment nodes
        for node in panelElementNode.xpath('./comment()'):
            panelInstance.comments.append(node.text)

        # extract the comments from inside the drilldown tag
        for node in panelElementNode.xpath('./drilldown/comment()'):
            panelInstance.drilldownComments.append(node.text)

    def createPanel(name):
        """
        Factory method for creating an appropriate panel object based upon the
        name.  Returns an instance of a BasePanel subclass, or throws a
        NotImplementedError if no suitable mapper is found.

        This method works by inspecting all objects that subclass BasePanel and
        attempting to match their matchTagName class attribute.
        """

        if not name:
            raise ValueError('Cannot create panel from nothing')

        for obj in globals().values():
            try:
                if issubclass(obj, BasePanel) and name == obj.matchTagName:
                    #  only Chart objects need to be instantiated
                    if obj is Chart:
                        return Chart()
                    else:
                        return obj()
            except:
                pass
        raise NotImplementedError(
            _('Cannot find object mapper for panel type: %s') % name)

    if not isinstance(panelElementNode.tag, splunk.util.string_type):
        return False
    panelType = panelElementNode.tag
    panelInstance = createPanel(panelType)

    id = panelElementNode.attrib.get('id')
    if id is not None:
        panelInstance.id = id

    logger.debug("found panel element type=%s" % panelType)
    if panelType == 'table':
        createTablePanelElementFromXml(panelElementNode, panelInstance)
    elif panelType == 'chart':
        createChartPanelElementFromXml(panelElementNode, panelInstance)
    elif panelType == 'html':
        createHtmlPanelElementFromXml(
            panelElementNode, panelInstance)
    elif panelType == 'viz':
        createVizPanelElementFromXml(panelElementNode, panelInstance)
    else:
        createDefaultPanelElementFromXml(panelElementNode, panelInstance)
    return panelInstance


if __name__ == '__main__':
    import unittest

    def getRowXml(args='', panels=1):
        nodes = ['<row %(args)s>']
        for i in range(0, panels):
            nodes.append('<single></single>')
        nodes.append('</row>')
        xml = ''.join(nodes)
        return xml % {'args': args}

    def getPanelElementXml(type="foo", options=None, args=None):
        options = options or (
            '<searchString> | metadata type="sources" | '
            'stats count</searchString>')
        args = args or ''
        xml = '''
            <%(type)s %(args)s>
                %(options)s
            </%(type)s>
        '''
        return xml % {'type': type, 'options': options, 'args': args}

    class CreatePanelElementTests(unittest.TestCase):

        def createPanel(self, type="foo", options=None, args=None):
            xml = getPanelElementXml(type, options, args)
            root = et.fromstring(xml)
            return createPanelElementFromXml(root)

        def testCreateUnknownPanel(self):
            with self.assertRaises(NotImplementedError):
                d = self.createPanel('foo')

        def testCreateAllowedPanels(self):
            for panelType in ['single', 'chart', 'table',
                              'html', 'map', 'event', 'list', 'viz']:
                d = self.createPanel(panelType)
                self.assertTrue(d.matchTagName == panelType)

        def testCreateHTMLPanel(self):
            d = self.createPanel(
                'html', args='src="/foo/bar"')
            self.assertTrue(d.options.get('serverSideInclude') == '/foo/bar')
            self.assertFalse(d.options.get('rawcontent'))
            d = self.createPanel(
                'html', options='<div>Test</div>', args='src="/foo/bar"')
            self.assertTrue(d.options.get('serverSideInclude') == '/foo/bar')
            self.assertFalse(d.options.get('rawcontent'))
            d = self.createPanel(
                'html', options='<div>Test</div>')
            self.assertFalse(d.options.get('serverSideInclude'))
            self.assertEqual(d.options.get('rawcontent'), '<div>Test</div>')

        def testCreateTablePanel(self):
            """tables only have special format fields"""
            d = self.createPanel('table', options='''
                <format>
                    <option name="fff">
                        <list>foo</list>
                        <list>bop</list>
                    </option>
                    <option name="bippity">
                        <option name="bippity">bop</option>
                    </option>
                </format>
                <format field="foobar" type="num">
                    <option name="fff">
                        <list>foo</list>
                        <list>bop</list>
                    </option>
                    <option>bar</option>
                </format>
                ''')
            self.assertTrue(d.fieldFormats == { # pylint: disable=E1103
                '*': [{'type': 'text',
                       'options': {'bippity': {'bippity': 'bop'},
                                   'fff': ['foo', 'bop']
                       }
                      }],
                'foobar': [{'type': 'num',
                            'options': {None: 'bar',
                                        'fff': ['foo', 'bop']
                            }
                           }]
            })
            #  formats can't mix options and lists.
            #  lists can contain options and options can contain list but
            #     neither can contain both.
            with self.assertRaises(ValueError):
                d = self.createPanel(
                    'table',
                    options='''
                        <format>
                            <option name="fff">
                                <list>foo</list>
                                <list>bop</list>
                                <option name="should">not work</option>
                            </option>
                            <option>bar</option>
                        </format>
                    ''')

        def testCreateChartPanelWithSelection(self):
            chart = self.createPanel('chart', options='''
                <selection>
                    <set token="foo">$start$</set>
                    <unset token="bar" />
                </selection>
                ''')

            self.assertIsNotNone(chart.selection)
            self.assertEqual(2, len(chart.selection))
            self.assertEqual("settoken", chart.selection[0].type)
            self.assertEqual("unsettoken", chart.selection[1].type)

        def testCreateCustomVizPanel(self):
            customViz = self.createPanel('viz', args='type="testapp.testviz"')
            self.assertTrue(customViz.type == 'testapp.testviz')


        def testCreateDefaultPanel(self):
            """All panels have some things in common"""
            #s test common nodes
            d = self.createPanel('single', options='''
                <title>Title1</title>
                <searchString>search string</searchString>
                <earliestTime>0</earliestTime>
                <latestTime>50</latestTime>
                <fields>foo bar baz</fields>
                ''')
            self.assertEqual(d.search.earliestTime, '0')
            self.assertEqual(d.search.latestTime, '50')
            self.assertEqual(d.title, 'Title1')
            self.assertEqual(d.searchFieldList, 'foo bar baz'.split())

            # should be able to accept one of the search modes
            d = self.createPanel('single', options='''
                <searchString>search string</searchString>
                ''')
            self.assertTrue(hasattr(d, 'search'),  'panel elements should have a search object')
            self.assertEqual(getattr(d.search, 'searchMode'), 'template')
            self.assertEqual(getattr(d.search, 'searchCommand'), 'search string')
            d = self.createPanel('single', options='''
                <searchName>search saved</searchName>
                <searchTemplate>search template</searchTemplate>
                <searchPostProcess>search postsearch</searchPostProcess>
                ''')
            self.assertEqual(getattr(d.search, 'searchMode'), 'saved')
            self.assertEqual(getattr(d.search, 'searchCommand'), 'search saved')
            d = self.createPanel('single', options='''
                <searchTemplate>search template</searchTemplate>
                ''')
            self.assertEqual(getattr(d.search, 'searchMode'), 'template')
            self.assertEqual(getattr(d.search, 'searchCommand'), 'search template')
            d = self.createPanel('single', options='''
                <searchPostProcess>search postsearch</searchPostProcess>
                ''')
            self.assertEqual(getattr(d.search, 'searchMode'), 'postsearch')
            self.assertEqual(getattr(d.search, 'searchCommand'), 'search postsearch')
            self.assertEqual(getattr(d.search, 'baseSearchId'), 'global')

            # Options should not override internal settings
            d = self.createPanel('chart', options='''
                <option name="id">xyz</option>
                <option name="managerid">abc</option>
                <option name="el">abc</option>
                <option name="tokenDependencies">abc</option>
                <option name="resizable">False</option>
                ''')

            for option in d.options:
                if option in ['id', 'el', 'managerid', 'tokenDependencies', 'resizable']:
                    self.assertTrue(False, 'Options should not override internal settings')

        def testCreateSavedSearch(self):
            """All panels have some things in common"""
            #s test common nodes
            d = self.createPanel('single', options='''
                <title>Title1</title>
                <search ref="search"/>
                ''')
            self.assertEqual(d.search.searchCommand, 'search')


        def testTokenDependencies(self):
            for panelType in ('table', 'chart', 'single', 'map', 'list', 'html'):
                panel = createPanelElementFromXml(et.fromstring('''
                    <%(type)s depends="$foo$">
                    </%(type)s>
                ''' % dict(type=panelType)))
                self.assertIsNotNone(panel)
                self.assertIsNotNone(panel.tokenDeps)
                self.assertEquals(panel.tokenDeps.depends, '$foo$')
                self.assertEquals(panel.tokenDeps.rejects, '')

                panel = createPanelElementFromXml(et.fromstring('''
                    <%(type)s rejects="$foo$">
                    </%(type)s>
                ''' % dict(type=panelType)))
                self.assertIsNotNone(panel)
                self.assertIsNotNone(panel.tokenDeps)
                self.assertEquals(panel.tokenDeps.rejects, '$foo$')
                self.assertEquals(panel.tokenDeps.depends, '')

                panel = createPanelElementFromXml(et.fromstring('''
                    <%(type)s id="foo" depends="$foo$" rejects="$bar$">
                    </%(type)s>
                ''' % dict(type=panelType)))
                self.assertIsNotNone(panel)
                self.assertIsNotNone(panel.tokenDeps)
                self.assertEquals(panel.tokenDeps.depends, '$foo$')
                self.assertEquals(panel.tokenDeps.rejects, '$bar$')

                panel = createPanelElementFromXml(et.fromstring('''
                    <%(type)s>
                    </%(type)s>
                ''' % dict(type=panelType)))
                self.assertIsNotNone(panel)
                self.assertIsNone(panel.tokenDeps)

                panel = createPanelElementFromXml(et.fromstring('''
                    <%(type)s depends="" rejects="">
                    </%(type)s>
                ''' % dict(type=panelType)))
                self.assertIsNotNone(panel)
                self.assertIsNone(panel.tokenDeps)

                dashboard = createDashboardFromXml(et.fromstring('''
                    <form>
                    
                        <fieldset>
                            <input token="foobar" rejects="$foobar$" />
                        </fieldset>
                    
                        <row depends="$foobar$">
                            <panel rejects="$foobar$">
                                <chart depends="$x$" rejects="$y$">
                                
                                </chart>
                            </panel>
                        </row>
                    </form>
                '''))

                self.assertIsNotNone(dashboard.rows[0].tokenDeps)
                self.assertEquals(dashboard.rows[0].tokenDeps.depends, "$foobar$")
                self.assertEquals(dashboard.rows[0].tokenDeps.rejects, "")
                self.assertIsNotNone(dashboard.rows[0].panels[0].tokenDeps)
                self.assertEquals(dashboard.rows[0].panels[0].tokenDeps.depends, "")
                self.assertEquals(dashboard.rows[0].panels[0].tokenDeps.rejects, "$foobar$")
                self.assertIsNotNone(dashboard.rows[0].panels[0].tokenDeps)
                self.assertEquals(dashboard.rows[0].panels[0].tokenDeps.depends, "")
                self.assertEquals(dashboard.rows[0].panels[0].tokenDeps.rejects, "$foobar$")
                self.assertIsNotNone(dashboard.rows[0].panels[0].panelElements[0].tokenDeps)
                self.assertEquals(dashboard.rows[0].panels[0].panelElements[0].tokenDeps.depends, "$x$")
                self.assertEquals(dashboard.rows[0].panels[0].panelElements[0].tokenDeps.rejects, "$y$")
                self.assertIsNotNone(dashboard.fieldset[0].tokenDeps)
                self.assertEquals(dashboard.fieldset[0].tokenDeps.depends, "")
                self.assertEquals(dashboard.fieldset[0].tokenDeps.rejects, "$foobar$")
                dashboard = createDashboardFromXml(et.fromstring('''
                    <form>

                        <fieldset>
                            <input token="multiselect" type="multiselect" rejects="$foobar$">
                                <search ref="foo"/>
                            </input>
                        </fieldset>

                        <row depends="$foobar$">
                            <panel rejects="$foobar$">
                                <chart depends="$x$" rejects="$y$">

                                </chart>
                            </panel>
                        </row>
                    </form>
                '''))
                self.assertEquals(dashboard.fieldset[0].search.searchCommand, "foo")


        def testSimpleDrilldownPopulated(self):
            for panelType in ('table', 'chart', 'single', 'map', 'list'):
                xmlNode = et.fromstring('''
                    <%(type)s id="panel1">
                        <title>Panel 1</title>
                        <drilldown>
                            <set token="foobar">($click.value$)</set>
                        </drilldown>
                    </%(type)s>
                ''' % dict(type=panelType))
                panel = createPanelElementFromXml(xmlNode)
                self.assertIsNotNone(panel)
                self.assertEquals(len(panel.simpleDrilldown), 1)

    class _findPrimarySearchNodeTests(unittest.TestCase):
        def testAnnotationBeforePrimary(self):
            chart = et.fromstring('''
              <chart>
                <title>test_chart_annotation_pdf_printing</title>
                <search type="annotation">
                  <query>index=_internal (log_level="WARN" OR log_level="ERROR" OR log_level="INFO") | eval annotation_label = "Category is" | eval annotation_category = log_level | table _time annotation_label annotation_category</query>
                  <earliest>-1m@m</earliest>
                  <latest>now</latest>
                </search>
                <search>
                  <query>index=_internal | timechart count</query>
                  <earliest>-1m@m</earliest>
                  <latest>now</latest>
                </search>
                <option name="charting.annotation.categoryColors">{"ERROR":"0xFF0000","WARN":"0x0000FF", "INFO": "0x008000"}</option>
                <option name="charting.chart">area</option>
              </chart>
            ''')
            primary = _findPrimarySearchNode(chart)
            self.assertIsNone(primary.get('type'), 'primary search type')
            self.assertEqual(primary.findtext('query'), 'index=_internal | timechart count', 'primary search type')

        def test_isPrimarySearchNode(self):
            primaryNode = et.fromstring('''
                <search type="primary">
                  <query>index=_internal | timechart count</query>
                  <earliest>-1m@m</earliest>
                  <latest>now</latest>
                </search>
            ''')
            self.assertTrue(_isPrimarySearchNode(primaryNode))

            defaultNode = et.fromstring('''
                <search>
                  <query>index=_internal | timechart count</query>
                  <earliest>-1m@m</earliest>
                  <latest>now</latest>
                </search>
            ''')
            self.assertTrue(_isPrimarySearchNode(defaultNode))

            annotationNode = et.fromstring('''
                <search type="annotation">
                  <query>index=_internal (log_level="WARN" OR log_level="ERROR" OR log_level="INFO") | eval annotation_label = "Category is" | eval annotation_category = log_level | table _time annotation_label annotation_category</query>
                  <earliest>-1m@m</earliest>
                  <latest>now</latest>
                </search>
            ''')
            self.assertFalse(_isPrimarySearchNode(annotationNode))

    class CreatePanelTests(unittest.TestCase):
        def getPanel(self, xml='<panel></panel>'):
            root = et.fromstring(xml)
            return createPanelFromXML(root)

        def testEmptyPanel(self):
            self.assertTrue(isinstance(self.getPanel(), Panel), '')

        def testPanelId(self):
            panel = self.getPanel(xml='<panel id="foo"></panel>')
            self.assertTrue(isinstance(panel, Panel), 'Panel should exist')
            self.assertEqual(panel.id, "foo", 'Panel should have id=foo')

        def testPanelMultipleSearches(self):
            """Extract new search format and multiple searches"""
            #s test common nodes
            d = self.getPanel(xml='''
            <panel>
                <search id="panel_search">
                    <query>search string also</query>
                    <earliest>-15m</earliest>
                    <latest>now</latest>
                </search>
                <search base="panel_search">
                    <query>search postsearch</query>
                </search>
            </panel>
            ''')
            self.assertEqual(len(d.searches), 2)
            self.assertEqual(getattr(d.searches[0], 'searchMode'), 'template')
            self.assertEqual(getattr(d.searches[0], 'searchCommand'), 'search string also')
            self.assertEqual(getattr(d.searches[0], 'id'), 'panel_search')
            self.assertEqual(getattr(d.searches[0], 'latestTime'), 'now')
            self.assertEqual(getattr(d.searches[0], 'earliestTime'), '-15m')
            self.assertEqual(getattr(d.searches[1], 'searchMode'), 'postsearch')
            self.assertEqual(getattr(d.searches[1], 'searchCommand'), 'search postsearch')
            self.assertEqual(getattr(d.searches[1], 'baseSearchId'), 'panel_search')

        def testPanelSavedSearch(self):
            """Extract new search format saved search"""
            d = self.getPanel(xml='''
            <panel>
                <search ref="panel_search"/>
            </panel>
            ''')
            self.assertEqual(len(d.searches), 1)
            self.assertEqual(getattr(d.searches[0], 'searchMode'), 'saved')
            self.assertEqual(getattr(d.searches[0], 'searchCommand'), 'panel_search')

    class CreateRowTests(unittest.TestCase):
        def getRowLxml(self, args='', panels=1):
            xml = getRowXml(args, panels)
            root = et.fromstring(xml)
            return createRowFromXml(root)

        def testCreateRow(self):
            d = self.getRowLxml()
            self.assertTrue(d)
            self.assertEqual(len(d.panels), 1)
            self.assertEqual(
                d.panels[0].panelElements[0].matchTagName, 'single')

        def testRowGrouping(self):
            d = self.getRowLxml(args='grouping="2,1"', panels=3)
            self.assertTrue(d)
            self.assertEqual(len(d.panels), 2)
            self.assertEqual(len(d.panels[0].panelElements), 2)
            self.assertEqual(len(d.panels[1].panelElements), 1)

        def testRowId(self):
            d = self.getRowLxml(args='id="foo"')
            self.assertTrue(d)
            self.assertEqual(d.id, "foo", "Row Id should be foo")

        def testCreateRowWith3Panels(self):
            d = self.getRowLxml(args='', panels=3)
            self.assertTrue(d)
            self.assertEqual(len(d.panels), 3)

        def testCreateRowWithPanels(self):
            xml = '''
                    <row>
                        <panel>
                            <single/>
                        </panel>
                    </row>
                '''
            root = et.fromstring(xml)
            d =  createRowFromXml(root)
            self.assertTrue(d)
            self.assertEqual(len(d.panels), 1)
            self.assertEqual(
                d.panels[0].panelElements[0].matchTagName, 'single')

        def testRowGroupingWithPanels(self):
            xml = '''
                    <row>
                        <panel>
                            <single/>
                            <single/>
                        </panel>
                        <panel>
                            <single/>
                        </panel>
                    </row>
                '''
            root = et.fromstring(xml)
            d =  createRowFromXml(root)
            self.assertTrue(d)
            self.assertEqual(len(d.panels), 2)
            self.assertEqual(len(d.panels[0].panelElements), 2)
            self.assertEqual(len(d.panels[1].panelElements), 1)

        def testCreateRowWithComments(self):
            xml = '''
                    <row>
                        <!-- this better work -->
                        <panel/>
                    </row>
                '''
            root = et.fromstring(xml)
            row =  createRowFromXml(root)
            xml = '''
                    <row>
                        <!-- this better work -->
                        <chart/>
                    </row>
                '''
            root = et.fromstring(xml)
            row =  createRowFromXml(root)

        def testCreateRowWithTitleException(self):
            with self.assertRaises(Exception):
                xml = '''
                        <row>
                            <title/>
                            <panel/>
                        </row>
                    '''
                root = et.fromstring(xml)
                row =  createRowFromXml(root)
            with self.assertRaises(Exception):
                xml = '''
                        <row>
                            <title/>
                            <chart/>
                        </row>
                    '''
                root = et.fromstring(xml)
                row =  createRowFromXml(root)


    class CreateDashboardTests(unittest.TestCase):
        def getSimpleLxml(self, root='dashboard', rows=1, fieldset=''):
            nodes = []
            nodes.append('<%(root)s>')
            nodes.append(fieldset)
            for i in range(0, rows):
                nodes.append(getRowXml())
            nodes.append('</%(root)s>')
            xml = ''.join(nodes)
            xml = xml % {'root': root}
            root = et.fromstring(xml)
            return createDashboardFromXml(root)

        def testCreateDashboard(self):
            d = self.getSimpleLxml()
            self.assertTrue(d)
            self.assertEqual(d.matchTagName, 'dashboard')

        def testCreateForm(self):
            d = self.getSimpleLxml(root='form')
            self.assertTrue(d)
            self.assertEqual(d.matchTagName, 'form')

        def testCreateFormWithFieldset(self):
            fieldset = '''
            <fieldset>
                <input token="foo" searchWhenChanged="True"></input>
                <html></html>
                <shouldntShow></shouldntShow>
            </fieldset>
            '''
            d = self.getSimpleLxml(root='form', fieldset=fieldset)
            self.assertTrue(d)
            self.assertTrue(d.fieldset)
            self.assertEqual(len(d.fieldset), 2)
            self.assertEqual(d.fieldset[0].__class__.__name__, 'TextInput')
            self.assertEqual(d.fieldset[0].searchWhenChanged, True)
            self.assertEqual(d.fieldset[1].matchTagName, 'html')
            self.assertEqual(d.matchTagName, 'form')

        def testCreateUnsupportedRoot(self):
            with self.assertRaises(Exception):
                self.getSimpleLxml(root='notFormOrDashboard')

        def testValidationMessages(self):
            msgs = getValidationMessages(et.fromstring('<dashboard></dashboard>'))
            self.assertIsNotNone(msgs)
            self.assertEquals(len(msgs), 0)

            msgs = getValidationMessages(et.fromstring('''
                <dashboard>
                    <row>
                        <table>
                            <drilldown>
                                <set token="foo">...</set>
                                <condition field="bar"></condition>
                            </drilldown>
                        </table>
                    </row>
                </dashboard>
            '''))
            self.assertIsNotNone(msgs)
            self.assertGreater(len(msgs), 0)

            msgs = getValidationMessages(et.fromstring('''
                <dashboard>
                    <row>
                        <table>
                            <drilldown>
                                <set field="bar" token="foo">...</set>
                            </drilldown>
                        </table>
                    </row>
                </dashboard>
            '''))
            self.assertIsNotNone(msgs)
            self.assertGreater(len(msgs), 0)

            msgs = getValidationMessages(et.fromstring('''
                <dashboard>
                    <row>
                        <table>
                            <drilldown>
                                <link field="bar">...</link>
                                <link field="bar">...</link>
                            </drilldown>
                        </table>
                    </row>
                </dashboard>
            '''))
            self.assertIsNotNone(msgs)
            self.assertGreater(len(msgs), 0)

            msgs = getValidationMessages(et.fromstring('''
                <dashboard>
                    <row>
                    </row>
                </dashboard>
            '''))
            self.assertIsNotNone(msgs)
            self.assertGreater(len(msgs), 0)

            msgs = getValidationMessages(et.fromstring('<foobar></foobar>'))
            self.assertIsNotNone(msgs)
            self.assertGreater(len(msgs), 0)

    class ExtractHTMLTests(unittest.TestCase):
        def testExtractEncodedHTML(self):
            self.assertEqual(" foo ", extractHtmlContent(et.fromstring('<html encoded="1"><![CDATA[ foo ]]></html>')))

        def testExtractEmptyHTML(self):
            self.assertEqual('', extractHtmlContent(et.fromstring('<html></html>')))
            self.assertEqual('', extractHtmlContent(et.fromstring('<html/>')))
            self.assertEqual('', extractHtmlContent(et.fromstring('<html id="foobar" />')))

        def testExtractInlineHTML(self):
            self.assertEqual('<h1>test</h1><p>foo</p>', extractHtmlContent(et.fromstring('<html id="foobar"><h1>test</h1><p>foo</p></html>')))

    loader = unittest.TestLoader()
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        loader.loadTestsFromTestCase(CreatePanelElementTests),
        loader.loadTestsFromTestCase(_findPrimarySearchNodeTests),
        loader.loadTestsFromTestCase(CreateRowTests),
        loader.loadTestsFromTestCase(CreateDashboardTests),
        loader.loadTestsFromTestCase(CreatePanelTests),
        loader.loadTestsFromTestCase(ExtractHTMLTests)
    ]))
