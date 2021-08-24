from __future__ import absolute_import
import lxml.etree as et
import xml.sax.saxutils as su

import splunk.models.legacy_views.base as base
import splunk.util

import logging
logger = logging.getLogger('splunk.models.legacy_views.panel')


def createPanel(name, flashOk=True, forceFlash=False):
    '''
    Factory method for creating an appropriate panel object based upon the
    name.  Returns an instance of a BasePanel subclass, or throws a
    NotImplementedError if no suitable mapper is found.
    
    This method works by inspecting all objects that sublcass BasePanel and
    attempting to match their matchTagName class attribute.
    '''
    
    if not name:
        raise ValueError('Cannot create panel from nothing')
        
    for obj in globals().values():
        try:
            if issubclass(obj, BasePanel) and name == obj.matchTagName:
                # only Chart objects need to be instantiated with the flashOk and forceFlash booleans
                if obj is Chart:
                    return Chart(flashOk, forceFlash)
                else:
                    return obj()
        except:
            pass
    raise NotImplementedError('Cannot find object mapper for panel type: %s' % name)



class BasePanel(base.ViewObject):
    '''
    Represents a view result display object.
    '''
    
    # define common XML node -> object property mappings
    commonNodeMap = [
        ('title', 'title'),
        ('earliestTime', 'searchEarliestTime'),
        ('latestTime', 'searchLatestTime')
    ]
    
    # define search mode XML node -> object property mappings
    searchModeNodeMap = [
        ('searchString', base.STRING_SEARCH_MODE),
        ('searchName', base.SAVED_SEARCH_MODE),
        ('searchTemplate', base.TEMPLATE_SEARCH_MODE),
        ('searchPostProcess', base.POST_SEARCH_MODE)
    ]
    

    def __init__(self):
        
        # init standard panel params
        self.title = None
        self.layoutPanel = 'results'
        self.autoRun = True
        self.options = {}
        self.intersect = None
        self.simpleDrilldown = {}
        
        # init standard search configuration params
        self.searchMode = None
        self.searchCommand = None
        self.searchEarliestTime = None
        self.searchLatestTime = None
        self.searchFieldList = []

        self.comments = []
        self.hasDrilldownTag = False
        self.drilldownComments = []

        
    def fromXml(self, lxmlNode):
        '''
        Extracts common panel attributes from the XML
        '''
        
        # import common nodes
        for nodeName, memberName in self.commonNodeMap:
            val = lxmlNode.findtext(nodeName)
            if val:
                setattr(self, memberName, val)
        
        # option params get their own container        
        for node in lxmlNode.findall('option'):
            self.options[node.get('name')] = node.text
        
        # handle different search modes
        for pair in self.searchModeNodeMap:
            if lxmlNode.find(pair[0]) != None:
                self.searchMode = pair[1]
                self.searchCommand = lxmlNode.findtext(pair[0])
                break

        # handle field lists
        if lxmlNode.find('fields') != None:
            self.searchFieldList = splunk.util.stringToFieldList(lxmlNode.findtext('fields'))
        
        # extract simple XML drilldown params
        self.hasDrilldownTag = (lxmlNode.find('drilldown') != None)
        for linkNode in lxmlNode.findall('drilldown/link'):
            if linkNode.text and len(linkNode.text) == 0:
                continue
                
            field = linkNode.attrib.get('field')
            series = linkNode.attrib.get('series')
            if not field and series:
                field = series
            if field:
                if len(field) == 0:
                    raise AttributeError('Unable to process drilldown because field attribute is missing: %s' % et.tostring(node))
            else:
                field = '*'
            
            self.simpleDrilldown[field] = linkNode.text;

        # extract the contents of all top-level comment nodes
        for node in lxmlNode.xpath('./comment()'):
            self.comments.append(node.text)

        # extract the comments from inside the drilldown tag
        for node in lxmlNode.xpath('./drilldown/comment()'):
            self.drilldownComments.append(node.text)

          
    def toXml(self):
        '''
        Serializes the current panel object into its XML form.  Returns an
        lxml node.
        '''

        if not self.matchTagName:
            raise NotImplementedError('Unable to convert panel object to XML; panel.title=%s panel.searchMode=%s' % (self.title, self.searchMode))
            
        root = et.Element(self.matchTagName)

        for pair in self.searchModeNodeMap:
            if self.searchMode == pair[1]:
                et.SubElement(root, pair[0]).text = self.searchCommand
                break

        for pair in self.commonNodeMap:
            if getattr(self, pair[1]) != None:
                et.SubElement(root, pair[0]).text = getattr(self, pair[1])
            
        if self.searchFieldList:
            et.SubElement(root, 'fields').text = splunk.util.fieldListToString(self.searchFieldList)

        for option in sorted(self.options):
            elOption = et.SubElement(root, 'option')
            elOption.set('name', option)
            elOption.text = self.options[option]

        if self.hasDrilldownTag:
            isChart = ('charting.chart' in self.options)
            ddRoot = et.SubElement(root, 'drilldown')
            for (field, link) in self.simpleDrilldown.items():
                linkEl = et.SubElement(ddRoot, 'link')
                linkEl.text = link
                if field != '*':
                    linkEl.set(isChart and 'series' or 'field', field)
            # append comments that belong inside the drilldown tag
            for comment in self.drilldownComments:
                commentEl = et.Comment()
                commentEl.text = comment
                ddRoot.append(commentEl)

            if len(ddRoot) == 0:
                ddRoot.text = ''

        # append all comment tags to the root node
        for comment in self.comments:
            commentEl = et.Comment()
            commentEl.text = comment
            root.append(commentEl)
        
        return root


    def toObject(self):
        '''
        Returns the expanded module object hierarchy needed to render this
        panel into a view
        '''
        raise NotImplementedError('The %s class has not properly implemented toObject()' % self.__class__)
       
       
    def decorateSearchAndOptions(self, child, enablePager=False):
        
        if not isinstance(child, dict):
            raise TypeError('Expected dict structure for param "child"')
        
        # process subpanels that aren't search generating    
        if self.searchMode == None:
            # add pager if asked
            if enablePager and splunk.util.normalizeBoolean(self.options.get('showPager', True)):
                output = self._generatePagerModule()
                output['children'].append(child)
            else:
                output = child
                
            if self.title:
                output['params']['group'] = self.title
                output['params']['groupLabel'] = _(self.title)
            if self.layoutPanel:
                output['layoutPanel'] = self.layoutPanel
            return output
            

        # continue on with search generators
        
        searchParams = {
            'autoRun': self.autoRun
        }
        viewstateParams = {'suppressionList': list(self.options.keys())}

        if self.title:
            searchParams['group'] = self.title or ''
            searchParams['groupLabel'] = self.title if self.title else '' 
            
        if self.searchMode in (base.STRING_SEARCH_MODE, base.TEMPLATE_SEARCH_MODE) :
            searchModuleName = 'HiddenSearch'
            searchParams['search'] = self.searchCommand
            searchParams['earliest'] = self.searchEarliestTime
            searchParams['latest'] = self.searchLatestTime
            #searchParams['reuseMaxSecondsAgo'] = 300            
        elif self.searchMode == base.SAVED_SEARCH_MODE:
            searchModuleName = 'HiddenSavedSearch'
            searchParams['savedSearch'] = self.searchCommand
            viewstateParams['savedSearch'] = self.searchCommand
            #searchParams['reuseMaxSecondsAgo'] = 300
        elif self.searchMode == base.POST_SEARCH_MODE:
            searchModuleName = 'HiddenPostProcess'
            searchParams['search'] = self.searchCommand
            
        else:
            raise AttributeError('Unable to process panel because of unknown search mode: %s' % self.searchMode)


        # construct base panel tree
        output = {
            'className': searchModuleName,
            'layoutPanel': self.layoutPanel,
            'params': searchParams,
            'children': [
                {
                    'className': 'ViewstateAdapter',
                    'params': viewstateParams,
                    'children': [
                        {
                            'className': 'HiddenFieldPicker',
                            'params': {
                                'fields': splunk.util.fieldListToString(self.searchFieldList) or '',
                                'strictMode': True
                            },
                            'children': [
                                {
                                    'className': 'JobProgressIndicator',
                                    'children': []
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        insertionPoint = output['children'][-1]['children'][-1]['children']
        
        # add pager if asked
        if enablePager and splunk.util.normalizeBoolean(self.options.get('showPager', True)):
            insertionPoint.append(self._generatePagerModule())
        insertionPoint = insertionPoint[-1]['children']
        
        # append the data panel
        insertionPoint.append(child)
            
        return output
            
        
    def _generatePagerModule(self):
        '''
        Returns a dict instance of a pager module
        '''
        
        return {
            'className': 'Paginator',
            'params': {
                'count': self.options.get('count', 10),
                'entityName': 'results' # TODO: this needs an 'auto' mode
            },
            'children': []
        }


    def _generateGimpModule(self):
        '''
        Returns a dict instance of a gimp module
        '''

        return {
            'className': 'Gimp',
            'params': {}
        }


    jsonablePropertyList = ['title', 'searchMode', 'searchCommand', 'searchEarliestTime', 'searchLatestTime', 'options', 'simpleDrilldown', 'comments', 'drilldownComments', 'hasDrilldownTag', 'searchFieldList']
        
    def toJsonable(self):
        '''
        Returns a native structure that represents the current panel.  Used
        with the UI viewmaster framework.
        '''
        
        output = {
            'type': self.matchTagName
        }
        for k in self.jsonablePropertyList:
            output[k] = getattr(self, k)
        
        return output
        
        
    def fromJsonable(self, primitive):
        '''
        Parses an object primitive and populates the correct members
        '''

        for k in self.jsonablePropertyList:
            if primitive.get(k) != None:
                # if incoming property is a dict, then update and not overwrite
                if isinstance(primitive[k], dict) and isinstance(getattr(self, k), dict):
                    getattr(self, k).update(primitive[k])
                else:
                    setattr(self, k, primitive.get(k))
        
        
CHART_BLACKLIST = set(['scaleX', ## this is being used as a hack to force Flash
                       
                       ## properties inherited from layoutSprite
                       
                       'chart.x',
                       'chart.y',
                       'chart.width',
                       'chart.height',
                       'chart.scaleX',
                       'chart.scaleY',
                       'chart.rotation',
                       'chart.alpha',
                       'chart.visible',
                       'chart.blendMode',
                       'chart.visibility',
                       'chart.clip',
                       'chart.snap',
                       'chart.minimumWidth',
                       'chart.minimumHeight',
                       'chart.maximumWidth',
                       'chart.maximumHeight',
                       'chart.margin',
                       'chart.alignmentX',
                       'chart.alignmentY',
                       'chart.layoutTransform',
                       'chart.renderTransform',
                       'chart.renderTransformOrigin',
                       'chart.renderTransformOriginMode',
                       
                       ## area chart properties
                       
                       'chart.areaBrushPalette',
                       'chart.areaStyle',
                       'chart.lineBrushPalette',
                       'chart.lineStyle',
                       
                       ## bar chart properties
                       
                       'chart.barBrushPalette',
                       'chart.barShapePalette',
                       'chart.barStyle',
                       'chart.barAlignment',
                       'chart.useAbsoluteSpacing',
                       
                       ## column chart properties
                       
                       'chart.columnBrushPalette',
                       'chart.columnShapePalette',
                       'chart.columnStyle',
                       'chart.columnAlignment',
                       
                       ## generic gauge properties
                        
                       'chart.rangePadding',
                       'chart.majorTickBrush',
                       'chart.majorTickStyle',
                       'chart.majorTickPlacement1',
                       'chart.majorTickPlacement2',
                       'chart.minorTickBrush',
                       'chart.minorTickStyle',
                       'chart.minorTickPlacement1',
                       'chart.minorTickPlacement2',
                       'chart.labelStyle',
                       'chart.labelPlacement',
                       'chart.valueStyle',
                       'chart.valuePlacement',
                       'chart.warningBrush',
                       'chart.warningShape',
                       'chart.warningStyle',
                       'chart.warningPlacement',
                       'chart.warningSize',
                       'chart.foregroundBrush',
                       'chart.foregroundStyle',
                       'chart.foregroundPlacement1',
                       'chart.foregroundPlacement2',
                       'chart.foregroundPadding',
                       'chart.backgroundBrush',
                       'chart.backgroundStyle',
                       'chart.backgroundPlacement1',
                       'chart.backgroundPlacement2',
                       'chart.backgroundPadding',
                       'chart.layers',
                       
                       ## filler gauge properties
                       
                       'chart.fillerBrushPalette',
                       'chart.fillerStyle',
                       'chart.fillerPlacement1',
                       'chart.fillerPlacement2',
                       
                       ## line chart properties
                       
                       'chart.lineBrushPalette',
                       'chart.lineStyle',
                       'chart.markerBrushPalette',
                       'chart.markerShapePalette',
                       'chart.markerStyle',
                       
                       ## marker gauge properties
                       
                       'chart.markerBrush',
                       'chart.markerShape',
                       'chart.markerPlacement1',
                       'chart.markerPlacement2',
                       'chart.markerThickness',
                       'chart.rangeBandBrushPalette',
                       'chart.rangeBandPlacement1',
                       'chart.rangeBandPlacement2',
                       
                       ## pie chart properties
                       
                       'chart.sliceBrushPalette',
                       'chart.sliceStyle',
                       'chart.labelLineBrush',
                       
                       ## radial gauge properties
                       
                       'chart.needleBrush',
                       'chart.needleShape',
                       'chart.needleStyle',
                       'chart.needleRadius1',
                       'chart.needleRadius2',
                       'chart.needleThickness',
                       'chart.rangeBandStyle',
                       'chart.rangeBandRadius1',
                       'chart.rangeBandRadius2',
                       'chart.majorTickRadius1',
                       'chart.majorTickRadius2',
                       'chart.minorTickRadius1',
                       'chart.minorTickRadius2',
                       'chart.labelRadius',
                       'chart.valueStyle',
                       'chart.valueRadius',
                       'chart.markerBrushPalette',
                       'chart.markerShapePalette',
                       
                       ## layout properties
                       
                       'layout.charts',
                       'layout.legends',
                       'layout.axisLabels',
                       'layout.axisTitles',
                       'layout.gridLines',
                       'layout.margin',
                       'layout.splitSeriesMargin',
                       
                       ## legend properties
                       
                       'legend',
                       'legend.defaultSwatchBrushPalette',
                       'legend.swatchPlacement',
                       'legend.labelStyle',
                       'legend.swatchStyle',
                       'legend.itemStyle',
                       
                       ## tooltip properties
                       
                       'tooltip',
                       'tooltip.backgroundBrush',
                       'tooltip.content.swatchStyle',
                       'tooltip.content.fieldStyle',
                       'tooltip.content.valueStyle',
                       
                       ## axis properties
                       
                       'axis',
                       'axis.reverse',
                       'axis.comparator',
                       'axis.categories',
                       'axis.minimumTime',
                       'axis.maximumTime',
                       
                       ## axis label properties
                       
                       'axisLabels',
                       'axisLabels.axis',
                       'axisLabels.placement',
                       'axisLabels.axisBrush',
                       'axisLabels.majorTickBrush',
                       'axisLabels.minorTickBrush',
                       'axisLabels.majorLabelStyle',
                       'axisLabels.majorLabelAlignment',
                       'axisLabels.majorLabelStyle',
                       'axisLabels.minorLabelAlignment',
                       'axisLabels.minorLabelVisibility',
                       'axisLabels.minorUnit',
                       'axisLabels.scaleMajorUnit',
                       'axisLabels.scaleMinorUnit',
                       'axisLabels.timeZone'
                       
                       ## axis grid line properties
                       
                       'gridLines',
                       'gridLines.axisLabels',
                       'gridLines.majorLineBrush',
                       'gridLines.minorLineBrush',
                       
                       ## axis title properties
                       
                       'axisTitle',
                       'axisTitle.placement',
                       'axisTitle.textColor',
                       'axisTitle.defaultTextFormat',
                       'axisTitle.htmlText',
                       'axisTitle.condenseWhite',
                       'axisTitle.wordWrap',
                       'axisTitle.overflowMode',
                       'axisTitle.useBitmapRendering',
                       'axisTitle.useBitmapSmoothing',
                       'axisTitle.bitmapSmoothingSharpness',
                       'axisTitle.bitmapSmoothingQuality',
                       
                       ## other properties
                       
                       'fieldColors'
                       
                       ])

class Chart(BasePanel):
    '''
    Represents a standard chart display of a search object
    '''
    
    # define the XML tag
    matchTagName = 'chart'

    def __init__(self, flashOk=True, forceFlash=False):
        BasePanel.__init__(self)
        self.flashOk = flashOk
        self.forceFlash = forceFlash
        if not flashOk and forceFlash:
            raise Exception("if flashOk is False, forceFlash cannot be True")

    def toObject(self):

        chartObjectParams = {
            'width': '100%'
        }
        if 'height' in self.options:
            chartObjectParams['height'] = self.options['height']

        canUseJSChart = not self.forceFlash
        chartFormatParams = {}
        
        for k in self.options:
            if k.startswith('charting.'):
                chartFormatParams[k] = self.options[k]

        # if the flashOk boolean is True, iterate through the charting properties to determine if we should
        # fall back to FlashChart
        if self.flashOk:
            if self.options.get('charting.chart', 'column') in set(['bubble', 'histogram', 'rangeMarker', 'ratioBar', 'valueMarker']):
                canUseJSChart = False
            elif 'charting.legend.masterLegend' in self.options and self.options.get('charting.legend.masterLegend') is not None and self.options.get('charting.legend.masterLegend') != 'null':
                canUseJSChart = False
            else:
                for k in self.options:
                    if k.startswith('charting.'):
                        normalizedKey = self.normalizePropertyKey(k)
                        if normalizedKey[9:] in CHART_BLACKLIST:
                            canUseJSChart = False
                            break
        
        flashChartChildren = []
        flashChartChildren.append(self._generateGimpModule())

        drilldown = self.options.get('drilldown', 'all')
        if (drilldown != 'none'):
            if self.simpleDrilldown and len(self.simpleDrilldown) > 0:   
                flashChartChildren.append({
                    'className': 'SimpleDrilldown',
                    'params' : {
                        'links': self.simpleDrilldown
                    }
                });  
            else:
                flashChartChildren.append({
                    'className': 'ConvertToDrilldownSearch',
                    'children' : [
                        {
                            'className': 'ViewRedirector',
                            'params' : {
                                'viewTarget' : 'flashtimeline'
                            }
                        }
                    ]
                })

        output = {
            'className': 'HiddenChartFormatter',
            'params': chartFormatParams,
            'children': [
                {
                    'className': canUseJSChart and 'JSChart' or 'FlashChart',
                    'params': chartObjectParams,
                    'children': flashChartChildren
                }
            ]
        }

        link_visible = splunk.util.normalizeBoolean(self.options.get('link.visible', True))
        link_search = self.options.get('link.search', None)
        link_target_view = self.options.get('link.viewTarget', 'flashtimeline')

        link = None
        if link_visible:
            link = {
                'className': 'ViewRedirectorLink',
                'params': {
                    'viewTarget': link_target_view
                }
            }

            if link_search != None:
                link = {
                    'className': 'HiddenSearch',
                    'params': { 'search': link_search },
                    'children': [link]
                }

        if link != None: output['children'].append(link)
        
        # Enables results preview for tables
        if not 'previewResults' in self.options or splunk.util.normalizeBoolean(self.options['previewResults']):
            output = {
                'className': 'EnablePreview',
                'params': {
                    'enable': True,
                    'display': False
                },
                'children': [output]
            }
        
        output = self.decorateSearchAndOptions(output)
        
        return output
    
    
    def normalizePropertyKey(self, key):
        """ Performs basic string manipulation on the key to normalize away
            the different ways of referring to axes, axis labels, etc. """
            
        ## normalize references to axes themselves
        returnKey = key.replace("axisX", "axis")
        returnKey = returnKey.replace("primaryAxis", "axis")
        returnKey = returnKey.replace("axisY", "axis")
        returnKey = returnKey.replace("secondaryAxis", "axis")
        
        ## normalize references to axis labels
        returnKey = returnKey.replace("axisLabelsX", "axisLabels")
        returnKey = returnKey.replace("axisLabelsY", "axisLabels")
        
        ## normalize references to axis title
        returnKey = returnKey.replace("axisTitleX", "axisTitle")
        returnKey = returnKey.replace("primaryAxisTitle", "axisTitle")
        returnKey = returnKey.replace("axisTitleY", "axisTitle")
        returnKey = returnKey.replace("secondaryAxisTitle", "axisTitle")
        
        ## normalize references to axis grid lines
        returnKey = returnKey.replace("gridLinesX", "gridLines")
        returnKey = returnKey.replace("gridLinesY", "gridLines")
        
        return returnKey
        
class Table(BasePanel):
    '''
    Represents a basic tabular output of search object
    '''        

    matchTagName = 'table'
    fieldFormats = None

            
    def parseOption(self, node):
        """Extract nested options/lists"""
        listNodes = node.findall('list')
        optionNodes = node.findall('option')

        if listNodes and optionNodes:
            raise ValueError("Tag cannot contain both list and option subtags")
        elif listNodes:
            result = []
            for listNode in listNodes:
                result.append(self.parseOption(listNode))
            return result
        elif optionNodes:
            result = {}
            for optionNode in optionNodes:
                result[optionNode.get('name')] = self.parseOption(optionNode)
            return result
        else:
            return node.text
            
            
    def fromXml(self, lxmlNode):
        """
        Add a format tag to provide cell formatting 
        (primarily for sparklines at the current time)
        Each format tag may have some option sub-tags
        Each option may contain list or option tags generating 
        lists or dictionaries respectively

        Each format tag may specify a field to filter on (defaults to all fields)
        and a type to apply (eg 'sparkline')
        """

        super(Table, self).fromXml(lxmlNode)
        fieldFormats = {}
        for formatNode in lxmlNode.findall('format'):
            field = formatNode.get('field', '*')
            formatType = formatNode.get('type', 'text')
            options = {}
            for optionNode in formatNode.findall('option'):
                options[optionNode.get('name')] = self.parseOption(optionNode)
            fieldFormats.setdefault(field, []).append({
                'type': formatType,
                'options': options
            });
        self.fieldFormats = fieldFormats


    def toXml(self):
        """
        Add the format tag to the resulting xml if required
        """
        root = super(Table, self).toXml()
        if self.fieldFormats:
            for field, formats in self.fieldFormats.items():
                for format in formats:
                    node = et.SubElement(root, 'format')
                    node.set('type', format['type'])
                    if field!='*':
                        node.set('field', field)
                    self.encodeOption(node, format['options'])
        return root


    def encodeOption(self, node, option):
        if isinstance(option, (tuple, list)):
            for item in option:
                el = et.SubElement(node, 'list')
                self.encodeOption(el, item)
        elif isinstance(option, dict):
            for key, val in option.items():
                el = et.SubElement(node, 'option')
                el.set('name', key)
                self.encodeOption(el, val)
        else:
            node.text = option
            

    def toObject(self):

        resultsTableParams = {
            'allowTransformedFieldSelect': (self.searchMode != base.POST_SEARCH_MODE),
            'entityName': 'results'
        }
        for k in ['count', 'displayRowNumbers', 'dataOverlayMode']:
            if k in self.options:
                resultsTableParams[k] = self.options[k]

        if self.fieldFormats:
            resultsTableParams['fieldFormats'] = self.fieldFormats
        
        
        resultsTableChildren = []
        resultsTableChildren.append(self._generateGimpModule())
        
        if len(self.simpleDrilldown) > 0:   
            resultsTableParams["drilldown"] = 'all'
            
            resultsTableChildren.append({
                'className': 'SimpleDrilldown',
                'params' : {
                    'links': self.simpleDrilldown
                }
            });
            
        else:
            drilldown = self.options.get('drilldown', 'row')

            if (drilldown != 'none'):
                resultsTableParams["drilldown"] = drilldown
                resultsTableChildren.append({
                    'className': 'ConvertToDrilldownSearch',
                    'children' : [
                        {
                            'className': 'ViewRedirector',
                            'params' : {
                                'viewTarget' : 'flashtimeline'
                            }
                        }
                    ]
                })
        
        

        output = [{
                'className': 'SimpleResultsTable',
                'params': resultsTableParams,
                'children': resultsTableChildren
            }]

        link_visible = splunk.util.normalizeBoolean(self.options.get('link.visible', True))
        link_search = self.options.get('link.search', None)
        link_target_view = self.options.get('link.viewTarget', 'flashtimeline')

        link = None
        if link_visible:
            link = {
                'className': 'ViewRedirectorLink',
                'params': {
                    'viewTarget': link_target_view
                }
            }

            if link_search != None:
                link = {
                    'className': 'HiddenSearch',
                    'params': { 'search': link_search },
                    'children': [link]
                }

        if link != None: output.append(link)

        
        # Enables results preview for tables
        if not 'previewResults' in self.options or splunk.util.normalizeBoolean(self.options['previewResults']):
            output = {
                'className': 'EnablePreview',
                'params': {
                    'enable': True,
                    'display': False
                },
                'children': output
            }
        
        output = self.decorateSearchAndOptions(output, True)
        
        return output


        
class Event(BasePanel):
    '''
    Represents a raw event renderer
    '''        

    matchTagName = 'event'


    def toObject(self):

        eventViewerParams = {}
        for k in ['count', 'displayRowNumbers', 'entityName', 'segmentation', 'maxLines', 'softWrap']:
            if k in self.options:
                eventViewerParams[k] = self.options[k]

        output = {
            'className': 'EventsViewer',
            'params': eventViewerParams,
            'children': [self._generateGimpModule()]
        }
        
        if 'wrap' in self.options and splunk.util.normalizeBoolean(self.options.get('wrap')):
            output = {
                'className': 'HiddenSoftWrap',
                'params': {
                    'enable': True
                },
                'children': [output]
            }


        if self.searchFieldList and not self.searchMode:
            output = {
                'className': 'HiddenFieldPicker',
                'params': {
                   'fields': splunk.util.fieldListToString(self.searchFieldList) or '',
                   'strictMode': False
                },
                'children': [output]
            }        
       
            
    
        output = self.decorateSearchAndOptions(output, True)
        
        return output


        
class List(BasePanel):
    '''
    Represents a basic list
    '''        

    matchTagName = 'list'


    def toObject(self):

        listerParamList = ['initialSortDir', 'labelFieldSearch', 'valueField', 'labelField', 'labelFieldTarget', 'initialSort']

        listerParams = {}
        for k in listerParamList:
            if k in self.options:
                listerParams[k] = self.options[k]
        
        output = {
            'className': 'LinkList',
            'params': listerParams,
            'children': [self._generateGimpModule()]
        }
        output = self.decorateSearchAndOptions(output, True)
        
        return output



class Single(BasePanel):
    '''
    Represents a single value panel.
    '''        

    matchTagName = 'single'


    def toObject(self):

        valid_options = ['additionalClass', 'linkView', 'field', 'linkFields', 'classField', 'beforeLabel', 'afterLabel', 'linkSearch']
        options = {}
        for option in valid_options:
            if option in self.options:
                option_value = self.options[option]
                options[option] = '' if option_value is None else self.options[option]
        
        output = {
            'className': 'SingleValue',
            'params': options,
            'children': [self._generateGimpModule()]
        }
        output = self.decorateSearchAndOptions(output)

        return output


class Map(BasePanel):
    '''
    Represents a map display of a search object
    '''

    # define the XML tag
    matchTagName = 'map'


    def toObject(self):

        mapObjectParams = {
            'width': '100%'
        }

        if 'height' in self.options:
            mapObjectParams['height'] = self.options['height']

        for k in self.options:
            if k.startswith('mapping.'):
                mapObjectParams[k] = self.options[k]

        mapChildren = []
        mapChildren.append(self._generateGimpModule())

        drilldown = self.options.get('drilldown', 'all')
        if (drilldown != 'none'):
            if self.simpleDrilldown and len(self.simpleDrilldown) > 0:
                mapChildren.append({
                    'className': 'SimpleDrilldown',
                    'params': {
                        'links': self.simpleDrilldown
                    }
                })
            else:
                mapChildren.append({
                    'className': 'ConvertToDrilldownSearch',
                    'children': [
                        {
                            'className': 'ViewRedirector',
                            'params': {
                                'viewTarget': 'flashtimeline'
                            }
                        }
                    ]
                })

        output = {
            'className': 'Map',
            'params': mapObjectParams,
            'children': mapChildren
        }

        output = self.decorateSearchAndOptions(output)

        return output

  
class Html(BasePanel):
    '''
    Represents a basic HTML content
    '''        

    matchTagName = 'html'


    def fromXml(self, lxmlNode):
        '''
        Override default parser and just get the text
        '''
        src = lxmlNode.get('src')
        if src:
            self.options['serverSideInclude'] = src
            return
        
        flatString = et.tostring(lxmlNode, method='html')
        flatString = flatString.replace('<html>', '').replace('</html>', '')
        self.options['rawcontent'] = flatString.strip('\r\n\t ')
        
        
    def toXml(self):
        xml = '<%s>%s</%s>' % (self.matchTagName, self.options['rawcontent'], self.matchTagName)
        return et.HTML(xml)

        
    def toObject(self):
        src = self.options.get('serverSideInclude')
        if src:
            output = {
                'className': 'ServerSideInclude',
                'params': {'src': src},
                'children': [self._generateGimpModule()]
            }
        else:
            output = {
                'className': 'StaticContentSample',
                'params': {'text': self.options['rawcontent']},
                'children': [self._generateGimpModule()]
            }
        output = self.decorateSearchAndOptions(output)

        return output
              
