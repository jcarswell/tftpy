# vim: ts=4 sw=4 et ai:
# -*- coding: utf8 -*-
"""This module implements the TFTP Client functionality. Instantiate an
instance of the client, and then use its upload or download method. Logging is
performed via the stanard python logging moduled."""

import logging

from typing import Callable,Union,TypeVar

from tftpy.shared import MIN_BLKSIZE,MAX_BLKSIZE,SOCK_TIMEOUT,tftpassert
from tftpy.context import Upload,Download
from tftpy.exceptions import TftpException

logger = logging.getLogger('tftpy.client')

file_object = TypeVar('File-Like Object')

class TftpClient:
    """This class is an implementation of a tftp client. Once instantiated, a
    download can be initiated via the download() method, or an upload via the
    upload() method."""

    def __init__(self, host:str, port:int =None, options:dict =None, localip:str =None) -> None:
        """Initialize the TFTP client class

        Args:
            host (str): The server for which you are connecting to
            port (int, optional): The server port. Defaults to 69.
            options (dict, optional): The TFTP options. Defaults to None.
            localip (str, optional): The source ip for all requests. Defaults to None.

        Raises:
            TftpException: Invlaid block size request in the options
        """
        
        self.context = None
        self.host = host
        self.iport = port or 69
        self.filename = None
        self.options = options or {}
        self.localip = localip or ""

        if 'blksize' in self.options:
            size = self.options['blksize']
            tftpassert(int == type(size), "blksize must be an int")

            if size < MIN_BLKSIZE or size > MAX_BLKSIZE:
                raise TftpException(f"Invalid blksize: {size}")

    def download(self, filename:str, output:Union[file_object,str],
                 packethook:Callable[['tftpy.packet.types.Data'],None] =None,
                 timeout:int =SOCK_TIMEOUT):
        """This method initiates a tftp download from the configured remote
        host, requesting the filename passed. A packethook may be passed for the
        use of building a UI or to perform additional action on the recieve data.
        
        Args:
            filename (str): The name of the file to request from the server
            output (str): Where to save the file. Can be either a file-name/path,
                            a file-like object or a '-' for stdout
            packethook (Callable, optional): A funtion to recieve a copy of the 
                            Data object recieved. Defaults to None.
            timeout (int, optional): Time out period for the request. Defaults to SOCK_TIMEOUT.
        """
        
        logger.debug("Creating download context with the following params:")
        logger.debug(f" host = {self.host}, port = {self.iport}, filename = {filename}")
        logger.debug(f" options = {self.options}, packethook = {packethook}, timeout = {timeout}")
        self.context = Download(self.host,
                                self.iport,
                                timeout,
                                output,
                                packethook = packethook,
                                options = self.options,
                                filename = filename,
                                localip = self.localip)

        self.context.start()
        # Download happens here
        self.context.end()

        metrics = self.context.metrics

        logger.info("Download complete.")
        if metrics.duration == 0:
            logger.info("Duration too short, rate undetermined")
        else:
            logger.info(f"Downloaded {metrics.bytes:.2f} bytes in {metrics.duration:.2f} seconds")
            logger.info(f"Average rate: {metrics.kbps:.2f} kbps")
        logger.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
        logger.info(f"Received {metrics.dupcount} duplicate packets")

    def upload(self, filename:str, input:Union[file_object,str],
               packethook:Callable[['tftpy.packet.types.Data'],None] =None,
               timeout:int =SOCK_TIMEOUT):
        """This method initiates a tftp upload to the configured remote host,
        uploading the filename passed. A packethook may be passed for the
        use of building a UI or validation when used in conjuction with a
        file like object.
        
        Args:
            filename (str): The filename to send to the server
            input (str): Where to read the file. Can be either a file-name/path,
                            a file-like object or a '-' for stdout
            packethook (Callable, optional): A funtion to recieve a copy of the 
                            Data object sent. Defaults to None.
            timeout (int, optional): Time out period for the request. Defaults to SOCK_TIMEOUT.
        """

        self.context = Upload(self.host,
                              self.iport,
                              timeout,
                              input,
                              packethook = packethook,
                              filename = filename,
                              options = self.options,
                              localip = self.localip)
        
        self.context.start()
        # Upload happens here
        self.context.end()

        metrics = self.context.metrics

        logger.info("Upload complete.")
        if metrics.duration == 0:
            logger.info("Duration too short, rate undetermined")
        else:
            logger.info(f"Uploaded {metrics.bytes} bytes in {metrics.duration:.2f} seconds")
            logger.info(f"Average rate: {metrics.kbps:.2f} kbps")
        logger.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
        logger.info(f"Resent {metrics.dupcount} packets")
