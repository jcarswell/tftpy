#!/usr/bin/env python
# vim: ts=4 sw=4 et ai:
# -*- coding: utf8 -*-

import sys
import logging
import os
import pathlib

from optparse import OptionParser

import tftpy

log = logging.getLogger('tftpy')
log.setLevel(logging.INFO)

# console handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
default_formatter = logging.Formatter('[%(asctime)s] %(message)s')
handler.setFormatter(default_formatter)
log.addHandler(handler)

def main():
    host = None
    src = None
    dest = None
    mode = None
  
    usage="""usage: %prog [options] source destination
             
             source|destination:
               - for STDIN|STDOUT -
               - host:file - for fetch put
               - path/file - for source/dest file name
               """
    parser = OptionParser(usage=usage)
    parser.add_option('-p',
                      '--port',
                      help='remote port to use (default: 69)',
                      default=69)
    parser.add_option('-b',
                      '--blksize',
                      help='udp packet size to use (default: 512)')
    parser.add_option('-d',
                      '--debug',
                      action='store_true',
                      default=False,
                      help='upgrade logging from info to debug')
    parser.add_option('-q',
                      '--quiet',
                      action='store_true',
                      default=False,
                      help="downgrade logging from info to warning")
    parser.add_option('-t',
                      '--tsize',
                      action='store_true',
                      default=False,
                      help="ask client to send tsize option in download")
    parser.add_option('-l',
                      '--localip',
                      action='store',
                      dest='localip',
                      default=None,
                      help='local IP for client to bind to (ie. interface)')
    options, args = parser.parse_args()
    
    if len(args) != 2:
        parser.error("Incorrect number of arguments")

    for x in range(0,2):
        arg = args[x]
        if arg.split(':'):
            host = arg.split(':')[0]
            if x == 0:
                src = arg.split(':')[1]
                mode = 'get'
            else:
                dest = arg.split(':')[1]
                mode = 'put'
        else:
            if not os.path.exists(os.path.abspath(arg)):
                parser.error(f"{arg} does not exist")
            if x == 0:
                src = os.path.abspath(arg)
            else:
                dest = arg.split(':')[1]
        
    if options.debug and options.quiet:
        sys.stderr.write("The --debug and --quiet options are "
                         "mutually exclusive.\n")
        parser.print_help()
        sys.exit(1)

    class Progress:
        def __init__(self, out):
            self.progress = 0
            self.out = out

        def progresshook(self, pkt):
            from tftpy.packet.types import Data

            if isinstance(pkt, Data):
                self.progress += len(pkt.data)
                self.out(f"Transferred {self.progress} bytes")
        
    if options.debug:
        log.setLevel(logging.DEBUG)
        # increase the verbosity of the formatter
        debug_formatter = logging.Formatter('[%(asctime)s%(msecs)03d] %(levelname)s [%(name)s:%(lineno)s] %(message)s')
        handler.setFormatter(debug_formatter)
    elif options.quiet:
        log.setLevel(logging.WARNING)

    progresshook = Progress(log.info).progresshook

    tftp_options = {}
    if options.blksize:
        tftp_options['blksize'] = int(options.blksize)
    if options.tsize:
        tftp_options['tsize'] = 0

    tclient = tftpy.TftpClient(host,
                               int(options.port),
                               tftp_options,
                               options.localip)
    try:
        if mode == 'get':
            tclient.download(src,
                             dest,
                             progresshook)
        elif mode == 'put':
            tclient.upload(src,
                           dest,
                           progresshook)
    except tftpy.TftpException as err:
        sys.stderr.write("%s\n" % str(err))
        sys.exit(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
