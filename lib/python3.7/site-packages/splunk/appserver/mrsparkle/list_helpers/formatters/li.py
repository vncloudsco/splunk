import logging
import cgi
import splunk.util
from splunk.appserver.mrsparkle.list_helpers.formatters import BaseFormatter

logger = logging.getLogger('splunk.appserver.mrsparkle.list_helpers.formatters.li')

class LiFormatter(BaseFormatter):
    
    formats = 'li'
    
    def getFieldList(self):
        fields = self.params.get('field_list', False)
        if fields:
            return fields.split(',')
        return False
    
    def format(self):
        response = []
        field_list = self.getFieldList()
        
        for elem in self.response:
            li = ['<li>']
            if field_list:
                for field in field_list:
                    if field in elem:
                        li.append('<span class="%s">%s</span> ' % (cgi.escape(splunk.util.unicode(field)), cgi.escape(splunk.util.unicode(elem[field]))))
                    else:
                        logger.warn('Cannot find field "%(field)s" in the response element %(elem)s.' % {'field': field, 'elem': elem})
            else:
                for k, v in elem.items():
                    li.append('<span class="%s">%s</span> ' % (cgi.escape(splunk.util.unicode(k)),
                                                               cgi.escape(splunk.util.unicode(v))))
            li.append('</li>')
            response.append(''.join(li))
        return '\n'.join(response)
