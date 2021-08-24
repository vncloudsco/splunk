# standard
from builtins import object
import logging
# contrib
import lxml.etree as et
# splunk
from splunk.models.dashboard import Dashboard
from splunk.models.legacy_views import panel
from splunk import rest

TYPES = {
    'chart': panel.Chart,
    'table': panel.Table,
    'event': panel.Event,
    'list': panel.List,
    'single': panel.Single,
    'html': panel.Html
}

logger = logging.getLogger('splunk.models.dashboard_panel')

class DashboardPanel(object):

    def __init__(self, dashboard_id, intersect, dashboard=None):
        """
        dashboard_id: The splunkd REST path for the resource.
        intersect: A tuple contain the row/column intersect (0 base).
        dashboard: Optional dashboard model object to short-circuit additional Dashboard fetch.
        """
        self.intersect = intersect
        self.errors = []
        if dashboard is None:
            self._dashboard = Dashboard.get(dashboard_id)
            self.panel_model = None
            if len(self._dashboard._obj.rows)-1 < intersect[0]:
                self._dashboard._obj.rows.insert(intersect[0], [])
            self._dashboard._obj.rows[intersect[0]].insert(intersect[0], None)
        else:
            self._dashboard = dashboard
            self.panel_model = self._dashboard._obj.rows[self.intersect[0]][self.intersect[1]]
        self.id = (self._dashboard.id, intersect)

    
    def set_type(self, type):
        """
        type: A name of a supported chart type you would like to set. NOTE this will clobber any existing chart properties you formally had set.
        """
        if TYPES.get(type) is None:
            raise ValueError('Non-supported panel type.')
        self.panel_model = TYPES.get(type)()
    
    def get_type(self):
        """
        The name of the chart tyoe for this panel.
        """
        for type in TYPES:
            if isinstance(self.panel_model, TYPES[type]):
                return type
        return None
    
    def get_dict(self):
        """
        A python dictionary representation of the panel
        """
        return self.panel_model.toJsonable()

    def set_dict(self, data):
        """
        set panel from dict.
        """
        try:
            self.set_type(data.get('type'))
        except Exception:
            self.errors.append('Invalid panel type')
            return False
        try:
            self.panel_model.fromJsonable(data)
        except Exception:
            self.errors.append('Invalid panel data')
            return False
        return True

    def get_xml_str(self, pretty_print=True):
        """
        get xml of a panel.

        TODO: TESTS PLEASE
        """
        return et.tostring(self.panel_model.toXml(), pretty_print=pretty_print)
    
    def set_xml_str(self, xml_str):
        """
        set panel from xml.
        
        TODO: TESTS PLEASE
        """
        try:
            xml = et.fromstring(xml_str)
        except Exception:
            self.errors.append('Invalid XML.')
            return False
        try:
            # TODO:
            # 1) add type detection
            # 2) instantiate appropriate panel class
            # 3) set xml thre the panel object fromXML method
            # 4) peace out
            self.panel_model.fromXml(xml)
        except Exception:
            self.errors.append('Invalid panel XML.')
            return False
        return True

    def add_option(self, k, v):
        """
        Adds an option to a panel.
        NOTE: Clobbers an existing key if it already exists.
        """
        self.panel_model.options[k] = v

    def validate_time(self, time):
        try:
            serverResponse, serverContent = rest.simpleRequest('/services/search/timeparser', getargs={'time': time, 'output_mode':'json'}, rawResult=True)
        except Exception:
            return False
        if serverResponse and serverResponse.status == 200:
            return True
        return False
    
    def save(self, validate_time=False):
        """
        Commit any changes made to a pane via the Dashboard model as the backend proxy.
        """
        is_saved = False
        self.errors = []
        #validate time
        if validate_time and self.panel_model:
            if self.panel_model.searchEarliestTime:
                if self.validate_time(self.panel_model.searchEarliestTime) is False:
                    self.errors.append('Invalid earliest time')
            if self.panel_model.searchLatestTime:
                if self.validate_time(self.panel_model.searchLatestTime) is False:
                    self.errors.append('Invalid latest time')
        self._dashboard._obj.rows[self.intersect[0]][self.intersect[1]] = self.panel_model
        if len(self.errors) == 0:
            is_saved = self._dashboard.passive_save()
            if is_saved is False:
                self.errors = self.errors + self._dashboard.errors
        return is_saved

    def delete(self):
        """
        Delete a panel via the Dashboard model as the backend proxy.
        """
        self.errors = []
        try:
            self._dashboard._obj.rows[self.intersect[0]].pop(self.intersect[1])
        except Exception:
            self.errors.append('Could not find panel to delete.')
            return False
        return self._dashboard.passive_save()
        
    @classmethod
    def get(cls, id, intersect):
        """
        Retrieve a known panel with it's associated splunkd REST path and row/column intersection.
        
        id: The splunkd REST path for the resource.
        intersect: A tuple containing the row/column intersect (0 based).
        """
        dashboard = Dashboard.get(id)
        return DashboardPanel(None, intersect, dashboard=dashboard)
