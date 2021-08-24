from builtins import object
import logging, splunk.bundle
from operator import itemgetter

logger = logging.getLogger('splunk.appserver.lib.eventrenderer')

RENDERER_SELECT_FIELD = 'eventtype'
TEMPLATE_APPSCOPE_SEPARATOR = ':'
CONF_NAME = 'event_renderers'
# This class is an abstraction from something that should have been a class. I do not take responsibility for the patterns. Feel free to re-write it. - Carl

class Custom(object):
    
    def __init__(self, namespace=None):
        '''
        Config wrapper for event renderers. Normlizes pathing and selection of appropriate renderer based on priority and matching eventtype.
        '''
        self.conf = self.getConf(namespace)
        self.mapping = self.getMapping(self.conf)
        self.priority = self.getPriority(self.mapping)
        logger.info('_getRenderers - loaded custom event renderers: self.mapping=%s self.priority=%s' % (self.mapping, self.priority))

    def getConf(self, namespace):
        '''
        Pre-process a Conf object into a a more primitive dict along with 
        some formatting routines.
        '''
        bundleConf = splunk.bundle.getConf(CONF_NAME, namespace=namespace)
        conf = {}
        for stanza in bundleConf.findStanzas():
            conf.setdefault(stanza, {})
            for key in bundleConf[stanza]:
                if key=='template':
                    conf[stanza][key] = self.getTemplate(bundleConf[stanza].get(key, ''), namespace)
                elif key=='priority':
                    conf[stanza][key] = int(bundleConf[stanza].get(key, 0))
                else:
                    conf[stanza][key] = bundleConf[stanza][key]
        return conf

    def getTemplate(self, template, namespace):
        '''
        Generate a proper formatted mako load path. Ignore absolute "//" prefix paths or generate appropriate app specific paths based on
        simplified file name only. 
        
        Args:
        template The fully qualified path or short file name for lookup. 
        '''
        if not template.startswith('//'):
            template = "/%s%s/event_renderers/%s" % (namespace, TEMPLATE_APPSCOPE_SEPARATOR, template)
        return template

    def getMapping(self, conf):
        '''
        Build the map between the a field and their custom renderers
        renderMap = {<eventtype>: <template_path>, ... }
        '''
        mapping = {}
        for stanza in conf:
            if RENDERER_SELECT_FIELD in conf[stanza]:
                key = conf[stanza][RENDERER_SELECT_FIELD]
                if key in mapping and mapping[key].get('priority')>conf[stanza].get('priority'):
                    continue
                mapping[ key ] = conf[stanza]
            else:
                mapping['default'] = conf['default']
        return mapping

    def getPriority(self, mapping):
        ''''
        Make a sorted list of renderers by priority, highest to lowest
        
        Args
        mapping Field/Custom renderer map.
        '''
        priority = sorted([ (k, v['priority']) for k, v in mapping.items() ], key=itemgetter(1), reverse=True )
        priority = [ k for k, v in priority ]
        return priority

    def getRenderer(self, fields):
        '''
        Based on an events current fields return the matching renderer.__class__
        
        Args:
        fields A dictionary of fields where a field name could have multiple values.
        '''
        # get the events field values and turn it into a python list
        fieldValues = fields.get(RENDERER_SELECT_FIELD, None)
        if fieldValues is None: return self.conf['default']
        fieldValuesList = [x.value for x in fieldValues._fieldValue]
        # walk down the list and find the renderer with the highest priority
        # note that the renderer's name should match a field value
        renderer = None
        fieldValue = None
        for renderer in self.priority:
            if renderer in fieldValuesList:
                fieldValue = renderer
                break
        # if not custom renderer was found, return the event with default rendering
        if fieldValue == None: return self.conf['default']
        return self.mapping[fieldValue]

    
if __name__ == '__main__':
    
    import unittest
    import splunk.search as search
    import splunk.auth as auth
    import time
    
    class CustomTests(unittest.TestCase):
        
        def testSimple(self):
            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = search.dispatch('windbag', sessionKey=sessionKey)
            time.sleep(1)
            event = job.results[0]
            custom = Custom(namespace='search')
            renderer = custom.getRenderer(event.fields)
            self.assertEquals(renderer.get('eventtype', None), '')
            self.assertEquals(renderer.get('priority'), 0)
            self.assertEquals(renderer.get('template'), '//results/EventsViewer_default_renderer.html')
            self.assertEquals(renderer.get('css_class', None), '')
            
        def testDuplicateEventtypePriority(self):
            sessionKey = auth.getSessionKey('admin', 'changeme')
            job = search.dispatch('| windbag | eval eventtype="testeventtype"', sessionKey=sessionKey)
            time.sleep(1)
            event = job.results[0]
            conf = splunk.bundle.getConf('event_renderers', sessionKey=sessionKey, namespace='search')

            conf.beginBatch()
            conf['event_renderer_test1']['eventtype'] = 'testeventtype'
            conf['event_renderer_test1']['priority'] = 300
            conf['event_renderer_test1']['css_class'] = 'testclass1'
            conf['event_renderer_test2']['eventtype'] = 'testeventtype'
            conf['event_renderer_test2']['priority'] = 400
            conf['event_renderer_test2']['css_class'] = 'testclass2'
            conf.commitBatch()
            custom = Custom(namespace='search')
            renderer = custom.getRenderer(event.fields)
            self.assertEquals(renderer.get('eventtype'), 'testeventtype')
            self.assertEquals(renderer.get('priority'), 400)
            self.assertEquals(renderer.get('template'), '//results/EventsViewer_default_renderer.html')
            self.assertEquals(renderer.get('css_class'), 'testclass2')

            conf.beginBatch()
            conf['event_renderer_test1']['eventtype'] = 'testeventtype'
            conf['event_renderer_test1']['priority'] = 500
            conf['event_renderer_test1']['css_class'] = 'testclass1'
            conf['event_renderer_test2']['eventtype'] = 'testeventtype'
            conf['event_renderer_test2']['priority'] = 400
            conf['event_renderer_test2']['css_class'] = 'testclass2'
            conf.commitBatch()
            custom = Custom(namespace='search')
            renderer = custom.getRenderer(event.fields)
            self.assertEquals(renderer.get('eventtype'), 'testeventtype')
            self.assertEquals(renderer.get('priority'), 500)
            self.assertEquals(renderer.get('template'), '//results/EventsViewer_default_renderer.html')
            self.assertEquals(renderer.get('css_class'), 'testclass1')

    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(CustomTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

                    
