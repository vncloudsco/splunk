from __future__ import absolute_import
from builtins import object

import logging

from future.moves.urllib import parse as urllib_parse

import lxml.etree as et
import lxml.html
import defusedxml.lxml as safe_lxml
import cherrypy

import splunk.entity as en
import splunk.util
import splunk.appserver.mrsparkle
import splunk.appserver.mrsparkle.lib.config as config
import splunk.appserver.mrsparkle.lib.util as util

logger = logging.getLogger('splunk.appserver.lib.appnav')

# define path to get current app view organization data
NAV_ENTITY_CLASS = 'data/ui/nav'
NAV_ENTITY_NAME = 'default'
NAV_ALT_ENTITY_NAME_S = 'default-%s'
NAV_CLASS_FREE = 'free'

DEFAULT_DISPLAYVIEW = 'flashtimeline'
LITE_DEFAULT_APP = 'search'
LINK_NODE_URI_SCHEME_WHITELIST = ['http', 'https', 'mailto', '']

def getAppNav(app, viewManifest, searches):
    '''
    A utility function that uses the AppNav object and returns
    a tuple with the nav tree and the default view. This is the same ouput
    as the old view.py getAppNav function
    '''
    visibleViews = {} #viewManifest #[view for view in viewManifest if viewManifest[view].get('isVisible')]
    for view in viewManifest:
        if viewManifest[view].get('isVisible'):
            visibleViews[view] = viewManifest[view]
    appNavObj = AppNav(app, viewManifest=visibleViews, searches=searches)
    nav = appNavObj.getNav()
    defaultView = appNavObj.getDefaultView()
    color = appNavObj.getNavColor()
    return (nav, defaultView, color)

