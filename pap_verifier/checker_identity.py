import os
from pathlib import Path

from .digest import extension_closure_digest, sha256_domain
from .jcs import canonicalize

VERIFIER_ID = "pap.verifier.python"
VERIFIER_VERSION = "0.1.0"

IMPLEMENTATION_ROOT = Path(__file__).resolve().parent.parent


def _closure_files():
    files = []
    root = IMPLEMENTATION_ROOT
    # build manifest
    if (root / "pyproject.toml").is_file():
        files.append("pyproject.toml")
    pkg_dir = root / "pap_verifier"
    if pkg_dir.is_dir():
        for p in pkg_dir.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            files.append(p.relative_to(root).as_posix())
    files = sorted(set(files))
    return files


def compute_checker_identity():
    root = IMPLEMENTATION_ROOT
    file_list = _closure_files()
    files_for_digest = []
    for rel in file_list:
        raw = (root / rel).read_bytes()
        # must be text
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            raise RuntimeError(f"binary file in closure: {rel}")
        files_for_digest.append((rel, raw))
    dependencies = []  # no third-party dependencies
    impl_digest = extension_closure_digest(
        "checker", VERIFIER_ID, VERIFIER_VERSION, files_for_digest, dependencies
    )
    checker_id = sha256_domain(
        "pap.checker.identity.v1",
        canonicalize({"id": VERIFIER_ID, "version": VERIFIER_VERSION,
                      "implementationDigest": impl_digest}).encode("utf-8"),
    )
    return {
        "id": VERIFIER_ID,
        "version": VERIFIER_VERSION,
        "implementationDigest": impl_digest,
        "checkerIdentity": checker_id,
        "files": file_list,
        "dependencies": dependencies,
    }
