import logging
import unittest
import os
from io import IOBase

from tftpy import context
from tftpy.packet.types import base
from tftpy.packet import types
from tftpy import states
from tftpy.exceptions import TftpException,TftpTimeout
from tftpy.shared import SOCK_TIMEOUT

base = os.path.dirname(os.path.abspath(__file__))

class TestTftpyState(unittest.TestCase):
    
    def test_context_client_upload(self):
        client = context.Upload('localhost',20001,SOCK_TIMEOUT,os.path.join(base,'640KBFILE'),filename='test_context_client_upload')
        self.assertIsInstance(client.fileobj,IOBase)
        self.assertRaises(TftpTimeout,client.start)
        self.assertIsInstance(client.state,states.SentWriteRQ)
        client.end()

    def test_context_client_download(self):
        client = context.Download('localhost',20001,SOCK_TIMEOUT,'test_context_client_download',filename='test_context_client_upload')
        self.assertIsInstance(client.fileobj,IOBase)
        self.assertRaises(TftpTimeout,client.start)
        self.assertIsInstance(client.state,states.SentReadRQ)
        client.end()

        if os.path.exists('../test_context_client_download'):
            os.remove('../test_context_client_download')

    def test_context_server_noopt(self):
        raddress = '127.0.0.2'
        rport = 10000
        timeout = 5
        root = os.path.dirname(os.path.abspath(__file__))
        # Testing without the dyn_func_file set.
        serverstate = context.Server(raddress,rport,timeout,root)

        self.assertIsInstance(serverstate,context.Server)

        rrq = types.ReadRQ()
        rrq.filename = '640KBFILE'
        rrq.mode = 'octet'
        rrq.options = {}

        # Start the download.
        serverstate.start(rrq.encode().buffer)
        # At a 512 byte blocksize, this should be 1280 packets exactly.
        for block in range(1, 1281):
            # Should be in expectack state.
            self.assertIsInstance(serverstate.state,states.ExpectAck)
            ack = types.Ack()
            ack.blocknumber = block % 65536
            serverstate.state = serverstate.state.handle(ack, raddress, rport)

        # The last DAT packet should be empty, indicating a completed
        # transfer.
        ack = types.Ack()
        ack.blocknumber = 1281 % 65536
        finalstate = serverstate.state.handle(ack, raddress, rport)
        self.assertTrue( finalstate is None )

    def test_context_server_insecure_path(self):
        raddress = '127.0.0.2'
        rport = 10000
        timeout = 5
        root = os.path.dirname(os.path.abspath(__file__))
        serverstate = context.Server(raddress,rport,timeout,root)

        self.assertIsInstance(serverstate,context.Server)

        rrq = types.ReadRQ()
        rrq.filename = '../setup.py'
        rrq.mode = 'octet'
        rrq.options = {}

        # Start the download.
        self.assertRaises(TftpException,
                serverstate.start, rrq.encode().buffer)

    def test_context_server_secure_path(self):
        raddress = '127.0.0.2'
        rport = 10000
        timeout = 5
        root = os.path.dirname(os.path.abspath(__file__))
        serverstate = context.Server(raddress,rport,timeout,root)

        self.assertIsInstance(serverstate,context.Server)

        rrq = types.ReadRQ()
        rrq.filename = '640KBFILE'
        rrq.mode = 'octet'
        rrq.options = {}

        # Start the download.
        serverstate.start(rrq.encode().buffer)
        # Should be in expectack state.
        self.assertIsInstance(serverstate.state,states.ExpectAck)
