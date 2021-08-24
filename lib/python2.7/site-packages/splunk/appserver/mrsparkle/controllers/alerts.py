# coding=UTF-8
import cherrypy
import datetime
import logging
from future.moves.urllib import parse as urllib_parse
import splunk.bundle
import splunk.auth
import sys
import splunk.appserver.mrsparkle.lib.paginator as paginator
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.models.fired_alert import FiredAlert
from splunk.models.fired_alert import FiredAlertSummary
from splunk.models.app  import App
from splunk.models.user import User
import splunk.util


logger = logging.getLogger('splunk.appserver.controllers.alerts')

def getArgValue(name, params, default_val):
    if name in params:
       value      = params.get(name)
       value      = '-' if value=='*'  else value
       return default_val if value==None else value
    return default_val

class AlertsController(BaseController):
    @route('/:app')
    @expose_page(must_login=True, methods='GET')
    def index(self, app, **params):
        # request param cast/defaults
        offset      = int(params.get('offset', 0))
        count       = int(params.get('count', 25))
        alerts_app  = getArgValue('eai:acl.app', params, app)
        alerts_user = urllib_parse.unquote_plus(getArgValue('eai:acl.owner', params, '-'))
        
        # fired alerts search filters
        search_params = ['severity', 'search']
        search_string = []
        for key in search_params:
            value = params.get(key)
            if value and value != '*':
                if key=='search':
                    search_string.append('%s' % value)
                else:
                    search_string.append('%s="%s"' % (key, urllib_parse.unquote_plus(value)))
        # fired alerts query
        if not 'alerts_id' in params:
            fired_alerts = FiredAlert.all()
        else:
            fired_alerts = FiredAlert.get_alerts(urllib_parse.unquote_plus(params.get('alerts_id')))
            
        
        # augment query with search
        if len(search_string) > 0:
           fired_alerts = fired_alerts.search(' '.join(search_string))
        # augment query with app or user filters
        fired_alerts = fired_alerts.filter_by_app(alerts_app).filter_by_user(alerts_user)
        fired_alerts._count_per_req = count
        if 'sort_by' in params or 'sort_dir' in params:
            fired_alerts = fired_alerts.order_by(params.get('sort_by', 'trigger_time'), sort_dir=params.get('sort_dir', 'desc'))
        
        # fired alert summary information
        fired_alert_summary = FiredAlertSummary.all().filter_by_app(alerts_app).filter_by_user(alerts_user)
        fired_alert_summary._count_per_req = count
        try:
            fired_alert_summary[0]
        except Exception as e:
            if e.statusCode == 402:
                return self.render_template('admin/402.html', {
                    'feature'               : _('Alerting')
                }) 
        # apps listings
        apps  = App.all().filter(is_disabled=False)
        
        # users listings
        users = User.all()
        max_users = 250
        users._count_per_req = max_users
        users = users[:max_users]
        
        # paginator
        pager = paginator.Google(fired_alerts.get_total(), max_items_page=count, item_offset=offset)
        
        app_label=splunk.bundle.getConf('app', namespace=app)['ui'].get('label')
        # view variables
        template_args = dict(app=alerts_app, apps=apps, users=users, count=count, current_user=splunk.auth.getCurrentUser().get('name'), 
                             fired_alerts=fired_alerts, 
                             fired_alert_summary=fired_alert_summary, 
                             offset=offset, pager=pager, app_label=app_label)
        return self.render_template('alerts/index.html', template_args)

    @route('/:app/:action=delete')
    @expose_page(must_login=True, methods='POST')
    def delete(self, app, action, id=None, **params):
        if isinstance(id, list):
            for idx in id:
                try:
                    FiredAlert.get(idx).delete()
                except:
                    logger.warn('Could not delete fired alert: %s' % idx)
        elif isinstance(id, splunk.util.string_type):
            try:
                FiredAlert.get(id).delete()
            except:
                logger.warn('Could not delete fired alert: %s' % id)
        raise cherrypy.HTTPRedirect(self.make_url(['alerts', app]) + '?%s' % cherrypy.request.query_string, 303)
        
    def render_template(self, template_path, template_args = {}):
        template_args['appList'] = []
        return super(AlertsController, self).render_template(template_path, template_args)
