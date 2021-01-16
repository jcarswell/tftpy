import logging
import struct

from .base import TftpPacket
from tftpy.shared import tftpassert
from tftpy.exceptions import TftpException

logger = logging.getLogger('tftpy.packet.types.error')

class Error(TftpPacket):
    """
        Error Packet
        
            2 bytes   2 bytes      string   1 byte
            --------------------------------------
     ERROR | 05     | ErrorCode |  ErrMsg  |   0  |
            --------------------------------------

    Error Codes

    Value     Meaning

    0         Not defined, see error message (if any).
    1         File not found.
    2         Access violation.
    3         Disk full or allocation exceeded.
    4         Illegal TFTP operation.
    5         Unknown transfer ID.
    6         File already exists.
    7         No such user.
    8         Failed to negotiate options
    """

    def __init__(self, errorcode: int = None) -> None:
        super().__init__()
        self.opcode = 5
        self.errorcode = errorcode
        self.errmsg = None
        self.errmsgs = {
            1: b"File not found",
            2: b"Access violation",
            3: b"Disk full or allocation exceeded",
            4: b"Illegal TFTP operation",
            5: b"Unknown transfer ID",
            6: b"File already exists",
            7: b"No such user",
            8: b"Failed to negotiate options"
            }

    def __str__(self) -> str:
        s = f"ERR packet: errorcode = {self.errorcode}"
        s += f"\n    msg = {self.errmsgs.get(self.errorcode,'')}"

        return s

    def encode(self) -> 'Error':
        """Encode the Error packet based on opcode and errorcode.

        Returns:
            Error: self
        """
        
        fmt = b"!HH%dsx" % len(self.errmsgs[self.errorcode])
        logger.debug(f"encoding ERR packet with fmt {fmt}")
        self.buffer = struct.pack(fmt,
                                  self.opcode,
                                  self.errorcode,
                                  self.errmsgs[self.errorcode])

        return self

    def decode(self) -> 'Error':
        """Decode Error packet

        Returns:
            Error: self
        """

        buflen = len(self.buffer)
        tftpassert(buflen >= 4, "malformed ERR packet, too short")
        logger.debug(f"Decoding ERR packet, length {buflen} bytes")

        if buflen == 4:
            logger.debug("Allowing this affront to the RFC of a 4-byte packet")
            fmt = b"!HH"
            logger.debug(f"Decoding ERR packet with fmt: {fmt}")
            self.opcode, self.errorcode = struct.unpack(fmt,
                                                        self.buffer)

        else:
            logger.debug("Good ERR packet > 4 bytes")
            fmt = b"!HH%dsx" % (len(self.buffer) - 5)
            logger.debug(f"Decoding ERR packet with fmt: {fmt}")
            self.opcode, self.errorcode, self.errmsg = struct.unpack(fmt, self.buffer)
        logger.error(f"ERR packet - errorcode: {self.errorcode}, message: {self.errmsg}")

        return self