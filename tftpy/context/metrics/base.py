import logging

from tftpy.shared import tftpassert,MAX_DUPS

logger = logging.getLogger('tftpy.context.metrics.base')

class Metrics:
    """A class representing metrics of the transfer."""
    
    def __init__(self) -> None:
        # Bytes transferred
        self.bytes = 0
        # Bytes re-sent
        self.resent_bytes = 0
        # Duplicate packets received
        self.dupcount = 0
        self.dups = {}
        # Times
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        # Rates
        self.bps = 0
        self.kbps = 0
        # Generic errors
        self.errors = 0
        self.__out_of_order = []

    def compute(self) -> None:
        """Compute transfer time
           
           Sets:
               duration: Time taken for the transfer
               bps: Speed in bytes per seconds
               kbps: Speed in kbps
               ooocount: number of out of order packets received
        """
        
        self.duration = self.end_time - self.start_time
        
        if self.duration == 0:
            self.duration = 1
        
        logger.debug(f"TftpMetrics.compute: duration is {self.duration}")
        self.bps = (self.bytes * 8.0) / self.duration
        self.kbps = self.bps / 1024.0
        logger.debug(f"TftpMetrics.compute: kbps is {self.kbps}")
        
        self.ooocount = len(self.__out_of_order)

    def add_dup(self, pkt: 'types.Data') -> None:
        """This method adds a dup for a packet to the metrics.

        Args:
            pkt (types.Data): Duplicate data packet
            
        Raises:
            AssertionError: Max Duplicate packets received
        """
        
        logger.debug("Recording a dup of {pkt}")
        s = str(pkt)
        
        self.dupcount += 1
        
        if s in self.dups:
            self.dups[s] += 1
        else:
            self.dups[s] = 1
        
        tftpassert(self.dupcount < MAX_DUPS, "Max duplicates reached")

    @property
    def duplicate(self) -> None:
        return self.dups

    @duplicate.setter
    def duplicate(self, pkt: 'types.Data') -> None:
        self.add_dup(pkt)

    @property
    def out_of_order(self) -> list:
        return self.__out_of_order

    @out_of_order.setter
    def out_of_order(self, pkt: 'packet.types') -> None:
        logger.debug("Recording a out of order packet")
        s = str(pkt)

        if s in self.dups:
            logger.debug("{pkt} is a duplicate packet")
            self.duplicate = pkt

        self.__out_of_order.append(s)