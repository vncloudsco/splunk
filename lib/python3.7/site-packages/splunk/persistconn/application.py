from builtins import object
class PersistentServerConnectionApplication(object):
    """
    Virtual class to inherit from to build a "persistent" handler which
    can be automatically managed by appserver.py
    """

    def __init__(self):
        pass

    # Handle a syncronous from splunkd.
    def handle(self, in_bytes):
        """
        Called for a simple synchronous request.
        @param in_bytes: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        raise NotImplementedError("PersistentServerConnectionApplication.handle")

    def handleStream(self, handle, in_bytes):
        """
        For future use
        """
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
