from unittest import TestCase

from hiroka.bencode import DecodeError, EncodeError, decode, encode


class TestBencode(TestCase):
    def test_decode(self):
        self.assertEqual(decode(b"0:"), b"")
        self.assertEqual(decode(b"10:BitTorrent"), b"BitTorrent")

        self.assertEqual(decode(b"i-10e"), -10)
        self.assertEqual(decode(b"i0e"), 0)
        self.assertEqual(decode(b"i3e"), 3)

        with self.assertRaisesRegex(DecodeError, "Invalid integer: negative zero"):
            decode(b"i-0e")

        with self.assertRaisesRegex(DecodeError, "Invalid integer: leading zeros"):
            decode(b"i-00e")

        with self.assertRaisesRegex(DecodeError, "Invalid integer: leading zeros"):
            decode(b"i00e")

        with self.assertRaisesRegex(DecodeError, "Invalid integer: leading zeros"):
            decode(b"i0010e")

        self.assertEqual(
            decode(b"l10:BitTorrenti0eli10eed6:string10:BitTorrentee"),
            [b"BitTorrent", 0, [10], {"string": b"BitTorrent"}],
        )

        self.assertEqual(
            decode(
                b"d10:dictionaryd6:string10:BitTorrente7:integeri3e4:listli10ee6:string10:BitTorrente"
            ),
            {
                "string": b"BitTorrent",
                "integer": 3,
                "list": [10],
                "dictionary": {"string": b"BitTorrent"},
            },
        )

        with self.assertRaisesRegex(DecodeError, "Invalid dictionary: keys not sorted"):
            decode(b"d6:string10:BitTorrent7:integeri3ee")

        with self.assertRaisesRegex(DecodeError, "Unexpected byte"):
            decode(b"a")

    def test_encode(self):
        self.assertEqual(encode(b""), b"0:")
        self.assertEqual(encode(b"BitTorrent"), b"10:BitTorrent")

        self.assertEqual(encode(-10), b"i-10e")
        self.assertEqual(encode(0), b"i0e")
        self.assertEqual(encode(3), b"i3e")

        self.assertEqual(
            encode([b"BitTorrent", 0, [10], {"string": b"BitTorrent"}]),
            b"l10:BitTorrenti0eli10eed6:string10:BitTorrentee",
        )

        self.assertEqual(
            encode(
                {
                    "string": b"BitTorrent",
                    "integer": 3,
                    "list": [10],
                    "dictionary": {"string": b"BitTorrent"},
                }
            ),
            b"d10:dictionaryd6:string10:BitTorrente7:integeri3e4:listli10ee6:string10:BitTorrente",
        )

        with self.assertRaisesRegex(EncodeError, "Unsupported type"):
            encode("a")
