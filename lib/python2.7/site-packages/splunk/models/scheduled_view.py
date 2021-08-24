'''
Provides object mapping for scheduled view objects
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, StructuredField, IntField



class ScheduleField(StructuredField):
    '''
    Represents splunk scheduler configuration for scheduled view objects
    '''

    is_scheduled        = BoolField('is_scheduled')
    cron_schedule       = Field('cron_schedule')
    next_scheduled_time = Field('next_scheduled_time')

class ActionField(StructuredField):
    '''
    Represents the alert action configuration for scheduled view objects
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

        pdfview     = Field()

        #TODO: use splunk.models.server_config.PDFConfig.is_enabled instead
        sendpdf     = BoolField()
        papersize   = Field()
        paperorientation = Field()

    email           = EmailActionField()

class ScheduledView(SplunkAppObjModel):
    '''
    Represents a Splunk saved search object
    '''

    resource = 'scheduled/views'

    schedule    = ScheduleField()
    action      = ActionField()
    is_disabled = BoolField('disabled')
    
    #def _calc_actions_list(self):
    #   actions_list = []

    #    if self.action.email.enabled:
    #        actions_list.append('email')
    #        
    #    return actions_list
    
    #def _fill_entity(self, entity, fill_value=''):
    #    super(SavedSearch, self)._fill_entity(entity, fill_value)
    #    entity['actions'] = ' '.join(self._calc_actions_list())

    def time_value(self, field):
        if field is not None:
            return field[:-1]
        return None

    def time_unit(self, field):
        if field is not None and len(field)>1:
            return field[-1]
        return None

