from builtins import object
import logging

logger = logging.getLogger('splunk.models.view_escaping.panel')


class Panel(object):
    '''
    Panel object
    '''

    def __init__(self, rowGrouping=1):
        '''
        Init
        - sets maxLength
        - initialize panelElements

        @type rowGrouping: int
        @param rowGrouping: how many panel elements in this one panel.
        '''
        self.id = None
        self.idGenerated = False
        self.tokenDeps = None
        self.maxLength = rowGrouping
        self.panelElements = []
        self.fieldset = []
        self.title = None
        self.ref = None
        self.app = None
        self.searches = []

    def appendPanelElement(self, panelElement):
        '''
        Add a panelElement to the panel.

        @rtype: boolean
        @return: True if it was added successful and
                 False if there is no more room in this panel
        '''
        if self.maxLength == None or len(self.panelElements) < self.maxLength:
            self.panelElements.append(panelElement)
            return True
        else:
            return False


if __name__ == '__main__':

    import unittest

    class PanelTests(unittest.TestCase):

        def testAddOnePanel(self):
            panel = Panel()
            self.assertTrue(panel.appendPanelElement({}))
            self.assertFalse(panel.appendPanelElement({}))

        def testAddTwoPanel(self):
            panel = Panel(2)
            self.assertTrue(panel.appendPanelElement({}))
            self.assertTrue(panel.appendPanelElement({}))
            self.assertFalse(panel.appendPanelElement({}))

        def testAddAny(self):
            panel = Panel(None)
            self.assertTrue(panel.appendPanelElement({}))
            self.assertTrue(panel.appendPanelElement({}))
            self.assertTrue(panel.appendPanelElement({}))

    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(PanelTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
