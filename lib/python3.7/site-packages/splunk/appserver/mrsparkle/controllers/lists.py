from __future__ import absolute_import
import os
import logging

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.appserver.mrsparkle.list_helpers import generators
from splunk.appserver.mrsparkle.lib import util

logger = logging.getLogger('splunk.appserver.controllers.lists')

# Get the generators module path and import all of the ListGeneratorControllers
# underneath it. Eventually we may move these to an external location for end users.
LIST_GENERATOR_PATH = os.path.dirname(os.path.abspath(generators.__file__))

class ListsController(BaseController):
    """
    /lists acts as a meta-endpoint, it loads its underlying endpoints at runtime
    so users can add their own listing endpoints at will.
   
    Adding new list generating controllers:
    Controllers meant to live underneath the /lists controller are normal
    controllers aside from the following exceptions:
    * They inherit from (ListGeneratorController)
    * They wrap their endpoints in the decorator @format_list_response
    * List generating controller endpoints should always return Python lists of
      dict objects like:
        [{'foo':'bar'}, ...]

    How it works:
    The ListsController loads any list_generator modules it finds and attaches the internal
    classes that decend from ListGeneratorController onto the list endpoint.
    Responses are routed through the @format_list_response and are converted into a string,
    allowing the controller endpoint to return Python objects.
    
    Generating the response:
    /lists attempts to return the response in the requested format.  If that format is not available it
    will attempt to inspect any Accept headers in the request and return a valid response based on the acceptible
    formats.  If the response cannot be fulfilled it will return a 406 response with headers revealing the available
    content types.  If a request is made to a list endpoint that does not exist, lists returns a 404
    """

    def __init__(self, path=None):
        BaseController.__init__(self)
        self.addListGeneratingControllers(path=path)

    def addListGeneratingControllers(self, path=None):
        '''
        Find all of the generators (aka specialized controllers that generate lists)
        and load them into the lists controller as normal endpoints.

        Yey for cool routes!
        '''
        path = path or LIST_GENERATOR_PATH
 
        for mod in util.import_from_path(path):
            for c in util.get_module_classes(mod, generators.ListGeneratorController):
                logger.info('List controller loaded: %s' % c.__name__)
                if c.endpoint == None:
                    logger.debug("ListGeneratorController %s does not define an endpoint property." % c.__name__)
                    continue
                else:
                    endpoint_name = c.endpoint
                logger.info('Setting lists/%s' % endpoint_name)
                setattr(self, endpoint_name, c())
 
    @route('/')
    def index(self):
        return "You are at the lists endpoint."

