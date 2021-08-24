from __future__ import absolute_import
from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import map
import lxml.etree as et

from splunk.models import ViewConfigurationException
import splunk.models.legacy_views.base as base
import splunk.models.legacy_views.forminput as forminput
import splunk.models.legacy_views.panel as panel
import splunk.util

import logging
logger = logging.getLogger('splunk.models.legacy_views.form')

class SimpleForm(base.ViewObject):
    '''
    Represents a form search object.  This object renders a set of input
    controls at the top of the page, and a series of result renderers below.
    The result renderers can either: 1)  all drive themselves off of 1 master
    search, or 2)  each specify their own search, with form elements adding
    common search intentions to all.
    '''
    
    matchTagName = 'form'
    
    def __init__(self, flashOk=True, forceFlash=False):

        self.flashOk = flashOk
        self.forceFlash = forceFlash
        # set core view properties
        self.isVisible = True
        self.label = None
        self.onunloadCancelJobs = True
        self.autoCancelInterval = 90
        self.autoRun = False
        self.stylesheet = None
        self.template = 'dashboard.html'
        self.submitButton = True

        self.searchTemplate = None
        self.searchEarliestTime = None
        self.searchLatestTime = None
        self.objectMode = 'SimpleForm'
        
        # init form element container
        self.fieldset = []
        
        # init panel container
        self.rows = []
        self.rowGrouping = [] 
        

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
        
        
    def fromXml(self, lxmlNode):
        
        if lxmlNode.tag != self.matchTagName:
            raise AttributeError("SimpleForm expected <form> root node; cannot continue parsing")
        
        # common params
        self.label = lxmlNode.findtext('label')
        self.displayView = lxmlNode.get('displayView')
        self.stylesheet = lxmlNode.get('stylesheet')
        self.refresh = int(lxmlNode.get('refresh', 0))
        self.isVisible = splunk.util.normalizeBoolean(lxmlNode.get('isVisible', True))
        self.onunloadCancelJobs = splunk.util.normalizeBoolean(lxmlNode.get('onunloadCancelJobs', True))
        self.autoCancelInterval = lxmlNode.get('autoCancelInterval', 90)
        
        # master search template
        self.searchTemplate = lxmlNode.findtext('./searchTemplate')
        self.searchEarliestTime = lxmlNode.findtext('./earliestTime')
        self.searchLatestTime = lxmlNode.findtext('./latestTime')
        
        fieldsetNode = lxmlNode.find('./fieldset')
        if fieldsetNode is not None:
            self.autoRun = splunk.util.normalizeBoolean(fieldsetNode.get('autoRun', False))
            self.submitButton = splunk.util.normalizeBoolean(fieldsetNode.get('submitButton', True))
        
            for item in fieldsetNode:
                if item.tag == 'html':
                    # no need to pass the flashOk boolean here since we are creating an HTML panel
                    panelInstance = panel.createPanel(item.tag)
                    panelInstance.fromXml(item)
                    panelInstance.layoutPanel = None;
                    self.fieldset.append(panelInstance)
                elif item.tag == 'input':
                    inputInstance = forminput.createInput(item.get('type'))
                    inputInstance.fromXml(item)
                    self.fieldset.append(inputInstance)
        
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
                panelInstance = panel.createPanel(item.tag, flashOk=self.flashOk, forceFlash=self.forceFlash)
                panelInstance.fromXml(item)
                rowList.append(panelInstance)
            self.rows.append(rowList)


    def toXml(self):
        
        root = et.Element('form')
        et.SubElement(root, 'label').text = self.label

        if self.searchTemplate:
            et.SubElement(root, 'searchTemplate').text = self.searchTemplate
            
        elFieldset = et.SubElement(root, 'fieldset')
        for forminput in self.fieldset:
            elFieldset.append(forminput.toXml())
        
        for i, row in enumerate(self.rows):
            if (len(row) > 0):
                elRow = et.SubElement(root, 'row')
                if self.rowGrouping[i] != None:
                    elRow.set('grouping', ','.join(map(str, self.rowGrouping[i])))
                for panel in row:
                    elRow.append(panel.toXml())

        return root
        
                
    def toObject(self):
        
        # build the standard dashboard view preamble
        output = {
            'isVisible': self.isVisible,
            'label': self.label,
            'onunloadCancelJobs': self.onunloadCancelJobs,
            'autoCancelInterval': self.autoCancelInterval,
            'stylesheet': self.stylesheet,
            'template': self.template,
            'objectMode': self.objectMode,

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
                    'className': 'Message',
                    'layoutPanel': 'messaging',
                    'params': {
                        'filter': 'splunk.search.job',
                        'clearOnJobDispatch': True,
                        'maxSize': 1
                    }
                },
                {
                    'className': 'DashboardTitleBar',
                    'layoutPanel': 'viewHeader',
                    'params': {}
                }
            ]
        }
        
        # define reference to the data tree location in which to insert
        # follow on modules
        insertionPoint = output['modules']
        lenOfInitialModules = len(insertionPoint)
        
        # insert the top level string replace module, if specified
        if self.searchTemplate:
            output['modules'].append({
                'className': 'HiddenSearch',
                'layoutPanel': 'viewHeader',
                'params': {
                    'search': self.searchTemplate,
                    'earliest': self.searchEarliestTime,
                    'latest': self.searchLatestTime
                },
                'children': []
            })
            insertionPoint = output['modules'][-1]['children']
        
        # insert the inputs, each a child of the previous
        for i, item in enumerate(self.fieldset):
            itemDef = item.toObject()

            inPnt = None
            if isinstance(itemDef, tuple):
                inPnt = itemDef[1]
                itemDef = itemDef[0]

            if itemDef:
                
                # attach layoutPanel to top item if this is the first in the branch
                if not self.searchTemplate and i == 0:
                    itemDef['layoutPanel'] = 'viewHeader'
                    
                insertionPoint.append(itemDef)
                if inPnt != None:
                    insertionPoint = inPnt
                else:
                    insertionPoint = itemDef['children']

        # Insert Submit Button
        insertionPoint.append({
            'className': 'SubmitButton',
            'layoutPanel': 'viewHeader',
            'params': {
                'allowSoftSubmit': True,
                'label': 'Search',
                'updatePermalink': True,
                'visible': self.submitButton
            },
            'children': []
        })
        insertionPoint = insertionPoint[-1]['children']
        
        # Insert the auto run call
        if self.autoRun and len(output['modules']) > lenOfInitialModules:
            formParent = output['modules'][lenOfInitialModules]
            params = formParent.get('params')
            if not params:
                formParent['params'] = {}
            formParent['params']['autoRun'] = self.autoRun

        # insert the result display panels, each a child of the last input object
        for i, row in enumerate(self.rows):
            for j, item in enumerate(row):
                item.layoutPanel = self.buildLayoutPanelCode(row=i, col=j)
                item.autoRun = False
                
                if self.searchTemplate and item.searchMode == base.TEMPLATE_SEARCH_MODE:
                    raise ViewConfigurationException(
                        'misconfigured form search; <searchTemplate> node must be either at the top level or inside panels, not both', 
                        self.label
                    )
                    
                itemDef = item.toObject()
                if itemDef:
                    insertionPoint.append(itemDef)
                
        return output
                
                
