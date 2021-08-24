#   Version 4.0
import splunk.Intersplunk as si
import sys
if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from StringIO import StringIO
from lxml import etree
import lxml
import defusedxml.lxml as safe_lxml

def tostr(node):
    if isinstance(node, lxml.etree._Element):
        if len(node.getchildren()) == 0:
            return node.text or "Null"
        return etree.tostring(node)
    return str(node)

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        defaultval = options.get('default', None)
        field = options.get('field', '_raw')
        outfield = options.get('outfield', 'xpath')
        if len(keywords) != 1:
            si.generateErrorResults('Requires exactly one path argument.')
            exit(0)
        path = keywords[0]
        # Support for searching with absolute path
        if len(path) > 1 and path[0] == '/' and path[1] != '/':
            path = '/data' + path
        results,dummyresults,settings = si.getOrganizedResults()
        # for each results
        for result in results:
            # get field value
            myxml = result.get(field, None)
            added = False
            if myxml != None:
                # make event value valid xml
                myxml = "<data>%s</data>" % myxml
                try:
                    et = safe_lxml.parse(StringIO(myxml))
                    nodes = et.xpath(path)
                    values = [tostr(node) for node in nodes]
                    result[outfield] = values
                    added = True
                except Exception as e:
                    pass # consider throwing exception and explain path problem
                
            if not added and defaultval != None:
                result[outfield] = defaultval
                
        si.outputResults(results)
    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
