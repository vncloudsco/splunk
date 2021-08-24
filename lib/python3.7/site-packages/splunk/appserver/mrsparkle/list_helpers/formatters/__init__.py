from builtins import object
class BaseFormatter(object):
    '''Base class for formatter classes.
    Each formatter should receive a list of dicts, and optional params.
    It should then return a string representaiton of the list in the format
    it specifies.
    
    Required class parameter settings:
    formats -- String representing the name of the format, eg 'json' or 'li'.
               Used by the @format_list_response decorator in conjunction with the
               output_mode parameter to determine the correct format to respond with.
        
    Commonly overriden instance methods:
    format -- last method called by the @format_list_response decorator.
              Should be replaced with logic that correctly converts the response into
              the desired format.
    '''
    
    formats = None
    
    def __init__(self, response, controller, **kw):
        self.response = response
        self.controller = controller
        self.params = kw
        
    def __str__(self):
        return self.format()

    def format(self):
        return str(self.response)
