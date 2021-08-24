# coding=UTF-8
import cherrypy
import logging
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.models.saved_search import SavedSearch
import splunk.pdf.availability 

logger = logging.getLogger('splunk.appserver.controllers.scheduledigestwizard')

class ScheduleDigestWizardController(BaseController):
    def step1_from_ui(self, params, saved_search):
        saved_search.schedule.is_scheduled = True
        saved_search.dispatch.earliest_time = params['dispatch.earliest_time']
        saved_search.dispatch.latest_time = params['dispatch.latest_time']
        
        ui_schedule = params.get('ui_schedule')
        if ui_schedule == '1h':
            saved_search.schedule.cron_schedule = '0 * * * *'
        elif ui_schedule == '1d':
            saved_search.schedule.cron_schedule = '0 0 * * *'
        elif ui_schedule == '1w':
            saved_search.schedule.cron_schedule = '0 0 * * 6'
        elif ui_schedule == '1m':
            saved_search.schedule.cron_schedule = '0 0 1 * *'
        else:
            saved_search.schedule.cron_schedule = params.get('ui_cron')
    
    def step1_to_ui(self, saved_search):
        if saved_search.schedule.cron_schedule == '0 * * * *':
            saved_search.ui_schedule = '1h'
        elif saved_search.schedule.cron_schedule == '0 0 * * *':
            saved_search.ui_schedule = '1d'
        elif saved_search.schedule.cron_schedule == '0 0 * * 6':
            saved_search.ui_schedule = '1w'
        elif saved_search.schedule.cron_schedule == '0 0 1 * *':
            saved_search.ui_schedule = '1m'
        else:
            saved_search.ui_schedule = 'cron'
    
    @route('/:app/:step=step1/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_new(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.ui_schedule = None
        return self.render_template('scheduledigestwizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_create(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.is_disabled = True        
        self.step1_from_ui(params, saved_search)
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['scheduledigestwizard', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        self.step1_to_ui(saved_search)
        return self.render_template('scheduledigestwizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=edit')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_edit(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        self.step1_to_ui(saved_search)
        return self.render_template('scheduledigestwizard/step1_edit.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        self.step1_from_ui(params, saved_search)
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['scheduledigestwizard', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        self.step1_to_ui(saved_search)
        return self.render_template('scheduledigestwizard/step1_edit.html', dict(app=app, saved_search=saved_search))

    def step2_from_ui(self, params, saved_search):    
        if not saved_search.action.script.enabled:
            saved_search.action.script.filename = None
        
        # assume that email is not enabled
        saved_search.action.email.format = None
        saved_search.action.email.sendresults = None
        saved_search.action.email.sendpdf = None
        saved_search.action.email.inline = None

        if not saved_search.action.email.enabled:
            return

        ui_include_enabled = params.get('ui_include_enabled')
        if ui_include_enabled is None:
            return

        # enable those fields as appropriate for ui_include_type
        ui_include_type = params.get('ui_include_type')
        if ui_include_type=='csv':
            saved_search.action.email.format = 'csv'
            saved_search.action.email.sendresults = True
        elif ui_include_type=='inline':
            saved_search.action.email.format = 'html'
            saved_search.action.email.sendresults = True
            saved_search.action.email.inline = True
        elif ui_include_type=='pdf':
            saved_search.action.email.format = 'pdf'
            saved_search.action.email.sendresults = True
            saved_search.action.email.sendpdf = True


    def step2_to_ui(self, saved_search):
        saved_search.ui_include_enabled = False
        saved_search.ui_include_type = None

        if saved_search.action.email.sendresults:
            if saved_search.action.email.format=='html':
                saved_search.ui_include_enabled = True
                saved_search.ui_include_type = 'inline'
            elif saved_search.action.email.format=='csv':
                saved_search.ui_include_enabled = True
                saved_search.ui_include_type = 'csv'
        elif saved_search.action.email.sendpdf:
            saved_search.ui_include_enabled = True
            saved_search.ui_include_type = 'pdf'

    @route('/:app/:action=step2')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step2_edit(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.ui_allow_pdf = splunk.pdf.availability.is_available(cherrypy.session['sessionKey'])
        self.step2_to_ui(saved_search)
        return self.render_template('scheduledigestwizard/step2.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step2/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step2_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        saved_search.action.email.enabled = False if params.get('action.email.enabled') is None else True
        saved_search.action.script.enabled = False if params.get('action.script.enabled') is None else True            
        self.step2_from_ui(params, saved_search)
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['scheduledigestwizard', app, 'step3'], _qs=dict(id=saved_search.id)), 303)
        saved_search.ui_allow_pdf = splunk.pdf.availability.is_available(cherrypy.session['sessionKey'])
        self.step2_to_ui(saved_search)
        return self.render_template('scheduledigestwizard/step2.html', dict(app=app, saved_search=saved_search))
    

    @route('/:app/:action=step3')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step3_edit(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('scheduledigestwizard/step3.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step3/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step3_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        saved_search.is_disabled = False
        metadata_sharing = params.get('metadata.sharing')
        if metadata_sharing == 'user':
            try:
                saved_search.unshare()
            except Exception:
                saved_search.errors = [_('Search %s cannot be private because it already exists. Try using another search name by cancelling this alert and creating a new one.') % saved_search.name ]
        elif metadata_sharing == 'app':
            try:
                saved_search.share_app()
            except Exception:
                saved_search.errors = [_('Search %s cannot be shared because it already exists. Try using another search name by cancelling this alert and creating a new one.') % saved_search.name ]
        if not saved_search.errors and saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['scheduledigestwizard', app, 'success'], _qs=dict(id=saved_search.id)), 303)
        return self.render_template('scheduledigestwizard/step3.html', dict(app=app, saved_search=saved_search))

    
    @route('/:app/:action=delete')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def delete(self, app, action, **params):
        SavedSearch.get(params.get('id')).delete()
        raise cherrypy.HTTPRedirect(self.make_url(['scheduledigestwizard', app, 'step1', 'new']), 303)   
    
    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('scheduledigestwizard/success.html', dict(app=app, saved_search=saved_search))
