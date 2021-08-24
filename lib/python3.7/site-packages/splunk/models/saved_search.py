'''
Provides object mapping for saved search objects
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, StructuredField, IntField
import splunk.search.Parser as Parser

import logging
logger = logging.getLogger('splunk.models.savedsearch')


class ScheduleField(StructuredField):
    '''
    Represents splunk scheduler configuration for saved search objects
    '''

    is_scheduled        = BoolField('is_scheduled')
    cron_schedule       = Field('cron_schedule')
    next_scheduled_time = Field('next_scheduled_time')
    run_on_startup      = BoolField('run_on_startup')


class ActionField(StructuredField):
    '''
    Represents the alert action configuration for saved search objects
    '''

    class EmailActionField(StructuredField):
        '''
        Represents the email alert action configuration
        '''

        enabled     = BoolField('action.email')
        format      = Field()
        inline      = BoolField()
        sendresults = BoolField()
        to          = Field()
        subject     = Field()

        #TODO: use splunk.models.server_config.PDFConfig.is_enabled instead
        sendpdf     = BoolField()
        papersize   = Field()
        paperorientation = Field()

    class SummaryActionField(StructuredField):
        '''
        Represents the summary indexing configuration
        '''
        enabled = BoolField('action.summary_index')
        _name   = Field()
        inline  = BoolField()
        
    class ScriptActionField(StructuredField):
        '''
        Represents the custom alert script action configuration
        '''
        enabled   = BoolField('action.script')
        filename  = Field()
        
    class RSSField(StructuredField):
        '''
        Represents the rss configuration
        '''
        enabled = BoolField('action.rss')
    
    class PopulateLookupField(StructuredField):
        enabled  = BoolField('action.populate_lookup')
        destination = Field('action.populate_lookup.dest')

    email           = EmailActionField()
    rss             = RSSField()
    script          = ScriptActionField()
    summary_index   = SummaryActionField()
    populate_lookup = PopulateLookupField()



class AlertField(StructuredField):
    '''
    Represents the saved search alerting configuration
    '''

    class SuppressAlertField(StructuredField):
        '''
        Represents the suppression configuration for saved search alerting
        configuration
        '''
        enabled = BoolField('alert.suppress')
        period  = Field()
        fieldlist  = Field('alert.suppress.fields')
        
    type          = Field('alert_type')
    comparator    = Field('alert_comparator')
    threshold     = Field('alert_threshold')
    condition     = Field('alert_condition')
    suppress      = SuppressAlertField()
    digest_mode   = BoolField()
    expires       = Field()
    severity      = Field()
    fired_count   = IntField('triggered_alert_count')
    track         = BoolField() 


class DispatchField(StructuredField):
    '''
    Represents the splunk search dispatch parameters
    '''

    buckets       = Field()
    earliest_time = Field()
    latest_time   = Field()
    lookups       = BoolField()
    max_count     = Field()
    max_time      = Field()
    reduce_freq   = Field()
    spawn_process = BoolField()
    time_format   = Field()
    ttl           = Field()

class UI(StructuredField):
    '''
    Represents the splunk UI related parameters
    '''
    
    dispatch_view = Field('request.ui_dispatch_view')
    dispatch_app  = Field('request.ui_dispatch_view')
    display_view  = Field('displayview')
    vsid          = Field('vsid')
    
class AutoSummarizeField(StructuredField):
    '''
    Represents the auto-summarrize related parameters
    '''
    enabled = BoolField('auto_summarize')
    can_summarize = Field(is_mutable=False)
    is_good_summarization_candidate = Field(is_mutable=False)
    cron_schedule = Field()
    earliest_time = Field('auto_summarize.dispatch.earliest_time')
    latest_time = Field('auto_summarize.dispatch.latest_time')
    timespan = Field(is_mutable=False)

class SavedSearch(SplunkAppObjModel):
    '''
    Represents a Splunk saved search object
    '''

    resource = 'saved/searches'

    search      = Field()
    description = Field()
    dispatch    = DispatchField()
    schedule    = ScheduleField()
    action      = ActionField()
    alert       = AlertField()
    is_disabled = BoolField('disabled')
    ui          = UI()
    auto_summarize = AutoSummarizeField()
    
    def _calc_actions_list(self):
        actions_list = []

        if self.action.email.enabled:
            actions_list.append('email')
            
        if self.action.script.enabled:
            actions_list.append('script')
            
        if self.action.rss.enabled:
            actions_list.append('rss')
    
        if self.action.summary_index.enabled:
            actions_list.append('summary_index')
    
        if self.action.populate_lookup.enabled:
            actions_list.append('populate_lookup')

        return actions_list
    
    def _fill_entity(self, entity, fill_value=''):
        super(SavedSearch, self)._fill_entity(entity, fill_value)
        entity['actions'] = ' '.join(self._calc_actions_list())
        
        # None == not set, the backend treats unset suppresison specially when saving a search
        if self.alert.suppress.enabled == None:
           entity['alert.suppress'] = ''

    
    def setSummarizationDetails(self): 
        CAN_SUMMARIZE_KEY = 'canSummarize'
        IS_GOOD_SUMMARIZATION_CANDIDATE_KEY = 'isGoodSummarizationCandidate'

        earliest_time = self.dispatch.earliest_time if self.dispatch.earliest_time  else '0'
        logger.debug("\n\n\n In setSummarizationDetails: search: %s, earliest_time: %s \n\n\n" % (self.search, earliest_time))
        if not self.search or not earliest_time: 
            return

        # Disallow acceleration for real-time searches 
        if earliest_time.startswith('rt'):
            return

        searchStr = self.search
        if not self.search.strip().startswith(u'|'):
               searchStr = u'search ' + searchStr
        
        try:
                parsedSearch = Parser.parseSearch(str(searchStr), timeline=False, hostPath=self.metadata.host_path, sessionKey=self.metadata.sessionKey)
                searchProps = parsedSearch.properties.properties
                self.auto_summarize.can_summarize = CAN_SUMMARIZE_KEY in searchProps and searchProps[CAN_SUMMARIZE_KEY]
                self.auto_summarize.is_good_summarization_candidate = IS_GOOD_SUMMARIZATION_CANDIDATE_KEY in searchProps and searchProps[IS_GOOD_SUMMARIZATION_CANDIDATE_KEY]
        except:
                self.auto_summarize.can_summarize = False
                self.auto_summarize.is_good_summarization_candidate = False
   
    def time_value(self, field):
        if field is not None:
            return field[:-1]
        return None

    def time_unit(self, field):
        if field is not None and len(field)>1:
            return field[-1]
        return None

    def is_realtime(self):
        return True if str(self.dispatch.earliest_time).startswith('rt') and str(self.dispatch.latest_time).startswith('rt') else False

    def get_alerts(self):
        '''
        Returns a SplunkQuerySet that can be used to access the alerts fired by this saved search, if no 
        alerts have been fired this method will return None

        The SplunkQuerySet can be modified to include a search, custom ordering etc..
        '''
        alerts_id = self.entity.getLink('alerts')
        if alerts_id == None:
           return None

        from splunk.models.fired_alert import FiredAlert
        return FiredAlert.get_alerts(alerts_id)
