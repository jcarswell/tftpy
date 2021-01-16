import logging
import struct

from typing import Union

from tftpy.shared import tftpassert
from tftpy.packet import types

logger = logging.getLogger('tftpy.packet.factory')

packet_type = Union[
    types.ReadRQ,
    types.WriteRQ,
    types.OptionAck,
    types.Ack,
    types.Data,
    types.Error
]

class PacketFactory:
    """This class generates TftpPacket objects. It is responsible for parsing
    raw buffers off of the wire and returning objects representing them, via
    the parse() method."""
    
    _classes = {
        1: types.ReadRQ,
        2: types.WriteRQ,
        3: types.Data,
        4: types.Ack,
        5: types.Error,
        6: types.OptionAck
        }

    def parse(self, buffer: bytes) -> packet_type:
        """This method is used to parse an existing datagram into its
        corresponding TftpPacket object.

        Args:
            buffer (bytes): Packet Data

        Returns:
            types: packet type base on the opcode
        """

        logger.debug(f"parsing a {len(buffer)} byte packet")
        (opcode,) = struct.unpack(str("!H"), buffer[:2])
        logger.debug(f"opcode is {opcode}")
        packet = self.__create(opcode)
        packet.buffer = buffer
        return packet.decode()

    def __create(self, opcode: int) -> packet_type:
        """This method returns the appropriate class object corresponding to
        the passed opcode.

        Args:
            opcode (int): The opcode from the buffer

        Returns:
            types: The Appropriate packet type class
        """

        tftpassert(opcode in self._classes, f"Unsupported opcode: {opcode}")
        packet = self._classes[opcode]()

        return packet