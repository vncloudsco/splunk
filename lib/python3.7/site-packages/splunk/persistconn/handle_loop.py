import sys
from splunk.persistconn.packet import PersistentServerConnectionPacketParser, PersistentServerConnectionProtocolException

class PersistentServerConnectionHandlingLoop(PersistentServerConnectionPacketParser):
    """
    Virtual class which exchanges packets on stdin/stdout.  When a new
    "start" packet is received, the load() method is called to find the
    handler tuple to accept the packets.
    """

    def __init__(self):
        PersistentServerConnectionPacketParser.__init__(self)
        self._current_handler = None
    
    def load(self, command, command_arg, stream_allowed):
        """
        Vitual method called to start a new request.

        @param command: Array of strings representing the command
        @param command_arg: A single extra string passed in to the handler
        @param stream_allowed: For future use
        @return Tuple with information about what handler to handle the
                request, or None if the request should be rejected as an error.
        @rtype  Four element tuple, the first is the python object to send requests to.
                The second one is the method to receive data sent to the handler.
                The third one is a method to called when the request complete.
                The final one is a boolean which is not used yet.
        """
        raise NotImplementedError("PersistentServerConnectionHandlingLoop.load")

    def handle_packet(self, in_packet):
        if in_packet.is_first():
            try:
                if self._current_handler is not None:
                    raise PersistentServerConnectionProtocolException("Got start while already active: " + str(in_packet))
                self._current_handler = self.load(in_packet.command, in_packet.command_arg, in_packet.allow_stream())
                if self._current_handler is None:
                    self.write("Can't load script \"%s\"" % in_packet.command[0])
            except:
                self.write(str(sys.exc_info()[1]))
                raise
            if self._current_handler is None:
                # If we get here we printed an error earlier because we
                # didn't find the script.  Just ignore any messages it
                # gets sent, but otherwise preserve the connection.
                def noop_handle(dummy, block):
                    pass
                def noop_done(dummy):
                    pass
                self._current_handler = (None, noop_handle, noop_done, False)
            else:
                self.write("")	# Empty error string indicates success
        if in_packet.has_block():
            if self._current_handler is None:
                raise PersistentServerConnectionProtocolException("Got block while inactive: " + str(in_packet))
            if self._current_handler[3]:	# are we streaming?
                reply = self._current_handler[1](self._current_handler[0], self, in_packet.block)
                if reply is not None:
                    self.write(reply)
            else:
                reply = self._current_handler[1](self._current_handler[0], in_packet.block)
                if reply is None:
                    reply = ""		# A non-steaming handler should always return *something*
                self.write(reply)
        if in_packet.is_last():
            self._current_handler[2](self._current_handler[0])	# call "done"
            self._current_handler = None
