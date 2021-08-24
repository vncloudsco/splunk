from __future__ import absolute_import
import logging
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
logger = logging.getLogger('splunk.appserver.mrsparkle.generators')

class ListGeneratorController(BaseController):

    endpoint = None
    
    COUNT = 30
    OFFSET = 0
    SORT_KEY = None
    SORT_DIR = 'asc'
    
    def __init__(self):
        '''Parent class for list generating controllers.'''
        BaseController.__init__(self)
        
    def normalizeSortDir(self, sortDir):
        logger.debug('%s does not implement a normalizeSortDir method.  Returning: %s' % (self.__class__.__name__, sortDir))
        return sortDir

    @route('/')
    @expose_page(handle_api=True)
    def index(self):
        msg = '%s, a list generating controller, did not implement an index method.' % self.__class__.__name__
        logger.debug(msg)
        return msg

