# coding=UTF-8
import logging
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.models.scheduled_view import ScheduledView
import splunk.entity as entity
import splunk.search 
import splunk.util

logger = logging.getLogger('splunk.appserver.controllers.scheduledview')

class ScheduledViewController(BaseController):

    @route('/:app/:viewName')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def edit(self, app, viewName, **params):
        owner = splunk.auth.getCurrentUser()['name']

        pdfPreviewUrl = None
        if "pdfPreviewUrl" in params:
            pdfPreviewUrl = params.get('pdfPreviewUrl')

        viewLabel = viewName
        if "viewLabel" in params:
            viewLabel = params.get('viewLabel')

        id = ScheduledView.build_id(name=viewName, owner=owner, namespace=app)
        scheduled_view = ScheduledView.get(id)
        if scheduled_view.schedule.cron_schedule == None:
            scheduled_view.schedule.cron_schedule = '*/30 * * * *'
        frequency, manual_cron = self._cronSchedule_to_UI(scheduled_view.schedule.cron_schedule)

        # TODO: refactor out to share code with pdfgen_endpoint
        ALERT_ACTIONS_ENTITY="/configs/conf-alert_actions"
        settings = entity.getEntity(ALERT_ACTIONS_ENTITY, 'email')

        # paperSize is 'letter', 'legal', 'A4', etc
        paperSize = settings.get('reportPaperSize') or 'letter'
        # paperOrientation is 'portrait' or 'landscape'
        paperOrientation = settings.get('reportPaperOrientation') or 'portrait'

        if scheduled_view.action.email.papersize == None:
            scheduled_view.action.email.papersize = paperSize
        paperSize = scheduled_view.action.email.papersize
        
        if scheduled_view.action.email.paperorientation == None:
            scheduled_view.action.email.paperorientation = paperOrientation
        paperOrientation = scheduled_view.action.email.paperorientation

        return self.render_template('scheduledview/edit.html', dict(app=app, scheduled_view=scheduled_view, frequency=frequency, manual_cron=manual_cron, paperSize=paperSize, paperOrientation=paperOrientation, pdfPreviewUrl=pdfPreviewUrl, viewLabel=viewLabel))

    @route('/:app/:action=update')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def update(self, app, action, **params):
        scheduled_view = ScheduledView.get(params.get('id'))
        logger.debug("scheduledviews update params: " + str(params))
        
        params['schedule.cron_schedule'] = self._cronSchedule_from_UI(params['frequency'], params['manual_cron'])
        params['action.email.papersize'] = params['paperSize']       
        params['action.email.paperorientation'] = params['paperOrientation']       
 
        scheduled_view.update(params)
        if scheduled_view.passive_save():
            return self.render_template('scheduledview/success.html', dict(app=app, scheduled_view=scheduled_view))
        else:
            frequency, manual_cron = self._cronSchedule_to_UI(scheduled_view.schedule.cron_schedule)
            
            return self.render_template('scheduledview/edit.html', dict(app=app, scheduled_view=scheduled_view, frequency=frequency, manual_cron=manual_cron, pdfPreviewUrl=params['pdfPreviewUrl']))

    FREQUENCY_CRON_MAPPING = [
        {'frequency': '30 minutes', 'cron': '*/30 * * * *'}, 
        {'frequency': 'hour', 'cron': '0 * * * *'}, 
        {'frequency': '12 hours', 'cron': '0 */12 * * *'},
        {'frequency': 'day_midnight', 'cron': '0 0 * * *'}, 
        {'frequency': 'day_6pm', 'cron': '0 18 * * *'}, 
        {'frequency': 'week', 'cron': '0 0 * * 6'}
        ]

    def _cronSchedule_to_UI(self, cron_schedule):
        manual_cron = ''
        frequency = 'cron'
        for mapping in self.FREQUENCY_CRON_MAPPING:
            if mapping['cron'] == cron_schedule:
                frequency = mapping['frequency']
                break           
        
        if frequency == 'cron':
            manual_cron = cron_schedule
        
        return frequency, manual_cron
        
    def _cronSchedule_from_UI(self, frequency, manual_cron):
        cron_schedule = ''
        if frequency == 'cron':
            cron_schedule = manual_cron
        else:
            for mapping in self.FREQUENCY_CRON_MAPPING:
                if mapping['frequency'] == frequency:
                    cron_schedule = mapping['cron']
                    break           
            
        return cron_schedule

    @route('/:app/:action=success')
    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    def success(self, app, action, **params):
        scheduled_view = ScheduledView.get(params.get('id'))
        return self.render_template('scheduledview/success.html', dict(app=app, scheduled_view=scheduled_view))

    @route('/:app/:action=sendTestEmail')
    @expose_page(must_login=True, trim_spaces=True, methods='POST')
    def sendTestEmail(self, app, action, **params):
        alertActionsSettings = entity.getEntity('/configs/conf-alert_actions', 'email')
        
        viewId = None
        sslink = None
        if 'input-dashboard' in params:
            viewId = params['input-dashboard']
        elif 'scheduled-view-id' in params:
            # this is using the deprecated PDF Report Server
            # we need to setup viewId from the scheduled-view-id parameter
            # and we need to set up the sslink param

            # parse out view id from scheduled-view-id
            # form: ../_ScheduledView__<view-id>
            # find first instance of _ScheduledView__ and then retrieve the last bit
            parts = params['scheduled-view-id'].partition("_ScheduledView__")
            if len(parts) == 3:
                viewId = parts[2]

            sslink = "%s/app/%s/%s" % (
                splunk.appserver.mrsparkle.lib.util.generateBaseLink(), 
                app, 
                viewId
                )

        if viewId is None:
            logger.error("Could not determine view ID from params=%s" % params)
            return _("Could not determine view from parameters")        
        
        commandParts = ["| sendemail"]
        commandParts.append('"server=%s"' % alertActionsSettings.get('mailserver', 'localhost'))
        commandParts.append('"use_ssl=%s"' % alertActionsSettings.get('use_ssl', 'false'))
        commandParts.append('"use_tls=%s"' % alertActionsSettings.get('use_tls', 'false'))
        commandParts.append('"to=%s"' % params['to'])
        commandParts.append('"sendpdf=True"')
        commandParts.append('"from=%s"' % alertActionsSettings.get('from', 'splunk@localhost'))
        commandParts.append('"papersize=%s"' % params['paper-size'])
        commandParts.append('"paperorientation=%s"' % params['paper-orientation'])       
        commandParts.append('"pdfview=%s"' % viewId)
        if sslink != None:
            commandParts.append('"sslink=%s"' % sslink)
        for key in params:
            if "sid_" in key:
                commandParts.append('"%s=%s"' % (key, params[key]))
 
        subjectTemplate = alertActionsSettings.get('subject', _('Splunk results for $name$'))
        commandParts.append('"subject=%s"' % splunk.util.interpolateString(subjectTemplate, {"name": viewId})) 

        commandStr = " ".join(commandParts)
        logger.info("Sending test email command=%s" % commandStr)
        
        try:
            owner = splunk.auth.getCurrentUser()['name']
            jobObj = splunk.search.dispatch(search=commandStr, namespace=app, owner=owner) 
            if jobObj != None:
                return "success"
            else:
                return _("Could not dispatch job for sendemail command.")
        except Exception as e:
            logger.error("commandStr=%s exception=%s" % (commandStr, e))
            return _("Exception while dispatching email job. Exception = %s") % e    
