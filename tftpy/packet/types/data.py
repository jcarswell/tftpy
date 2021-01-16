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
    
    def __init__(self) -> None:
        super().__init__()
        self.opcode = 3
        self.blocknumber = 0
        self.data = None

    def __str__(self) -> str:
        s = f"DAT packet: block {self.blocknumber}"
        if self.data:
            s += f"\n    data: {len(self.data)} bytes"

        return s

    def encode(self) -> 'Data':
        """Encode the Data packet.

        Returns:
            Data: self
        """

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

    def decode(self) -> 'Data':
        """Decode Data packet.

        Returns:
            Data: self
        """

        # We know the first 2 bytes are the opcode. The second two are the
        # block number.
        (self.blocknumber,) = struct.unpack(str("!H"), self.buffer[2:4])
        logger.debug(f"decoding DAT packet, block number {self.blocknumber}")
        logger.debug(f"should be {len(self.buffer)} bytes in the packet total")
        # Everything else is data.
        
        self.data = self.buffer[4:]
        logger.debug(f"found {len(self.data)} bytes of data")
        
        return self
