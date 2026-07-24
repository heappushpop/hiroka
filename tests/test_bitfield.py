from unittest import TestCase

from hiroka.bitfield import Bitfield


class TestBitfield(TestCase):
    def test_init(self):
        bitfield = Bitfield(b"\x00\x00")
        self.assertEqual(bitfield.data, bytes.fromhex("0000"))
        bitfield = Bitfield(10)
        self.assertEqual(bitfield.data, bytes.fromhex("0000"))

        with self.assertRaises(TypeError):
            Bitfield("0000")

    def test_contains(self):
        bitfield = Bitfield(b"\x00\x00")
        self.assertFalse(3 in bitfield)
        bitfield.add(3)
        self.assertTrue(3 in bitfield)

    def test_add(self):
        bitfield = Bitfield(b"\x00\x00")
        bitfield.add(3)
        self.assertEqual(bitfield.data, bytes.fromhex("1000"))

    def test_remove(self):
        bitfield = Bitfield(b"\x10\x00")
        bitfield.remove(3)
        self.assertEqual(bitfield.data, bytes.fromhex("0000"))
