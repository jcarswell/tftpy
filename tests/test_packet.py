import logging
import unittest

from tftpy.packet import types,factory

class TestTftpyClasses(unittest.TestCase):

    def test_packet_type_ReadRQ(self):
        #log.debug("===> Running testcase testTftpPacketRRQ")
        options = {}
        rrq = types.ReadRQ()
        rrq.filename = 'myfilename'
        rrq.mode = 'octet'
        rrq.options = options
        rrq.encode()
        self.assertIsNotNone(rrq.buffer, "Buffer populated")
        rrq.decode()
        self.assertEqual(rrq.filename, "myfilename", "Filename correct")
        self.assertEqual(rrq.mode, "octet", "Mode correct")
        self.assertEqual(rrq.options, options, "Options correct")
        # repeat test with options
        rrq.options = { 'blksize': '1024' }
        rrq.filename = 'myfilename'
        rrq.mode = 'octet'
        rrq.encode()
        self.assertIsNotNone(rrq.buffer, "Buffer populated")
        rrq.decode()
        self.assertEqual(rrq.filename, "myfilename", "Filename correct")
        self.assertEqual(rrq.mode, "octet", "Mode correct")
        self.assertEqual(rrq.options['blksize'], '1024', "blksize correct")

    def test_packet_type_WriteRQ(self):
        #log.debug("===> Running test case testTftpPacketWRQ")
        options = {}
        wrq = types.WriteRQ()
        wrq.filename = 'myfilename'
        wrq.mode = 'octet'
        wrq.options = options
        wrq.encode()
        self.assertIsNotNone(wrq.buffer, "Buffer populated")
        wrq.decode()
        self.assertEqual(wrq.opcode, 2, "Opcode correct")
        self.assertEqual(wrq.filename, "myfilename", "Filename correct")
        self.assertEqual(wrq.mode, "octet", "Mode correct")
        self.assertEqual(wrq.options, options, "Options correct")
        # repeat test with options
        wrq.options = { 'blksize': '1024' }
        wrq.filename = 'myfilename'
        wrq.mode = 'octet'
        wrq.encode()
        self.assertIsNotNone(wrq.buffer, "Buffer populated")
        wrq.decode()
        self.assertEqual(wrq.opcode, 2, "Opcode correct")
        self.assertEqual(wrq.filename, "myfilename", "Filename correct")
        self.assertEqual(wrq.mode, "octet", "Mode correct")
        self.assertEqual(wrq.options['blksize'], '1024', "Blksize correct")


    def test_packet_type_date(self):
        #log.debug("===> Running testcase testTftpPacketDAT")
        dat = types.Data()
        dat.blocknumber = 5
        data = b"this is some data"
        dat.data = data
        dat.encode()
        self.assertIsNotNone(dat.buffer, "Buffer populated")
        dat.decode()
        self.assertEqual(dat.opcode, 3, "DAT opcode is correct")
        self.assertEqual(dat.blocknumber, 5, "Block number is correct")
        self.assertEqual(dat.data, data, "DAT data is correct")

    def test_packet_type_Ack(self):
        #log.debug("===> Running testcase testTftpPacketACK")
        ack = types.Ack()
        ack.blocknumber = 6
        ack.encode()
        self.assertIsNotNone(ack.buffer, "Buffer populated")
        ack.decode()
        self.assertEqual(ack.opcode, 4, "ACK opcode is correct")
        self.assertEqual(ack.blocknumber, 6, "ACK blocknumber correct")

    def test_packet_type_error(self):
        #log.debug("===> Running testcase testTftpPacketERR")
        err = types.Error()
        err.errorcode = 4
        err.encode()
        self.assertIsNotNone(err.buffer, "Buffer populated")
        err.decode()
        self.assertEqual(err.opcode, 5, "ERR opcode is correct")
        self.assertEqual(err.errorcode, 4, "ERR errorcode is correct")

    def test_packet_type_optionack(self):
        #log.debug("===> Running testcase testTftpPacketOACK")
        oack = types.OptionAck()
        # Test that if we make blksize a number, it comes back a string.
        oack.options = { 'blksize': 2048 }
        oack.encode()
        self.assertIsNotNone(oack.buffer, "Buffer populated")
        oack.decode()
        self.assertEqual(oack.opcode, 6, "OACK opcode is correct")
        self.assertEqual(oack.options['blksize'],
                         '2048',
                         "OACK blksize option is correct")
        # Test string to string
        oack.options = { 'blksize': '4096' }
        oack.encode()
        self.assertIsNotNone(oack.buffer, "Buffer populated")
        oack.decode()
        self.assertEqual(oack.opcode, 6, "OACK opcode is correct")
        self.assertEqual(oack.options['blksize'],
                         '4096',
                         "OACK blksize option is correct")

    def test_packet_factory_(self):
        #log.debug("===> Running testcase testTftpPacketFactory")
        # Make sure that the correct class is created for the correct opcode.
        classes = {
            1: types.ReadRQ,
            2: types.WriteRQ,
            3: types.Data,
            4: types.Ack,
            5: types.Error,
            6: types.OptionACK
            }
        packet_factory = factory.PacketFactory()
        for opcode in classes:
            self.assertTrue(isinstance(packet_factory._PacketFactory__create(opcode),
                            classes[opcode]),
                            f"opcode {opcode} returns the correct class")