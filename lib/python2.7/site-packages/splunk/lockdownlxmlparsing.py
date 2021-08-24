# lock down lxml per SPL-31061, SPL-90436
import lxml.etree
class NullResolver(lxml.etree.Resolver):
    def resolve(self, url, public_id, context):
        return self.resolve_string('', context)

class SafeXMLParser(lxml.etree.XMLParser):
    """An XML Parser that ignores requests for external entities"""
    def __init__(self, *a, **kw):
        super(SafeXMLParser, self).__init__(*a, **kw)
        self.resolvers.add(NullResolver())

parser = SafeXMLParser()
lxml.etree.set_default_parser(parser)
lxml.etree.UnsafeXMLParser = lxml.etree.XMLParser
lxml.etree.XMLParser = SafeXMLParser
