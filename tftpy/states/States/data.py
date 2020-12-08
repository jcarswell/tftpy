from tftpy.exceptions import TftpOptionsError
from tftpy.states.base import TftpState
from tftpy.packet import types
from tftpy.shared import TftpErrors

class ExpectData(TftpState):
    """Just sent an ACK packet. Waiting for DAT."""

    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an ACK, which should be a DAT."""
        if isinstance(pkt, types.Data):
            return self.handle_dat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, types.Ack):
            # Umm, we ACK, you don't.
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received ACK from peer when expecting DAT")

        elif isinstance(pkt, types.WriteRQ):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError("Received WRQ from peer when expecting DAT")

        elif isinstance(pkt, type.Error):
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError(f"Received ERR from peer: {str(pkt)}")

        else:
            self.send_error(TftpErrors.ILLEGALTFTPOP)
            raise TftpOptionsError(f"Received unknown packet type from peer: {str(pkt)}")