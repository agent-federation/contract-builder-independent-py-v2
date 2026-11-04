import unittest, hashlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pap_verifier.jcs import canonicalize, parse_strict

class TestJCS(unittest.TestCase):
    def test_utf16_key_order(self):
        obj = {"a":1,"😀":2,"\ufffd":3,"A":4,"b":5}
        c = canonicalize(obj)
        self.assertEqual(c, '{"A":4,"a":1,"b":5,"😀":2,"�":3}')
        self.assertEqual(len(c.encode("utf-8")), 36)
        self.assertEqual(hashlib.sha256(c.encode("utf-8")).hexdigest(), "9267454f732ed7ef9939b28dc1e451c88c2967ff4a6b1746bf638d313e72b508")

    def test_string_escaping(self):
        s = "\x01" + "\t" + "\n" + '"' + "\\" + "é" + "😀"
        c = canonicalize({"s": s})
        self.assertEqual(c, '{"s":"\\u0001\\t\\n\\"\\\\é😀"}')
        self.assertEqual(len(c.encode("utf-8")), 28)
        self.assertEqual(hashlib.sha256(c.encode("utf-8")).hexdigest(), "9033f8f21bc1c3367ebcad55e2298bf113b63f9e5f21c20678de00e760c5ff5d")

    def test_numbers_valid(self):
        self.assertEqual(canonicalize(9007199254740991), "9007199254740991")
        self.assertEqual(canonicalize(-9007199254740991), "-9007199254740991")

    def test_numbers_invalid(self):
        for bad in [b"9007199254740992", b"1.0", b"1e3", b"-0"]:
            with self.assertRaises(Exception):
                parse_strict(bad)

    def test_duplicate_keys(self):
        with self.assertRaises(Exception):
            parse_strict(b'{"a":1,"a":2}')

    def test_bom(self):
        with self.assertRaises(Exception):
            parse_strict(b'\xef\xbb\xbf{"a":1}')

    def test_non_integer(self):
        with self.assertRaises(Exception):
            parse_strict(b'{"a":1.5}')

if __name__ == "__main__":
    unittest.main()
