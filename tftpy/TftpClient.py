# vim: ts=4 sw=4 et ai:
# -*- coding: utf8 -*-
"""This module implements the TFTP Client functionality. Instantiate an
instance of the client, and then use its upload or download method. Logging is
performed via a standard logging object set in TftpShared."""


import types
import logging
from .TftpShared import *
from .TftpPacketTypes import *
from .TftpContexts import TftpContextClientDownload, TftpContextClientUpload

log = logging.getLogger('tftpy.TftpClient')

class TftpClient(TftpSession):
    """This class is an implementation of a tftp client. Once instantiated, a
    download can be initiated via the download() method, or an upload via the
    upload() method."""

    def __init__(self, host, port=69, options={}, localip = ""):
        TftpSession.__init__(self)
        self.context = None
        self.host = host
        self.iport = port
        self.filename = None
        self.options = options
        self.localip = localip

        if 'blksize' in self.options:
            size = self.options['blksize']
            tftpassert(int == type(size), "blksize must be an int")

            if size < MIN_BLKSIZE or size > MAX_BLKSIZE:
                raise TftpException(f"Invalid blksize: {size}")

    def download(self, filename, output, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp download from the configured remote
        host, requesting the filename passed. It writes the file to output,
        which can be a file-like object or a path to a local file. If a
        packethook is provided, it must be a function that takes a single
        parameter, which will be a copy of each DAT packet received in the
        form of a TftpPacketDAT object. The timeout parameter may be used to
        override the default SOCK_TIMEOUT setting, which is the amount of time
        that the client will wait for a receive packet to arrive.

        Note: If output is a hyphen, stdout is used."""

        # We're downloading.
        log.debug("Creating download context with the following params:")
        log.debug(f" host = {self.host}, port = {self.port}, filename = {filename}")
        log.debug(f" options = {self.options}, packethook = {packethook}, timeout = {timeout}")
        self.context = TftpContextClientDownload(self.host,
                                                 self.iport,
                                                 filename,
                                                 output,
                                                 self.options,
                                                 packethook,
                                                 timeout,
                                                 localip = self.localip)

        self.context.start()
        # Download happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Download complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info(f"Downloaded {metrics.bytes:.2f} bytes in {metrics.duration:.2f} seconds")
            log.info(f"Average rate: {metrics.kbps:.2f} kbps")
        log.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
        log.info(f"Received {metrics.dupcount} duplicate packets")

    def upload(self, filename, input, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp upload to the configured remote host,
        uploading the filename passed. It reads the file from input, which
        can be a file-like object or a path to a local file. If a packethook
        is provided, it must be a function that takes a single parameter,
        which will be a copy of each DAT packet sent in the form of a
        TftpPacketDAT object. The timeout parameter may be used to override
        the default SOCK_TIMEOUT setting, which is the amount of time that
        the client will wait for a DAT packet to be ACKd by the server.

        Note: If input is a hyphen, stdin is used."""

        self.context = TftpContextClientUpload(self.host,
                                               self.iport,
                                               filename,
                                               input,
                                               self.options,
                                               packethook,
                                               timeout,
                                               localip = self.localip)
        
        self.context.start()
        # Upload happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Upload complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info(f"Uploaded {metrics.bytes} bytes in {metrics.duration:.2f} seconds")
            log.info(f"Average rate: {metrics.kbps:.2f} kbps")
        log.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
        log.info(f"Resent {metrics.dupcount} packets")
