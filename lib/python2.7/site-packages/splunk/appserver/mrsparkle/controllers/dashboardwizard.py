# coding=UTF-8
import cherrypy
import datetime
import splunk.util
import logging
from splunk.models.saved_search import SavedSearch
from splunk.models.dashboard import Dashboard
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk.appserver.controllers.dashboardwizard')

class DashboardWizardController(BaseController):
    @route('/:app/:step=step1/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_new(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        name = params.get('name', '')
        saved_search = SavedSearch(app, owner, name, **params)
        
        return self.render_template('dashboardwizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_create(self, app, step, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        saved_search = SavedSearch(app, owner, **params)
        saved_search.is_disabled = True
        # no need to suppress or track dashboard searches
        saved_search.alert.track = False
        saved_search.alert.suppress.enabled = False
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['dashboardwizard', app, 'step2', 'new'], _qs=dict(id=saved_search.id)), 303)
        return self.render_template('dashboardwizard/step1_new.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=edit')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step1_edit(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        return self.render_template('dashboardwizard/step1_edit.html', dict(app=app, saved_search=saved_search))

    @route('/:app/:step=step1/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step1_update(self, app, step, action, **params):
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.update(params)
        if saved_search.passive_save():
            raise cherrypy.HTTPRedirect(self.make_url(['dashboardwizard', app, 'step2', 'new'], _qs=dict(id=saved_search.id)), 303)
        return self.render_template('dashboardwizard/step1_edit.html', dict(app=app, saved_search=saved_search))
    
    @route('/:app/:step=step2/:action=new')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step2_new(self, app, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        saved_search = SavedSearch.get(params.get('id'))
        dashboard = Dashboard(app, owner, None)
        dashboard.metadata.sharing = 'app'
        dashboards = Dashboard.filter_by_can_write_simple_xml(app)
        template_args = dict(app=app, saved_search=saved_search, dashboard=dashboard, dashboards=dashboards, 
                             dashboard_action=None, panel_type='event', panel_title=None)
        return self.render_template('dashboardwizard/step2.html', template_args)

    @route('/:app/:step=step2/:action=create')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step2_create(self, app, step, action, **params):
        # saved search models
        saved_search = SavedSearch.get(params.get('id'))
        # dashboard model
        dashboard_action = params.get('dashboard.action')
        owner = splunk.auth.getCurrentUser()['name']
        if dashboard_action=='get':
            try:
                dashboard = Dashboard.get(params.get('dashboard.id'))
            except:
                dashboard = Dashboard(app, owner, None)
                dashboard.errors = [_('Please choose an existing dashboard.')]
        else:
            dashboard_name = params.get('dashboard.name', '')
            try:
                dashboard_name.encode('ascii')
            except:
                date = str(splunk.util.dt2epoch(datetime.datetime.now())).replace('.', '_')
                dashboard_name = '%s_%s' % (splunk.auth.getCurrentUser()['name'], date)
            dashboard = Dashboard(app, owner, dashboard_name)
            dashboard.label = params.get('dashboard.label')
            dashboard.metadata.sharing = params.get('sharing', 'user')

        if not dashboard.errors and saved_search.passive_save() and dashboard.passive_save():
            # update saved search only on save success
            if dashboard.metadata.sharing=='app':
                try:
                    saved_search.share_app()
                except Exception:
                    saved_search.errors = [_('Search %s cannot be shared because it already exists. Try using another search name in the previous step.') % saved_search.name ]
            else:
                try:
                    saved_search.unshare()
                except Exception:
                    saved_search.errors = [_('Search %s cannot be private because it already exists. Try using another search name in the previous step.') % saved_search.name]
            if not saved_search.errors:
                raise cherrypy.HTTPRedirect(self.make_url(['dashboardwizard', app, 'step3'], _qs=dict(search_id=saved_search.id, dashboard_id=dashboard.id, dashboard_action=dashboard_action)), 303)
        dashboards = Dashboard.filter_by_can_write_simple_xml()
        template_args = dict(app=app, saved_search=saved_search, dashboard=dashboard, dashboards=dashboards, dashboard_action=dashboard_action)
        return self.render_template('dashboardwizard/step2.html', template_args)

    @route('/:app/:step=step2/:action=edit')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step2_edit(self, app, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        saved_search = SavedSearch.get(params.get('id'))
        dashboard = Dashboard.get(params.get('dashboard_id'))
        dashboard_action = params.get('dashboard_action')
        if dashboard_action=='new':
            dashboard.delete()
        dashboards = Dashboard.filter_by_can_write_simple_xml()
        template_args = dict(app=app, saved_search=saved_search, dashboard=dashboard, dashboards=dashboards, 
                             dashboard_action=dashboard_action)
        return self.render_template('dashboardwizard/step2.html', template_args)
        
    @route('/:app/:action=step3')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def step3_edit(self, app, action, **params):
        owner = splunk.auth.getCurrentUser()['name']
        saved_search = SavedSearch.get(params.get('search_id'))
        dashboard = Dashboard.get(params.get('dashboard_id'))
        dashboard_action = params.get('dashboard_action')
        panel_type = 'event' 
        if saved_search.ui.display_view in ['charting', 'report_builder_format_report', 'report_builder_display']:
            panel_type = 'chart' 
        template_args = dict(app=app, saved_search=saved_search, dashboard=dashboard, dashboard_action=dashboard_action, panel_type=panel_type, panel_title=None)
        return self.render_template('dashboardwizard/step3.html', template_args)

    @route('/:app/:step=step3/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def step3_update(self, app, step, action, **params):
        # saved search models
        saved_search = SavedSearch.get(params.get('id'))
        saved_search.auto_summarize.enabled = params.get('auto_summarize.enabled') == 'True'
        saved_search.auto_summarize.earliest_time = params.get('auto_summarize.earliest_time')
        saved_search.auto_summarize.timespan = params.get('auto_summarize.timespan')
        schedule_type = params.get('schedule_type')
        saved_search.schedule.is_scheduled = True
        saved_search.is_disabled = False
        if schedule_type=='preset':
            alert_preset = params.get('alert_preset')
            if alert_preset=='cron':
                saved_search.schedule.cron_schedule = params.get('alert_cron')
            else:
                saved_search.schedule.cron_schedule = alert_preset
        elif schedule_type=='never':
            saved_search.schedule.is_scheduled = False
            saved_search.schedule.cron_schedule = None
        elif schedule_type=='continuous':
            saved_search.schedule.cron_schedule = '* * * * *'

        # dashboard model
        dashboard = Dashboard.get(params.get('dashboard_id'))
        panel_type = params.get('panel_type', 'event')
        dashboard.create_panel(panel_type, saved_search=saved_search.name, title=params.get('panel_title'))

        if saved_search.passive_save() and dashboard.passive_save():
            # update saved search only on save success         
            raise cherrypy.HTTPRedirect(self.make_url(['dashboardwizard', app, 'success'], _qs=dict(search_id=saved_search.id, dashboard_id=dashboard.id)), 303)
        template_args = dict(app=app, saved_search=saved_search, dashboard=dashboard, dashboard_action=params.get('dashboard_action'))
        return self.render_template('dashboardwizard/step3.html', template_args)
        
    @route('/:app/:action=delete')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def delete(self, app, action, **params):
        SavedSearch.get(params.get('id')).delete()
        dashboard_id = params.get('dashboard_id')
        if dashboard_id:
            Dashboard.get(dashboard_id).delete()
        raise cherrypy.HTTPRedirect(self.make_url(['dashboardwizard', app, 'step1', 'new']), 303) 

    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        saved_search = SavedSearch.get(params.get('search_id'))
        dashboard = Dashboard.get(params.get('dashboard_id'))
        return self.render_template('dashboardwizard/success.html', dict(app=app, saved_search=saved_search, dashboard=dashboard))
