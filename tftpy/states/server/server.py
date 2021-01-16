import logging
import os

from typing import Union

from tftpy.states.base import TftpState,ExpectData
from .base import TftpServerState
from tftpy.exceptions import TftpException,TftpOptionsError,TftpFileNotFoundError
from tftpy.states.states import ExpectAck
from tftpy.packet import types
from tftpy.shared import TftpErrors

logger = logging.getLogger()

class ReceiveReadRQ(TftpServerState):
    """This class represents the state of the TFTP server when it has just
    received an RRQ packet."""
    
    def handle(self, pkt: types.ReadRQ, raddress: str, rport: int) -> ExpectAck:
        """Handle an initial RRQ packet as a server.

        Args:
            pkt (types.ReadRQ): Packet Data
            raddress (str): Remote Addres
            rport (int): Remote Port

        Raises:
            TftpFileNotFoundError: When the requested file is not found or the dyn_file_func returns None

        Returns:
            ExpectAck: Next context state
        """
        
        logger.debug("In tftpy.states.server.ReceiveReadRQ.handle")
        
        sendoack = self.server_initial(pkt, raddress, rport)
        logger.info(f"Opening file {self.full_path} for reading")
        
        if os.path.exists(self.full_path):
            # Note: Open in binary mode for win32 portability, since win32
            # blows.
            self.context.fileobj = open(self.full_path, "rb")

        elif self.context.dyn_file_func:
            logger.debug(f"No such file {self.full_path} but using dyn_file_func")
            self.context.fileobj = self.context.dyn_file_func(self.context.file_to_transfer, 
                                                              raddress=raddress,
                                                              rport=rport)

            if self.context.fileobj is None:
                logger.debug("dyn_file_func returned 'None', treating as FileNotFound")
                self.send_error(TftpErrors.FILENOTFOUND)
                raise TftpFileNotFoundError(f"File not found: {self.full_path}")

        else:
            logger.warn(f"File not found: {self.full_path}")
            self.send_error(TftpErrors.FILENOTFOUND)
            raise TftpFileNotFoundError(f"File not found: {self.full_path}")

        # Options negotiation.
        if sendoack and 'tsize' in self.context.options:
            # getting the file size for the tsize option. As we handle
            # file-like objects and not only real files, we use this seeking
            # method instead of asking the OS
            self.context.fileobj.seek(0, os.SEEK_END)
            tsize = str(self.context.fileobj.tell())
            self.context.fileobj.seek(0, 0)
            self.context.options['tsize'] = tsize

        if sendoack:
            # Note, next_block is 0 here since that's the proper
            # acknowledgement to an OACK.
            # FIXME: perhaps we do need a TftpStateExpectOACK class...
            self.send_oack()
            # Note, self.context.next_block is already 0.
        else:
            self.context.next_block = 1
            logger.debug("No requested options, starting send...")
            self.context.pending_complete = self.send_dat()

        # Note, we expect an ack regardless of whether we sent a DAT or an
        # OACK.
        # Note, we don't have to check any other states in this method, that's
        # up to the caller.
        return ExpectAck(self.context)


class ReceiveWriteRQ(TftpServerState):
    """This class represents the state of the TFTP server when it has just
    received a WRQ packet."""

    def make_subdirs(self) -> None:
        """The purpose of this method is to, if necessary, create all of the
        subdirectories leading up to the file to the written.
        """

        # Pull off everything below the root.
        subpath = self.full_path[len(self.context.root):]
        logger.debug(f"make_subdirs: subpath is {subpath}")
        
        # Split on directory separators, but drop the last one, as it should
        # be the filename.
        dirs = subpath.split(os.sep)[:-1]
        logger.debug(f"dirs is {dirs}")
        current = self.context.root
        
        for dir in dirs:
            if dir:
                current = os.path.join(current, dir)
                if not os.path.isdir(current):
                    os.mkdir(current, 0o700) # FIXME - This should be defined in the server startup

    def handle(self, pkt: types.WriteRQ, raddress: str, rport: int) -> ExpectData:
        """Handle an initial WRQ packet as a server.

        Args:
            pkt (types.WriteRQ): Packet Data
            raddress (str): Remote Addres
            rport (int): Remote Port

        Raises:
            TftpException: Invalid File Path requested

        Returns:
            context.ExpectAck: Next context state
        """

        logger.debug("In tftpy.states.server.ReceiveWriteRQ.handle")
        
        sendoack = self.server_initial(pkt, raddress, rport)
        
        if self.context.upload_open:
            f = self.context.upload_open(self.full_path, self.context)
            if f is None:
                self.send_error(TftpErrors.ACCESSVIOLATION)
                raise TftpException(f"Dynamic path {self.full_path} not permitted",error_code=TftpErrors.ACCESSVIOLATION)
            else:
                self.context.fileobj = f

        else:
            logger.info(f"Opening file {self.full_path} for writing")
            if os.path.exists(self.full_path):
                logger.warning(f"File {self.context.file_to_transfer} exists already, overwriting...")

            # FIXME: I think we should upload to a temp file and not overwrite
            # the existing file until the file is successfully uploaded.
            self.make_subdirs()
            self.context.fileobj = open(self.full_path, "wb")

        # Options negotiation.
        if sendoack:
            logger.debug("Sending OACK to client")
            self.send_oack()
        else:
            logger.debug("No requested options, expecting transfer to begin...")
            self.send_ack()

        self.context.next_block = 1
        
        # We may have sent an OACK, but we're expecting a DAT as the response
        # to either the OACK or an ACK, so lets unconditionally use the
        # TftpStateExpectDAT state.
        # Note, we don't have to check any other states in this method, that's
        # up to the caller.
        return ExpectData(self.context)


class Start(TftpState):
    """The start state for the server. This is a transitory state since at
    this point we don't know if we're handling an upload or a download. We
    will commit to one of them once we interpret the initial packet."""

    def handle(self,
               pkt: Union[types.ReadRQ,types.WriteRQ],
               raddress: str, 
               rport: int) -> Union[ReceiveWriteRQ,ReceiveReadRQ]:
        """Handle a packet we just received.

        Args:
            pkt (Union[types.ReadRQ,types.WriteRQ]): Recieved Packet
            raddress (str): Remote client address
            rport (int): Remote client port

        Raises:
            TftpOptionsError: received an invalid packet for the expected state

        Returns:
            Union[ReceiveWriteRQ,ReceiveReadRQ]: Returns the next state
        """
    
        logger.debug("In tftpy.states.Start.server.handle")
        
        if isinstance(pkt, types.ReadRQ):
            logger.debug("Handling an RRQ packet")
            return ReceiveReadRQ(self.context).handle(pkt,
                                                      raddress,
                                                      rport)
        elif isinstance(pkt, types.WriteRQ):
            logger.debug("Handling a WRQ packet")
            return ReceiveWriteRQ(self.context).handle(pkt,
                                                       raddress,
                                                       rport)
        else:
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError(f"Invalid packet to begin up/download: {pkt}")