import logging
import socket
import time

from tftpy.shared import MAX_BLKSIZE
from tftpy.exceptions import TftpException,TftpTimeout
from tftpy.packet.factory import PacketFactory
from .metrics import Metrics

logger = logging.getLogger('tftpy.context.base')

class Context:
    """The base class of the contexts."""

    def __init__(self, host, port, timeout, **kwargs):
        """Constructor for the base context, setting shared instance
        variables.

        Args:
            host (str): Host address or name
            port (int): tftp port
            timeout (int): timeout period
            localip (str, optional): Listen Address. Defaults to None.
        
        kwargs:
            filename (str): Filename to send or receive
            fileobj (class): File-like object supporting .read or .write
            options (dict): Options for the session
            packethook (func): function to receive a copy of the Data Packet
            mode (str): Server mode currently only supports 'octet'
        """
        
        self.file_to_transfer = kwargs.get('filename', None)
        self.fileobj = kwargs.get('fileobj', None)
        self.options = kwargs.get('options', {})
        self.packethook = kwargs.get('packethook', None)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.mode = kwargs.get('mode', "octet")
        localip = kwargs.get('localip', None)
        
        if localip is not None:
            self.sock.bind((localip, 0))
        
        self.sock.settimeout(timeout)
        self.timeout = timeout
        self.state = None
        self.next_block = 0
        self.factory = PacketFactory()
        # Note, setting the host will also set self.address, as it's a property.
        self.host = host
        
        if isinstance(port, int):
            port = int(port)
        if 0 < port < 65535:
            self.port = port
        elif port == 0:
            # if the port is 0 set to the default TFTP port (69)
            self.port = 69
        else:
            raise ValueError("port must be between 1 and 65534")
        
        # The port associated with the TID
        self.tidport = None
        # Metrics
        self.metrics = Metrics()
        # Fluag when the transfer is pending completion.
        self.pending_complete = False
        # Time when this context last received any traffic.
        self.last_update = 0
        # The last packet we sent, if applicable, to make resending easy.
        self.last_pkt = None
        # Count the number of retry attempts.
        self.retry_count = 0

    @property
    def block_size(self):
        """Fetch the current blocksize for this session."""
        
        return int(self.options.get('blksize', 512))

    def __del__(self):
        """Simple destructor to try to call housekeeping in the end method if
        not called explicitely. Leaking file descriptors is not a good
        thing."""
        
        self.end()

    def check_timeout(self, now):
        """Compare current time with last_update time, and raise an exception
        if we're over the timeout time.

        Args:
            now (time.time): time to check against

        Raises:
            TftpTimeout: Raised if the period of time is greater than the timeout period set
        """
        
        logger.debug(f"checking for timeout on session {self}")
        if now - self.last_update > self.timeout:
            raise TftpTimeout("Timeout waiting for traffic")

    def start(self):
        raise NotImplementedError

    def end(self, close_fileobj=True):
        """Perform session cleanup, since the end method should always be
        called explicitely by the calling code, this works better than the
        destructor.
        
        Set close_fileobj to False so fileobj can be returned open.

        Args:
            close_fileobj (bool, optional): keep the file object open or close it. Defaults to True.
        """
        
        logger.debug("in TftpContext.end - closing socket")
        self.sock.close()
        if close_fileobj and self.fileobj is not None and not self.fileobj.closed:
            logger.debug("self.fileobj is open - closing")
            self.fileobj.close()

    @property
    def host(self):
        "Get the host address or name"
        
        return self.__host

    @host.setter
    def host(self, host):
        """Sets the address property as a result of the host that is set."""
        
        self.__host = host
        self.address = socket.gethostbyname(host)

    @property
    def next_block(self):
        """Gets the next_block"""
        return self.__eblock

    @next_block.setter
    def next_block(self, block):
        """Sets the next block or roles over if greater than 2^16 blocks"""
        
        if block >= 2 ** 16:
            logger.debug("Block number rollover to 0 again")
            block = 0
        self.__eblock = block

    def __str__(self):
        return f"{self.host}:{self.port} {self.state}"
    
    def cycle(self):
        """Here we wait for a response from the server after sending it
        something, and dispatch appropriate action to that response.

        Raises:
            TftpTimeout: if the timeout threashold has been exceeded
        """
        
        try:
            (buffer, (raddress, rport)) = self.sock.recvfrom(MAX_BLKSIZE)
        except socket.timeout:
            logger.warning("Timeout waiting for traffic, retrying...")
            raise TftpTimeout("Timed-out waiting for traffic")

        # Ok, we've received a packet. Log it.
        logger.debug(f"Received {len(buffer)} bytes from {raddress}:{rport}")
        
        # And update our last updated time.
        self.last_update = time.time()

        # Decode it.
        recvpkt = self.factory.parse(buffer)

        # Check for known "connection".
        if raddress != self.address:
            logger.warning(f"Received traffic from {raddress}, expected host {self.host}. Discarding")

        if self.tidport and self.tidport != rport:
            logger.warning(f"Received traffic from {raddress}:{rport} but we're connected to {self.host}:{self.tidport}. Discarding.")

        # If there is a packethook defined, call it. We unconditionally
        # pass all packets, it's up to the client to screen out different
        # kinds of packets. This way, the client is privy to things like
        # negotiated options.
        if self.packethook:
            self.packethook(recvpkt)

        # And handle it, possibly changing state.
        self.state = self.state.handle(recvpkt, raddress, rport)
        # If we didn't throw any exceptions here, reset the retry_count to
        # zero.
        self.retry_count = 0
        
    def send(self,pkt):
        """Handles all the packet sending operations.

        Args:
            pkt (class): tftpy.packet.types class
        """
        
        _ = pkt.encode()
        
        logger.debug("send data")
        logger.debug(f"  sendto buffer: {type(pkt.buffer)}{pkt.buffer}")
        logger.debug(f"  sendto host: {type(self.host)}{self.host}")
        logger.debug(f"  sendto port: {type(self.port)}{self.port}")
        
        self.sock.sendto(pkt.buffer, (self.host, self.port))
        
        if self.next_block == 0:
            self.next_block = 1
        else:
            self.next_block += 1
            
        self.last_pkt = pkt
