# coding=UTF-8
import re
import cherrypy
import logging

from splunk.models.saved_search import SavedSearch
import splunk.pdf.availability
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk.appserver.controllers.alertswizardv2')

class AlertsWizardV2Controller(BaseController):
    
    def step1_from_ui(self, params, saved_search):
        ui_howoften = params.get('ui_howoften')
        saved_search.schedule.is_scheduled = True
        saved_search.schedule.cron_schedule = '* * * * *'
        if ui_howoften == 'realtime':
            saved_search.dispatch.earliest_time = 'rt'
            saved_search.dispatch.latest_time = 'rt'
            saved_search.alert.type = 'always'
            saved_search.alert.digest_mode = False
            saved_search.alert.track = False
            saved_search.alert.suppress.enabled = None
            # no need for suppression here, all-time real-time alerts purge the 
            # accummulated results after each alert triggering
            return

        saved_search.alert.digest_mode = True
        saved_search.alert.track = True
        if saved_search.alert.type=='custom' and saved_search.alert.condition=='':
            saved_search.errors.append(_('Custom condition is required.'))
        if ui_howoften == 'schedule':
            ui_schedule = params.get('ui_schedule')
            if ui_schedule == '1h':
                saved_search.schedule.cron_schedule = '0 * * * *'
                saved_search.dispatch.earliest_time = '-1h@h'
                saved_search.dispatch.latest_time = '@h'
            elif ui_schedule == '1d':
                saved_search.schedule.cron_schedule = '0 0 * * *'
                saved_search.dispatch.earliest_time = '-1d@d'
                saved_search.dispatch.latest_time = '@d'
            elif ui_schedule == '1w':
                saved_search.schedule.cron_schedule = '0 0 * * 0'
                saved_search.dispatch.earliest_time = '-1w@w'
                saved_search.dispatch.latest_time = '@w'
            elif ui_schedule == '1m':
                saved_search.schedule.cron_schedule = '0 0 1 * *'
                saved_search.dispatch.earliest_time = '-1mon@mon'
                saved_search.dispatch.latest_time = '@mon'
            else:
                saved_search.schedule.cron_schedule = params.get('ui_cron')
                if re.search('\w+', saved_search.dispatch.earliest_time or '') is None:
                    saved_search.errors.append(_('Running on a cron schedule requires an earliest time'))

        elif ui_howoften == 'rolling':
            ui_rolling_value = params.get('ui_rolling_value')
            ui_rolling_unit = params.get('ui_rolling_unit')
            saved_search.dispatch.earliest_time = 'rt-%s%s' % (ui_rolling_value, ui_rolling_unit)
            saved_search.dispatch.latest_time = 'rt-0%s' % ui_rolling_unit
    
        if saved_search.alert.suppress.period is not None:
            new_value = params.get('ui_rolling_value')
            new_unit = params.get('ui_rolling_unit')
            potential_new_suppression = '%s%s' % (new_value, new_unit)
            if len(new_value) is not 0 and saved_search.alert.suppress.period != potential_new_suppression:
                new_suppress_period_match = re.match('(\d+)(\w+)', potential_new_suppression)
                new_suppress_value = new_suppress_period_match.group(1)
                new_suppress_unit = new_suppress_period_match.group(2)
                saved_search.alert.suppress.period = self.time_conversion(new_suppress_value, new_suppress_unit)

    def time_conversion(self, value, unit):
        if unit == 'd':
            value = str(int(value)*24)
            unit = 'h'
            return '%s%s' % (value, unit)
        if int(value) is 1 or int(value) is 2:
            if unit =='h':
                value = str(int(value)*60)
                unit = 'm'
            elif unit == 'm':
                value = str(int(value)*60)
                unit = 's'
        return '%s%s' % (value, unit)

    def step1_to_ui(self, saved_search):
        saved_search.ui_rolling_value = '1'
        saved_search.ui_rolling_unit = None
        saved_search.ui_schedule = None
        
        if saved_search.dispatch.earliest_time == 'rt':
            saved_search.ui_howoften = 'realtime'
        elif saved_search.dispatch.earliest_time and saved_search.dispatch.earliest_time.startswith('rt-'):
            saved_search.ui_howoften = 'rolling'
            time_parts = re.match('rt-(\d+)([mhd])', saved_search.dispatch.earliest_time)
            if time_parts:
                saved_search.ui_rolling_value = time_parts.group(1)
                saved_search.ui_rolling_unit = time_parts.group(2)
        else:
            saved_search.ui_howoften = 'schedule'
            if saved_search.schedule.cron_schedule == '0 * * * *' and saved_search.dispatch.latest_time == '@h' and saved_search.dispatch.earliest_time == '-1h@h':
                saved_search.ui_schedule = '1h'
            elif saved_search.schedule.cron_schedule == '0 0 * * *' and saved_search.dispatch.latest_time == '@d' and saved_search.dispatch.earliest_time == '-1d@d':
                saved_search.ui_schedule = '1d'
            elif saved_search.schedule.cron_schedule == '0 0 * * 0' and saved_search.dispatch.latest_time == '@w' and saved_search.dispatch.earliest_time == '-1w@w':
                saved_search.ui_schedule = '1w'
            elif saved_search.schedule.cron_schedule == '0 0 1 * *' and saved_search.dispatch.latest_time == '@mon' and saved_search.dispatch.earliest_time == '-1mon@mon':
                saved_search.ui_schedule = '1m'
            else:
                saved_search.ui_schedule = 'cron'

        
    @route('/:app/:step=step1/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_new(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.ui_howoften = 'realtime'
        saved_search.ui_schedule = None
        saved_search.ui_rolling_value = '1'
        saved_search.ui_rolling_unit = None
        return self.render_template('alertswizardv2/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_create(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        params['name'] = params.get('name', '')
        saved_search = SavedSearch(app, owner, **params)
        saved_search.is_disabled = True
        self.step1_from_ui(params, saved_search)
        if len(saved_search.errors)==0 and saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizardv2', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        self.step1_to_ui(saved_search)
        return self.render_template('alertswizardv2/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=edit')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_edit(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        self.step1_to_ui(saved_search)
        return self.render_template('alertswizardv2/step1_edit.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        self.step1_from_ui(params, saved_search)
        if len(saved_search.errors)==0 and saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizardv2', app, 'step2'], _qs=dict(id=saved_search.id)), 303)
        self.step1_to_ui(saved_search)
        return self.render_template('alertswizardv2/step1_edit.html', dict(app=app, saved_search=saved_search))

    def step2_from_ui(self, params, saved_search):
        ui_suppress_value = params.get('ui_suppress_value')
        ui_suppress_unit = params.get('ui_suppress_unit')
        saved_search.alert.suppress.period = '%s%s' % (ui_suppress_value, ui_suppress_unit)
        saved_search.alert.digest_mode = splunk.util.normalizeBoolean(params.get('alert.digest_mode', False))
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
            saved_search.action.email.sendpdf = True
            saved_search.action.email.format = 'pdf'

    def step2_to_ui(self, saved_search):
        saved_search.ui_suppress_value = None
        saved_search.ui_suppress_unit = None
        if saved_search.alert.suppress.period:
            suppress_period_match = re.match('(\d+)(\w+)', saved_search.alert.suppress.period)
            if suppress_period_match:
                saved_search.ui_suppress_value = suppress_period_match.group(1)
                saved_search.ui_suppress_unit = suppress_period_match.group(2)
            
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
        self.step1_to_ui(saved_search)
        self.step2_to_ui(saved_search)
        return self.render_template('alertswizardv2/step2.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step2/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step2_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        saved_search.action.email.enabled = False if params.get('action.email.enabled') is None else True
        if saved_search.action.email.enabled is False:
            saved_search.action.email.to = None
        saved_search.action.script.enabled = False if params.get('action.script.enabled') is None else True
        saved_search.alert.track = False if params.get('alert.track') is None else True
        saved_search.alert.suppress.enabled = False if params.get('alert.suppress.enabled') is None else True
        if saved_search.action.email.enabled is False and saved_search.action.script.enabled is False and saved_search.alert.track is False:
            saved_search.errors.append(_('Enable at least one action.'))
        self.step2_from_ui(params, saved_search)
        if not saved_search.errors and saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizardv2', app, 'step3'], _qs=dict(id=saved_search.id)), 303)
        for idx, error in enumerate(saved_search.errors):
            if error == 'action.email.to is required if email action is enabled':
                saved_search.errors[idx] = _('Provide at least one address for scheduled report emails.')
        saved_search.ui_allow_pdf = splunk.pdf.availability.is_available(cherrypy.session['sessionKey'])
        self.step1_to_ui(saved_search)
        self.step2_to_ui(saved_search)
        return self.render_template('alertswizardv2/step2.html', dict(app=app, saved_search=saved_search))
    

    @route('/:app/:action=step3')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step3_edit(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        self.step1_to_ui(saved_search)
        return self.render_template('alertswizardv2/step3.html', dict(app=app, saved_search=saved_search))

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
            raise cherrypy.HTTPRedirect(self.make_url(['alertswizardv2', app, 'success'], _qs=dict(id=saved_search.id)), 303)
        self.step1_to_ui(saved_search)
        return self.render_template('alertswizardv2/step3.html', dict(app=app, saved_search=saved_search))

    
    @route('/:app/:action=delete')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def delete(self, app, action, **params):
        SavedSearch.get(params.get('id')).delete()
        raise cherrypy.HTTPRedirect(self.make_url(['alertswizardv2', app, 'step1', 'new']), 303)   
    
    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('alertswizardv2/success.html', dict(app=app, saved_search=saved_search))
