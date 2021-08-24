# coding=UTF-8
from __future__ import absolute_import
import cherrypy
import logging
import splunk.appserver.mrsparkle # bulk edit
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.models.dashboard_panel import DashboardPanel
from splunk.models.dashboard import Dashboard
from splunk.models.saved_search import SavedSearch

import splunk.auth
import json
import splunk.util as util

logger = logging.getLogger('splunk.appserver.controllers.panels')

class PanelEditorController(BaseController):
    @route('/:app/:action=edit/:row/:column')
    @expose_page(must_login=True, methods='GET')
    def edit(self, app, action, row, column, **params):
        # saved_searches = SavedSearch.all().filter_by_app(app)
        row = int(row)
        column = int(column)
        dashboard_panel = DashboardPanel.get(params.get('id'), (row, column))
        # panel options layering via GET params with 'options.*' prefix
        option_key = 'options.'
        for param in params:
            if param.startswith(option_key):
                dashboard_panel.add_option(param[len(option_key):], params[param])
        enable_fragment_id = splunk.util.normalizeBoolean(params.get('enable_fragment_id', True))
        view_id = params.get('id').split('/')[-1:][0]
        template_args = dict(app=app, dashboard_panel=dashboard_panel,
            enable_fragment_id=enable_fragment_id, saved_searches={}, is_transforming=util.normalizeBoolean(params.get('is_transforming', True)),
            view_id=view_id)
        return self.render_template('paneleditor/edit.html', template_args)

    @route('/:app/:action=update/:row/:column')
    @expose_page(must_login=True, methods='POST')
    def update(self, app, action, row, column, **params):
        row = int(row)
        column = int(column)
        dashboard_panel = DashboardPanel.get(params.get('id'), (row, column))
        #application/json POST
        try:
            #cherrypy gives file descriptor for POST's
            data = json.loads(cherrypy.request.body.read())
        except Exception as e:
            return json.dumps({'error': 'Could not read data for panel update', 'trace': str(e)})
        dashboard_panel.set_dict(data)
        if not dashboard_panel.save():
            return json.dumps({'error': 'Could not save panel changes'})
        return json.dumps({'success': 'Successfully saved', 'panel': dashboard_panel.get_dict()})

    @route('/:app/:action=delete/:row/:column')
    @expose_page(must_login=True, methods='POST')
    def delete(self, app, action, row, column, **params):
        row = int(row)
        column = int(column)
        dashboard_panel = DashboardPanel.get(params.get('id'), (row, column))
        if dashboard_panel.delete():
            cherrypy.response.status = 204
            return ""
        cherrypy.response.status = 400
        return json.dumps({'error': dashboard_panel.errors})

    @route('/:app/:action=searchedit/:row/:column')
    @expose_page(must_login=True, methods='GET')
    def searchedit(self, app, action, row, column, **params):
        row = int(row)
        column = int(column)
        dashboard = Dashboard.get(params.get('id'))
        dashboard_panel = DashboardPanel(None, (row, column), dashboard=dashboard)
        saved_searches = SavedSearch.all().filter_by_app(app)
        saved_search_id = params.get('saved_search_id')
        owner = splunk.auth.getCurrentUser()['name']
        inline_search = SavedSearch(app, owner, None)
        ui_search_mode = dashboard_panel.panel_model.searchMode
        # set the saved_search object
        if saved_search_id:
            saved_search = SavedSearch.get(saved_search_id)
            ui_search_mode = 'saved'
        # otherwise defer to the first saved search item if it exists or an empty one
        else:
            saved_search_query = SavedSearch.all()
            if len(saved_search_query)>0:
                saved_search = saved_search_query[0]
            else:
                saved_search = SavedSearch(app, owner, None)

        # based on search mode pre-populate an active saved_search and the inline_search accordingly
        if dashboard_panel.panel_model.searchMode=='saved' and not saved_search_id:
            saved_search_query = SavedSearch.all().filter_by_app(None).search('name=%s' % util.fieldListToString([dashboard_panel.panel_model.searchCommand]))
            if len(saved_search_query)>0:
                saved_search = saved_search_query[0]
            # invalid/non-existant saved search reference, revert to empty saved search model
            else:
                saved_search.search = dashboard_panel.panel_model.searchCommand
                saved_search.dispatch.earliest_time = dashboard_panel.panel_model.searchEarliestTime
                saved_search.dispatch.latest_time = dashboard_panel.panel_model.searchLatestTime
        elif dashboard_panel.panel_model.searchMode=='string':
            inline_search.search = dashboard_panel.panel_model.searchCommand
            inline_search.dispatch.earliest_time = dashboard_panel.panel_model.searchEarliestTime
            inline_search.dispatch.latest_time = dashboard_panel.panel_model.searchLatestTime

        template_args = dict(app=app, dashboard=dashboard, dashboard_panel=dashboard_panel, saved_searches=saved_searches, saved_search=saved_search,
                             ui_search_mode=ui_search_mode, inline_search=inline_search)
        return self.render_template('paneleditor/searchedit.html', template_args)

    @route('/:app/:action=searchupdate/:row/:column')
    @expose_page(must_login=True, methods='POST')
    def searchupdate(self, app, action, row, column, **params):
        row = int(row)
        column = int(column)
        dashboard_panel = DashboardPanel.get(params.get('id'), (row, column))
        dashboard_panel.panel_model.searchMode = params.get('panel_model.searchMode')
        dashboard_panel.panel_model.searchCommand = params.get('panel_model.searchCommand', '')
        dashboard_panel.panel_model.searchEarliestTime = params.get('panel_model.searchEarliestTime', '').strip()
        dashboard_panel.panel_model.searchLatestTime = params.get('panel_model.searchLatestTime', '').strip()
        if dashboard_panel.save(validate_time=True):
            return ''
        cherrypy.response.status = 400
        return json.dumps({'error': dashboard_panel.errors})
