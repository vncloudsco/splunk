from __future__ import absolute_import

import logging
from splunk.appserver.mrsparkle.lib import error
from splunk.appserver.mrsparkle.lib import util
from splunk.appserver.mrsparkle.controllers.view import ViewController
from splunk.appserver.mrsparkle.lib.decorators import expose_page

logger = logging.getLogger('splunk.appserver.mrsparkle.lib.error')

class ErrorController(ViewController):

    def handle_error(self, **kwargs):
        try:
            if not util.isLite():
                return error.handleError(**kwargs)
            else:
                return self.render_error_page(**kwargs)
        except Exception as e:
            # If anything exception/redirect occurs while rendering the fancy error page, use the safe error page instead
            # This includes redirects when user is not logged in
            logger.info("Reverting to default error page:" + str(e))
            return error.handleError(**kwargs)

    @expose_page()
    def render_error_page(self, **kwargs):
        splunkd = {}
        splunkd['/services/server/info'] = util.getServerInfoPayload()
        if kwargs.get('status', '')[:3] ==  '404':
            errMsg = kwargs.get('message', '')
            logger.info("Masking the original 404 message: '%s' for security reasons" % errMsg)
            kwargs['message'] = 'The page requested could not be found.'
        templateArgs = {
            'app': 'search',
            'page': 'error',
            'dashboard': '',
            'splunkd': splunkd,
            'error_status': kwargs
        }
        return self.render_template('pages/error.html', templateArgs)
