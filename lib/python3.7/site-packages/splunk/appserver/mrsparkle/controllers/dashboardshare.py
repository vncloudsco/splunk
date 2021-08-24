# coding=UTF-8
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import logging

logger = logging.getLogger('splunk.appserver.controllers.dashboardshare')

class DashboardShareController(BaseController):
    @route('/:action=new')
    @expose_page(must_login=True, methods='GET')
    def edit(self, action, **params):
        template_args = {}
        return self.render_template('dashboardshare/new.html', template_args)

    @route('/:action=create')
    @expose_page(must_login=True, methods='POST')
    def update(self, action, **params):
        template_args = {}
        success = True
        if success is False:
            return self.render_template('dashboardshare/new.html', template_args)
        return self.render_template('dashboardshare/success.html')

