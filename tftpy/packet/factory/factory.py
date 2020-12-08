import logging
import struct

from tftpy.shared import tftpassert
from tftpy.packet import types

logger = logging.getLogger()

class PacketFactory:
    """This class generates TftpPacket objects. It is responsible for parsing
    raw buffers off of the wire and returning objects representing them, via
    the parse() method."""
    
    classes = {
        1: types.ReadRQ,
        2: types.WriteRQ,
        3: types.Data,
        4: types.Ack,
        5: types.Error,
        6: types.OptionAck
        }

    def parse(self, buffer):
        """This method is used to parse an existing datagram into its
        corresponding TftpPacket object. The buffer is the raw bytes off of
        the network."""

        logger.debug(f"parsing a {len(buffer)} byte packet")
        (opcode,) = struct.unpack(str("!H"), buffer[:2])
        logger.debug(f"opcode is {opcode}")
        packet = self.__create(opcode)
        packet.buffer = buffer
        return packet.decode()

    def __create(self, opcode):
        """This method returns the appropriate class object corresponding to
        the passed opcode."""
        
        tftpassert(opcode in self.classes, f"Unsupported opcode: {opcode}")
        packet = self.classes[opcode]()

        return packet