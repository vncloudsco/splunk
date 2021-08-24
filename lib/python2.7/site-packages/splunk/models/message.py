'''
Provides object mapping for saved search objects
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field

class Message(SplunkAppObjModel):
    '''
    Represents a Splunk message object
    '''

    resource = 'messages'
    
    name = Field()
    value = Field()

