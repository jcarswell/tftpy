# vim: ts=4 sw=4 et ai:
# -*- coding: utf8 -*-

"""This module holds all objects shared by all other modules in tftpy."""

MIN_BLKSIZE = 8
DEF_BLKSIZE = 512
MAX_BLKSIZE = 65536
SOCK_TIMEOUT = 5
MAX_DUPS = 20
TIMEOUT_RETRIES = 5
DEF_TFTP_PORT = 69

# A hook for deliberately introducing delay in testing.
DELAY_BLOCK = 0

def tftpassert(condition, msg):
    """This function is a simple utility that will check the condition
    passed for a false state. If it finds one, it throws a TftpException
    with the message passed. This just makes the code throughout cleaner
    by refactoring."""
    if not condition:
        raise AssertionError(msg)

class TftpErrors:
    """This class is a convenience for defining the common tftp error codes,
    and making them more readable in the code."""
    NOTDEFINED = 0
    FILENOTFOUND = 1
    ACCESSVIOLATION = 2
    DISKFULL = 3
    ILLEGALTFTPOP = 4
    UNKNOWNTID = 5
    FILEALREADYEXISTS = 6
    NOSUCHUSER = 7
    FAILEDNEGOTIATION = 8
