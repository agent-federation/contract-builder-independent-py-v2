"""RFC 8785 JCS canonicalization restricted to I-JSON subset."""
import json
import re

MAX_INT = 2**53 - 1
MIN_INT = -(2**53 - 1)


class JCSError(Exception):
    pass


def _utf16_code_units(s: str):
    return [u for u in s.encode("utf-16-le") and __import__("struct").unpack("<" + "H" * (len(s.encode("utf-16-le")) // 2), s.encode("utf-16-le"))]


def utf16_sort_key(s: str):
    data = s.encode("utf-16-le")
    units = [int.from_bytes(data[i:i+2], "little") for i in range(0, len(data), 2)]
    return units


def escape_string(s: str) -> str:
    for ch in s:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise JCSError("lone surrogate")
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\r":
            out.append("\\r")
        elif cp < 0x20:
            out.append("\\u%04x" % cp)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonicalize(obj) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, str):
        # scalar sequence check
        for ch in obj:
            cp = ord(ch)
            if 0xD800 <= cp <= 0xDFFF:
                raise JCSError("lone surrogate")
        return escape_string(obj)
    if isinstance(obj, int) and not isinstance(obj, bool):
        if obj > MAX_INT or obj < MIN_INT:
            raise JCSError("integer out of I-JSON range")
        return str(obj)
    if isinstance(obj, float):
        raise JCSError("floating point not allowed")
    if isinstance(obj, list):
        return "[" + ",".join(canonicalize(x) for x in obj) + "]"
    if isinstance(obj, dict):
        # sort keys by UTF-16 code unit order
        keys = sorted(obj.keys(), key=utf16_sort_key)
        # ensure keys are str
        for k in keys:
            if not isinstance(k, str):
                raise JCSError("object key must be string")
        parts = []
        for k in keys:
            parts.append(escape_string(k) + ":" + canonicalize(obj[k]))
        return "{" + ",".join(parts) + "}"
    raise JCSError("unsupported type %r" % (type(obj),))


def parse_strict(data: bytes, nesting_limit: int = 64, string_limit: int = 16 * 1024 * 1024):
    if data.startswith(b"\xef\xbb\xbf"):
        raise JCSError("BOM not allowed")
    text = data.decode("utf-8")  # strict
    # duplicate key detection
    def obj_hook(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise JCSError("duplicate key")
        return dict(pairs)

    def parse_int(s):
        if s == "-0" or s == "+0":
            raise JCSError("negative zero not allowed")
        # reject leading zeros except "0"
        if len(s) > 1 and s[0] == "0" and s[1].isdigit():
            raise JCSError("leading zero")
        if len(s) > 2 and s[0] == "-" and s[1] == "0" and s[2].isdigit():
            raise JCSError("leading zero")
        val = int(s)
        if val > MAX_INT or val < MIN_INT:
            raise JCSError("integer out of range")
        return val

    def parse_float(s):
        raise JCSError("non-integer number token")

    obj = json.loads(text, parse_int=parse_int, parse_float=parse_float,
                     object_pairs_hook=obj_hook)

    # validate nesting depth and string sizes
    def check(o, depth):
        if depth > nesting_limit:
            raise JCSError("nesting depth exceeded")
        if isinstance(o, str):
            if len(o.encode("utf-8")) > string_limit:
                raise JCSError("string size exceeded")
            for ch in o:
                cp = ord(ch)
                if 0xD800 <= cp <= 0xDFFF:
                    raise JCSError("lone surrogate")
        elif isinstance(o, dict):
            for k, v in o.items():
                if not isinstance(k, str):
                    raise JCSError("non-string key")
                if len(k.encode("utf-8")) > string_limit:
                    raise JCSError("key size exceeded")
                check(v, depth + 1)
        elif isinstance(o, list):
            for item in o:
                check(item, depth + 1)
        elif isinstance(o, bool):
            pass
        elif isinstance(o, int):
            pass
        else:
            raise JCSError("unsupported value type")
    check(obj, 0)
    return obj, text
