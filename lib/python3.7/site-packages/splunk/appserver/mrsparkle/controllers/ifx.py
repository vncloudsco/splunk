from __future__ import absolute_import

from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

import logging

logger = logging.getLogger('splunk.appserver.controllers.ifx')
    
class IFXController(BaseController):
    """/ifx"""

    @route('/')
    @expose_page(must_login=True, methods=['GET', 'POST'])
    def index(self, **kwargs):
        logger.warn('Handling a request to the legacy IFX controller, redirecting to the new AFX page.')
        app = kwargs.pop('namespace', 'search')
        return self.redirect_to_url(['app', app, 'field_extractor'], kwargs)