import os
import imp
import inspect
from splunk.persistconn.handle_loop import PersistentServerConnectionHandlingLoop
from splunk.persistconn.packet import PersistentServerConnectionProtocolException

class PersistentServerConnectionApplicationServer(PersistentServerConnectionHandlingLoop):
    """
    Main loop for servicing "persistent" requests from splunkd.  When
    getting a request, the handling script is automatically loaded from
    the passed-in path, and a python class which inherits from
    PersistentServerConnectionApplication is found to answer the request.
    """

    def __init__(self):
        PersistentServerConnectionHandlingLoop.__init__(self)
        self._cache = {}

    def load(self, command, command_arg, stream_allowed):
        if len(command) < 1:
            raise PersistentServerConnectionProtocolException("No script name to start")
        class_and_meths = self._get_class_and_methods(command[0], stream_allowed)
        if class_and_meths is None:
            return None
        (handler_class, handler_method, done_method, is_streaming) = class_and_meths
        handler_object = handler_class.__new__(handler_class)
        handler_object.__init__(command[1:], command_arg)
        return handler_object, handler_method, done_method, is_streaming

    def _get_class_and_methods(self, filename, stream_allowed):
        meths = self._cached_load_file(filename)
        if meths is None:
            return None
        (handler_class, handle_method, handleStream_method, done_method) = meths
        if stream_allowed and handleStream_method is not None:
            return handler_class, handleStream_method, done_method, True
        return handler_class, handle_method, done_method, False

    def _cached_load_file(self, filename):
        if filename in self._cache:
            return self._cache[filename]
        rv = PersistentServerConnectionApplicationServer._load_file(filename)
        if rv is not None:
            self._cache[filename] = rv
        return rv

    @staticmethod
    def _load_file(filename):
        (dirname, fileonly) = os.path.split(filename)
        namepart = os.path.splitext(fileonly)[0]
        try:
            (filehandle, filename, data) = imp.find_module(namepart, [dirname])
        except ImportError:
            return None
        munged_name = PersistentServerConnectionApplicationServer._munge_module_name(namepart, dirname)
        try:
            m = imp.load_module(munged_name, filehandle, filename, data)
        finally:
            if filehandle is not None:
                filehandle.close()
        handler_class = PersistentServerConnectionApplicationServer._find_handler_in_module(m)
        handle_method = getattr(handler_class, "handle")
        # Look for a handleStream() functions, but not the stub that is implemented by the base class
        handleStream_method = None
        for mc in handler_class.mro():
            if mc.__name__ == "PersistentServerConnectionApplication":
                break
            if "handleStream" in mc.__dict__:
                handleStream_method = getattr(handler_class, "handleStream")
                break
        done_method = getattr(handler_class, "done")
        return handler_class, handle_method, handleStream_method, done_method

    @staticmethod
    def _munge_module_name(modname, dirname):
        munged_name = "pschand__"
        for ch in modname:
            if ch.isalnum():
                munged_name += ch
            else:
                munged_name += '_'
        munged_name += "__in_"
        for ch in dirname:
            if ch.isalnum():
                munged_name += ch
            else:
                munged_name += '_'
        return munged_name

    @staticmethod
    def _find_handler_in_module(m):
        # We'll automatically look for the class that inherits from
        # "PersistentServerConnectionApplication" in the module we just
        # loaded.  It must be defined in the file we directly import and
        # must be unique.
        def look_for_handler(c):
            if inspect.isclass(c) and c.__name__ != "PersistentServerConnectionApplication":
                # It would be nice if we could just test issubclass(c, ...)
                # but since it imports it itself the base class with be prefixed
                # and may not match.  Instead we just match on the class name.
                for mc in c.mro():
                    if mc.__name__ == "PersistentServerConnectionApplication":
                        return True
            return False
        classes = inspect.getmembers(m, look_for_handler)
        if len(classes) < 1:
            raise NotImplementedError("No class implements PersistentServerConnectionApplication")
        if len(classes) > 1:
            raise NotImplementedError("More than one class implements PersistentServerConnectionApplication")
        return classes[0][1]

if __name__ == "__main__":
    h = PersistentServerConnectionApplicationServer()
    h.run()
