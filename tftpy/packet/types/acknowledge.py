import logging
import struct

from typing import Any

from .base import TftpPacket, TftpPacketInitial
from tftpy.exceptions import TftpException
from tftpy.shared import MIN_BLKSIZE, MAX_BLKSIZE

logger = logging.getLogger('tftpy.packet.types.acknowledge')

class Ack(TftpPacket):
    """
    Acknowledgement Packet
           2 bytes  2 bytes
           -----------------
    ACK   | 04    | Block # |
           -----------------
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.opcode = 4
        self.blocknumber = 0

    def __str__(self) -> str:
        return f"ACK packet: block {self.blocknumber}" 

    def encode(self) -> 'Ack':
        """Encode acknowlegement packet for sending

        Returns:
            Ack: self
        """

        logger.debug(f"encoding ACK: opcode = {self.opcode}, block = {self.blocknumber}")
        self.buffer = struct.pack(str("!HH"), self.opcode, self.blocknumber)
        return self

    def decode(self) -> 'Ack':
        """Decode and acknowlegement packet

        Returns:
            Ack: self
        """

        if len(self.buffer) > 4:
            logger.debug("detected TFTP ACK but request is too large, will truncate")
            logger.debug(f"buffer was: {repr(self.buffer)}")
            self.buffer = self.buffer[0:4]

        self.opcode, self.blocknumber = struct.unpack(str("!HH"), self.buffer)
        logger.debug(f"decoded ACK packet: opcode = {self.opcode}, block = {self.blocknumber}")
        return self


class OptionAck(TftpPacketInitial):
    """
    Option Acknowledgement
    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    |  opc  |  opt1  | 0 | value1 | 0 |  optN  | 0 | valueN | 0 |
    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.opcode = 6

    def __str__(self) -> str:
        return f"OACK packet:\n    options = {self.options}"

    def encode(self) -> 'OptionAck':
        """Encode option acknowlegement packet for sending
        
        Returns:
            OptionAck: self
        """

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

    def decode(self) -> 'OptionAck':
        """Decode an option acknowlegement packet

        Returns:
            OptionAck: self
        """

        self.options = self.decode_options(self.buffer[2:])
        return self

    def match_options(self, option: str, value: str) -> Any:
        return self.validate_option(option,value)

    def validate_option(self, option: str, value: str) -> Any:
        """Validates all option recieved and convert string to integers for numbered options

        Raises:
            TftpException: Invalid Block size requested
            TftpException: Negitive File size requested
            TftpException: Unsupported Options

        Returns:
            str,int: parsed and valid value
        """
        
        option = option.lower()
        if option == 'blksize':
            # We can accept anything between the min and max values.
            value = int(value)
            if MIN_BLKSIZE <= value <= MAX_BLKSIZE:
                logger.debug(f"negotiated blksize of {value} bytes")
            else:
                raise TftpException(f"blksize {value} option outside allowed range")
        
        elif option == 'tsize':
            value = int(value)
            if value < 0:
                raise TftpException("Negative file sizes not supported")
        
        else:
            raise TftpException(f"Unsupported option: {value}")

        return value