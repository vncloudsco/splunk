from __future__ import absolute_import
from builtins import range
from builtins import map
import lxml.etree as et
import splunk.util
from splunk.models import ViewConfigurationException
import splunk.models.legacy_views.base as base
import splunk.models.legacy_views.panel as panel

import logging
logger = logging.getLogger('splunk.models.legacy_views.dashboard')

class SimpleDashboard(base.ViewObject):
    
    matchTagName = 'dashboard'
        
    # define set of default attributes to assign to view
    standardAttributeMap = {
        'displayView': None,
        'isVisible': True,
        'onunloadCancelJobs': True,
        'autoCancelInterval': 90,
        'refresh': -1,
        'stylesheet': None,
        'template': 'dashboard.html',
        'objectMode': 'SimpleDashboard'
    }
    
    # define attributes that are to be cast to boolean
    booleanAttributeKeys = ['isVisible', 'onunloadCancelJobs']
    
    # define attributes that are to be cast to integers
    integerAttributeKeys = ['refresh', 'autoCancelInterval']

    def __init__(self, flashOk=True, forceFlash=False):

        self.label = None
        self.flashOk = flashOk
        self.forceFlash = forceFlash
        # set core view properties
        for k, v in list(self.standardAttributeMap.items()):
            setattr(self, k, v)

        # init panel container
        self.rows = []
        self.rowGrouping = []

        # instance members to track comment tags
        self.topLevelComments = []
        self.perRowComments = [] # will be a list of lists for comments by row
        
    def hasRowGrouping(self):
        for rowGroup in self.rowGrouping:
            if isinstance(rowGroup, list) and len(rowGroup)>0:
                return True
        return False
       
    def buildLayoutPanelCode(self, row, col):

        # deal with merged panels by slotting them in the same col
        if self.rowGrouping[row]:
            groupMap = []
            for i, groupSize in enumerate(self.rowGrouping[row]):
                for j in range(groupSize):
                    groupMap.append(i)
            if col >= len(groupMap):
                group = len(groupMap) - 1
            else:
                group = groupMap[col]

            col = group

        return 'panel_row%s_col%s' % (row+1, col+1)

    
    def getPanelPositionBySequence(self, seq):
        '''
        Returns the position of the panel
        '''
        
        seq = int(seq)
        pos = 0
        for i, row in enumerate(self.rows):
            for j, panel in enumerate(row):
                if seq == pos:
                    return (i, j)
                pos += 1
        raise IndexError('No panel found at sequence %s' % seq)
        
        
    def getPanelBySequence(self, seq):
        '''
        Returns the panel object that exists at the position, assuming a
        cursor moving top to bottom, left to right
        '''

        i, j = self.getPanelPositionBySequence(seq)
        return self.rows[i][j]

    def fromXml(self, lxmlNode):

        if lxmlNode.tag != self.matchTagName:
            raise AttributeError("SimpleDashboard expected <dashboard> root node; cannot continue parsing")

        self.label = lxmlNode.findtext('label')
        self.searchTemplate = lxmlNode.findtext('searchTemplate')
        self.searchEarliestTime = lxmlNode.findtext('earliestTime')
        self.searchLatestTime = lxmlNode.findtext('latestTime')

        # set core view attributes
        for k in self.standardAttributeMap:
            v = lxmlNode.get(k)
            if v != None:
                if k in self.booleanAttributeKeys:
                    v = splunk.util.normalizeBoolean(v)
                elif k in self.integerAttributeKeys:
                    v = int(v)
                setattr(self, k, v)

        for row in lxmlNode.findall('row'):
            if row.get('grouping'):
                self.rowGrouping.append(
                    list(map(int, row.get('grouping').replace(' ', '').strip(',').split(',')))
                )
            else:
                self.rowGrouping.append(None)

            rowList = []
            for item in row:
                if not isinstance(item.tag, splunk.util.string_type):
                    continue
                if item.tag == 'panel':
                    for element in item:
                        rowList.append(self.buildElement(element))
                else:
                    rowList.append(self.buildElement(item))
            self.rows.append(rowList)

            rowComments = []
            for node in row.xpath('./comment()'):
                rowComments.append(node.text)
            self.perRowComments.append(rowComments)

        for node in lxmlNode.xpath('./comment()'):
            self.topLevelComments.append(node.text)

    def buildElement(self, element):
        panelInstance = panel.createPanel(element.tag, flashOk=self.flashOk, forceFlash=self.forceFlash)
        panelInstance.fromXml(element)
        return panelInstance

    def toXml(self):
        '''
        Returns an lxml representation of this object
        '''
        
        root = et.Element('dashboard')
        
        et.SubElement(root, 'label').text = self.label
        
        # only output attributes if they are not the default
        for k in self.standardAttributeMap:
            v = getattr(self, k)
            if v != None and v != self.standardAttributeMap[k]:
                root.set(k, splunk.util.toUTF8(v))

        for i, row in enumerate(self.rows):
            elRow = None
            if (len(row) > 0):
                elRow = et.SubElement(root, 'row')
                if self.rowGrouping[i] != None:
                    elRow.set('grouping', ','.join(map(str, self.rowGrouping[i])))
                for panel in row:
                    elRow.append(panel.toXml())

            if len(self.perRowComments) > i and len(self.perRowComments[i]) > 0:
                if elRow is None:
                    elRow = et.SubElement(root, 'row')
                for comment in self.perRowComments[i]:
                    commentEl = et.Comment()
                    commentEl.text = comment
                    elRow.append(commentEl)


        for comment in self.topLevelComments:
            commentEl = et.Comment()
            commentEl.text = comment
            root.append(commentEl)

        return root
        
                
    def toObject(self):
       
        # build the standard dashboard view preamble
        output = {
            'label': self.label,

            'modules': [
                {
                    'className': 'AccountBar',
                    'layoutPanel': 'appHeader'
                },
                {
                    'className': 'AppBar',
                    'layoutPanel': 'navigationHeader'
                },
                {
                    'className': 'Message',
                    'layoutPanel': 'messaging',
                    'params': {
                        'filter': '*',
                        'clearOnJobDispatch': False,
                        'maxSize': 1
                    }
                },
                {
                    'className': 'DashboardTitleBar',
                    'layoutPanel': 'viewHeader',
                    'params': {}
                },
                {
                    'className': 'Message',
                    'layoutPanel': 'navigationHeader',
                    'params': {
                        'filter': 'splunk.search.job',
                        'clearOnJobDispatch': True,
                        'maxSize': 1,
                        'level': 'warn'
                    }
                }
            ]
        }


        # add standard props
        for k in self.standardAttributeMap:
            output[k] = getattr(self, k)

        # row grouping enabled
        output['hasRowGrouping'] = self.hasRowGrouping()
        
        # inject the specified panels into grid fashion
        sequence = 0
        for i, row in enumerate(self.rows):
            for j, item in enumerate(row):
                item.layoutPanel = self.buildLayoutPanelCode(row=i, col=j)
                itemDef = item.toObject()
                if itemDef:
                    itemDef['intersect'] = (i, j)
                    itemDef['panelType'] = item.matchTagName
                    itemDef['sequence'] = sequence
                    output['modules'].append(itemDef)
                    sequence = sequence + 1
                
        return output

    jsonablePropertyList = ['label', 'refresh', 'rowGrouping']
    

    def toJsonable(self):
        '''
        Generate abridged JSON-ready structure of object representation for use
        with UI widget editing
        '''
  
        output = {
            'rows': []
        }
        for k in self.jsonablePropertyList:
            output[k] = getattr(self, k)
        
        for i, row in enumerate(self.rows):
            subset = []
            for j, panel in enumerate(row):
                position = [i, j]
                subset.append({
                    'type': panel.matchTagName,
                    'title': panel.title or panel.searchCommand,
                    'position': position
                })
            output['rows'].append(subset)

        return output
                
                
    def fromJsonable(self, primitive):
        '''
        Parses an object primitive into the current ViewObject.  This method is
        used strictly to reorder panels.  Adding and deleting are atomic
        actions that are handled by other means.
        '''
        
        # set base dashboard props
        for k in self.jsonablePropertyList:
            if primitive.get(k) != None:
                setattr(self, k, primitive.get(k))
            
        # reorder the panels
        if 'rows' in primitive:

            currentPanelCount = sum([len(x) for x in self.rows])
            incomingPanelCount = sum([len(x) for x in primitive['rows']])
            if currentPanelCount != incomingPanelCount:
                raise AttributeError('Number of panel rows has changed from %s to %s; aborting reorder' % (currentPanelCount, incomingPanelCount))
            
            reorderedPanelRows = []
        
            for i, row in enumerate(primitive['rows']):
                if len(row) > 0:
                    newRow = []
                    for j, panel in enumerate(row):
                        p = panel['position']
                        newRow.append(self.rows[p[0]][p[1]])
                        logger.debug('Panel reshuffle: %s => %s' % ((p[0], p[1]), (i, j)))
                    reorderedPanelRows.append(newRow)
                
            self.rows = reorderedPanelRows


