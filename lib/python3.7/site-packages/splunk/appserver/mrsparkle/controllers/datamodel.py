import logging
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import mako.filters

logger = logging.getLogger('splunk.appserver.controllers.datamodel')

class DataModelController(BaseController):
    """
    Handle file uploading logic for data model 
    """

    @route('/:action=upload')
    @expose_page(methods=['POST'])
    def upload_datamodel_file(self, fileContents=None,  **kw):
        '''
        Handles uploaded files for data models 
        '''
 
        logger.debug('Uploading data model file: %s, contents: %s' % (fileContents.filename, fileContents.value)) 
        escaped_contents = mako.filters.html_escape(fileContents.value)
        response = """
            <html>
                <body>%s</body>
            </html>
        """ % escaped_contents
        return response;  



