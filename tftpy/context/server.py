import logging
import time

from io import IOBase
from typing import Callable
from typing import Any

from .base import Context
from tftpy.states import Start

logger = logging.getLogger('tftpy.context.server')

class Server(Context):
    """The context for the server."""
    
    def __init__(self, host: str, port: int, timeout: int, root: str, 
                 dyn_file_func: Callable[[str,str,int],Any] = None,
                 upload_open: Callable[[str,Context],IOBase]=None,
                 **kwargs) -> None:
        """Prepare the server context to process data from a client

        Args:
            host (str): The requesting clients IP
            port (int): The requesting clients Port
            timeout (int): stocket timeout
            root (str): server root path
            dyn_file_func (Callable[[str,str,int],Any], optional): A dynamic fucntion function to read from
            upload_open (Callable[[str,Context],IOBase], optional): A dynamic function to write data to
        """
        
        super().__init__(host, port, timeout, **kwargs)
        
        # At this point we have no idea if this is a download or an upload. We
        # need to let the start state determine that.
        self.state = Start(self)

        self.root = root
        self.dyn_file_func = dyn_file_func
        self.upload_open = upload_open

    def start(self, buffer: bytes = None) -> None:
        """Start the state cycle. Note that the server context receives an
        initial packet in its start method. Also note that the server does not
        loop on cycle(), as it expects the TftpServer object to manage
        that.

        Args:
            buffer (bytes, optional): Buffer Data receivied from the client.
                Should be either a read or write request
        """
        
        logger.debug("In tftpy.contex.server.start")
        self.metrics.start_time = self.last_update = time.time()

        pkt = self.factory.parse(buffer)
        logger.debug(f"tftpy.contex.server.start() - factory returned a {pkt}")

        # Call handle once with the initial packet. This should put us into
        # the download or the upload state.
        self.state = self.state.handle(pkt,self.host,self.port)

    def end(self, *args, **kwargs) -> None:
        """Finish up the context."""
        
        super().end(*args, **kwargs)

        self.metrics.end_time = time.time()
        logger.debug(f"Set metrics.end_time to {self.metrics.end_time}")
        self.metrics.compute()
