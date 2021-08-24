from builtins import object
import logging
from splunk.util import normalizeBoolean


logger = logging.getLogger('splunk.models.legacy_views.panelElements')


class BasePanel(object):
    """
    Represents a view result display object.
    """

    hasSearch = True

    def __init__(self):
        # init standard panel params
        self.id = None
        self.title = None
        self.layoutPanel = 'results'
        self.autoRun = True
        self.options = {}
        self.intersect = None
        self.simpleDrilldown = {}

        # init standard search configuration params
        self.search = None
        self.searchFieldList = None

        self.comments = []
        self.hasDrilldownTag = False
        self.drilldownComments = []

        self.context = None
        self.tokenDeps = None


class Chart(BasePanel):
    """
    Represents a standard chart display of a search object
    """
    # define the XML tag
    matchTagName = 'chart'

    def __init__(self):
        BasePanel.__init__(self)
        self.selection = None


class Map(BasePanel):
    """
    Represents a map display of a search object
    """
    # define the XML tag
    matchTagName = 'map'


class Table(BasePanel):
    """
    Represents a basic tabular output of search object
    """
    matchTagName = 'table'
    fieldFormats = None
    optionTypeMap = {
        "count": int,
        "dataOverlayMode": str,
        "displayRowNumbers": normalizeBoolean,
        "link.visible": normalizeBoolean,
        "link.search": str,
        "link.viewTarget": str,
        "showPager": normalizeBoolean
    }


class Event(BasePanel):
    """
    Represents a raw event renderer
    """
    matchTagName = 'event'
    optionTypeMap = {
        "count": int,
        "maxLines": int,
        "displayRowNumbers": normalizeBoolean,
        "showPager": normalizeBoolean,
        "wrap": normalizeBoolean
    }


class List(BasePanel):
    """
    Represents a basic list
    """
    matchTagName = 'list'


class Single(BasePanel):
    """
    Represents a single value panel.
    """
    matchTagName = 'single'


class Html(BasePanel):
    """
    Represents a basic HTML content
    """
    matchTagName = 'html'
    hasSearch = False

class Viz(BasePanel):
    """
    Represents a custom visualization panel.
    """
    matchTagName = 'viz'
