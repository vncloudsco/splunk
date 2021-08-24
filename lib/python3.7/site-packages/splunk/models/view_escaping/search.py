from __future__ import absolute_import
from builtins import object

from splunk.models.view_escaping.base import STRING_SEARCH_MODE, DEFAULT_SEARCH_ID,POST_SEARCH_MODE
from splunk.models.view_escaping.base import SAVED_SEARCH_MODE, TEMPLATE_SEARCH_MODE
from splunk.models.view_escaping.drilldown import parseEventHandler
from splunk.models.view_escaping.tokendeps import parseTokenDeps

class Search(object):

    def __init__(self, searchMode=STRING_SEARCH_MODE, searchCommand="", earliestTime=None, latestTime=None, id=None, base=None, app=None, cache=None, sampleRatio=None, tokenDeps=None, refresh=None, refreshType=None):
        self.searchMode = searchMode
        self.searchCommand = searchCommand
        self.earliestTime = earliestTime
        self.latestTime = latestTime
        self.id = id
        self.baseSearchId = base
        self.app = app
        self.statusBuckets = 0
        self.sampleRatio = sampleRatio
        self.refresh = refresh
        self.refreshType = refreshType
        if self.searchMode == POST_SEARCH_MODE and self.baseSearchId == None:
            self.baseSearchId = DEFAULT_SEARCH_ID
        self.eventHandlers = []
        self.cache = cache
        self.tokenDeps = tokenDeps

    def normalizedSearchCommand(self):
        return self.searchCommand.strip()


def createSearchFromSearchXml(searchNode):
    """
    Parses a search from search, dashboard, panel element xml nodes
    @param searchNode: Lxml representing a form or dashboard element
    @param id: and optional id to force id to
    @return:
    """

    opt = dict()
    base = searchNode.attrib.get('base')
    if searchNode.find('query') is not None:
        opt['searchMode'] = TEMPLATE_SEARCH_MODE
        opt['searchCommand'] = (
            searchNode.findtext('query')).replace("\n", " ").replace("\t", " ")
        sampleRatio = searchNode.findtext('sampleRatio')
        if sampleRatio is not None:
            opt['sampleRatio'] = int(sampleRatio)
    elif searchNode.get('ref') is not None:
        opt['searchMode'] = SAVED_SEARCH_MODE
        opt['searchCommand'] = (
            searchNode.get('ref')).replace("\n", " ").replace("\t", " ")
        if searchNode.get('app') is not None:
            opt['app'] = searchNode.get('app')
        cacheVal = searchNode.findtext('cache')
        if cacheVal:
            opt['cache'] = cacheVal
    elif not base:
        return False
    for nodePair in [('earliest', 'earliestTime'), ('latest', 'latestTime')]:
        nodeVal = searchNode.findtext(nodePair[0])
        if nodeVal:
            opt[nodePair[1]] = nodeVal
    refresh = searchNode.findtext('refresh')
    if refresh is not None:
        opt['refresh'] = refresh
    refreshType = searchNode.findtext('refreshType')
    if refreshType is not None:
        opt['refreshType'] = refreshType
    id = searchNode.attrib.get('id')
    tokenDeps = parseTokenDeps(searchNode)
    if id:
        opt['id'] = id
    if base:
        opt['base'] = base
        opt['searchMode'] = POST_SEARCH_MODE
    if tokenDeps:
        opt['tokenDeps'] = tokenDeps
    search = Search(**opt)
    for evtName in ('progress', 'preview', 'done', 'finalized', 'error', 'fail', 'cancelled'):
        createEventHandlerFromXml(search, searchNode, evtName)
    return search

def createEventHandlerFromXml(search, searchNode, eventName):
    node = searchNode.find(eventName)
    if node is not None:
        search.eventHandlers.append((eventName, parseEventHandler(node, ('any', 'match'))))
