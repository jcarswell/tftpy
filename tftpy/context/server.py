import logging
import time

from .base import Context
from tftpy.states import Start

logger = logging.getLogger()

class Server(Context):
    """The context for the server."""
    
    def __init__(self, host, port, timeout, root, dyn_file_func=None, upload_open=None, **kwargs):
        
        super().__init__(self, host, port, timeout, **kwargs)
        
        # At this point we have no idea if this is a download or an upload. We
        # need to let the start state determine that.
        self.state = Start(self)

        self.root = root
        self.dyn_file_func = dyn_file_func
        self.upload_open = upload_open

    def start(self, buffer=None):
        """Start the state cycle. Note that the server context receives an
        initial packet in its start method. Also note that the server does not
        loop on cycle(), as it expects the TftpServer object to manage
        that."""
        
        logger.debug("In tftpy.contex.server.start")
        self.metrics.start_time = self.last_update = time.time()

        pkt = self.factory.parse(buffer)
        logger.debug(f"tftpy.contex.server.start() - factory returned a {pkt}")

        # Call handle once with the initial packet. This should put us into
        # the download or the upload state.
        self.state = self.state.handle(pkt,self.host,self.port)

    def end(self, *args, **kwargs):
        """Finish up the context."""
        
        super().end(*args, **kwargs)

        self.metrics.end_time = time.time()
        logger.debug(f"Set metrics.end_time to {self.metrics.end_time}")
        self.metrics.compute()
