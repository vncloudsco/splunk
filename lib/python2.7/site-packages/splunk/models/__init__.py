'''
Model layer exceptions
'''

class ViewConfigurationException(Exception):
    '''
    Indicates an invalid view configuration.
    '''

    def __init__(self, msg=None, viewId=None, viewXml=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.viewId = viewId
        self.viewXml = viewXml
        
    def __str__(self):
        return '%s; viewId=%s' % (self.msg, self.viewId)
