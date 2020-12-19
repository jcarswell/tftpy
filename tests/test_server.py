import logging
import unittest
import os
import time
import threading

import tftpy

# FIXME: Tests are not suppported on Windows/Cygwin
#        os.fork()
#        signal - alarms are only supported on Unix

class TestTftpyServer(unittest.TestCase):
    def test_server_download_stop_now(self, output='/tmp/out'):
        root = os.path.dirname(os.path.abspath(__file__))
        server = tftpy.TftpServer(root)
        client = tftpy.TftpClient('localhost',
                                  20001,
                                  {})
        # Fork a server and run the client in this process.
        child_pid = os.fork()
        if child_pid:
            with self.assertRaises(tftpy.TftpException, msg="Server should not exit early"):
                time.sleep(1)
                def delay_hook(pkt):
                    time.sleep(0.005) # 5ms
                client.download('640KBFILE', output, delay_hook)

            os.kill(child_pid, 15)
            os.waitpid(child_pid, 0)

        else:
            import signal
            def handlealarm(signum, frame):
                server.stop(now=True)
            signal.signal(signal.SIGALRM, handlealarm)
            signal.alarm(2)
            self.assertRaises(tftpy.TftpException, server.listen, 'localhost', 20001, msg="Got an unexpected exception")

            # Wait until parent kills us
            while True:
                time.sleep(1)

    def test_server_download_stop(self, output='/tmp/out'):
        root = os.path.dirname(os.path.abspath(__file__))
        server = tftpy.TftpServer(root)
        client = tftpy.TftpClient('localhost',
                                  20001,
                                  {})
        # Fork a server and run the client in this process.
        child_pid = os.fork()
        if child_pid:
            with self.assertRaises(tftpy.TftpException, msg="Server should not exit early"):
                time.sleep(1)
                def delay_hook(pkt):
                    time.sleep(0.005) # 5ms
                client.download('640KBFILE', output, delay_hook)

            os.kill(child_pid, 15)
            os.waitpid(child_pid, 0)

        else:
            import signal
            def handlealarm(signum, frame):
                server.stop(now=False)
            signal.signal(signal.SIGALRM, handlealarm)
            signal.alarm(2)
            self.assertRaises(tftpy.TftpException, server.listen, 'localhost', 20001, msg="Got an unexpected exception")
            # Wait until parent kills us
            while True:
                time.sleep(1)

    def test_server_download_dynamic_port(self, output='/tmp/out'):
        root = os.path.dirname(os.path.abspath(__file__))

        server = tftpy.TftpServer(root)
        server_thread = threading.Thread(target=server.listen,
                                         kwargs={'listenip': 'localhost',
                                                 'listenport': 0})
        server_thread.start()

        try:
            server.is_running.wait()
            client = tftpy.TftpClient('localhost', server.listenport, {})
            time.sleep(1)
            client.download('640KBFILE',
                            output)
        finally:
            server.stop(now=False)
            server_thread.join()