if __name__ == '__main__':
    
    xml = '''
    <!-- this is a comment -->
    <dashboard>
      <label>Super Sweet Auto-Dashboard</label>
      <row grouping="1,2">
        <single>
          <searchString>| metadata type="sources" | stats count</searchString>
          <option name="afterLabel">sources</option>
        </single>
        <single>
          <searchString>| metadata type="sourcetypes" | stats count</searchString>
          <option name="afterLabel">sourcetypes</option>
        </single>
        <single>
          <searchString>| metadata type="hosts" | stats count</searchString>
          <option name="afterLabel">hosts</option>
        </single>
      </row>
      <row>
        <chart>
          <searchName>JV chart</searchName>
        </chart>

        <chart>
          <title></title>
          <searchString>index=_internal metrics group="pipeline" NOT sendout | head 1000 | timechart per_second(cpu_seconds) by processor</searchString>
          <earliestTime>-30h</earliestTime>
          <latestTime>-10h</latestTime>
          <option name="charting.chart">line</option>
          <option name="charting.primaryAxisTitle.text">Time</option>
          <option name="charting.secondaryAxisTitle.text">Load (%)</option>
        </chart>
      </row>

      <row>
        <list>
          <title>Sources (lister)</title>
          <searchString>| metadata type=sources | sort -totalCount</searchString>
          <option name="valueField">totalCount</option>
          <option name="labelField">source</option>
          <option name="labelFieldTarget">flashtimeline</option>
          <option name="labelFieldSearch">*</option>
        </list>
        <table>
          <title>Sources (table)</title>
          <searchName>JV changesearch</searchName>
          <fields>added, deleted, changed, _time</fields>
          <option name="displayRowNumbers">false</option>
        </table>
        <table>
          <title>Sources (table)</title>
          <searchString>changelist | head 1000 | top 30 user</searchString>
          <fields>user count</fields>
          <option name="count">20</option>
        </table>
      </row>

      <row>
        <html>
            This lists all of the data you have loaded into <strong>your</strong> default indexes over all time.
        </html>
      </row>

    </dashboard>
    '''
        
    
    root = et.fromstring(xml)
    d = SimpleDashboard()
    d.fromXml(root)
    
    import pprint, json
    
    logging.getLogger().setLevel(10)
    logging.debug('asdf')
    j = d.toJsonable()
    j['rows'].reverse()
    
    d.fromJsonable(j)
    
    #print json.dumps(d.toJsonable(), indent=4)
    pprint.pprint(d.toObject())
    #print et.tostring(d.toXml(), pretty_print=True)
