import logging
import os
import sys
import time

from .base import Client
from tftpy.shared import TIMEOUT_RETRIES
from tftpy.packet import types
from tftpy.exceptions import TftpException,TftpTimeout,TftpFileNotFoundError
from tftpy.states import SentReadRQ,SentWriteRQ

logger = logging.getLogger('tftpy.context.client')

class Upload(Client):
    """The upload context for the client during an upload.
    Note: If input is a hyphen, then we will use stdin."""
    
    def __init__(self, host, port, timeout, input, **kwargs):
                     
        super().__init__(host, port, timeout, **kwargs)
        
        # If the input object has a read() function, assume it is file-like.
        if hasattr(input, 'read'):
            self.fileobj = input
        elif input == '-':
            self.fileobj = sys.stdin
        else:
            self.fileobj = open(input, "rb")

        logger.debug("tftpy.context.client.upload.__init__()")
        logger.debug(f" file_to_transfer = {self.file_to_transfer}, options = {self.options}")

    def start(self):
        logger.info(f"Sending tftp upload request to {self.host}")
        logger.info(f"    filename -> {self.file_to_transfer}")
        logger.info(f"    options -> {self.options}")

        self.metrics.start_time = time.time()
        logger.debug(f"Set metrics.start_time to {self.metrics.start_time}")

        pkt = types.WriteRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = self.mode
        pkt.options = self.options

        self.send(pkt)
        self.state = SentWriteRQ(self)

        while self.state:
            try:
                logger.debug(f"State is {self.state}")
                self.cycle()
            except TftpTimeout as err:
                logger.error(str(err))
                self.retry_count += 1
                
                if self.retry_count >= TIMEOUT_RETRIES:
                    logger.debug("hit max retries, giving up")
                    raise
                else:
                    logger.warning("resending last packet")
                    self.state.resend_last()

    def end(self, *args):
        """Finish up the context."""
        
        super().end(*args)

        self.metrics.end_time = time.time()
        logger.debug(f"Set metrics.end_time to {self.metrics.end_time}")
        self.metrics.compute()
        

class Download(Client):
    """The download context for the client during a download.
    Note: If output is a hyphen, then the output will be sent to stdout."""
    
    def __init__(self, host, port, timeout, output, **kwargs):
        super().__init__(host, port, timeout, **kwargs)
        
        self.filelike_fileobj = False

        # If the output object has a write() function, assume it is file-like.
        if hasattr(output, 'write'):
            self.fileobj = output
            self.filelike_fileobj = True
        # If the output filename is -, then use stdout
        elif output == '-':
            self.fileobj = sys.stdout
            self.filelike_fileobj = True
        else:
            try:
                self.fileobj = open(output, "wb")
            except OSError as err:
                raise TftpException("Could not open output file", err)

        logger.debug("tftpy.context.client.Download.__init__()")
        logger.debug(f" file_to_transfer = {self.file_to_transfer}, options = {self.options}")

    def start(self):
        """Initiate the download."""
        
        logger.info(f"Sending tftp download request to {self.host}")
        logger.info(f"    filename -> {self.file_to_transfer}")
        logger.info(f"    options -> {self.options}")

        self.metrics.start_time = time.time()
        logger.debug(f"Set metrics.start_time to {self.metrics.start_time}")

        pkt = types.ReadRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = self.mode
        pkt.options = self.options

        self.send(pkt)
        self.state = SentReadRQ(self)

        while self.state:
            try:
                logger.debug(f"State is {self.state}")
                self.cycle()
            
            except TftpTimeout as err:
                logger.error(str(err))
                self.retry_count += 1
                if self.retry_count >= TIMEOUT_RETRIES:
                    logger.debug("hit max retries, giving up")
                    raise TftpTimeout("Max retries reached")
                else:
                    logger.warning("resending last packet")
                    self.state.resend_last()
                    
            except TftpFileNotFoundError as err:
                # If we received file not found, then we should not save the open
                # output file or we'll be left with a size zero file. Delete it,
                # if it exists.
                
                logger.error("Received File not found error")
                if self.fileobj is not None and not self.filelike_fileobj and os.path.exists(self.fileobj.name):
                    logger.debug(f"unlinking output file of {self.fileobj.name}")
                    os.unlink(self.fileobj.name)

                raise TftpFileNotFoundError(err)

    def end(self):
        """Finish up the context."""
        
        super().end(not self.filelike_fileobj)
        self.metrics.end_time = time.time()
        logger.debug(f"Set metrics.end_time to {self.metrics.end_time}")
        self.metrics.compute()