from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField

class EventType(SplunkAppObjModel):
    '''
    Represents a Splunk eventtype object.
    '''
    
    resource = 'saved/eventtypes' 

    description     = Field()
    disabled        = BoolField()
    search          = Field()

