from __future__ import division
from builtins import range
from builtins import object

import math
import logging

logger = logging.getLogger('splunk.appserver.lib.paginator')

class Google(object):
    """
    Class to enable pagination .
    Based on Google search pagination pattern - http://google.com

    p = Google(10000)
    if p.previous_exists():
        logger.debug("Can have a previous page")
    for page in p.page_range:
        logger.debug("Page: %s" % page)
        logger.debug("This page is active:%s" % p.active(page))
    if p.next_exists():
        logger.debug("Can have a next page")
    """
    def __init__(self, item_count, max_items_page=10, max_pages=10, item_offset=0):
        """
        Args

        item_count: The total count of items to page through.
        max_items_page: The maximum amount of items to display per page.
        max_pages: The maximum amount of pages.
        item_offset: A zero-index offset used to denote your position relative to pages.
        """
        self.item_count = item_count
        self.max_items_page = max_items_page if max_items_page else 10
        self.max_pages = max_pages
        self.item_offset = item_offset
        self.total_pages = self.__total_pages()
        self.active_page = self.__active_page()
        self.page_range = self.__page_range()

    def __page_range(self):
        """
        A non-zero starting list of numbers representing a page range respecting max_items_page and max_pages constraints.
        """
        if self.total_pages==1:
            return []
        else:
            page_mid_point = self.max_pages // 2
        if self.active_page<=page_mid_point:
            start = 1
            end = min(self.total_pages, self.max_pages) + 1
        else:
            end = min(self.active_page+page_mid_point, self.total_pages) + 1
            start =  max(end - self.max_pages, 1)
        return list(range(start, end))
         
    def __total_pages(self):
        return (self.item_count + self.max_items_page - 1) // self.max_items_page
    
    def __active_page(self):
        return int(math.floor((self.item_offset/self.max_items_page) + 1))

    def next_exists(self):
        if len(self.page_range) == 0:
            return False;
        if self.active_page < self.total_pages:
            return True
        else:
            return False

    def next_offset(self):
        if self.next_exists():
            page = self.active_page + 1
            return self.page_item_offset(page)
        else:
            return -1

    def previous_exists(self):
        if len(self.page_range) == 0:
            return False
        if self.active_page > 1:
            return True
        else:
            return False

    def previous_offset(self):
        if self.previous_exists():
            page = self.active_page - 1
            return self.page_item_offset(page)
        else:
            return -1

    def page_item_offset(self, page_num):
        return (self.max_items_page * page_num) - self.max_items_page

    def is_active_page(self, page_num):
        if page_num==self.active_page:
            return True
        else:
            return False


# ////////////////////////////////////////////////////////////////////////////
# Test routines
# ////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':

    import unittest

    class GooglePaginatorTests(unittest.TestCase):

        def testOnePage(self):
            pagination = Google(9)
            self.assertEqual(len(pagination.page_range), 0)
            self.assertEqual(pagination.total_pages, 1)
            self.assertFalse(pagination.next_exists())
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(10)
            self.assertEqual(len(pagination.page_range), 0)
            self.assertEqual(pagination.total_pages, 1)
            self.assertFalse(pagination.next_exists())
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))

        def testTwoPages(self):
            pagination = Google(11)
            self.assertEqual(len(pagination.page_range), 2)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 2)
            self.assertEqual(pagination.total_pages, 2)
            self.assertTrue(pagination.next_exists())
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(11, item_offset=9)
            self.assertEqual(len(pagination.page_range), 2)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 2)
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(11, item_offset=10)
            self.assertEqual(len(pagination.page_range), 2)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 2)
            self.assertTrue(pagination.is_active_page(2))

        def testGreaterThanTwoPages(self):
            pagination = Google(99)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertEqual(pagination.total_pages, 10)
            self.assertTrue(pagination.next_exists())
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))
            self.assertEqual(len(pagination.page_range), 10)

            pagination = Google(100)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertEqual(pagination.total_pages, 10)
            self.assertTrue(pagination.next_exists())
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(101)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertEqual(pagination.total_pages, 11)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 10)
            self.assertFalse(pagination.previous_exists())
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(101, item_offset=9)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertEqual(pagination.total_pages, 11)
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(101, item_offset=10)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertEqual(pagination.total_pages, 11)
            self.assertTrue(pagination.is_active_page(2))

            pagination = Google(101, item_offset=99)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 2)
            self.assertEqual(pagination.page_range[-1], 11)
            self.assertEqual(pagination.total_pages, 11)
            self.assertTrue(pagination.is_active_page(10))

            pagination = Google(101, item_offset=100)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 2)
            self.assertEqual(pagination.page_range[-1], 11)
            self.assertEqual(pagination.total_pages, 11)
            self.assertTrue(pagination.is_active_page(11))

            pagination = Google(53, item_offset=50)
            self.assertEqual(len(pagination.page_range), 6)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 6)
            self.assertEqual(pagination.total_pages, 6)
            self.assertTrue(pagination.is_active_page(6))

        def testFlow(self):
            item_count = 1001
            pagination = Google(item_count)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertFalse(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), -1)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 10)
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(item_count, item_offset=10)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 0)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 20)
            self.assertTrue(pagination.is_active_page(2))

            pagination = Google(item_count, item_offset=40)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 1)
            self.assertEqual(pagination.page_range[-1], 10)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 30)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 50)
            self.assertTrue(pagination.is_active_page(5))

            pagination = Google(item_count, item_offset=50)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 2)
            self.assertEqual(pagination.page_range[-1], 11)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 40)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 60)
            self.assertTrue(pagination.is_active_page(6))

            pagination = Google(item_count, item_offset=60)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 3)
            self.assertEqual(pagination.page_range[-1], 12)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 50)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 70)
            self.assertTrue(pagination.is_active_page(7))

            pagination = Google(item_count, item_offset=990)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 92)
            self.assertEqual(pagination.page_range[-1], 101)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 980)
            self.assertTrue(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), 1000)
            self.assertTrue(pagination.is_active_page(100))

            pagination = Google(item_count, item_offset=1000)
            self.assertEqual(len(pagination.page_range), 10)
            self.assertEqual(pagination.page_range[0], 92)
            self.assertEqual(pagination.page_range[-1], 101)
            self.assertTrue(pagination.previous_exists())
            self.assertEqual(pagination.previous_offset(), 990)
            self.assertFalse(pagination.next_exists())
            self.assertEqual(pagination.next_offset(), -1)
            self.assertTrue(pagination.is_active_page(101))

        def testOffset(self):
            pagination = Google(11)
            self.assertEqual(pagination.page_item_offset(1), 0)
            self.assertEqual(pagination.page_item_offset(2), 10)
            self.assertEqual(pagination.previous_offset(), -1)
            self.assertEqual(pagination.next_offset(), 10)
            self.assertTrue(pagination.is_active_page(1))

            pagination = Google(200, item_offset=199)
            self.assertEqual(pagination.previous_offset(), 180)
            self.assertEqual(pagination.next_offset(), -1)
            self.assertTrue(pagination.is_active_page(20))

            pagination = Google(200, item_offset=189)
            self.assertEqual(pagination.previous_offset(), 170)
            self.assertEqual(pagination.next_offset(), 190)
            self.assertTrue(pagination.is_active_page(19))


    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(GooglePaginatorTests))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
