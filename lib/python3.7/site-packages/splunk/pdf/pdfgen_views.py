from __future__ import absolute_import
from builtins import object

import copy

import lxml.etree as et
from lxml.html import fromstring, tostring

from splunk.pdf.pdfgen_search import InlineSearchManager, SavedSearchManager, PostProcessSearchManager
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field
from splunk.models.view_escaping.base import STRING_SEARCH_MODE, TEMPLATE_SEARCH_MODE, SAVED_SEARCH_MODE, \
    POST_SEARCH_MODE
from splunk.models.view_escaping.fromdash import createDashboardFromXml, createPanelFromXML, createSearchFromSearchXml
from splunk.models.view_escaping.cleanhtml import cleanHtmlMarkup

import splunk.search.Parser as Parser
from splunk.util import normalizeBoolean, toDefaultStrings
import splunk.util
from splunk import ResourceNotFound, SearchException
import splunk.pdf.pdfgen_utils as pu


logger = pu.getLogger()

class AbstractViewType(object):
    # data describing associated search and search job
    search = None
    _viewStateDict = None
    _namespace = None
    _owner = None
    _sessionKey = None
    _searchFieldList = []
    _fieldFormats = {}

    def __init__(self):
        self._error = None
        self._searchError = None

    def dispatchSearch(self, overrideNowTime=None, maxRowsPerTable=None, stripLeadingSearchCommand=False):
        """ dispatch the view's search, returns true if successful """
        if self.search is not None:
            try:
                kwargs = dict(overrideNowTime=overrideNowTime, stripLeadingSearchCommand=stripLeadingSearchCommand)
                if 'maxRowsPerTable' in kwargs and all(view == 'event' for view in self.getRenderTypes()):
                    kwargs['maxRowsPerTable'] = maxRowsPerTable
                logger.debug('Dispatching %s with args %s', self.search, kwargs)
                self.search.dispatch(**kwargs)
                return self.search.job is not None
            except SearchException as e:
                self._searchError = str(e)

    def setSearchJobObj(self, job):
        if self.search is not None:
            logger.debug("Applying existing search job sid=%s to view", job.id)
            self.search.setJob(job)

    def getViewIndex(self):
        """ return the view index, for reports, always return 0, for dashboard panels,
            return the sequence number """
        return 0

    def requiresSearchJobObj(self):
        nonSearchRenderTypes = ('html',)
        types = self.getRenderTypes()
        logger.debug("requiresSearchJobObj types = %s, nonSearchRenderTypes = %s" % (types, nonSearchRenderTypes))

        for type in types:
            if type in nonSearchRenderTypes:
                continue
            return True
        return False

    def getSearchJobObj(self):
        return self.search.job if self.search is not None else None

    def getSearchJobResults(self):
        return self.search.results()

    def getSearchJobFeed(self, feedCount = None):
        kwargs = dict()
        if feedCount is not None:
            kwargs['count'] = feedCount
        return self.search.feed(**kwargs)

    def getSearchJobEvents(self):
        return self.search.events()

    def isRealtime(self):
        return self.search.isRealtime()

    def isSearchComplete(self):
        return self.search.isComplete()

    def touchSearchJob(self):
        if self.search is not None:
            self.search.touch()

    def cancelSearch(self):
        self.search.cancel()

    def getRenderTypes(self):
        """ returns array of types
            type: 'chart', 'table', 'events', 'map', 'single'
        """
        return []

    def getRenderParams(self):
        return {}

    def getChartProps(self):
        props = {}

        if self._viewStateDict != None:
            props.update(pu.mapViewStatePropsToJSChartProps(self._viewStateDict))

        return props

    def getMapProps(self):
        return {}

    def getSingleValueProps(self):
        return {}

    def getOptions(self):
        options = {'displayRowNumbers': 'false'}

        if self._viewStateDict != None:
            options.update(pu.mapViewStatePropsToJSChartProps(self._viewStateDict))

        return options

    def getSearchFieldList(self):
        return self._searchFieldList

    def getFieldFormats(self):
        return self._fieldFormats

    def getTitle(self):
        return None

    def getSubtitle(self):
        return None

    def getDescription(self):
        return None

    def debugOut(self):
        debugMsg = str(self) + ": "
        debugMsg += "searchFieldList: " + str(self.getSearchFieldList())
        return debugMsg

    def hasError(self):
        return self._error is not None

    def getError(self):
        return self._error

    def hasSearchError(self):
        return self._searchError is not None

    def getSearchError(self):
        return self._searchError