class AppNav(object):
    '''
    Instantiate an AppNav object in order to parse information from nav XML
    and build a fleshed out navigation hierarchy
    '''

    # inputs
    app = None
    viewManifest = None
    searches = None

    # data from splunkd entity
    _navDefinitionXML = None

    # outputs
    _nav = None
    _defaultView = None
    _navColor = None

    def __init__(self, app, viewManifest=None, searches=None, navData=None):
        self.app = app

        if util.isLite():
            appList = splunk.auth.getUserPrefsGeneral('app_list')
            taList  = splunk.auth.getUserPrefsGeneral('ta_list')
            # allow TA's in the TA List to open it's Nav
            if (appList and app not in appList) and (taList and app not in taList):
                self.app = LITE_DEFAULT_APP

        if viewManifest != None:
            self.viewManifest = viewManifest
        if searches != None:
            self.searches = searches
        if navData != None:
            self._navDefinitionXML = self._parseNavDefinitionXML(navData)

    def getNav(self):
        if self._nav != None:
            return self._nav

        self._buildNav()
        return self._nav

    def getDefaultView(self):
        if self._defaultView != None:
            return self._defaultView

        self._buildNav()
        return self._defaultView

    def getNavColor(self):
        if self._navColor != None:
            return self._navColor

        navDefinitionXML = self._getNavDefinitionXML()
        if navDefinitionXML is not None:
            # check for specification of navColor in the root node
            self._navColor = navDefinitionXML.get('color')
            return self._navColor
        else:
            return None

    def _getViewManifest(self):
        if self.viewManifest != None:
            return self.viewManifest

        self.viewManifest = {}
        try:
            views = en.getEntities('data/ui/views', namespace=self.app, count=-1, digest=1, search='isVisible=1')
            for view in views:
                self.viewManifest[view]= {
                    'label':views.get(view, {}).get('label', view),
                    'isVisible':views.get(view, {}).get('isVisible', 1),
                    'isDashboard':views.get(view, {}).get('isDashboard', 1),
                    'name':view,
                    'app':views.get(view, {}).get('eai:acl', {}).get('app', "")
                    }
        except splunk.ResourceNotFound:
            logger.warn('Unable to retrieve current views')

        return self.viewManifest

    def _getSearches(self):
        if self.searches != None:
            return self.searches

        try:
            # Customers with 3k+ savedsearches run into high cpu and memory usage
            # Maximum count is recommended to be at 500.
            fetchCount = config.getConfig(sessionKey=cherrypy.session.get('sessionKey'), namespace=None).get('APP_NAV_REPORTS_LIMIT') or 500
            self.searches = en.getEntities('saved/searches', namespace=self.app, search='is_visible=1 AND disabled=0', count=fetchCount, _with_new='1')
            if '_new' in self.searches:
                del self.searches['_new']
        except splunk.ResourceNotFound:
            logger.warn('Unable to retrieve current saved searches')
            self.searches = {}
        return self.searches

    def _getNavDefinitionXML(self):
        if self._navDefinitionXML is not None:
            return self._navDefinitionXML

        navDefinition = None
        navAltClass = None

        # set alternate class
        if cherrypy.config.get('is_free_license'):
            navAltClass = NAV_CLASS_FREE

        # try alternate nav
        if navAltClass:
            try:
                navDefinition = en.getEntity(NAV_ENTITY_CLASS, NAV_ALT_ENTITY_NAME_S % NAV_CLASS_FREE, namespace=self.app)
            except splunk.ResourceNotFound:
                pass

        # if no alt, then proceed with default
        if not navDefinition:
            try:
                navDefinition = en.getEntity(NAV_ENTITY_CLASS, NAV_ENTITY_NAME, namespace=self.app)
            except splunk.ResourceNotFound:
                logger.warn('"%s" app does not have a navigation configuration file defined.' % self.app) # TK mgn 06/19/09
            except Exception as e:
                logger.exception(e)
                raise

        # parse the XML
        self._navDefinitionXML = self._parseNavDefinitionXML(navDefinition)

        return self._navDefinitionXML

    def _parseNavDefinitionXML(self, navDefinition):
        navDefinitionXML = None
        try:
            parser = et.XMLParser(remove_blank_text=True)
            navDefinitionXML = safe_lxml.fromstring(navDefinition['eai:data'], parser=parser)
        except et.XMLSyntaxError as e:
            logger.error('Invalid app nav XML encountered: %s' % e)
        except Exception as e:
            logger.error('Unable to parse nav XML for app=%s; %s' % (self.app, e))
        return navDefinitionXML

    def _buildNav(self):
        viewManifest = self._getViewManifest()
        navDefinitionXML = self._getNavDefinitionXML()
        output = []

        # if application has nav defined
        if navDefinitionXML is not None:

            # empty nav means don't do anything; omitted nav is treated down below
            if len(navDefinitionXML) == 0:
                return output

            self._replaceNavTokens(navDefinitionXML, viewManifest)
            output = self._decorateNavItems(navDefinitionXML, viewManifest, self.app)

            # check for the default view; if no default set, pick the first
            # view listed in nav; if none, try to get first in manifest
            defaultNodes = navDefinitionXML.xpath('//view[@default]')
            for node in defaultNodes:
                if splunk.util.normalizeBoolean(node.get('default')):
                    defaultView = node.get('name')
                    break
            else:
                fallbackNodes = navDefinitionXML.xpath('//view[@name]')
                for node in fallbackNodes:
                    defaultView = node.get('name')
                    break
                else:
                    defaultView = sorted(viewManifest.keys())[0]


        # otherwise dump all views into a generic menu
        else:
            logger.warn('Unable to process navigation configuration for app "%s"; using defaults.' % self.app) # TK mgn 06/19/09
            DEFAULT_VIEW_COLLECTION = 'Default Views'
            output.append({
                'label': DEFAULT_VIEW_COLLECTION,
                'submenu': [
                    {'label': _(viewManifest[name]['label']), 'uri': name}
                    for name
                    in sorted(viewManifest)
                ]
            })

            defaultView = DEFAULT_DISPLAYVIEW

        self._nav = output
        self._defaultView = defaultView

    def _replaceNavTokens(self, navDefinitionXML, viewManifest):
        '''
        Inserts the proper view and saved search items as required by the XML
        nodes placed into the nav XML data.  Modified the 'navDefinitionXML' lxml
        node in-place.

        The XML nodes currently recognized are:
            <view source="unclassified" />
            <view source="all" />
        '''

        # get a list of explicitly marked views and saved searches
        searches = None
        markedViews = []
        for node in navDefinitionXML.xpath('//view[@name]'):
            markedViews.append(node.get('name'))

        markedSaved = []
        for node in navDefinitionXML.xpath('//saved[@name]'):
            if searches is None:
                searches = self._getSearches()

            if node.get('name') in searches:
                savedSearch = searches[node.get('name')]
                node.set('uri', savedSearch.getLink('alternate'))
                node.set('sharing', savedSearch.get('eai:acl', {}).get('sharing'))
                markedSaved.append(node.get('name'))
            else:
                node.getparent().remove(node)
        #
        # handle views
        # identify the <view source="" /> nodes and fill in with views
        #
        for node in navDefinitionXML.xpath('//view[@source]'):
            source = node.get('source')
            match  = node.get('match', '').lower()

            if source == 'all':
                for viewName in sorted(viewManifest):
                    if match and viewName.lower().find(match) == -1:
                        continue
                    if not splunk.util.normalizeBoolean(viewManifest.get(viewName, {}).get('isDashboard')):
                        continue
                    linkNode = et.Element('view')
                    linkNode.set('name', viewName)
                    node.addprevious(linkNode)

            elif source == 'unclassified':
                for viewName in sorted(viewManifest):
                    if (viewName in markedViews) or (match and viewName.lower().find(match) == -1):
                        continue
                    if not splunk.util.normalizeBoolean(viewManifest.get(viewName, {}).get('isDashboard')):
                        continue

                    viewEntry = viewManifest.get(viewName, {}).get('viewEntry', None)

                    if viewEntry != None:
                        version = viewEntry.get('version', '0')
                        rootNode = viewEntry.get('rootNode', '')
                        if rootNode == 'dashboard' and version == '2':
                            # APPLAT-4226: Don't show v2 dashboards in the menu.
                            continue

                    linkNode = et.Element('view')
                    linkNode.set('name', viewName)
                    node.addprevious(linkNode)
                    if match:
                        markedViews.append(viewName)
            else:
                logger.warn('Unable to process view item; unknown source: %s' %  source)

            node.getparent().remove(node)

        #
        # handle saved searches
        # identify the <saved source="" /> nodes and fill in with the proper
        # saved search items; allow matching on name substring
        #
        for node in navDefinitionXML.xpath('//saved[@source]'):
            if searches is None:
                searches = self._getSearches()

            source = node.get('source', '').lower()
            match = node.get('match', '').lower()

            if source == 'all':
                keys = splunk.util.objUnicode(list(searches.keys()))
                for savedName in sorted(keys, key=splunk.util.unicode.lower):
                    if match and savedName.lower().find(match) == -1:
                        continue
                    savedNode = et.Element('saved')
                    savedNode.set('name', savedName)
                    savedNode.set('uri', searches[savedName].getLink("alternate"))
                    savedNode.set('sharing', searches[savedName].get('eai:acl', {}).get('sharing'))
                    dispatch_view = searches[savedName].get('request.ui_dispatch_view')
                    if dispatch_view:
                        savedNode.set('dispatchView', dispatch_view)
                    if node.get('view'):
                        savedNode.set('view', node.get('view'))
                    node.addprevious(savedNode)

            elif source == 'unclassified':
                keys = splunk.util.objUnicode(list(searches.keys()))
                for savedName in sorted(keys, key=splunk.util.unicode.lower):
                    if savedName not in markedSaved:
                        if match and savedName.lower().find(match) == -1:
                            continue
                        savedNode = et.Element('saved')
                        savedNode.set('name', savedName)
                        savedNode.set('uri', searches[savedName].getLink("alternate"))
                        savedNode.set('sharing', searches[savedName].get('eai:acl', {}).get('sharing'))
                        dispatch_view = searches[savedName].get('request.ui_dispatch_view')
                        if dispatch_view:
                            savedNode.set('dispatchView', dispatch_view)
                        if node.get('view'):
                            savedNode.set('view', node.get('view'))
                        node.addprevious(savedNode)
                        if match:
                            markedSaved.append(savedName)

            else:
                logger.warn('Unable to process saved search item; unknown source: %s' % source)

            node.getparent().remove(node)

    def _decorateNavItems(self, branch, viewManifest, app):
        '''
        Rewrites the incoming nav definition by decorating view names with
        proper links, and saved searches as views with search name specified.
        This recursive method is used by getAppNav().

        Input Example:
            <nav>
                <collection label="Dashboards">
                    <a href="http://google.com">Google</a>
                </collection>
                <collection label="Views">
                    <view source="all" />
                </collection>
                <collection label="Saved Searches" sort="alpha">
                    <collection label="Recent Searches">
                        <saved source="recent" />
                    </collection>
                    <saved name="All firewall errors" />
                    <divider />
                </collection>
            </nav>

        Output Example:


        '''

        output = []
        for node in branch:
            # update the view nodes with the proper links and labels
            if node.tag == 'view':
                viewData = viewManifest.get(node.get('name'))
                if viewData:
                    if viewData['isVisible']:
                        output.append({
                            'viewName': node.get('name'),
                            'label': _(viewData.get('label')),
                            'uri': util.make_url(['app', app, node.get('name', '')])
                        })
                else:
                    logger.warn(_('An unknown view name \"%(view)s\" is referenced in the navigation definition for \"%(app)s\".') % {'view': node.get('name'), 'app': app})

            # update saved searches and point them to the saved search redirector
            elif node.tag == 'saved':
                if node.get('view'):
                    uri = util.make_url(
                        ['app', app, node.get('view')],
                        {'s': node.get('uri')}
                    )
                else:
                    uri = util.make_url(
                        ['app', app, '@go'],
                        {'s': node.get('uri')}
                    )
                reportUri = util.make_url(
                        ['app', app, 'report'],
                        {'s': node.get('uri')}
                    )
                searchDict = {
                    'label': node.get('name'),
                    'uri': uri,
                    'reportUri': reportUri,
                    'sharing': node.get('sharing', None)
                    }
                if node.get('dispatchView'):
                    searchDict['dispatchView'] = node.get('dispatchView')
                output.append(searchDict)

            elif node.tag == 'a':
                uri = node.get('href')

                if uri.startswith('/'):
                    uri = util.make_url(uri)

                (isAllowed, uriScheme) = self._isAllowedUriScheme(uri)
                if not isAllowed:
                    logger.warning("Prohibited scheme specified for link node in nav definition. app='%s' label='%s'. scheme='%s' not in whitelist=%s" % (app, node.text, uriScheme, LINK_NODE_URI_SCHEME_WHITELIST))
                    continue

                anchor = {
                    'label': _(node.text),
                    'uri': uri
                }
                if node.get('target') == '_blank':
                    anchor['external'] = True
                output.append(anchor)

            elif node.tag == 'divider':
                output.append({
                    'label': '------',
                    'uri': '#',
                    'divider': 'actionsMenuDivider'
                })

            elif node.tag == 'collection':
                subcollection = {
                    'label': _(node.get('label')),
                    'submenu': self._decorateNavItems(node, viewManifest, app)
                }

                # only show submenu if it contains something
                if len(subcollection['submenu']) > 0:
                    output.append(subcollection)

        if self.isEmpty(output):
            return []

        return output

    def isEmpty(self, nav):
        for el in nav:
            if not 'divider' in el:
                return False
        return True

    def _isAllowedUriScheme(self, uri):
        # pylint: disable=E1101
        uri = uri.strip()

        # we allow empty uri
        if uri is None or len(uri) == 0:
            return (True, "")

        # need to remove all whitespace from uri, even if html-encoded
        uri = lxml.html.fromstring(uri).text

        # we are not preventing an HTML element without inner text
        if uri is None or len(uri) == 0:
            return (True, "")

        uri = "".join(uri.split())

        # whitelist uri scheme to make sure no malicious hrefs make their way in
        uriParts = urllib_parse.urlparse(uri)
        if not uriParts.scheme.lower() in LINK_NODE_URI_SCHEME_WHITELIST:
            return (False, uriParts.scheme)

        return (True, uriParts.scheme)

# tests
if __name__ == '__main__':

    import unittest
    class UriSchemeProhibitionTest(unittest.TestCase):

        def testAllowed(self):
            allowedUris = [ "http://google.com",
                            "https://google.com",
                            "otherview",
                            "/app/otherapp/otherview",
                            "/manager/otherapp/otherview",
                            "mailto:arobbins@splunk.com",
                            " ",
                            "<a>",
                            "&lt;a&gt;" ]

            appnav = AppNav("test")
            for uri in allowedUris:
                (allowed, scheme) = appnav._isAllowedUriScheme(uri)
                self.assertEquals(allowed, True)

        def testProhibited(self):
            prohibitedUris = [  "javascript:alert('HACKED!');",
                                " javascript:alert('HACKED!');",
                                "javascript:alert('HACKED!'); ",
                                "java&#09;script&#09;:alert('HACKED!');",
                                "java&#13;script&#13;:alert('HACKED!');" ]

            appnav = AppNav("test")
            for uri in prohibitedUris:
                (allowed, scheme) = appnav._isAllowedUriScheme(uri)
                self.assertEquals(allowed, False)

    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(UriSchemeProhibitionTest))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
