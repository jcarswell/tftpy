import unittest
import os
import time
from multiprocessing import Queue

import tftpy
from tftpy import shared

# FIXME: Tests are not suppported on Windows/Cygwin
#        os.fork()
#        signal - alarms are only supported on Unix

base = os.path.dirname(os.path.abspath(__file__))

class TestTftpyClient(unittest.TestCase):

    def client_upload(self, options, input=None, transmitname=None, server_kwargs=None):
        """Fire up a client and a server and do an upload."""
        
        root = '/tmp'
        filename = '640KBFILE'
        input_path = os.path.join(base, filename)
        
        if not input:
            input = input_path
        if transmitname:
            filename = transmitname
        server_kwargs = server_kwargs or {}
        server = tftpy.TftpServer(root, 'localhost', 20001, **server_kwargs)
        client = tftpy.TftpClient('localhost', 20001, options)

        # Fork a server and run the client in this process.
        child_pid = os.fork()
        if child_pid:
            # parent - let the server start
            try:
                time.sleep(1)
                client.upload(filename, input)
            finally:
                os.kill(child_pid, 15)
                os.waitpid(child_pid, 0)

        else:
            server.listen()
            
        if os.path.exists(os.path.join(root,filename)):
            os.remove(os.path.join(root,filename))

    def client_download(self, options, output='/tmp/out'):
        """Fire up a client and a server and do a download."""
        server = tftpy.TftpServer(base, 'localhost', 20001)
        client = tftpy.TftpClient('localhost', 20001, options)
        
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
            os.remove(output)
        except Exception:
            pass

    class file_like_class:
        def write(self,*args,**kwargs):
            pass
        def read(self,*args,**kwargs):
            return 'test123'
        def close(self):
            pass

    def test_download_no_options(self):
        self.client_download({})

    def test_download_tsize(self):
        self.client_download({'tsize': 64*1024})

    def test_download_fd(self):
        output = open('/tmp/out', 'wb')
        self.client_download({}, output)

    def test_download_blksize(self):
        for blksize in [512, 1024, 2048, 4096]:
            self.client_download({'blksize': blksize})

    def test_download_custom_open(self):
        test_file = self.file_like_class()
        self.client_download({}, test_file)

    def test_upload_no_option(self):
        self.client_upload({})

    def test_upload_fd(self):
        fileobj = open('tests/640KBFILE', 'rb')
        self.client_upload({}, input=fileobj)

    def test_upload_path_with_subdirs(self):
        self.client_upload({}, transmitname='foo/bar/640KBFILE')

    def test_upload_path_with_leading_slash(self):
        self.client_upload({}, transmitname='/640KBFILE')

    def test_upload_blksize(self):
        for blksize in [512, 1024, 2048, 4096]:
            self.client_upload({'blksize': blksize})

    def test_upload_custom_open(self):
        test_file = self.file_like_class()
        self.client_upload({}, test_file)

    def test_upload_custom_open_forbidden(self):

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

    def testClientServerUploadTsize(self):
        self.client_upload({'tsize': 64*1024}, transmitname='/foo/bar/640KBFILE')

    def test_download_delay(self):
        shared.DELAY_BLOCK = 10
        self.client_download({})
        shared.DELAY_BLOCK = 0