from __future__ import absolute_import
from builtins import object

import logging

from splunk.models.view_escaping.panel import Panel

logger = logging.getLogger('splunk.models.view_escaping.row')


class Row(object):

    def __init__(self, rowGrouping=None):
        self.id = None
        self.idGenerated = False
        self.tokenDeps = None
        rowGrouping = rowGrouping or []
        self.panels = []
        logger.debug("Creating row with %s elementd" % rowGrouping)
        for panelSize in rowGrouping:
            logger.debug("Creating panel with %s elements" % panelSize)
            self.panels.append(Panel(panelSize))

    def appendPanelElement(self, panelElement):
        '''
        Append an element to the first panel that has room
        if there is no free spot create a panel and put the element inside
        '''
        for panel in self.panels:
            if panel.appendPanelElement(panelElement):
                break
        else:
            panel = Panel(1)
            self.panels.append(panel)
            return panel.appendPanelElement(panelElement)
        return True


if __name__ == '__main__':

    import unittest

    class RowTests(unittest.TestCase):

        def testRowOnePanelRowOneElement(self):
            row = Row([1])
            self.assertEqual(len(row.panels), 1)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 1)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 2)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 3)

        def testRowTwoPanelRow(self):
            row = Row([2, 1])
            self.assertEqual(len(row.panels), 2)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 2)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 2)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 2)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 3)
            #TODOmelting: don't reach in two levels deep.
            self.assertEqual(len(row.panels[0].panelElements), 2)
            self.assertEqual(len(row.panels[1].panelElements), 1)
            self.assertEqual(len(row.panels[2].panelElements), 1)

        def testRowThreePanelRow(self):
            row = Row([2, 0, 1])
            self.assertEqual(len(row.panels), 3)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels[0].panelElements), 1)
            self.assertEqual(len(row.panels[1].panelElements), 0)
            self.assertEqual(len(row.panels[2].panelElements), 0)
            self.assertEqual(len(row.panels), 3)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels[0].panelElements), 2)
            self.assertEqual(len(row.panels[1].panelElements), 0)
            self.assertEqual(len(row.panels[2].panelElements), 0)
            self.assertEqual(len(row.panels), 3)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels[0].panelElements), 2)
            self.assertEqual(len(row.panels[1].panelElements), 0)
            self.assertEqual(len(row.panels[2].panelElements), 1)
            self.assertEqual(len(row.panels), 3)
            self.assertTrue(row.appendPanelElement({}))
            self.assertEqual(len(row.panels), 4)
            #TODOmelting: don't reach in two levels deep.
            self.assertEqual(len(row.panels[0].panelElements), 2)
            self.assertEqual(len(row.panels[1].panelElements), 0)
            self.assertEqual(len(row.panels[2].panelElements), 1)
            self.assertEqual(len(row.panels[3].panelElements), 1)

    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(RowTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