_VIEW_ENTITY_CLASS = 'data/ui/views'

class DashboardEntity(SplunkAppObjModel):
    """
    A dashboard definition which is retrieved using the /data/ui/views endpoint
    """
    resource = 'data/ui/views'
    data = Field('eai:data')

class PanelEntity(SplunkAppObjModel):
    """
    A reusable panel definition which is retrieved using the /data/ui/panels endpoint
    """
    resource = 'data/ui/panels'
    data = Field('eai:data')

def getDashboardTitleAndPanels(dashboard_name, namespace, owner, sessionKey):
    dashboard_id = DashboardEntity.build_id(name=dashboard_name, namespace=namespace, owner=owner)
    dashboard = DashboardEntity.get(dashboard_id, sessionKey=sessionKey)
    return getDashboardTitleAndPanelsFromXml(dashboard.data, namespace, owner, sessionKey)


def fetchPanelXML(panel_ref, namespace, owner, sessionKey):
    panel_id = PanelEntity.build_id(panel_ref, namespace, owner)
    panel = PanelEntity.get(panel_id, sessionKey=sessionKey)
    return panel.data


def getDashboardTitleAndPanelsFromXml(dashboardXml, namespace, owner, sessionKey):
    dashboard = createDashboardFromXml(et.fromstring(splunk.util.toUTF8(dashboardXml)), sourceApp=namespace)
    panels = []

    for panel in dashboard.all_panels():
        if panel.ref:
            try:
                panelNode = et.fromstring(fetchPanelXML(panel.ref, panel.app or namespace, owner, sessionKey))
                # parse the search node in ref-panel
                for searchNode in panelNode.findall('search'):
                    search = createSearchFromSearchXml(searchNode)
                    if search:
                        dashboard.searches.append(search)
                panels.append(createPanelFromXML(panelNode, sourceApp=namespace))
            except ResourceNotFound:
                # append the error message directly which will be pick up later
                panels.append("Dashboard panel ""%s"" not found." % panel.ref)
        else:
            panels.append(panel)

    panelList = []

    def add_element(props, search, error=None):
        logger.debug('Adding element %s', props)
        panelElement = DashboardPanel(props, search, len(panelList), namespace, owner, sessionKey)
        if error:
            panelElement._error = error
        panelList.append(panelElement)

    searchMap = dict()
    managerMap = dict()
    for search, _ in dashboard.all_searches():
        if search.id is not None:
            searchMap[search.id] = search

    for panel in panels:
        if isinstance(panel, str):
            add_element({}, None, error=panel)
            continue
        for element in panel.panelElements:
            if element.matchTagName == 'html':
                extractHtmlContent(namespace, element)
            elementDict, search = createElementDictAndSearch(element, panel, searchMap, managerMap, namespace, owner,
                                                             sessionKey)
            if elementDict is not None:
                add_element(elementDict, search)

    return dashboard.label, dashboard.description, panelList


