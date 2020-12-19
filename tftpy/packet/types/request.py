from .base import TftpPacketInitial

class ReadRQ(TftpPacketInitial):
    """
    Read Request
          2 bytes    string    1 byte    string    1 byte
          -----------------------------------------------
    RRQ  | 01/02 |  Filename  |   0  |    Mode    |   0  |
          -----------------------------------------------
    """
    def __init__(self):
        super().__init__()
        self.opcode = 1

    def __str__(self):
        s = f"RRQ packet: filename = {self.filename} mode = {self.mode}"
        if self.options:
            s += f"\n    options = {self.options}"
        return s

class WriteRQ(TftpPacketInitial):
    """
    Write Request
          2 bytes    string    1 byte    string    1 byte
          -----------------------------------------------
    WRQ  | 01/02 |  Filename  |   0  |    Mode    |   0  |
          -----------------------------------------------
    """
    
    def __init__(self):
        super().__init__()
        self.opcode = 2

    def __str__(self):
        s = f"WRQ packet: filename = {self.filename} mode = {self.mode}"
        if self.options:
            s += f"\n    options = {self.options}"
        return s