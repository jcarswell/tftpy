"""This module implements all contexts for state handling during uploads and
downloads, the main interface to which being the TftpContext base class.

The concept is simple. Each context object represents a single upload or
download, and the state object in the context object represents the current
state of that transfer. The state object has a handle() method that expects
the next packet in the transfer, and returns a state object until the transfer
is complete, at which point it returns None. That is, unless there is a fatal
error, in which case a TftpException is returned instead."""

from .server import Server
from .client import Upload,Download