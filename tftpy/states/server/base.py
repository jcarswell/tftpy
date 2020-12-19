import logging
import os

from tftpy.states.base import TftpState
from tftpy.exceptions import TftpException
from tftpy.shared import TftpErrors,DEF_BLKSIZE

logger = logging.getLogger()

class TftpServerState(TftpState):
    """The base class for server states."""

    def __init__(self, context):
        super().__init__(context)

        # This variable is used to store the absolute path to the file being
        # managed.
        self.full_path = None

    def server_initial(self, pkt, raddress, rport):
        """This method performs initial setup for a server context transfer,
        put here to refactor code out of the TftpStateServerRecvRRQ and
        TftpStateServerRecvWRQ classes, since their initial setup is
        identical. The method returns a boolean, sendoack, to indicate whether
        it is required to send an OACK to the client."""
        
        options = pkt.options
        sendoack = False
        if not self.context.tidport:
            self.context.tidport = rport
            logger.info(f"Setting tidport to {rport}")

        logger.debug("Setting default options, blksize")
        self.context.options = { 'blksize': DEF_BLKSIZE }

        if options:
            logger.debug(f"Options requested: {options}")
            supported_options = self.return_Supported_options(options)
            self.context.options.update(supported_options)
            sendoack = True

        # FIXME - only octet mode is supported at this time.
        if pkt.mode != 'octet':
            #self.sendError(TftpErrors.IllegalTftpOp)
            #raise TftpException("Only octet transfers are supported at this time.")
            logger.warning("Received non-octet mode request. I'll reply with binary data.")

        # test host/port of client end
        if self.context.host != raddress or self.context.port != rport:
            self.send_error(TftpErrors.UNKNOWNTID)
            logger.error(f"Expected traffic from {self.context.host}:{self.context.port} but received it "
                            f"from {raddress}:{rport} instead.")

            self.context.metrics.errors += 1
            return self

        logger.debug(f"Requested filename is {pkt.filename}")

        # Build the filename on this server and ensure it is contained
        # in the specified root directory.
        #
        # Filenames that begin with server root are accepted. It's
        # assumed the client and server are tightly connected and this
        # provides backwards compatibility.
        #
        # Filenames otherwise are relative to the server root. If they
        # begin with a '/' strip it off as otherwise os.path.join will
        # treat it as absolute (regardless of whether it is ntpath or
        # posixpath module
        if pkt.filename.startswith(self.context.root):
            full_path = pkt.filename
        else:
            full_path = os.path.join(self.context.root, pkt.filename.lstrip('/'))

        # Use abspath to eliminate any remaining relative elements
        # (e.g. '..') and ensure that is still within the server's
        # root directory
        self.full_path = os.path.abspath(full_path)
        logger.debug(f"full_path is {full_path}")

        if self.full_path.startswith(self.context.root):
            logger.info("requested file is in the server root - good")
        else:
            logger.warning("requested file is not within the server root - bad")
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpException("bad file path")

        self.context.file_to_transfer = pkt.filename

        return sendoack