from builtins import object
import cherrypy
import re
import logging

import splunk

logger = logging.getLogger('splunk.appserver.lib.htmlinjectiontoolfactory')


class HtmlInjectionToolFactory(object):
    '''
    HtmlInjectionToolFactory module

    This class implements a CherryPy "Tool" that acts
    as a middleware for injecting hooks into all HTML
    responses from Splunk Web.
    '''

    def __init__(self, cherrypy):
        '''Constructor'''
        # Inject cherrypy for unit testability
        self.cherrypy = cherrypy
        self.registered_head_hooks = []

    @classmethod
    def register_cherrypy_hook(cls):
        '''
        Registers the singleton instance of this Tool as a handler
        for the on_start_resource hook. This allows us to intercept
        all responses through cherrypy and inject the hooks code.
        '''
        if not cls._has_registered_cherrypy_hook:
            cherrypy.tools.hook_injection_tool = cherrypy.Tool('on_start_resource', cls.singleton())
            cherrypy.config.update({'tools.hook_injection_tool.on': True})
            cls._has_registered_cherrypy_hook = True

    _has_registered_cherrypy_hook = False

    def register_head_injection_hook(self, hook):
        '''
        Registers a hook with this method.
        The hook is expecting to have a render method which yield the HTML to inject.
        '''
        if hook not in self.registered_head_hooks:
            self.registered_head_hooks.append(hook)

    @classmethod
    def singleton(cls):
        '''
        Retrieves the singleton instance of this class.
        '''
        if not cls._singleton_instance:
            cls._singleton_instance = cls(cherrypy)
        return cls._singleton_instance

    _singleton_instance = None

    def __call__(self):
        '''
        Callable "dunder" method.

        This method is called by cherrypy for each web request
        according to the hook we bind to in `register_cherrypy_hook`.

        When called, this method dynamically decorates the request
        handler with an wrapper function injecting the
        registered hooks at runtime.
        '''

        if self.cherrypy.request.handler:
            handler = self.cherrypy.request.handler

            def wrapper(*args, **kwargs):
                resp = handler(*args, **kwargs)
                if resp is not None and 'html' in self.cherrypy.response.headers['Content-Type']:
                    hooks_agr = ""
                    for hook in self.registered_head_hooks:
                        try:
                            hooks_agr += hook.render()
                        except Exception as e:
                            # We failed to inject one of the hook. Ignore the error and
                            # allow other hooks to inject their HTML code.
                            logger.error('HTML injection tool factory error: Failed to inject hook in the response.')
                    if hooks_agr != "":
                        resp = re.sub(r'(<\s*/\s*head\s*>)', hooks_agr + '\\1', splunk.util.toDefaultStrings(resp))
                return resp
            self.cherrypy.request.handler = wrapper
