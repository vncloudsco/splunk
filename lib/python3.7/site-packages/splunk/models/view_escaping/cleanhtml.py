import logging
from random import randint
import time
import sys

import lxml.html as html
from lxml.html import clean

logger = logging.getLogger('splunk.models.view_escaping')
             
def cleanHtmlMarkup(htmlStr):
    if htmlStr is None or htmlStr.strip() == '':
        return htmlStr
    logger.debug("Cleaning HTML string=%s", htmlStr)
    if sys.version_info > (3, 0) and isinstance(htmlStr, bytes):
        htmlStr = htmlStr.decode()
    cleaner = html.clean.Cleaner(comments=False,
                                 links=False,
                                 meta=False,
                                 page_structure=False,
                                 processing_instructions=False,
                                 embedded=False,
                                 frames=False,
                                 forms=False,
                                 annoying_tags=False,
                                 remove_unknown_tags=False,
                                 safe_attrs_only=False)

    # SPL-77044
    # Dirty workaround to retain dollar signs ($) in the cleaned output without patching the lxml.html.clean module
    dollarReplacement = None
    while True:
        dollarReplacement = "__DOLLAR%d%d__" % (int(time.time() * 1000), randint(10000, 99999))
        if not dollarReplacement in htmlStr:
            break

    htmlStr = htmlStr.replace("$", dollarReplacement)

    frag = html.fragment_fromstring(htmlStr, create_parent=True)
    cleaner(frag)
    result = html.tostring(frag, )
    if sys.version_info > (3, 0) and isinstance(result, bytes):
        result = result.decode()
    result = result.replace(dollarReplacement, "$")
    return unwrapFragment(result)


def unwrapFragment(htmlStr):
    return htmlStr[5:-6] if htmlStr[0:5] == '<div>' and htmlStr[-6:] == '</div>' else htmlStr


if __name__ == "__main__":
    import unittest

    class HtmlCleanupTests(unittest.TestCase):
        def testCleanupSimpleHTML(self):
            self.assertEqual(
                "foobar",
                cleanHtmlMarkup("foobar")
            )

        def testCleanupRetainsDollarSignsInUrls(self):
            self.assertEqual(
                '<a href="foo?bar=$token$">link</a>',
                cleanHtmlMarkup('<a href="foo?bar=$token$">link</a>')
            )

        def testRemovesScripts(self):
            self.assertEqual(
                '<p>some text</p>',
                cleanHtmlMarkup('<p>some text</p><script>foo</script>')
            )
            
        def testEmptyHTML(self):
            self.assertEqual(None, cleanHtmlMarkup(None))
            self.assertEqual('', cleanHtmlMarkup(''))

    loader = unittest.TestLoader()
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        loader.loadTestsFromTestCase(HtmlCleanupTests),
    ]))