if __name__ == '__main__':
    
    xml = '''<form>
      <label>My Fanciness</label>

      <searchTemplate>sourcetype="$thesource$" $username$</searchTemplate>

      <fieldset>

          <!-- inserts default textbox -->
          <input token="username">
              <prefix>user=</prefix>
              <default>erik</default>
              <seed>johnvey*</seed>
          </input>

          <input type="text" token="thesource">
              <label>Sourcetype</label>
              <default>jira</default>
              <seed>p4change</seed>
          </input>

          <input type="time" />

          <!--input token="this" type="dropdown">
              <label>SOmething</label>
              <search>sourcetype=jira | top user | fields user</search>
              <select value="00">first</select>
              <select value="00">first</select>
              <select value="00">first</select>
          </input-->

      </fieldset>

      <row>
          <chart>
              <title>Big ideas chart</title>
          </chart>
          <table>
              <title>Big ideas table</title>
          </table>
      </row>

      <row>
          <table>
              <title>commits per user</title>
              <searchPostProcess>timechart count by user</searchPostProcess>
              <option name="charting.chart">line</option>
          </table>
          <table>
              <title>avg lines added by user</title>
              <searchPostProcess>timechart avg(added) by user</searchPostProcess>
              <option name="charting.chart">line</option>
          </table>
      </row>

    </form>'''
    
    root = et.fromstring(xml)
    d = SimpleForm()
    d.fromXml(root)
    
    print(et.tostring(d.toXml(), pretty_print=True))
