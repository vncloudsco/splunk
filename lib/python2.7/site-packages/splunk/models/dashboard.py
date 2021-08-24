from builtins import map
import logging

from future.moves.urllib import parse as urllib_parse

import lxml.etree as et
import defusedxml.lxml as safe_lxml

import splunk.util
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, StructuredField
from splunk.models.legacy_views import panel, dashboard

logger = logging.getLogger('splunk.models.dashboard')


# define the max number of panels per row
DEFAULT_DASHBOARD_ROW_SIZE = 2
MAX_DASHBOARD_ROW_SIZE = 3

class Dashboard(SplunkAppObjModel):
    '''
    Represents a simple XML dashboard.  This is a wrapper model class for the
    view objects previously defined in /models/legacy_views.
    '''

    resource = 'data/ui/views'


    #
    # properties
    #

    data = Field('eai:data')
    
    def get_label(self):
        return self._obj.label
    
    def set_label(self, label):
        self._obj.label = label

    label = property(get_label, set_label)
    

    # 
    # constructor
    #
    def __init__(self, namespace, owner, name, entity=None, **kwargs):
        super(Dashboard, self).__init__(namespace, owner, name, entity=entity, **kwargs)
        self._obj  = dashboard.SimpleDashboard()


    #
    # internal adapters
    #

    def from_entity(self, entity):
        super(Dashboard, self).from_entity(entity)
        data = entity['eai:data']
        if data:
            root = safe_lxml.fromstring(splunk.util.toUTF8(data))
            self._obj = dashboard.SimpleDashboard()
            try:
                self._obj.fromXml(root)
            except Exception as e:
                logger.warn('Could not load xml %s' % e)

    def _fill_entity(self, entity, fill_value=''):
        super(Dashboard, self)._fill_entity(entity, fill_value)
        entity['eai:data'] = et.tostring(
            self._obj.toXml(), 
            xml_declaration=True, 
            encoding='utf-8', 
            pretty_print=True)

    def is_default(self):
        return False if self.entity.getLink('remove') else True


    #
    # classmethods
    #

    @classmethod
    def filter_by_can_write_simple_xml(cls, app = None):
        """filter for writable simple xml dashboards"""
        simple_xml_filter = '%s="%s"' % ('eai:data', urllib.parse.unquote_plus('*<dashboard>*'))
        writable_filter = 'eai:acl.can_write="1"'
        exclude_names = 'NOT name="pdf_activity"'
        query = cls.search(simple_xml_filter).search(writable_filter).search(exclude_names)
        if app:
            query = query.filter_by_app(app)
        items = list(query) if query else []
        return [item for item in items if not item.is_default()]

    #
    # panel management
    #

    def create_panel(self, type, saved_search=None, **panel_definition):
        '''
        type: table, chart, html, event or list
        '''
        chart_type = None
        chart_types = [
            'bar',
            'area',
            'column',
            'bubble',
            'pie',
            'scatter',
            'line',
            'radialGauge',
            'fillerGauge',
            'markerGauge',
        ]

        # if the type matches an enriched chart, remap
        if chart_types.count(type) > 0:
            chart_type = type
            type = 'chart'
       
        # calculate desired number of panels that constitute a complete row
        row_count = len(self._obj.rows)
        if row_count == 0:
            expected_row_size = DEFAULT_DASHBOARD_ROW_SIZE
        else:
            expected_row_size = min(MAX_DASHBOARD_ROW_SIZE, sum(map(len, self._obj.rows)) // row_count )

        # if last row still has room, don't add row; otherwise create new row
        if row_count > 0 and len(self._obj.rows[-1]) < expected_row_size:
            pass
        else:
            self._obj.rows.append([])
            self._obj.rowGrouping.append(None)

        if saved_search is not None:
            panel_definition['searchCommand'] = saved_search
            panel_definition['searchMode'] = 'saved'
        
        if chart_type:
            panel_definition.setdefault('options', {})
            panel_definition['options']['charting.chart'] = chart_type

        # generate new panel object
        panel_object = panel.createPanel(type)
        panel_object.fromJsonable(panel_definition)

        # insert into view object into last row
        self._obj.rows[-1].append(panel_object)
        
        # update the internal member
        self.data = et.tostring(self._obj.toXml(), xml_declaration=True, encoding='utf-8', pretty_print=True)
    


    def get_panel(self, panel_sequence):
        '''
        Returns a specific dashboard panel at the given index (panel_sequence)
        in a primitive dictionary format.
        
        This is a wrapper method to the models.legacy_views.panel module.

        Ex:

            {
                blah: blah
            }
        '''

        i,j = self._obj.getPanelPositionBySequence(panel_sequence)
        panel = self._obj.rows[i][j]

        output = panel.toJsonable()
        output['panel_sequence'] = panel_sequence
        return output

    def get_panels(self):
        '''
        Returns a list of dashboard panels in a primitive dictionary format.
        '''

        panels = []
        for row in self._obj.rows:
           for panel in row:
               panel = panel.toJsonable()
               panels.append(panel)
        return panels
            
    def set_panel(self, panel_sequence, panel_class, **panel_definition):
        '''
        Updates an existing dashboard panel at a given index
        '''

        # get the container and panel info
        i,j = self._obj.getPanelPositionBySequence(panel_sequence)
        
        if panel_class == None:
            raise ValueError('Cannot set panel with unknown class; panel_definition=%s' % panel_definition)

        panel_object = self._obj.rows[i][j]
        
        # for now, remove any time terms from saved search mode
        # TODO: revisit when we verify support for this
        if panel_definition.get('searchMode') == 'saved':
            panel_definition['searchEarliestTime'] = None
            panel_definition['searchLatestTime'] = None
        
        # if the class changes, make a new object
        if panel_class != panel_object.matchTagName:
            newPanel = panel.createPanel(panel_class)
            newPanel.fromJsonable(panel_definition)
            self._obj.rows[i][j] = newPanel
        else:
            panel_object.fromJsonable(panel_definition)
                
    

    def delete_panel(self, panel_sequence):
        '''
        Deletes the panel at the specified index
        '''

        i,j = self._obj.getPanelPositionBySequence(panel_sequence)
        self._obj.rows[i].pop(j)
