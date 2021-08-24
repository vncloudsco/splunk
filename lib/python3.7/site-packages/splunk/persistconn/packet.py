from builtins import range
from builtins import object

import sys, os
import json
import splunk.util

class PersistentServerConnectionProtocolException(Exception):
    """
    Exception thrown when a recieved packet can't be interpreted
    """
    pass

class PersistentServerConnectionRequestPacket(object):
    """
    Object representing a recieved packet
    """

    def __init__(self):
        self.opcode = None
        self.command = None
        self.command_arg = None
        self.block = None

    def is_first(self):
        """
        @rtype: bool
        @return: True if this packet represents the beginning of the request
        """
        return (self.opcode & PersistentServerConnectionRequestPacket.OPCODE_REQUEST_INIT) != 0

    def is_last(self):
        """
        @rtype: bool
        @return: True if this packet represents the end of the request
        """
        return (self.opcode & PersistentServerConnectionRequestPacket.OPCODE_REQUEST_END) != 0

    def has_block(self):
        """
        @rtype: bool
        @return: True if this packet contains an input block for the request
        """
        return (self.opcode & PersistentServerConnectionRequestPacket.OPCODE_REQUEST_BLOCK) != 0

    def allow_stream(self):
        """
        For future use.
        """
        return (self.opcode & PersistentServerConnectionRequestPacket.OPCODE_REQUEST_ALLOW_STREAM) != 0

    def __str__(self):
        s = "is_first=%c is_last=%c allow_stream=%c" % (
            "NY"[self.is_first()],
            "NY"[self.is_last()],
            "NY"[self.allow_stream()])
        if self.command is not None:
            s += " command=%s" % json.dumps(self.command)
        if self.command_arg is not None:
            s += " command_arg=%s" % json.dumps(self.command_arg)
        if self.has_block():
            s += " block_len=%u block=%s" % (
               len(self.block),
               json.dumps(str(self.block)))
        return s

    OPCODE_REQUEST_INIT = 0x01
    OPCODE_REQUEST_BLOCK = 0x02
    OPCODE_REQUEST_END = 0x04
    OPCODE_REQUEST_ALLOW_STREAM = 0x08

    def read(self, handle):
        """
        Read a length-prefixed protocol data from a file handle, filling this object

        @param handle: File handle to read from
        @rtype: bool
        @return: False if we're at EOF
        """
        while True:
            opbyte = handle.read(1)
            if opbyte == b"":
                return False
            if opbyte != b"\n":
                break	# ignore extra newlines before opcode
        self.opcode = ord(opbyte)
        if self.is_first():
            command_pieces = PersistentServerConnectionRequestPacket._read_number(handle)
            self.command = []
            for i in range(0, command_pieces):
                piece = PersistentServerConnectionRequestPacket._read_string(handle)
                if sys.version_info >= (3, 0):
                    piece = piece.decode()
                self.command.append(piece)
            self.command_arg = PersistentServerConnectionRequestPacket._read_string(handle)
            if self.command_arg == b"":
                self.command_arg = None
            elif sys.version_info >= (3, 0):
                self.command_arg = self.command_arg.decode()
        if self.has_block():
             self.block = PersistentServerConnectionRequestPacket._read_string(handle)
        return True

    @staticmethod
    def _read_to_eol(handle):
        v = b""
        while True:
            e = handle.read(1)
            if not e:
                if v == b"":
                    raise EOFError
                break
            if e == b'\n':
                break
            v += e
        return v

    @staticmethod
    def _read_number(handle):
        while True:
            v = PersistentServerConnectionRequestPacket._read_to_eol(handle)
            if v != b"":		# ignore empty lines before a count
                break
        try:
            n = int(v)
        except ValueError:
            raise PersistentServerConnectionProtocolException("expected non-negative integer, got \"%s\"" % v)
        if n < 0:
            raise PersistentServerConnectionProtocolException("expected non-negative integer, got \"%d\"" % n)
        return n

    @staticmethod
    def _read_string(handle):
        return handle.read(PersistentServerConnectionRequestPacket._read_number(handle))

class PersistentServerConnectionPacketParser(object):
    """
    Virtual class which handles packet-level I/O with stdin/stdout.  The
    handle_packet method must be overridden.
    """

    def __init__(self):
        self._owed_flush = False

    def write(self, data):
        """
        Write out a string, preceded by its length.  If a dict is passed
        in, it is automatically JSON encoded

        @param data: String or dictionary to send.
        """
        if sys.version_info >= (3, 0):
            if isinstance(data, bytes):
                sys.stdout.buffer.write(("%u\n" % len(data)).encode("ascii"))
                sys.stdout.buffer.write(data)
            elif isinstance(data, str):
                edata = data.encode("utf-8")
                sys.stdout.buffer.write(("%u\n" % len(edata)).encode("ascii"))
                sys.stdout.buffer.write(edata)
            elif isinstance(data, dict):
                edata = json.dumps(data, separators=(',', ':')).encode("utf-8")
                sys.stdout.buffer.write(("%u\n" % len(edata)).encode("ascii"))
                sys.stdout.buffer.write(edata)
            else:
                raise TypeError("Don't know how to serialize %s" % type(data).__name__)
        else:
            if isinstance(data, splunk.util.string_type):
                sys.stdout.write("%u\n%s" % (len(data), data))
            elif isinstance(data, dict):
                s = json.dumps(data, separators=(',', ':'))
                sys.stdout.write("%u\n%s" % (len(s), s))
            else:
                raise TypeError("Don't know how to serialize %s" % type(data).__name__)
        self._owed_flush = True

    def run(self):
        """
        Continuously read packets from stdin, passing each one to handle_packet()
        """
        if os.name.startswith("nt"):
            import msvcrt
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        while True:
            in_packet = PersistentServerConnectionRequestPacket()
            handle = sys.stdin
            if sys.version_info >= (3, 0):
                handle = sys.stdin.buffer
            if not in_packet.read(handle):
                break
            self.handle_packet(in_packet)
            if self._owed_flush:
                sys.stdout.flush()
                self._owed_flush = False

    def handle_packet(self, in_packet):
        """
        Virtual method called for each recieved packet

        @param in_packet: PersistentServerConnectionRequestPacket object recieved
        """
        raise NotImplementedError("PersistentServerConnectionPacketParser.handle_packet")
