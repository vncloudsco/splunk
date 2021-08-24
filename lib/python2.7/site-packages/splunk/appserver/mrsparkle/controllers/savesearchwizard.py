# coding=UTF-8
import cherrypy
import splunk.appserver.mrsparkle # bulk edit
import logging
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.decorators import set_cache_level
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.auth

from splunk.models.saved_search import SavedSearch

logger = logging.getLogger('splunk.appserver.controllers.savesearchwizard')

class SaveSearchWizardController(BaseController):
    @route('/:app/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def new(self, app, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')


        saved_search = SavedSearch(app, owner, **params)
        saved_search.setSummarizationDetails()

        return self.render_template('savesearchwizard/new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def create(self, app, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.metadata.sharing = params.get('sharing', 'user')
        
 
        #TODO: remove this
        #saved_search.auto_summarize.cron_schedule = '*/10 * * * *'

        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['savesearchwizard', app, 'success'], _qs=dict(id=saved_search.id)), 303)

        saved_search.setSummarizationDetails()
        return self.render_template('savesearchwizard/new.html', dict(app=app, saved_search=saved_search))
        

    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('savesearchwizard/success.html', dict(app=app, saved_search=saved_search))
