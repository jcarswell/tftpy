import logging

from tftpy.shared import tftpassert,TftpErrors,DELAY_BLOCK,MIN_BLKSIZE,MAX_BLKSIZE
from tftpy.exceptions import TftpException,TftpOptionsError
from tftpy.packet import types
from tftpy.shared import TftpErrors

logger = logging.getLogger()

class TftpState:
    """The base class for the states."""

    def __init__(self, context):
        """Constructor for setting up common instance variables. The involved
        file object is required, since in tftp there's always a file
        involved."""
        
        self.context = context

    def handle(self, pkt, raddress, rport):
        """An abstract method for handling a packet. It is expected to return
        a TftpState object, either itself or a new state."""
        
        raise NotImplementedError

    def handle_oack(self, pkt):
        """This method handles an OACK from the server, syncing any accepted
        options."""
        if len(pkt.options.keys()) > 0:
            if pkt.match_options(self.context.options):
                logger.info("Successful negotiation of options")
                # Set options to OACK options
                self.context.options = pkt.options
                for key in self.context.options:
                    logger.info(f"    {key} = {self.context.options[key]}")
            else:
                logger.error("Failed to negotiate options")
                raise TftpOptionsError("Failed to negotiate options")
        else:
            raise TftpException("No options found in OACK")

    def return_supported_options(self, options):
        """This method takes a requested options list from a client, and
        returns the ones that are supported."""
        
        # We support the options blksize and tsize right now.
        
        accepted_options = {}
        
        for option in options:
            if option == 'blksize':
                # Make sure it's valid.
                if int(options[option]) > MAX_BLKSIZE:
                    logger.info(f"Client requested blksize greater than {MAX_BLKSIZE} setting to maximum")
                    accepted_options[option] = MAX_BLKSIZE
                elif int(options[option]) < MIN_BLKSIZE:
                    logger.info(f"Client requested blksize less than {MIN_BLKSIZE} setting to minimum") 
                    accepted_options[option] = MIN_BLKSIZE
                else:
                    accepted_options[option] = options[option]
            elif option == 'tsize':
                logger.debug("tsize option is set")
                accepted_options['tsize'] = 0
            else:
                logger.info(f"Dropping unsupported option: {option}")
        
        logger.debug(f"Returning these accepted options: {accepted_options}")
        
        return accepted_options

    def send_dat(self):
        """This method sends the next DAT packet based on the data in the
        context. It returns a boolean indicating whether the transfer is
        finished."""
        
        finished = False
        blocknumber = self.context.next_block
        
        # Test hook
        if DELAY_BLOCK and DELAY_BLOCK == blocknumber:
            import time
            logger.debug("Deliberately delaying 10 seconds...")
            time.sleep(10)
        
        dat = None
        blksize = self.context.block_size()
        buffer = self.context.fileobj.read(blksize)
        logger.debug(f"Read {len(buffer)} bytes into buffer")
        
        if len(buffer) < blksize:
            logger.info(f"Reached EOF on file {self.context.file_to_transfer}")
            finished = True
        
        dat = types.Data()
        dat.data = buffer
        dat.blocknumber = blocknumber
        self.context.metrics.bytes += len(dat.data)
        logger.debug(f"Sending DAT packet {dat.blocknumber}")
        self.context.sock.sendto(dat.encode().buffer,
                                 (self.context.host, self.context.tidport))
        
        if self.context.packethook:
            self.context.packethook(dat)
        
        self.context.last_pkt = dat
        
        return finished

    def send_ack(self, blocknumber=None):
        """This method sends an ack packet to the block number specified. If
        none is specified, it defaults to the next_block property in the
        parent context."""
        
        logger.debug(f"In send_ack, passed blocknumber is {blocknumber}")
        if blocknumber is None:
            blocknumber = self.context.next_block
        
        logger.info(f"Sending ack to block {blocknumber}")
        ackpkt = types.Ack()
        ackpkt.blocknumber = blocknumber
        self.context.sock.sendto(ackpkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = ackpkt

    def send_error(self, errorcode):
        """This method uses the socket passed, and uses the errorcode to
        compose and send an error packet."""
        
        logger.debug(f"In send_error, being asked to send error {errorcode}")
        errpkt = types.Error()
        errpkt.errorcode = errorcode
        
        if self.context.tidport == None:
            logger.debug("Error packet received outside session. Discarding")
        else:
            self.context.sock.sendto(errpkt.encode().buffer,
                                     (self.context.host,
                                      self.context.tidport))

        self.context.last_pkt = errpkt

    def send_oack(self):
        """This method sends an OACK packet with the options from the current
        context."""
        
        logger.debug(f"In send_oack with options {self.context.options}")
        pkt = types.OptionAck()
        pkt.options = self.context.options
        self.context.sock.sendto(pkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))

        self.context.last_pkt = pkt

    def resend_last(self):
        "Resend the last sent packet due to a timeout."
        
        logger.warning(f"Resending packet {self.context.last_pkt} on sessions {self}")
        self.context.metrics.resent_bytes += len(self.context.last_pkt.buffer)
        self.context.metrics.add_dup(self.context.last_pkt)
        sendto_port = self.context.tidport

        if not sendto_port:
            # If the tidport wasn't set, then the remote end hasn't even
            # started talking to us yet. That's not good. Maybe it's not
            # there.
            sendto_port = self.context.port

        self.context.sock.sendto(self.context.last_pkt.encode().buffer,
                                 (self.context.host, sendto_port))

        if self.context.packethook:
            self.context.packethook(self.context.last_pkt)

    def handle_dat(self, pkt):
        """This method handles a DAT packet during a client download, or a
        server upload."""

        logger.info(f"Handling DAT packet - block {pkt.blocknumber}")
        logger.debug(f"Expecting block {self.context.next_block}")

        if pkt.blocknumber == self.context.next_block:
            logger.debug(f"Good, received block {pkt.blocknumber} in sequence")

            self.send_ack()
            self.context.next_block += 1

            logger.debug(f"Writing {len(pkt.data)} bytes to output file")

            self.context.fileobj.write(pkt.data)
            self.context.metrics.bytes += len(pkt.data)
            
            # Check for end-of-file, any less than full data packet.
            if len(pkt.data) < self.context.block_size():
                logger.info("End of file detected")
                return None

        elif pkt.blocknumber < self.context.next_block:
            if pkt.blocknumber == 0:
                logger.warning("There is no block zero!")
                self.send_error(TftpErrors.ILLEGALTFTPOP)
                raise TftpException("There is no block zero!", error_code=TftpErrors.ILLEGALTFTPOP)

            logger.warning(f"Dropping duplicate block {pkt.blocknumber}")
            self.context.metrics.add_dup(pkt)
            logger.debug(f"ACKing block {pkt.blocknumber} again, just in case")
            self.send_ack(pkt.blocknumber)

        else:
            # FIXME: should we be more tolerant and just discard instead?
            msg = f"Whoa! Received future block {pkt.blocknumber} but expected {self.context.next_block}"
            logger.error(msg)
            raise TftpException(msg)

        # Default is to ack
        return ExpectData(self.context)
    
    
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