from builtins import object
import os
import logging
import cherrypy
from splunk.appserver.mrsparkle.lib import util
from splunk.appserver.mrsparkle.list_helpers.formatters import BaseFormatter

logger = logging.getLogger('splunk.appserver.mrsparkle.list_helpers.formatters')

FORMATTERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'formatters')

class FormatterMapper(object):
    
    _inst = None
    
    def __new__(cls, *args, **kwargs):
        if cls._inst == None:
            cls._inst = object.__new__(cls, *args, **kwargs)
            
            cls._inst.map = {}
            cls._inst.buildFormatterMap()
        return cls._inst

    def __init__(self):
        '''Singleton that builds a map of the formatters classes based on FORMATTERS_PATH.'''
        pass
        
    def getMap(self):
        return self.map
        
    def buildFormatterMap(self, path=None):
        '''
        Creates a simple map of responses using a response formater's handles property.
        For now it's not smart about collisions; last in gets priority.
        '''
        self.map = {}
        if path == None:
            path = FORMATTERS_PATH
            
        for mod in util.import_from_path(path):
            for c in [c for c in util.get_module_classes(mod, BaseFormatter) if not c == BaseFormatter]:
                logger.debug("Loading formatter %s." % c.__name__)
                if isinstance(c.formats, str):
                    self.map[c.formats] = c
                elif isinstance(c.formats, list):
                    for format in c.formats:
                        self.map[format] = c
                elif c.formats == None:
                    logger.error("Formatter class %s does not implement a 'formats' property. Skipping it." % c.__name__)
        return self.map
        
if not __name__ == '__main__':
    FormatterMapper() # tap the singleton to build the map
