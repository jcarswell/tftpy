import logging

from tftpy.shared import tftpassert,MAX_DUPS

logger = logging.getLogger()

class Metrics:
    """A class representing metrics of the transfer."""
    
    def __init__(self):
        # Bytes transferred
        self.bytes = 0
        # Bytes re-sent
        self.resent_bytes = 0
        # Duplicate packets received
        self.dups = {}
        self.dupcount = 0
        # Times
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        # Rates
        self.bps = 0
        self.kbps = 0
        # Generic errors
        self.errors = 0

    def compute(self):
        # Compute transfer time
        
        self.duration = self.end_time - self.start_time
        
        if self.duration == 0:
            self.duration = 1
        
        logger.debug(f"TftpMetrics.compute: duration is {self.duration}")
        self.bps = (self.bytes * 8.0) / self.duration
        self.kbps = self.bps / 1024.0
        logger.debug(f"TftpMetrics.compute: kbps is {self.kbps}")
        
        for key in self.dups:
            self.dupcount += self.dups[key]

    def add_dup(self, pkt):
        """This method adds a dup for a packet to the metrics."""
        
        logger.debug("Recording a dup of {pkt}")
        s = str(pkt)
        
        if s in self.dups:
            self.dups[s] += 1
        else:
            self.dups[s] = 1
        
        tftpassert(self.dups[s] < MAX_DUPS, "Max duplicates reached")