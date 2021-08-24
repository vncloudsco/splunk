from builtins import object
import cherrypy

class NoReferrerHook(object):
    '''
    SPL-131344: Provide mechanism to block HTTP referrers
    at the Splunk Web Level
    '''
    def __init__(self, cherrypy):
        # Inject cherrypy for unit testability
        self.cherrypy = cherrypy

    @classmethod
    def singleton(cls):
        '''
        Retrieves the singleton instance of this class.
        '''
        if not cls._singleton_instance:
            cls._singleton_instance = cls(cherrypy)
        return cls._singleton_instance

    _singleton_instance = None

    '''
    Handles rendering the hook's code.
    '''

    template = '''
        <meta name="referrer" content="never" />
        <meta name="referrer" content="no-referrer" />
    '''

    def render(self):
        '''
        Renders the hook template.
        '''
        return self.template