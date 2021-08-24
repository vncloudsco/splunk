# coding=UTF-8
from __future__ import absolute_import
import cherrypy

import logging
logger = logging.getLogger('splunk.appserver.controllers.embed')
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route

class EmbedController(BaseController):
    
    @route('/')
    @set_cache_level('never')
    @expose_page(must_login=False, methods='GET', embed=True)
    def index(self, **params):
        cherrypy.response.headers.pop('X-Frame-Options', None)
        data = {
            'app': '-',
            'page': 'embed',
            'splunkd': {},
            'oid': params.get('oid', None),
        }
        return self.render_template('pages/base.html', data)

