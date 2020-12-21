import logging

from tftpy.packet import types
from tftpy.shared import TftpErrors,DEF_BLKSIZE
from tftpy.states.base import TftpState,ExpectData
from tftpy.exceptions import TftpException, TftpOptionsError, TftpFileNotFoundError
from .acknowledge import ExpectAck

logger = logging.getLogger()

class SentWriteRQ(TftpState):
    """Just sent an WRQ packet for an upload."""

    def handle(self, pkt, raddress, rport):
        """Handle a packet we just received."""
        
        if not self.context.tidport:
            self.context.tidport = rport
            logger.debug(f"Set remote port for session to {rport}")

        # If we're going to successfully transfer the file, then we should see
        # either an OACK for accepted options, or an ACK to ignore options.
        if isinstance(pkt, types.OptionAck):
            logger.info("Received OACK from server")
            try:
                self.handle_oack(pkt)
            except TftpException:
                logger.error("Failed to negotiate options")
                self.send_error(TftpErrors.FAILEDNEGOTIATION)
                raise TftpOptionsError("Failed to negotiate options")
            else:
                logger.debug("Sending first DAT packet")
                self.context.pending_complete = self.send_dat()
                logger.debug("Changing state to TftpStateExpectACK")
                return ExpectAck(self.context)

        elif isinstance(pkt, types.Ack):
            logger.info("Received ACK from server")
            logger.debug("Apparently the server ignored our options")
            # The block number should be zero.
            if pkt.blocknumber == 0:
                logger.debug("Ack blocknumber is zero as expected")
                logger.debug("Sending first DAT packet")
                self.context.pending_complete = self.send_dat()
                logger.debug("Changing state to TftpStateExpectACK")
                return ExpectAck(self.context)
            else:
                logger.warning(f"Discarding ACK to block {pkt.blocknumber}")
                logger.debug("Still waiting for valid response from server")
                return self

        elif isinstance(pkt, types.Error):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError(f"Received ERR from server: {pkt}")

        elif isinstance(pkt, types.ReadRQ):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received RRQ from server while in upload")

        elif isinstance(pkt, types.Data):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received DAT from server while in upload")

        else:
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received unknown packet type from server: {pkt}")

        # By default, no state change.
        return self

class SentReadRQ(TftpState):
    """Just sent an RRQ packet."""

    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an RRQ to the server."""
        
        if not self.context.tidport:
            self.context.tidport = rport
            logger.info(f"Set remote port for session to {rport}")

        # Now check the packet type and dispatch it properly.
        if isinstance(pkt, types.OptionAck):
            logger.info("Received OACK from server")

            try:
                self.handle_oack(pkt)
            except TftpException as err:
                logger.error(f"Failed to negotiate options: {str(err)}")
                self.send_error(TftpErrors.FAILEDNEGOTIATION)
                raise TftpException("Failed to negotiate options", error_code=TftpErrors.FAILEDNEGOTIATION)
            else:
                logger.debug("Sending ACK to OACK")

                self.send_ack(blocknumber=0)

                logger.debug("Changing state to TftpStateExpectDAT")
                return ExpectData(self.context)

        elif isinstance(pkt, types.Data):
            # If there are any options set, then the server didn't honour any
            # of them.
            logger.info("Received DAT from server")
            if self.context.options:
                logger.info("Server ignored options, falling back to defaults")
                self.context.options = { 'blksize': DEF_BLKSIZE }
            return self.handle_dat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, types.Ack):
            # Umm, we ACK, the server doesn't. # <- Does this guy think he's a comedian?
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received ACK from server while in download")

        elif isinstance(pkt, types.WriteRQ):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received WRQ from server while in download")

        elif isinstance(pkt, types.Error):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            logger.debug(f"Received ERR packet: {pkt}")
            if pkt.errorcode == TftpErrors.FILENOTFOUND:
                raise TftpFileNotFoundError("File not found")
            else:
                raise TftpOptionsError(f"Received ERR from server: {pkt}")

        else:
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpException(f"Received unknown packet type from server: {pkt}")

        # By default, no state change.
        return self