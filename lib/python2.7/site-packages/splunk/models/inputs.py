from splunk.models.base import SplunkAppObjModel

class SplunkTCPInput(SplunkAppObjModel):
    '''
    Represents the TCP input settings 
    '''
    
    resource = '/data/inputs/tcp/cooked'

   
    
