import hashlib
import struct


def sha256_domain(domain: str, data: bytes) -> str:
    h = hashlib.sha256()
    h.update(domain.encode("ascii"))
    h.update(b"\x00")
    h.update(data)
    return "sha256:" + h.hexdigest()


def frame_record(tag: str, parts) -> bytes:
    out = struct.pack(">I", len(tag.encode("utf-8")))
    out += tag.encode("utf-8")
    out += struct.pack(">I", len(parts))
    for part in parts:
        if isinstance(part, str):
            b = part.encode("utf-8")
        else:
            b = part
        out += struct.pack(">I", len(b)) + b
    return out


def normalize_input_bytes(raw: bytes, normalization: str) -> bytes:
    if normalization == "none":
        return raw
    if b"\x00" in raw:
        return raw
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def input_file_digest(path: str, normalized_bytes: bytes) -> str:
    rec = frame_record("input", [path.encode("utf-8"), normalized_bytes])
    return sha256_domain("pap.input.file.v1", rec)


def normalized_input_set_digest(records) -> str:
    # records: list of (path, normalized_bytes)
    ordered = sorted(records, key=lambda r: r[0].encode("utf-8"))
    payload = b""
    for path, nb in ordered:
        payload += frame_record("input", [path.encode("utf-8"), nb])
    return sha256_domain("pap.input.set.v1", payload)


def extension_closure_digest(kind, ext_id, version, files, dependencies) -> str:
    # files: list of (path, text_bytes_raw) -> normalized
    payload = b""
    payload += frame_record("extension", [kind.encode("utf-8"), ext_id.encode("utf-8"), version.encode("utf-8")])
    norm_files = []
    for path, raw in files:
        text = raw.decode("utf-8")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        norm_files.append((path, text.encode("utf-8")))
    for path, nb in sorted(norm_files, key=lambda r: r[0].encode("utf-8")):
        payload += frame_record("file", [path.encode("utf-8"), nb])
    deps = sorted(dependencies, key=lambda d: (d[0].encode("utf-8"), d[1].encode("utf-8")))
    for name, ver, integrity in deps:
        payload += frame_record("dependency", [name.encode("utf-8"), ver.encode("utf-8"), integrity.encode("utf-8")])
    return sha256_domain("pap.extension.closure.v1", payload)
