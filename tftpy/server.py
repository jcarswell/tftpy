# vim: ts=4 sw=4 et ai:
# -*- coding: utf8 -*-
"""This module implements the TFTP Server functionality. Instantiate an
instance of the server, and then run the listen() method to listen for client
requests. Logging is performed via a standard logging object set in
TftpShared."""

import socket, os, time
import select
import threading
import logging

from errno import EINTR
from typing import Callable

from tftpy.shared import TftpErrors,SOCK_TIMEOUT,MAX_BLKSIZE,TIMEOUT_RETRIES
from tftpy.packet import types
from tftpy.context import Server
from tftpy.exceptions import TftpException,TftpTimeout

logger = logging.getLogger('tftpy.server')

class TftpServer:
    """This class implements a tftp server object. Run the listen() method to
    listen for client requests.

    dyn_file_func: Is a callable that takes a requested download
        path that is not present on the file system and must return either a
        file-like object to read from or None if the path should appear as not
        found. This permits the serving of dynamic content.
        
        This function should take three arguments:
            filename (str): The name of the file
            raddress (str, kwarg): The clinets IP
            rport (int, kwarg): Rhe clients port
        
        This function should return a file-like object or None
    

    upload_open: Is a callable that is triggered on every upload with the
        requested destination path and server context. It must either return a
        file-like object ready for writing or None if the path is invalid.
        
        This function should take two arguments:
            path (str): The requested file path
            context (tftp.Context.Server, kwarg): the current server context
        
        This function should return a file-like object or None
    """

    def __init__(self, tftproot:str =None, listenip:str =None, listenport:int =None, 
                 dyn_file_func:Callable[[str,str,int],'file-like object'] =None, 
                 upload_open:Callable[[str,str,int],'file-like object'] =None) -> None:
        """Initialize the calls 

        Args:
            tftproot (str, optional): Server root. Defaults to ./tftpboot
            listenip (str, optional): Listening address. Defaults to 127.0.0.1.
            listenport (int, optional): Listening port. Defaults to 69.
            dyn_file_func (file like save function, optional): If specified this 
                function will be used instead of server root. Defaults to None.
            upload_open (file like read function, optional): If specified 
                the server will use this path for file reads instead of server root. Defaults to None.

        Raises:
            TftpException: dynamic file function(s) is not callable
            TftpException: tftp root is not readable
            FileNotFoundError: the tftp root specified doesn't exist
        """

        self.listenip = listenip or '127.0.0.1'
        self.listenport = listenport or 69
        self.sock = None
        self.root = os.path.abspath(tftproot or './tftpboot')
        self.dyn_file_func = dyn_file_func
        self.upload_open = upload_open
        
        # A dict of sessions, where each session is keyed by a string like
        # ip:tid for the remote end.
        self.sessions = {}
        
        # A threading event to help threads synchronize with the server
        # is_running state.
        self.is_running = threading.Event()

        self.shutdown_gracefully = False
        self.shutdown_immediately = False

        for name in ['dyn_file_func','upload_open']:
            attr = getattr(self, name)
            if attr and not callable(attr):
                raise TftpException(f"{name} supplied, but it is not callable.")
        
        if os.path.isdir(self.root):
            logger.debug(f"tftproot {self.root} exists")
            if not os.access(self.root, os.R_OK) or not os.access(self.root, os.W_OK):
                raise TftpException("The tftproot must be readable and writable")
        else:
            raise FileNotFoundError("The tftproot does not exist or isn't a directory")

    def listen(self, timeout:int =None) -> None:
        """Start a server listening on the supplied interface and port.

        Args:
            timeout (int, optional): The default server timeout. Defaults to 5 seconds

        Raises:
            socket.error: Failed to bind to a the IP Address and port
        """

        self.timeout = timeout or SOCK_TIMEOUT
    
        logger.info(f"Server requested on ip {self.listenip}, port {self.listenport}")
        try:
            # FIXME - sockets should be non-blocking - Need to add threading model
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.listenip, self.listenport))
            _, self.listenport = self.sock.getsockname()
        except socket.error as err:
            # Reraise it for now.
            raise socket.error(err)

        self.is_running.set()
        self.running()
        self.is_running.clear()

        logger.debug("server returning from while loop")
        self.shutdown_gracefully = self.shutdown_immediately = False

    def running(self) -> None:
        """Main Server loop to handle new connections"""
        
        logger.debug("Starting receive loop...")
        while True:
            logger.debug("Configuration:")
            logger.debug(f" shutdown_immediately: {self.shutdown_immediately}")
            logger.debug(f" shutdown_gracefully: {self.shutdown_gracefully}")
            
            deletion_list = []
            
            if self.shutdown_immediately:
                logger.warning(f"Shutting down now. Session count: {len(self.sessions)}")
                self.sock.close()
                for key in self.sessions:
                    self.sessions[key].end()
                self.sessions = []
                break

            elif self.shutdown_gracefully and not self.sessions:
                logger.warning("In graceful shutdown mode and all sessions complete.")
                self.sock.close()
                break

            # Build the inputlist array of sockets to select() on.
            inputlist = []
            inputlist.append(self.sock)
            for key in self.sessions:
                inputlist.append(self.sessions[key].sock)

            # Block until some socket has input on it.
            logger.debug(f"Performing select on this inputlist: {inputlist}")
            try:
                readyinput, _, _ = select.select(inputlist, [], [], self.timeout)
            except OSError as err:
                if err.args[0] == EINTR:
                    # Interrupted system call
                    logger.debug("Interrupted syscall, retrying")
                    continue
                else:
                    raise # what are we raising
            
            # Handle the available data, if any. Maybe we timed-out.
            for readysock in readyinput:
                # Is the traffic on the main server socket? ie. new session?
                deletion_list = self.process_data(readysock)

            logger.debug("Looping on all sessions to check for timeouts")
            now = time.time()

            for key in self.sessions:
                try:
                    self.sessions[key].check_timeout(now)
                except TftpTimeout as err:
                    logger.error(str(err))
                    self.sessions[key].retry_count += 1

                    if self.sessions[key].retry_count >= TIMEOUT_RETRIES:
                        logger.debug(f"hit max retries on {self.sessions[key]}, giving up")
                        deletion_list.append(key)
                    else:
                        logger.debug(f"resending on session {self.sessions[key]}")
                        self.sessions[key].state.resend_last()

            logger.debug("Iterating deletion list.")
            for key in deletion_list:
                logger.info(f"Session {key} complete")
                if key in self.sessions:
                    logger.debug("Gathering up metrics from session before deleting")
                    self.sessions[key].end()
                    metrics = self.sessions[key].metrics
                    
                    if metrics.duration == 0:
                        logger.info("Duration too short, rate undetermined")
                    else:
                        logger.info(f"Transferred {metrics.bytes} bytes in {metrics.duration:.2f} seconds")
                        logger.info(f"Average rate: {metrics.kbps:.2f} kbps")
                    
                    logger.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
                    logger.info(f"{metrics.dupcount} duplicate packets")
                    logger.debug(f"Deleting session {key}")
                    
                    del self.sessions[key]
                    logger.debug(f"Session list is now {self.sessions}")
                else:
                    logger.warning(f"Strange, session {key} is not on the deletion list")


    def process_data(self,readysock:socket.socket) -> list:
        """Handle the data sent to the server per session

        Args:
            readysock (socket.socket): current socket session

        Returns:
            [list]: deleted sessions
        """
        
        deletion_list = []
        
        if readysock == self.sock:
            logger.debug("Data ready on our main socket")
            buffer, (raddress, rport) = self.sock.recvfrom(MAX_BLKSIZE)

            logger.debug(f"Read {len(buffer)} bytes")

            if self.shutdown_gracefully:
                logger.warning("Discarding data on main port, in graceful shutdown mode")

            # Forge a session key based on the client's IP and port,
            # which should safely work through NAT.
            key = f"{raddress}:{rport}"

            if not key in self.sessions:
                logger.debug(f"Creating new server context for session key = {key}")
                self.sessions[key] = Server(raddress,
                                            rport,
                                            self.timeout,
                                            self.root,
                                            self.dyn_file_func,
                                            self.upload_open)
                
                try:
                    self.sessions[key].start(buffer)
                except TftpException as err:
                    deletion_list.append(key)
                    logger.error(f"Fatal exception thrown from session {key}: {str(err)}")
            
            else:
                logger.warning("received traffic on main socket for existing session?")

            logger.info("Currently handling these sessions:")

            for _,session in self.sessions.items():
                logger.info(f"    {session}")

        else:
            # Must find the owner of this traffic.
            for key in self.sessions:
                if readysock == self.sessions[key].sock:
                    logger.debug(f"Matched input to session key {key}")
                    try:
                        self.sessions[key].cycle()
                        if self.sessions[key].state == None:
                            logger.info("Successful transfer.")
                            deletion_list.append(key)

                    except TftpException as err:
                        deletion_list.append(key)
                        logger.error(f"Fatal exception thrown from session {key}: {str(err)}")

                    # Break out of for loop since we found the correct
                    # session.
                    break
            else:
                logger.error("Can't find the owner for this packet. Discarding.")
                
        return deletion_list

    def stop(self, now:bool =False) -> None:
        """Stop the server gracefully. Do not take any new transfers,
        but complete the existing ones. If force is True, drop everything
        and stop. Note, immediately will not interrupt the select loop, it
        will happen when the server returns on ready data, or a timeout.
        ie. SOCK_TIMEOUT
        """

        if now:
            self.shutdown_immediately = True
        else:
            self.shutdown_gracefully = True