def extractHtmlContent(namespace, element):
    try:
        if 'rawcontent' in element.options and element.options['rawcontent']:
            element.options['rawcontent'] = toDefaultStrings(tostring(fromstring(cleanHtmlMarkup(element.options['rawcontent'])), encoding='utf-8', method='xml'))
        elif 'serverSideInclude' in element.options and element.options['serverSideInclude']:
            src = element.options['serverSideInclude']
            try:
                src = pu.getAppStaticResource(namespace, src)
                fh = None
                try:
                    fh = open(src, 'r')
                    output = fh.read()
                except Exception as e:
                    output = "HTML File %s not found" % element.options['serverSideInclude']
                    logger.error('failed to read html file, error %s' % e)
                finally:
                    if fh:
                        fh.close()
            except Exception as e:
                output = e.args[0]
                logger.error('File "%s" is out of scope' % src)

            output = "<html>%s</html>" % cleanHtmlMarkup(output)
            element.options['rawcontent'] = toDefaultStrings(tostring(fromstring(output), encoding='utf-8', method='xml'))
    except Exception as ex:
        logger.warn('failed to extract xml content, error %s' % ex)
        element.options['rawcontent'] = ""



def createElementDictAndSearch(element, panel, searchMap, managerMap, namespace, owner, sessionKey):
    result = dict(
        type=element.matchTagName
    )

    if panel.title is not None:
        result['title'] = panel.title
        result['subtitle'] = element.title
    else:
        result['title'] = element.title or ""

    result['options'] = element.options
    if hasattr(element, 'searchFieldList') and element.searchFieldList is not None and len(element.searchFieldList) > 0:
        result['searchFieldList'] = element.searchFieldList

    if hasattr(element, 'fieldFormats') and len(element.fieldFormats) > 0:
        result['fieldFormats'] = element.fieldFormats

    search = createSearchManager(element.search, searchMap, managerMap, namespace, owner,
                                 sessionKey) if element.hasSearch else None
    return result, search


def createSearchManager(searchObj, searchMap, managerMap, namespace, owner, sessionKey):
    mgr = None
    if searchObj is None:
        return mgr
    # provide default value for default tokens
    if searchObj.earliestTime is not None and searchObj.earliestTime == '$earliest$':
        searchObj.earliestTime = '0'
    if searchObj.latestTime is not None and searchObj.latestTime == '$latest$':
        searchObj.latestTime = ''

    mode = searchObj.searchMode
    if mode in (STRING_SEARCH_MODE, TEMPLATE_SEARCH_MODE):
        mgr = InlineSearchManager(searchObj.searchCommand, searchObj.earliestTime, searchObj.latestTime,
                                  namespace=namespace, owner=owner, sessionKey=sessionKey, sampleRatio=searchObj.sampleRatio)
    elif mode == SAVED_SEARCH_MODE:
        mgr = SavedSearchManager(searchObj.searchCommand,
                                 earliestTime=searchObj.earliestTime, latestTime=searchObj.latestTime,
                                 namespace=namespace, owner=owner, sessionKey=sessionKey)
    elif mode == POST_SEARCH_MODE:
        ref = searchObj.baseSearchId
        parent = managerMap[ref] if ref in managerMap else createSearchManager(searchMap.get(ref), searchMap,
                                                                               managerMap, namespace=namespace,
                                                                               owner=owner, sessionKey=sessionKey)
        if parent is None:
            logger.error('Parent search ref=%s for search=%s not found', ref, searchObj.id)
        else:
            mgr = PostProcessSearchManager(searchObj.searchCommand, parent, namespace=namespace, owner=owner,
                                       sessionKey=sessionKey)

    logger.debug('Created search manager %s', mgr)
    return mgr


