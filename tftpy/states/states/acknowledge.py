import logging

from tftpy.states.base import TftpState
from tftpy.exceptions import TftpException
from tftp.packet import types

logger = logging.getLogger()

class ExpectAck(TftpState):
    """This class represents the state of the transfer when a DAT was just
    sent, and we are waiting for an ACK from the server. This class is the
    same one used by the client during the upload, and the server during the
    download."""

    def handle(self, pkt, raddress, rport):
        "Handle a packet, hopefully an ACK since we just sent a DAT."
        
        if isinstance(pkt, types.Ack):
            logger.debug(f"Received ACK for packet {pkt.blocknumber}")

            # Is this an ack to the one we just sent?
            if self.context.next_block == pkt.blocknumber:
                if self.context.pending_complete:
                    logger.info("Received ACK to final DAT, we're done.")
                    return None

                else:
                    logger.debug("Good ACK, sending next DAT")
                    self.context.next_block += 1
                    logger.debug(f"Incremented next_block to {self.context.next_block}")
                    self.context.pending_complete = self.send_dat()

            elif pkt.blocknumber < self.context.next_block:
                logger.warning(f"Received duplicate ACK for block {pkt.blocknumber}")
                self.context.metrics.add_dup(pkt)

            else:
                logger.warning("Oooh, time warp. Received ACK to packet we didn't send yet. Discarding.")
                self.context.metrics.errors += 1

            return self

        elif isinstance(pkt, types.Error):
            logger.error(f"Received ERR packet from peer: {str(pkt)}")
            raise TftpException(f"Received ERR packet from peer: {str(pkt)}")
        
        else:
            logger.warning(f"Discarding unsupported packet: {str(pkt)}")
            return self