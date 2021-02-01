import unittest
import os
import time
import logging

from multiprocessing import Queue
from tempfile import TemporaryFile,TemporaryDirectory

import tftpy
from tftpy import shared

log = logging.getLogger('tftpy')
log.setLevel(logging.INFO)

# console handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
default_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(default_formatter)
log.addHandler(handler)

# FIXME: Tests are not suppported on Windows/Cygwin
#        os.fork()
#        signal - alarms are only supported on Unix

base = os.path.dirname(os.path.abspath(__file__))

class TestTftpyClient(unittest.TestCase):

    def client_upload(self, options, src_file=None, transmitname=None, server_kwargs=None):
        """Fire up a client and a server and do an upload."""
             
        root = TemporaryDirectory()

        if not src_file:
            src_file = os.path.join(base, '640KBFILE')

        filename = transmitname or '640KBFILE'
        
        server_kwargs = server_kwargs or {}
        server = tftpy.TftpServer(root.name, 'localhost', 20001, **server_kwargs)
        client = tftpy.TftpClient('localhost', 20001, options)

        # Fork a server and run the client in this process.
        child_pid = os.fork()
        if child_pid:
            # parent - let the server start
            try:
                time.sleep(1)
                client.upload(filename, src_file)
            finally:
                os.kill(child_pid, 15)
                os.waitpid(child_pid, 0)

        else:
            server.listen()
            
        root.cleanup()

    def client_download(self, options, output=None):
        """Fire up a client and a server and do a download."""
        server = tftpy.TftpServer(base, 'localhost', 20001)
        client = tftpy.TftpClient('localhost', 20001, options)
        
        if not output:
            output = TemporaryFile()
        
        # Fork a server and run the client in this process.
        child_pid = os.fork()
        if child_pid:
            # parent - let the server start
            try:
                time.sleep(1)
                client.download('640KBFILE', output)
            finally:
                os.kill(child_pid, 15)
                os.waitpid(child_pid, 0)

        else:
            server.listen()

        try:
            output.close()
        except Exception:
            pass

    class file_like_class:
        def __init__(self,*args,**kwargs):
            self.closed=False
            self.open=True            
        def write(self,*args,**kwargs):
            pass
        def read(self,*args,**kwargs):
            return 'test123'
        def close(self):
            self.closed=True
            pass

    def test_download_no_options(self):
        print('TEST - test_download_no_options')
        self.client_download({})

    def test_download_tsize(self):
        print('TEST - test_download_tsize')
        self.client_download({'tsize': 64*1024})

    def test_download_fd(self):
        print('TEST - test_download_fd')
        output = TemporaryFile()
        self.client_download({}, output)

    def test_download_blksize(self):
        print('TEST - test_download_blksize')
        for blksize in [512, 1024, 2048, 4096]:
            self.client_download({'blksize': blksize})

    def test_download_custom_open(self):
        print('TEST - test_download_custom_open')
        test_file = self.file_like_class()
        self.client_download({}, test_file)

    def test_upload_no_option(self):
        print('TEST - test_upload_no_option')
        self.client_upload({})

    def test_upload_fd(self):
        print('TEST - test_upload_fd')
        fileobj = open('tests/640KBFILE', 'rb')
        self.client_upload({}, src_file=fileobj)

    def test_upload_path_with_subdirs(self):
        print('TEST - test_upload_path_with_subdirs')
        self.client_upload({}, transmitname='foo/bar/640KBFILE')

    def test_upload_path_with_leading_slash(self):
        print('TEST - test_upload_path_with_leading_slash')
        self.client_upload({}, transmitname='/640KBFILE')

    def test_upload_blksize(self):
        print('TEST - test_upload_blksize')
        for blksize in [512, 1024, 2048, 4096]:
            self.client_upload({'blksize': blksize})

    def test_upload_custom_open(self):
        print('TEST - test_upload_custom_open')
        test_file = self.file_like_class()
        self.client_upload({}, test_file)

    def test_upload_custom_open_forbidden(self):
        print('TEST - test_upload_custom_open_forbidden')

        def test_upload_func(self, return_func):
            q = Queue()

            def upload_open(path, context):
                q.put('called')
                return return_func(path)
            self.client_upload(
                {},
                server_kwargs={'upload_open': upload_open})
            self.assertEqual(q.get(True, 1), 'called')

        with self.assertRaisesRegex(tftpy.TftpException, 'Access violation'):
            test_upload_func(self, lambda p: None)

    def test_client_server_upload_tsize(self):
        print('TEST - test_client_server_upload_tsize')
        self.client_upload({'tsize': 64*1024}, transmitname='/foo/bar/640KBFILE')

    def test_download_delay(self):
        print('TEST - test_download_delay')
        shared.DELAY_BLOCK = 10
        self.client_download({})
        shared.DELAY_BLOCK = 0