class DashboardPanel(AbstractViewType):
    _panelDict = {}
    _sequenceNum = 0

    def __init__(self, panelDict, search, sequenceNum, namespace, owner, sessionKey):
        AbstractViewType.__init__(self)
        self.search = search
        self._namespace = namespace
        self._owner = owner
        self._sessionKey = sessionKey
        self._panelDict = copy.deepcopy(panelDict)
        self._sequenceNum = sequenceNum
        logger.debug("DashboardPanel::__init__> sequenceNum: " + str(self._sequenceNum) + ", panelDict: " + str(self._panelDict))

        if 'searchFieldList' in panelDict:
            self._searchFieldList = panelDict['searchFieldList']
        if 'fieldFormats' in panelDict:
            self._fieldFormats = panelDict['fieldFormats']

        if search is None or (isinstance(search, InlineSearchManager) and not search.resolve()):
            self._searchError = 'No search provided'
        elif isinstance(search, SavedSearchManager):
            try:
                self._viewStateDict = pu.getViewStatePropsFromSavedSearchModel(search.model(), namespace=namespace,
                                                                           owner=owner, sessionKey=sessionKey)
            except ResourceNotFound as e:
                self._searchError = 'saved search not found: "%s"' % self.search.searchName
                logger.error('saved_search %s not found, error %s' % (self.search.searchName, e))


    def dispatchSearch(self, **kwargs):
        newargs = dict()
        newargs.update(kwargs)
        newargs['stripLeadingSearchCommand'] = True
        return super(DashboardPanel, self).dispatchSearch(**newargs)

    def getViewIndex(self):
        return self._sequenceNum

    def getRenderTypes(self):
        return [self._panelDict['type']]

    def getChartProps(self):
        # Layer in charting properties from
        # 1. the viewstate (super call)
        # 2. the report viz properties and
        # 3. options defined in the XML
        props = super(DashboardPanel, self).getChartProps()
        if isinstance(self.search, SavedSearchManager):
            props.update(pu.getChartingPropsFromSavedSearchModel(self.search.model()))
        if 'options' in self._panelDict:
            props.update(pu.mapDashboardPanelOptionsToJSChartProps(self._panelDict['options']))

        return props

    def getMapProps(self):
        props = super(DashboardPanel, self).getMapProps()
        if 'options' in self._panelDict:
            mappingProps = {key.replace("mapping.", ""):value for key, value in self._panelDict['options'].items() if key.startswith("mapping")}
            props.update(mappingProps)

        logger.debug("map props: %s, options: %s" % (props, self._panelDict))
        return props

    def getSingleValueProps(self):
        singleValueProps = {}
        if 'options' in self._panelDict:
            singleValueOptions = self._panelDict['options']
            for key, value in singleValueOptions.items():
                singleValueProps['display.visualizations.singlevalue.' + key] = value
        return singleValueProps

    def getTitle(self):
        return self._panelDict['title']

    def getSubtitle(self):
        return self._panelDict.get('subtitle', None)

    def getDescription(self):
        return None

    def getOptions(self):
        options = super(DashboardPanel, self).getOptions()

        if 'options' in self._panelDict:
            if 'rowNumbers' in self._panelDict['options']:
                options['displayRowNumbers'] = self._panelDict['options']['rowNumbers']
            options.update(self._panelDict['options'])

        if hasattr(self.search, 'model'):
            options.update(pu.getTrellisPropsFromSavedSearchModel(self.search.model()))

        return options

