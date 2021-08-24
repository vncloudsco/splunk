# coding=UTF-8
import cherrypy
import logging
import splunk.appserver.mrsparkle # bulk edit
from splunk.models.saved_search import SavedSearch
from splunk.models.server_config import PDFConfig
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.auth

logger = logging.getLogger('splunk.appserver.controllers.alertswizard')

class AlertsWizardController(BaseController):
    @route('/:app/:step=step1/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_new(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        return self.render_template('alertswizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_create(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.metadata.sharing = params.get('sharing', 'user')
        saved_search.is_disabled = True
        # set a default comparator otherwise always will be the first selected
        saved_search.alert.type = 'number of events'
        saved_search.alert.comparator = 'greater than'
        saved_search.alert.threshold = '0'
        # set some default values - we know this will be an alert so schedule it
        # this way we get some default values set by the backend
        saved_search.schedule.is_scheduled  = True
        saved_search.schedule.cron_schedule = '0 */12 * * *'
        saved_search.alert.suppress.enabled = None
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizard', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        return self.render_template('alertswizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=edit')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_edit(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('alertswizard/step1_edit.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        if params.get('sharing')=='app':
            try:
                saved_search.share_app()
            except Exception:
                saved_search.errors = [_('Search %s cannot be shared because it already exists. Try using another search name by cancelling this alert and creating a new one.') % saved_search.name ]
        else:
            try:
                saved_search.unshare()
            except Exception:
                saved_search.errors = [_('Search %s cannot be private because it already exists. Try using another search name by cancelling this alert and creating a new one.') % saved_search.name ]
        if not saved_search.errors and saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizard', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        return self.render_template('alertswizard/step1_edit.html', dict(app=app, saved_search=saved_search))


    @route('/:app/:action=step2')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step2_edit(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('alertswizard/step2.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step2/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step2_update(self, app, step, action, **params):
        errors = []
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        alert_preset = params.get('alert_preset')
        digest_mode = params.get('alert.digest_mode')
        saved_search.alert.digest_mode = digest_mode
        if alert_preset == 'cron':
            saved_search.schedule.cron_schedule = params.get('alert_cron')
        else:
            saved_search.schedule.cron_schedule = alert_preset
        if params.get('saved_search.alert.suppress.enabled'):
            saved_search.alert.suppress.enabled = True
            if digest_mode == '0':
                saved_search.alert.suppress.fieldlist = params.get('alert.suppress.fields')
        else:
            saved_search.alert.suppress.enabled = False
        saved_search.alert.suppress.period = params.get('suppress_value', '') + params.get('suppress_unit', '')
        if params.get('alert.expires') == 'custom':
            saved_search.alert.expires = params.get('expires_value', '') + params.get('expires_unit', '')
        saved_search.schedule.is_scheduled = True
        if params.get('alert.type')=='custom':
            if not params.get('alert.condition'):
                errors.append(_('Conditional search is a required field'))
            saved_search.alert.threshold = None
            saved_search.alert.comparator = None
        elif params.get('alert.type')=='always':
            saved_search.alert.condition = None
            saved_search.alert.threshold = None
            saved_search.alert.comparator = None
        else:
            saved_search.alert.condition = None
        if saved_search.passive_save() and len(errors)==0:
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizard', app, 'step3'], _qs=dict(id=saved_search.id)), 303)
        saved_search.errors = saved_search.errors + errors
        return self.render_template('alertswizard/step2.html', dict(app=app, saved_search=saved_search))
    

    @route('/:app/:action=step3')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step3_edit(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        pdf_config = PDFConfig.get()
        email_results_type = None
        if saved_search.action.email.format == 'html':
            saved_search.action.email.format = 'inline'
        elif saved_search.action.email.sendpdf:
            saved_search.action.email.format = 'pdf'
        # first time nudge them not to track if always was selected
        saved_search.alert.track = False if saved_search.alert.type=='always' else True
        return self.render_template('alertswizard/step3.html', dict(app=app, email_results_type=email_results_type, saved_search=saved_search, pdf_config=pdf_config))

    @route('/:app/:step=step3/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step3_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        saved_search.action.rss.enabled = False if params.get('action.rss.enabled') is None else True
        saved_search.action.script.enabled = False if params.get('action.script.enabled') is None else True
        saved_search.action.email.enabled = False if params.get('action.email.enabled') is None else True
        email_results_type = params.get('email_results_type')
        if email_results_type == 'csv':
            saved_search.action.email.format = 'csv'
            saved_search.action.email.sendresults = True
            saved_search.action.email.inline = False
        elif email_results_type == 'inline':
            saved_search.action.email.format = 'html'
            saved_search.action.email.sendresults = True
            saved_search.action.email.inline = True
        elif email_results_type == 'pdf':
            saved_search.action.email.format = None
            saved_search.action.email.sendresults = False
            saved_search.action.email.sendpdf = True
        elif email_results_type == 'raw' or email_results_type == 'plain':
            saved_search.action.email.format = email_results_type
            saved_search.action.email.sendresults = True
            saved_search.action.email.inline = True
        saved_search.alert.track = False if params.get('alert.track') is None else True
        saved_search.is_disabled = False
        has_action = saved_search.action.email.enabled or saved_search.action.rss.enabled or saved_search.action.script.enabled or saved_search.alert.track
        if saved_search.passive_save() and has_action:
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizard', app, 'success'], _qs=dict(id=saved_search.id)), 303)
        pdf_config = PDFConfig.get()
        if has_action is False:
            saved_search.errors.append(_('Please select at least one action'))
        return self.render_template('alertswizard/step3.html', dict(app=app, email_results_type=email_results_type, saved_search=saved_search, pdf_config=pdf_config))

    
    @route('/:app/:action=delete')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def delete(self, app, action, **params):
        SavedSearch.get(params.get('id')).delete()
        raise cherrypy.HTTPRedirect(self.make_url(['alertswizard', app, 'step1', 'new']), 303)   
    
    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('alertswizard/success.html', dict(app=app, saved_search=saved_search))
