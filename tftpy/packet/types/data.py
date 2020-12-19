import struct
import logging

from .base import TftpPacket

logger = logging.getLogger('tftpy.packet.types.data')

class Data(TftpPacket):
    """
           2 bytes  2 bytes  n bytes
           ---------------------~~--
    DATA  | 03    | Block # | Data  |
           ---------------------~~--
    """
    def __init__(self):
        super().__init__()
        self.opcode = 3
        self.blocknumber = 0
        self.data = None

    def __str__(self):
        s = 'DAT packet: block %s' % self.blocknumber
        if self.data:
            s += '\n    data: %d bytes' % len(self.data)
        return s

    def encode(self):
        """Encode the DAT packet. This method populates self.buffer, and
        returns self for easy method chaining."""
        if len(self.data) == 0:
            logger.debug("Encoding an empty DAT packet")
        data = self.data
        if not isinstance(self.data, bytes):
            data = self.data.encode('ascii')
        fmt = b"!HH%ds" % len(data)
        self.buffer = struct.pack(fmt,
                                  self.opcode,
                                  self.blocknumber,
                                  data)
        return self

    def decode(self):
        """Decode self.buffer into instance variables. It returns self for
        easy method chaining."""
        # We know the first 2 bytes are the opcode. The second two are the
        # block number.
        (self.blocknumber,) = struct.unpack(str("!H"), self.buffer[2:4])
        logger.debug("decoding DAT packet, block number %d", self.blocknumber)
        logger.debug("should be %d bytes in the packet total", len(self.buffer))
        # Everything else is data.
        self.data = self.buffer[4:]
        logger.debug("found %d bytes of data", len(self.data))
        return self