class Report(AbstractViewType):
    _savedSearchName = None
    _savedSearchModel = None
    _useViewState = False
    _isTransformingSearch_memo = None

    def __init__(self, savedSearchName, namespace=None, owner=None, sessionKey=None):
        AbstractViewType.__init__(self)
        self._namespace = namespace
        self._owner = owner
        self._sessionKey = sessionKey
        self.search = SavedSearchManager(savedSearchName, namespace=namespace, owner=owner, sessionKey=sessionKey)
        self._viewStateDict = pu.getViewStatePropsFromSavedSearchModel(self.search.model(), namespace=namespace,
                                                                       owner=owner, sessionKey=sessionKey)

        self._savedSearchName = savedSearchName
        self._savedSearchModel = self.search.model()
        logger.debug("Report::init> _savedSearchModel.ui.display_view: " + str(self._savedSearchModel.ui.display_view))
        logger.debug("Report::init> _viewStateDict: " + str(self._viewStateDict))

    def getRenderTypes(self):
        """ determine which render types to use for the report
        """
        if self._isTransformingSearch():
            showViz = normalizeBoolean(self._savedSearchModel.entity.get("display.visualizations.show", True))
            if showViz:
                reportVizType = self._savedSearchModel.entity.get("display.visualizations.type", "charting")
                renderVizType = None
                if reportVizType == "mapping":
                    renderVizType = 'map'
                elif reportVizType == "singlevalue":
                    renderVizType = 'single'
                else:
                    renderVizType = 'chart'
                return [renderVizType, 'table']
            else:
                return ['table']
        else:
            return ['event']

    def _isTransformingSearch(self):
        if self._isTransformingSearch_memo is not None:
            return self._isTransformingSearch_memo

        searchStr = self._savedSearchModel.search
        if not searchStr.strip().startswith(u'|'):
            searchStr = u'search ' + searchStr
        parsedSearch = Parser.parseSearch(str(searchStr), parseOnly='f', sessionKey=self._sessionKey, namespace=self._namespace, owner=self._owner)
        searchProps = parsedSearch.properties.properties

        self._isTransformingSearch_memo = "reportsSearch" in searchProps
        return self._isTransformingSearch_memo

    def getChartProps(self):
        chartProps = {}

        if self._viewStateDict is None:
            chartProps = pu.getChartingPropsFromSavedSearchModel(self._savedSearchModel)
        else:
            chartProps = pu.mapViewStatePropsToJSChartProps(self._viewStateDict)

        logger.debug("chartProps = %s" % chartProps)

        return chartProps

    def getMapProps(self):
        mapProps = pu.getMapPropsFromSavedSearchModel(self._savedSearchModel)
        logger.debug("mapProps = %s" % mapProps)
        return mapProps

    def getSingleValueProps(self):
        singleValueProps = self._savedSearchModel.entity
        logger.debug("singleValueProps = %s" % singleValueProps)
        return singleValueProps

    def getOptions(self):
        options = {'displayRowNumbers': 'true'}

        if self._isTransformingSearch():
            options.update(self.getTableProps())
        else:
            options.update(self.getEventProps())

        options.update(pu.getTrellisPropsFromSavedSearchModel(self._savedSearchModel))

        return options

    def getEventProps(self):
        eventProps = {}

        if self._viewStateDict is None:
            eventProps = pu.getEventPropsFromSavedSearchModel(self._savedSearchModel)
        else:
            eventProps = pu.mapViewStatePropsToJSChartProps(self._viewStateDict)

        logger.debug("eventProps = %s" % eventProps)

        return eventProps

    def getTableProps(self):
        tableProps = {}

        if self._viewStateDict is None:
            tableProps = pu.getTablePropsFromSavedSearchModel(self._savedSearchModel)
        else:
            tableProps = pu.mapViewStatePropsToJSChartProps(self._viewStateDict)

        logger.debug("tableProps = %s" % tableProps)

        return tableProps

    def getTitle(self):
        title = None
        if self._viewStateDict != None and "ChartTitleFormatter" in self._viewStateDict:
            if "default" in self._viewStateDict["ChartTitleFormatter"]:
                title = self._viewStateDict["ChartTitleFormatter"]["default"]
        else:
            title = self._savedSearchName

        return title

    def getDescription(self):
        return pu.getDescriptionFromSavedSearchModel(self._savedSearchModel)

class SearchReport(AbstractViewType):
    _search = None
    _title = None

    def __init__(self, search, et='', lt='', title='Splunk search results',  namespace=None, owner=None, sessionKey=None):
        AbstractViewType.__init__(self)
        self._namespace = namespace
        self._owner = owner
        self._sessionKey = sessionKey
        self.search = InlineSearchManager(search, et, lt, namespace=namespace, owner=owner, sessionKey=sessionKey)
        self._title = title

    def getRenderTypes(self):
        searchStr = self.search.resolve()
        if not searchStr.strip().startswith(u'|'):
            searchStr = u'search ' + searchStr
        parsedSearch = Parser.parseSearch(str(searchStr), parseOnly='f', sessionKey=self._sessionKey, namespace=self._namespace, owner=self._owner)
        searchProps = parsedSearch.properties.properties
        logger.debug("searchProps=%s" % searchProps)

        isTransformingSearch = "reportsSearch" in searchProps
        if isTransformingSearch:
            return ['chart', 'table']
        else:
            return ['event']

    def getTitle(self):
        return self._title
