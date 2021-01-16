import struct
import logging

from tftpy.shared import tftpassert
from tftpy.exceptions import TftpException

logger = logging.getLogger('tftp.packet.types.base')

class TftpPacketWithOptions:
    """This class exists to permit some TftpPacket subclasses to share code
    regarding options handling. It does not inherit from TftpPacket, as the
    goal is just to share code here, and not cause diamond inheritance."""

    def __init__(self) -> None:
        self.options = {}

    @property
    def options(self) -> dict:
        """Getter function for the option property"""
        return self._options

    @options.setter
    def options(self, options: dict) -> None:
        """Setter function for option property

        Args:
            options (dict): option names and values
        """
        
        logger.debug("in TftpPacketWithOptions.setoptions")
        logger.debug("options: %s", options)
        myoptions = {}
        for key in options:
            newkey = key
            if isinstance(key, bytes):
                newkey = newkey.decode('ascii')
            newval = options[key]
            if isinstance(newval, bytes):
                newval = newval.decode('ascii')
            myoptions[newkey] = newval
            logger.debug("populated myoptions with %s = %s", newkey, myoptions[newkey])

        logger.debug("setting options hash to: %s", myoptions)
        self._options = myoptions

    def decode_options(self, buffer: bytes) -> dict:
        """This method decodes the section of the buffer that contains an
        unknown number of options. It returns a dictionary of option names and
        values.

        Args:
            buffer (bytes): packet data received on the socket

        Raises:
            TftpException: invalid option received

        Returns:
            dict: option names and values
        """
        
        fmt = b"!"
        options = {}

        logger.debug(f"decode_options: buffer is: {repr(buffer)}")
        logger.debug(f"size of buffer is {len(buffer)} bytes")
        if len(buffer) == 0:
            logger.debug("size of buffer is zero, returning empty hash")
            return {}

        # Count the nulls in the buffer. Each one terminates a string.
        logger.debug("about to iterate options buffer counting nulls")
        length = 0
        
        for i in range(len(buffer)):
            if ord(buffer[i:i+1]) == 0:
                logger.debug(f"found a null at length {length}")
                if length > 0:
                    fmt += b"%dsx" % length
                    length = -1
                else:
                    raise TftpException("Invalid options in buffer")
                
            length += 1

        logger.debug(f"about to unpack, fmt is: {fmt}")
        mystruct = struct.unpack(fmt, buffer)

        tftpassert(len(mystruct) % 2 == 0,
                   "packet with odd number of option/value pairs")

        for i in range(0, len(mystruct), 2):
            key = mystruct[i].decode('ascii')
            val = mystruct[i+1].decode('ascii')
            logger.debug(f"setting option {key} to {val}")
            logger.debug(f"types are {type(key)} and {type(val)}")
            options[key] = val

        return options


class TftpPacket:
    """This class is the parent class of all tftp packet classes. It is an
    abstract class, providing an interface, and should not be instantiated
    directly."""
    
    def __init__(self) -> None:
        self.opcode = 0
        self.buffer = None

    def encode(self) -> None:
        """The encode method of a TftpPacket takes keyword arguments specific
        to the type of packet, and packs an appropriate buffer in network-byte
        order suitable for sending over the wire.

        This is an abstract method."""
        raise NotImplementedError

    def decode(self) -> None:
        """The decode method of a TftpPacket takes a buffer off of the wire in
        network-byte order, and decodes it, populating internal properties as
        appropriate. This can only be done once the first 2-byte opcode has
        already been decoded, but the data section does include the entire
        datagram.

        This is an abstract method."""
        raise NotImplementedError


class TftpPacketInitial(TftpPacket, TftpPacketWithOptions):
    """This class is a common parent class for the RRQ and WRQ packets, as
    they share quite a bit of code."""
    
    def __init__(self) -> None:
        super().__init__()
        self.filename = None
        self.mode = None

    def encode(self) -> 'TftpPacketInitial':
        """Encode the packet's buffer from the instance variables.

        Raises:
            TftpException: Unsupported mode in the options

        Returns:
            TftpPacketInitial: self
        """
        
        tftpassert(self.filename, "filename required in initial packet")
        tftpassert(self.mode, "mode required in initial packet")
        
        # Make sure filename and mode are bytestrings.
        filename = self.filename
        mode = self.mode
        
        if not isinstance(filename, bytes):
            filename = filename.encode('ascii')
        if not isinstance(self.mode, bytes):
            mode = mode.encode('ascii')

        ptype = None
        if self.opcode == 1: 
            ptype = "RRQ"
        else:
            ptype = "WRQ"
            
        logger.debug(f"Encoding {ptype} packet, filename = {filename}, mode = {mode}")
        

        fmt = b"!H"
        fmt += b"%dsx" % len(filename)
        
        if mode == b"octet":
            fmt += b"5sx"
        elif mode == b"netascii":
            fmt += b"8sx"
        else:
            raise TftpException(f"Unsupported mode: {mode}")
        
        # Add options. Note that the options list must be bytes.
        options_list = []
        
        for key,value in self.options.items():
            logger.debug(f"    Option {key} = {value}")
            # Populate the option name
            name = key
            if not isinstance(name, bytes):
                name = name.encode('ascii')
            options_list.append(name)
            fmt += b"%dsx" % len(name)

            # Work with all strings.
            if isinstance(value, int):
                value = str(value).encode('ascii')
            elif not isinstance(value, bytes):
                value = value.encode('ascii')
                
            options_list.append(value)
            fmt += b"%dsx" % len(value)

        logger.debug(f"fmt is {fmt}")
        logger.debug(f"options_list is {options_list}")
        logger.debug(f"size of struct is {struct.calcsize(fmt)}")
        
        self.buffer = struct.pack(fmt,
                                  self.opcode,
                                  filename,
                                  mode,
                                  *options_list)

        logger.debug("buffer is %s", repr(self.buffer))
        return self

    def decode(self) -> 'TftpPacketInitial':
        """Decode the buffer

        Returns:
            TftpPacketInitial: self
        """
        tftpassert(self.buffer, "Can't decode, buffer is empty")

        nulls = 0
        fmt = b""
        length = 0
        tlength = 0
        
        logger.debug("in decode: about to iterate buffer counting nulls")
        
        subbuf = self.buffer[2:]
        
        for i in range(len(subbuf)):
            if ord(subbuf[i:i+1]) == 0:
                nulls += 1
                logger.debug(f"found a null at length {length}, now have {nulls}")
                fmt += b"%dsx" % length
                length = -1
                # At 2 nulls, we want to mark that position for decoding.
                if nulls == 2:
                    break
            length += 1
            tlength += 1

        logger.debug(f"hopefully found end of mode at length {length}")
        # length should now be the end of the mode.
        tftpassert(nulls == 2, "malformed packet")
        shortbuf = subbuf[:tlength+1]
        logger.debug(f"about to unpack buffer with fmt: {fmt}")
        logger.debug(f"unpacking buffer: {repr(shortbuf)}", )
        mystruct = struct.unpack(fmt, shortbuf)

        tftpassert(len(mystruct) == 2, "malformed packet")
        self.filename = mystruct[0].decode('ascii')
        self.mode = mystruct[1].decode('ascii').lower() # force lc - bug 17
        logger.debug(f"set filename to {self.filename}")
        logger.debug(f"set mode to {self.mode}")

        self.options = self.decode_options(subbuf[tlength+1:])
        logger.debug(f"options dict is now {self.options}")
        return self
