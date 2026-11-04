import unittest, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pap_verifier.digest import (sha256_domain, normalize_input_bytes, input_file_digest,
    normalized_input_set_digest, extension_closure_digest)
from pap_verifier.jcs import canonicalize

class TestDigests(unittest.TestCase):
    def test_domain_hello(self):
        self.assertEqual(sha256_domain("pap.artifact.v1", b"hello"), "sha256:49ade3eaed5c81a07ee5245b923abe3c629747f0eebe57a0052307d5965d5112")
        self.assertEqual(sha256_domain("pap.source.raw.v1", b"hello"), "sha256:8240a5313b027e89a99054c87e683a87d68f59dc566a40f16aa68edcbf1a81b7")
        self.assertEqual(sha256_domain("pap.package.v1", b"hello"), "sha256:4cb73e2896d009395089ea045b54b15eea2bc4c03e519bc08dc0f619da308308")

    def test_framing_ambiguity(self):
        a = sha256_domain("pap.test.v1", __import__("pap_verifier.digest", fromlist=["frame_record"]).frame_record("x", [b"ab", b"c"]))
        b = sha256_domain("pap.test.v1", __import__("pap_verifier.digest", fromlist=["frame_record"]).frame_record("x", [b"a", b"bc"]))
        self.assertEqual(a, "sha256:a4ff1eac1c490e25d4a23ef485f9219a4a51b2c370ba86ed20ba0d8e5c7334e5")
        self.assertEqual(b, "sha256:19777dd70824683c8483961510324f7656c03378f3a4b64192e8bee7ff0ecff2")

    def test_input_normalization(self):
        raw = bytes.fromhex("613a20310d0a623a20320d0a")
        norm = normalize_input_bytes(raw, "lf")
        self.assertEqual(norm.hex(), "613a20310a623a20320a")
        self.assertEqual(input_file_digest("inputs/crlf.yml", norm), "sha256:2633064c5d3066746beae7416e97e87816fe9b031c6f57af4c9b02ca1c00453b")
        self.assertEqual(normalized_input_set_digest([("inputs/crlf.yml", norm)]), "sha256:92e9ec329516a5672fc40fd0b4474f2a2fd7790d87817c37b772af3347df2021")

    def test_checker_identity_vector(self):
        files = [("src/checks/digest.ts", b'export const checkId = "pap.check.digest-integrity/1";\n'),
                 ("src/checks/source.ts", b"export const spanCheck = true;\n")]
        deps = [("zod", "3.23.8", "sha512-9K5fXZ0G8p3oUo4WQ9m2l1v0B9m3r7Yqk1s2V4pL6c0=")]
        impl = extension_closure_digest("checker", "pap.verifier.reference", "0.1.0", files, deps)
        self.assertEqual(impl, "sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0")
        ci = sha256_domain("pap.checker.identity.v1", canonicalize({"id":"pap.verifier.reference","version":"0.1.0","implementationDigest":impl}).encode("utf-8"))
        self.assertEqual(ci, "sha256:15a0b0149dc95f7b9711e7b28fc4189ed8539b03ffd2c96e967205316d75963f")

    def test_package_identity(self):
        from pathlib import Path
        from pap_verifier.jcs import parse_strict
        data = Path("pap/fixtures/pap-v0.1/F01-unchanged/assurance-package.json").read_bytes()
        obj, _ = parse_strict(data)
        canon = canonicalize(obj)
        pid = sha256_domain("pap.package.v1", canon.encode("utf-8"))
        self.assertEqual(pid, "sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020")

if __name__ == "__main__":
    unittest.main()
