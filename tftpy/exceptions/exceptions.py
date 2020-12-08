from tftpy.shared import TftpErrors

class TftpException(Exception):
    """This class is the parent class of all exceptions regarding the handling
    of the TFTP protocol."""
    
    def __init__(self,message,*args,error_code=None,**kwargs):
        if isinstance(error_code, int) or isinstance(error_code,TftpErrors):
            self.error_code = error_code

        super().__init__(message, *args, **kwargs)

class TftpOptionsError(TftpException):
    error_code = TftpErrors.ILLEGALTFTPOP

class TftpTimeout(TftpException):
    """This class represents a timeout error waiting for a response from the
    other end."""
    pass


class TftpFileNotFoundError(TftpException):
    """This class represents an error condition where we received a file
    not found error."""
    pass
