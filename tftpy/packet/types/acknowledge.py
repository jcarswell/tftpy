import logging
import struct

from .base import TftpPacket, TftpPacketInitial
from tftpy.exceptions import TftpException
from tftpy.shared import MIN_BLKSIZE, MAX_BLKSIZE

logger = logging.getLogger()

class TftpPacketACK(TftpPacket):
    """
    Acknowledgement Packet
           2 bytes  2 bytes
           -----------------
    ACK   | 04    | Block # |
           -----------------
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 4
        self.blocknumber = 0

    def __str__(self):
        return f"ACK packet: block {self.blocknumber}" 

    def encode(self):
        logger.debug(f"encoding ACK: opcode = {self.opcode}, block = {self.blocknumber}")
        self.buffer = struct.pack(str("!HH"), self.opcode, self.blocknumber)
        return self

    def decode(self):
        if len(self.buffer) > 4:
            logger.debug("detected TFTP ACK but request is too large, will truncate")
            logger.debug(f"buffer was: {repr(self.buffer)}")
            self.buffer = self.buffer[0:4]
        self.opcode, self.blocknumber = struct.unpack(str("!HH"), self.buffer)
        logger.debug(f"decoded ACK packet: opcode = {self.opcode}, block = {self.blocknumber}")
        return self


class TftpPacketOACK(TftpPacketInitial):
    """
    Option Acknowledgement
    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    |  opc  |  opt1  | 0 | value1 | 0 |  optN  | 0 | valueN | 0 |
    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    """
    
    def __init__(self):
        super().__init__(self)
        self.opcode = 6

    def __str__(self):
        return f"OACK packet:\n    options = {self.options}"

    def encode(self):
        fmt = b"!H" # opcode
        options_list = []
        logger.debug("in TftpPacketOACK.encode")
        for key,value in self.options.items():            
            if isinstance(value, int):
                value = str(value).encode('ascii')
            elif not isinstance(value, bytes):
                value = value.encode('ascii')

            if not isinstance(key, bytes):
                key = key.encode('ascii')

            logger.debug(f"Option - {key} : {value}")
            
            fmt += b"%dsx" % len(key)
            fmt += b"%dsx" % len(value)
            options_list.append(key)
            options_list.append(value)
            
        self.buffer = struct.pack(fmt, self.opcode, *options_list)
        return self

    def decode(self):
        self.options = self.decode_options(self.buffer[2:])
        return self

    def match_options(self, options):
        """This method takes a set of options, and tries to match them with
        its own. It can accept some changes in those options from the server as
        part of a negotiation. Changed or unchanged, it will return a dict of
        the options so that the session can update itself to the negotiated
        options."""
        
        for name in self.options:
            if name in options:
                if name == 'blksize':
                    # We can accept anything between the min and max values.
                    size = int(self.options[name])
                    if size >= MIN_BLKSIZE and size <= MAX_BLKSIZE:
                        logger.debug(f"negotiated blksize of {size} bytes")
                        options['blksize'] = size
                    else:
                        raise TftpException(f"blksize {size} option outside allowed range")
                
                elif name == 'tsize':
                    size = int(self.options[name])
                    if size < 0:
                        raise TftpException("Negative file sizes not supported")
                
                else:
                    raise TftpException(f"Unsupported option: {name}")
                
        return True