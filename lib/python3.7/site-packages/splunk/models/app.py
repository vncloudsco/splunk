from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField

'''
Provides object mapping for app objects
'''



class App(SplunkAppObjModel):
    '''
    Represents a Splunk app.
    '''
    
    resource = 'apps/local'
    
    check_for_updates   = BoolField()
    is_configured       = BoolField(api_name='configured')
    is_disabled         = BoolField('disabled')
    is_visible          = BoolField(api_name='visible')
    label               = Field()
    requires_restart    = BoolField(api_name='state_change_requires_restart')

