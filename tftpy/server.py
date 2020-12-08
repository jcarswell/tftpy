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
from .shared import *
from tftpy.packet.types import TftpPacketRRQ,TftpPacketWRQ,TftpPacketDAT,TftpPacketACK,TftpPacketERR,TftpPacketOACK
from tftpy.packet.factory import TftpPacketFactory
from .TftpContexts import TftpContextServer

log = logging.getLogger('tftpy.TftpServer')

class TftpServer:
    """This class implements a tftp server object. Run the listen() method to
    listen for client requests.

    tftproot is the path to the tftproot directory to serve files from and/or
    write them to.

    dyn_file_func is a callable that takes a requested download
    path that is not present on the file system and must return either a
    file-like object to read from or None if the path should appear as not
    found. This permits the serving of dynamic content.

    upload_open is a callable that is triggered on every upload with the
    requested destination path and server context. It must either return a
    file-like object ready for writing or None if the path is invalid."""

    def __init__(self, tftproot='./tftpboot', dyn_file_func=None, upload_open=None):

        self.listenip = None
        self.listenport = None
        self.sock = None
        self.root = os.path.abspath(tftproot)
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

        for name in 'dyn_file_func', 'upload_open':
            attr = getattr(self, name)
            if attr and not callable(attr):
                raise TftpException(f"{name} supplied, but it is not callable.")
        
        if os.path.exists(self.root):
            log.debug(f"tftproot {self.root} does exist")
            if not os.path.isdir(self.root):
                raise TftpException("The tftproot must be a directory.")
            else:
                if not os.access(self.root, os.R_OK) or not os.access(self.root, os.W_OK):
                    raise TftpException("The tftproot must be readable and writable")
        else:
            raise TftpException("The tftproot does not exist.")

    def listen(self, listenip=None, listenport=DEF_TFTP_PORT, timeout=SOCK_TIMEOUT):
        """Start a server listening on the supplied interface and port. This
        defaults to INADDR_ANY (all interfaces) and UDP port 69. You can also
        supply a different socket timeout value, if desired."""

        listenip = listenip or '0.0.0.0'

        log.info(f"Server requested on ip {listenip}, port {listenport}")
        try:
            # FIXME - sockets should be non-blocking
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((listenip, listenport))
            _, self.listenport = self.sock.getsockname()
        except socket.error as err:
            # Reraise it for now.
            raise socket.error(err)

        self.is_running.set()

        log.info("Starting receive loop...")
        while True:
            log.debug("Configuration:")
            log.debug(f" shutdown_immediately: {self.shutdown_immediately}")
            log.debug(f" shutdown_gracefully: {self.shutdown_gracefully}")
            if self.shutdown_immediately:
                log.warning(f"Shutting down now. Session count: {len(self.sessions)}")
                self.sock.close()
                for key in self.sessions:
                    self.sessions[key].end()
                self.sessions = []
                break

            elif self.shutdown_gracefully:
                if not self.sessions:
                    log.warning("In graceful shutdown mode and all sessions complete.")
                    self.sock.close()
                    break

            # Build the inputlist array of sockets to select() on.
            inputlist = []
            inputlist.append(self.sock)
            for key in self.sessions:
                inputlist.append(self.sessions[key].sock)

            # Block until some socket has input on it.
            log.debug(f"Performing select on this inputlist: {inputlist}")
            try:
                readyinput, readyoutput, readyspecial = select.select(inputlist, [], [], SOCK_TIMEOUT)
            except select.error as err:
                if err[0] == EINTR:
                    # Interrupted system call
                    log.debug("Interrupted syscall, retrying")
                    continue
                else:
                    raise # what are we raising

            deletion_list = []

            # Handle the available data, if any. Maybe we timed-out.
            for readysock in readyinput:
                # Is the traffic on the main server socket? ie. new session?
                if readysock == self.sock:
                    log.debug("Data ready on our main socket")
                    buffer, (raddress, rport) = self.sock.recvfrom(MAX_BLKSIZE)

                    log.debug(f"Read {len(buffer)} bytes")

                    if self.shutdown_gracefully:
                        log.warning("Discarding data on main port, in graceful shutdown mode")
                        continue

                    # Forge a session key based on the client's IP and port,
                    # which should safely work through NAT.
                    key = f"{raddress:rport}"

                    if not key in self.sessions:
                        log.debug(f"Creating new server context for session key = {key}")
                        self.sessions[key] = TftpContextServer(raddress,
                                                               rport,
                                                               timeout,
                                                               self.root,
                                                               self.dyn_file_func,
                                                               self.upload_open)
                        
                        try:
                            self.sessions[key].start(buffer)
                        except TftpException as err:
                            deletion_list.append(key)
                            log.error("Fatal exception thrown from session {key}: {str(err)}")
                    
                    else:
                        log.warning("received traffic on main socket for existing session?")

                    log.info("Currently handling these sessions:")

                    for _,session in self.sessions.items():
                        log.info(f"    {session}")

                else:
                    # Must find the owner of this traffic.
                    for key in self.sessions:
                        if readysock == self.sessions[key].sock:
                            log.debug(f"Matched input to session key {key}")
                            try:
                                self.sessions[key].cycle()
                                if self.sessions[key].state == None:
                                    log.info("Successful transfer.")
                                    deletion_list.append(key)

                            except TftpException as err:
                                deletion_list.append(key)
                                log.error(f"Fatal exception thrown from session {key}: {str(err)}")

                            # Break out of for loop since we found the correct
                            # session.
                            break
                    else:
                        log.error("Can't find the owner for this packet. Discarding.")

            log.debug("Looping on all sessions to check for timeouts")
            now = time.time()

            for key in self.sessions:
                try:
                    self.sessions[key].check_timeout(now)
                except TftpTimeout as err:
                    log.error(str(err))
                    self.sessions[key].retry_count += 1

                    if self.sessions[key].retry_count >= TIMEOUT_RETRIES:
                        log.debug(f"hit max retries on {self.sessions[key]}, giving up")
                        deletion_list.append(key)
                    else:
                        log.debug(f"resending on session {self.sessions[key]}")
                        self.sessions[key].state.resendLast()

            log.debug("Iterating deletion list.")
            for key in deletion_list:
                log.info('')
                log.info("Session {key} complete")
                if key in self.sessions:
                    log.debug("Gathering up metrics from session before deleting")
                    self.sessions[key].end()
                    metrics = self.sessions[key].metrics
                    if metrics.duration == 0:
                        log.info("Duration too short, rate undetermined")
                    else:
                        log.info(f"Transferred {metrics.bytes} bytes in {metrics.duration:.2f} seconds")
                        log.info(f"Average rate: {metrics.kbps:.2f} kbps")
                    log.info(f"{metrics.resent_bytes:.2f} bytes in resent data")
                    log.info(f"{metrics.dupcount} duplicate packets")
                    log.debug(f"Deleting session {key}")
                    del self.sessions[key]
                    log.debug(f"Session list is now {self.sessions}")
                else:
                    log.warning(f"Strange, session {key} is not on the deletion list")

        self.is_running.clear()

        log.debug("server returning from while loop")
        self.shutdown_gracefully = self.shutdown_immediately = False

    def stop(self, now=False):
        """Stop the server gracefully. Do not take any new transfers,
        but complete the existing ones. If force is True, drop everything
        and stop. Note, immediately will not interrupt the select loop, it
        will happen when the server returns on ready data, or a timeout.
        ie. SOCK_TIMEOUT"""

        if now:
            self.shutdown_immediately = True
        else:
            self.shutdown_gracefully = True
