import os
import re
import json
import struct
from pathlib import Path
from datetime import datetime, timezone

from .jcs import parse_strict, canonicalize, JCSError
from .digest import (sha256_domain, frame_record, normalize_input_bytes,
                     input_file_digest, normalized_input_set_digest)
from .checker_identity import compute_checker_identity, VERIFIER_ID, VERIFIER_VERSION

MANIFEST_LIMIT = 1 * 1024 * 1024
PAYLOAD_FILES_LIMIT = 4096
FILE_BYTES_LIMIT = 256 * 1024 * 1024
TOTAL_PAYLOAD_BYTES_LIMIT = 1 * 1024 * 1024 * 1024
JSON_NESTING_LIMIT = 64
JSON_STRING_LIMIT = 16 * 1024 * 1024
CLAIMS_FILES_LIMIT = 16
PROVENANCE_BINDINGS_LIMIT = 100000
RELATION_ENTITIES_LIMIT = 100000
RELATION_EDGES_LIMIT = 1000000
SIGNATURE_ENVELOPES_LIMIT = 32

KNOWN_CHECKS = {"pap.check.digest-integrity/1", "pap.check.source-quote/1",
                "pap.check.relation-consistency/1"}

KNOWN_FEATURES = set()  # v0.1 supports none beyond core


class UsageError(Exception):
    pass


class PackageNotFound(Exception):
    pass


def _now_iso(now_str=None):
    if now_str:
        # parse RFC3339
        s = now_str.strip()
        # normalize
        # Python fromisoformat handles offsets in 3.11+
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        dt = dt.astimezone(timezone.utc)
        return dt, _render_iso(dt)
    dt = datetime.now(timezone.utc)
    return dt, _render_iso(dt)


def _render_iso(dt):
    # preserve fraction, strip trailing zeros
    s = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if dt.microsecond:
        frac = f"{dt.microsecond:06d}".rstrip("0")
        s += "." + frac
    s += "Z"
    return s


def _valid_rfc3339(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt is not None
    except Exception:
        return False


def _path_grammar_ok(path):
    if not isinstance(path, str):
        return False
    if len(path.encode("utf-8")) > 255:
        return False
    segs = path.split("/")
    if any(seg == "" for seg in segs):
        return False
    if len(segs) > 16:
        return False
    for seg in segs:
        if len(seg.encode("utf-8")) > 255:
            return False
        if not re.fullmatch(r"[A-Za-z0-9._-]+", seg):
            return False
        if seg in (".", ".."):
            return False
    return True


def _safe_resolve(root, rel):
    # returns absolute path; ensure inside root
    root_r = Path(root).resolve()
    target = (root_r / rel)
    # lexical containment
    try:
        target.resolve()
    except Exception:
        pass
    # check relative
    try:
        target.relative_to(root_r)
    except ValueError:
        return None
    return target


def _is_symlink(path):
    return Path(path).is_symlink()


def verify(package_path, now_str=None, trust_policy_path=None, limits=None):
    checker_info = compute_checker_identity()
    checker_identity = checker_info["checkerIdentity"]
    impl_digest = checker_info["implementationDigest"]

    # resolve root
    p = Path(package_path)
    if not p.exists():
        raise PackageNotFound("pap.package.not-found")
    if p.is_symlink():
        resolved = p.resolve()
    else:
        resolved = p
    if not resolved.is_dir():
        raise UsageError("pap.cli.usage: package is not a directory")
    root = resolved

    now_dt, evaluated_at = _now_iso(now_str)

    # policy
    policy_id = None
    policy_digest = None
    policy_state = "ABSENT"
    policy_obj = None
    policy_required_checks = []
    policy_required_dims = []
    if trust_policy_path:
        pp = Path(trust_policy_path)
        try:
            raw = pp.read_bytes()
        except Exception:
            raise UsageError("pap.trust.policy-invalid")
        # parse
        try:
            text = raw.decode("utf-8")
            pobj, _ = parse_strict(raw, JSON_NESTING_LIMIT, JSON_STRING_LIMIT)
        except Exception:
            raise UsageError("pap.trust.policy-invalid")
        if not isinstance(pobj, dict):
            raise UsageError("pap.trust.policy-invalid")
        policy_obj = pobj
        # canonical bytes for digest
        try:
            canon = canonicalize(pobj).encode("utf-8")
        except Exception:
            raise UsageError("pap.trust.policy-invalid")
        policy_digest = sha256_domain("pap.trust-policy.v1", canon)
        policy_id = pobj.get("id") if isinstance(pobj.get("id"), str) else None
        # state freshness
        issued = pobj.get("issuedAt")
        expires = pobj.get("expiresAt")
        try:
            if isinstance(issued, str):
                idt = datetime.fromisoformat(issued.replace("Z", "+00:00"))
                if now_dt < idt.astimezone(timezone.utc):
                    policy_state = "STALE"
            if isinstance(expires, str):
                edt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if now_dt > edt.astimezone(timezone.utc):
                    policy_state = "STALE"
            if policy_state != "STALE":
                policy_state = "FRESH"
        except Exception:
            policy_state = "STALE"
        # required checks/dims
        if isinstance(pobj.get("requiredChecks"), list):
            policy_required_checks = [x for x in pobj["requiredChecks"] if isinstance(x, str)]
        if isinstance(pobj.get("requiredDimensions"), list):
            policy_required_dims = [x for x in pobj["requiredDimensions"] if isinstance(x, str)]

    # limits (effective) - defaults
    limits = limits or {}
    manifest_limit = limits.get("manifestBytes", MANIFEST_LIMIT)
    # (others not lowered support except defaults)

    diagnostics = []
    limitations = []

    def add_diag(code, severity, scope, message):
        diagnostics.append({"code": code, "severity": severity, "scope": scope, "message": message})

    # manifest read
    manifest_path = root / "assurance-package.json"
    manifest_bytes = None
    manifest_io_error = False
    try:
        if not manifest_path.is_file():
            raise FileNotFoundError("missing")
        manifest_bytes = manifest_path.read_bytes()
    except Exception:
        manifest_io_error = True

    manifest_obj = None
    manifest_parse_failed = False
    manifest_limit_hit = False
    package_identity = None
    pap_version = None
    integrity_package = "FAIL"
    integrity_artifacts = "NOT_EVALUATED"
    sources_integrity = "NOT_EVALUATED"
    sources_availability = "NOT_APPLICABLE"
    scan_complete = True

    # undeclared scan (will do later) placeholder

    # payload storage
    artifacts_list = []  # manifest entries
    inputs_list = []
    sources_list = []
    claims_declared = {}  # kind -> ref
    profile_obj = None
    extensions_obj = None
    required_features = []
    check_specs = []

    # If manifest IO error
    if manifest_io_error:
        add_diag("pap.package.io", "error", "package", "manifest cannot be read")
        integrity_package = "FAIL"
        manifest_parse_failed = True
    else:
        # size limit
        if len(manifest_bytes) > manifest_limit:
            add_diag("pap.package.limit-exceeded", "error", "package", "manifest byte limit exceeded")
            manifest_limit_hit = True
            manifest_parse_failed = True
            integrity_package = "FAIL"
        else:
            # parse
            try:
                obj, _text = parse_strict(manifest_bytes, JSON_NESTING_LIMIT, JSON_STRING_LIMIT)
                manifest_obj = obj
                integrity_package = "PASS"
            except JCSError as e:
                msg = str(e)
                if "duplicate key" in msg:
                    add_diag("pap.package.duplicate-key", "error", "package", msg)
                elif "limit" in msg or "depth" in msg or "size" in msg:
                    add_diag("pap.package.limit-exceeded", "error", "package", msg)
                    manifest_limit_hit = True
                else:
                    add_diag("pap.package.manifest-json", "error", "package", msg)
                manifest_parse_failed = True
                integrity_package = "FAIL"
            except Exception as e:
                add_diag("pap.package.manifest-json", "error", "package", str(e))
                manifest_parse_failed = True
                integrity_package = "FAIL"

    # If parsed, validate
    claim_invalid = False
    claim_unsupported_versions = []
    path_invalid_found = False
    path_duplicate_found = False
    unknown_field_found = False
    schema_error_found = False
    duplicate_id_found = False

    # declared payload paths collection
    declared_paths = []  # list of (path, kind)
    # map for reading
    artifact_entries = []
    input_entries = []
    source_entries = []

    if manifest_obj is not None and isinstance(manifest_obj, dict):
        # compute package identity now (even if invalid)
        try:
            package_identity = sha256_domain("pap.package.v1", canonicalize(manifest_obj).encode("utf-8"))
        except Exception:
            package_identity = None
        pap_version = manifest_obj.get("papVersion") if isinstance(manifest_obj.get("papVersion"), str) else None

        # top-level unknown fields
        allowed_top = {"papVersion","package","subject","build","artifacts","inputs","sources",
                       "claims","profile","checkSpecs","extensions","requiredFeatures"}
        for k in manifest_obj:
            if k not in allowed_top:
                add_diag("pap.package.unknown-field", "error", "package", f"unknown field {k}")
                unknown_field_found = True
                integrity_package = "FAIL"

        # required fields
        for r in ("papVersion", "package", "artifacts", "checkSpecs"):
            if r not in manifest_obj:
                add_diag("pap.package.schema", "error", "package", f"missing required field {r}")
                schema_error_found = True
                integrity_package = "FAIL"

        # papVersion
        pv = manifest_obj.get("papVersion")
        if "papVersion" in manifest_obj:
            if not isinstance(pv, str) or not re.fullmatch(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", pv):
                add_diag("pap.package.schema", "error", "package", "invalid papVersion")
                schema_error_found = True
                integrity_package = "FAIL"

        # package
        pkg = manifest_obj.get("package")
        if "package" in manifest_obj:
            if not isinstance(pkg, dict):
                add_diag("pap.package.schema", "error", "package", "package must be object")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                allowed_pkg = {"id","title","createdAt","producer"}
                for k in pkg:
                    if k not in allowed_pkg:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field package.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                if "id" not in pkg:
                    add_diag("pap.package.schema", "error", "package", "package.id required")
                    schema_error_found = True
                    integrity_package = "FAIL"
                else:
                    if not isinstance(pkg.get("id"), str) or not (1 <= len(pkg["id"]) <= 512):
                        add_diag("pap.package.schema", "error", "package", "invalid package.id")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "title" in pkg and (not isinstance(pkg["title"], str) or len(pkg["title"]) > 512):
                    add_diag("pap.package.schema", "error", "package", "invalid package.title")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "createdAt" in pkg:
                    # rfc3339 basic
                    if not isinstance(pkg["createdAt"], str):
                        add_diag("pap.package.schema", "error", "package", "invalid createdAt")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "producer" in pkg:
                    pr = pkg["producer"]
                    if not isinstance(pr, dict):
                        add_diag("pap.package.schema", "error", "package", "invalid producer")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    else:
                        if set(pr.keys()) != {"name","version"} and not set(pr.keys()).issubset({"name","version"}):
                            # required name/version
                            pass
                        if "name" not in pr or "version" not in pr:
                            add_diag("pap.package.schema", "error", "package", "producer missing fields")
                            schema_error_found = True
                            integrity_package = "FAIL"
                        else:
                            if not isinstance(pr.get("name"), str) or not (1 <= len(pr["name"]) <= 256):
                                add_diag("pap.package.schema", "error", "package", "invalid producer.name")
                                schema_error_found = True
                                integrity_package = "FAIL"
                            if not isinstance(pr.get("version"), str) or not (1 <= len(pr["version"]) <= 128):
                                add_diag("pap.package.schema", "error", "package", "invalid producer.version")
                                schema_error_found = True
                                integrity_package = "FAIL"
                        for k in pr:
                            if k not in ("name","version"):
                                add_diag("pap.package.unknown-field", "error", "package", f"unknown field producer.{k}")
                                unknown_field_found = True
                                integrity_package = "FAIL"

        # subject
        if "subject" in manifest_obj:
            subj = manifest_obj["subject"]
            if not isinstance(subj, dict):
                add_diag("pap.package.schema", "error", "package", "subject must be object")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                allowed = {"projectId","revision"}
                for k in subj:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field subject.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                if "projectId" not in subj:
                    add_diag("pap.package.schema", "error", "package", "subject.projectId required")
                    schema_error_found = True
                    integrity_package = "FAIL"
                else:
                    if not isinstance(subj.get("projectId"), str) or not (1 <= len(subj["projectId"]) <= 512):
                        add_diag("pap.package.schema", "error", "package", "invalid projectId")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "revision" in subj and (not isinstance(subj["revision"], str) or len(subj["revision"]) > 256):
                    add_diag("pap.package.schema", "error", "package", "invalid revision")
                    schema_error_found = True
                    integrity_package = "FAIL"

        # build
        if "build" in manifest_obj:
            build = manifest_obj["build"]
            if not isinstance(build, dict):
                add_diag("pap.package.schema", "error", "package", "build must be object")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                allowed = {"engineVersion","manifestVersion","inputDigest","normalizedInputDigest","extensions"}
                for k in build:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field build.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                for f in ("engineVersion","manifestVersion"):
                    if f in build and (not isinstance(build[f], str) or len(build[f]) < 1):
                        add_diag("pap.package.schema", "error", "package", f"invalid build.{f}")
                        schema_error_found = True
                        integrity_package = "FAIL"
                for f in ("inputDigest","normalizedInputDigest"):
                    if f in build:
                        if not (isinstance(build[f], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", build[f])):
                            add_diag("pap.package.schema", "error", "package", f"invalid build.{f}")
                            schema_error_found = True
                            integrity_package = "FAIL"
                if "extensions" in build:
                    exts = build["extensions"]
                    if not isinstance(exts, list):
                        add_diag("pap.package.schema", "error", "package", "build.extensions must be array")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    else:
                        for e in exts:
                            if not isinstance(e, dict):
                                add_diag("pap.package.schema", "error", "package", "invalid build extension")
                                schema_error_found = True
                                integrity_package = "FAIL"
                                continue
                            if set(e.keys()) != {"kind","id","version"}:
                                add_diag("pap.package.schema", "error", "package", "invalid build extension keys")
                                schema_error_found = True
                                integrity_package = "FAIL"
                                continue
                            if e.get("kind") not in ("profile","adapter","renderer","checker"):
                                add_diag("pap.package.schema", "error", "package", "invalid build extension kind")
                                schema_error_found = True
                                integrity_package = "FAIL"
                            if not isinstance(e.get("id"), str) or not (1 <= len(e["id"]) <= 256):
                                add_diag("pap.package.schema", "error", "package", "invalid build extension id")
                                schema_error_found = True
                                integrity_package = "FAIL"
                            if not isinstance(e.get("version"), str) or not (1 <= len(e["version"]) <= 128):
                                add_diag("pap.package.schema", "error", "package", "invalid build extension version")
                                schema_error_found = True
                                integrity_package = "FAIL"

        # artifacts
        arts = manifest_obj.get("artifacts")
        if "artifacts" in manifest_obj:
            if not isinstance(arts, list) or len(arts) < 1:
                add_diag("pap.package.schema", "error", "package", "artifacts must be non-empty array")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                for a in arts:
                    if not isinstance(a, dict):
                        add_diag("pap.package.schema", "error", "package", "artifact must be object")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    allowed = {"id","path","mediaType","bytes","digest"}
                    for k in a:
                        if k not in allowed:
                            add_diag("pap.package.unknown-field", "error", "package", f"unknown field artifact.{k}")
                            unknown_field_found = True
                            integrity_package = "FAIL"
                    for r in ("id","path","mediaType","bytes","digest"):
                        if r not in a:
                            add_diag("pap.package.schema", "error", "package", f"artifact missing {r}")
                            schema_error_found = True
                            integrity_package = "FAIL"
                    # validate fields
                    if "id" in a and (not isinstance(a["id"], str) or not (1 <= len(a["id"]) <= 256)):
                        add_diag("pap.package.schema", "error", "package", "invalid artifact.id")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if "path" in a:
                        if not _path_grammar_ok(a["path"]):
                            add_diag("pap.package.path-invalid", "error", "package", "invalid artifact path")
                            path_invalid_found = True
                            integrity_package = "FAIL"
                        else:
                            if not a["path"].startswith("artifacts/"):
                                add_diag("pap.package.path-invalid", "error", "package", "artifact path must start with artifacts/")
                                path_invalid_found = True
                                integrity_package = "FAIL"
                            declared_paths.append((a["path"], "artifact"))
                    if "mediaType" in a and (not isinstance(a["mediaType"], str) or not (1 <= len(a["mediaType"]) <= 256)):
                        add_diag("pap.package.schema", "error", "package", "invalid mediaType")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if "bytes" in a and (not isinstance(a["bytes"], int) or isinstance(a["bytes"], bool) or a["bytes"] < 0):
                        add_diag("pap.package.schema", "error", "package", "invalid bytes")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if "digest" in a and not (isinstance(a["digest"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", a["digest"])):
                        add_diag("pap.package.schema", "error", "package", "invalid digest")
                        schema_error_found = True
                        integrity_package = "FAIL"
                artifact_entries = arts if isinstance(arts, list) else []

        # inputs
        ins = manifest_obj.get("inputs", [])
        if "inputs" in manifest_obj:
            if not isinstance(ins, list):
                add_diag("pap.package.schema", "error", "package", "inputs must be array")
                schema_error_found = True
                integrity_package = "FAIL"
                ins = []
            for it in ins:
                if not isinstance(it, dict):
                    add_diag("pap.package.schema", "error", "package", "input must be object")
                    schema_error_found = True
                    integrity_package = "FAIL"
                    continue
                allowed = {"id","path","mediaType","digest","normalization"}
                for k in it:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field input.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                for r in ("id","path","mediaType","digest","normalization"):
                    if r not in it:
                        add_diag("pap.package.schema", "error", "package", f"input missing {r}")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "id" in it and (not isinstance(it["id"], str) or not (1 <= len(it["id"]) <= 256)):
                    add_diag("pap.package.schema", "error", "package", "invalid input.id")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "path" in it:
                    if not _path_grammar_ok(it["path"]):
                        add_diag("pap.package.path-invalid", "error", "package", "invalid input path")
                        path_invalid_found = True
                        integrity_package = "FAIL"
                    else:
                        if not it["path"].startswith("inputs/"):
                            add_diag("pap.package.path-invalid", "error", "package", "input path must start with inputs/")
                            path_invalid_found = True
                            integrity_package = "FAIL"
                        declared_paths.append((it["path"], "input"))
                if "mediaType" in it and (not isinstance(it["mediaType"], str) or not (1 <= len(it["mediaType"]) <= 256)):
                    add_diag("pap.package.schema", "error", "package", "invalid input mediaType")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "digest" in it and not (isinstance(it["digest"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", it["digest"])):
                    add_diag("pap.package.schema", "error", "package", "invalid input digest")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "normalization" in it and it["normalization"] not in ("lf","none"):
                    add_diag("pap.package.schema", "error", "package", "invalid normalization")
                    schema_error_found = True
                    integrity_package = "FAIL"
            input_entries = ins if isinstance(ins, list) else []

        # sources
        srcs = manifest_obj.get("sources", [])
        if "sources" in manifest_obj:
            if not isinstance(srcs, list):
                add_diag("pap.package.schema", "error", "package", "sources must be array")
                schema_error_found = True
                integrity_package = "FAIL"
                srcs = []
            for s in srcs:
                if not isinstance(s, dict):
                    add_diag("pap.package.schema", "error", "package", "source must be object")
                    schema_error_found = True
                    integrity_package = "FAIL"
                    continue
                allowed = {"id","path","mediaType","digest","acquiredAt","acquisition"}
                for k in s:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field source.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                for r in ("id","mediaType","digest"):
                    if r not in s:
                        add_diag("pap.package.schema", "error", "package", f"source missing {r}")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "id" in s and (not isinstance(s["id"], str) or not (1 <= len(s["id"]) <= 256)):
                    add_diag("pap.package.schema", "error", "package", "invalid source.id")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "path" in s:
                    if not _path_grammar_ok(s["path"]):
                        add_diag("pap.package.path-invalid", "error", "package", "invalid source path")
                        path_invalid_found = True
                        integrity_package = "FAIL"
                    else:
                        if not s["path"].startswith("sources/"):
                            add_diag("pap.package.path-invalid", "error", "package", "source path must start with sources/")
                            path_invalid_found = True
                            integrity_package = "FAIL"
                        declared_paths.append((s["path"], "source"))
                if "mediaType" in s and (not isinstance(s["mediaType"], str) or not (1 <= len(s["mediaType"]) <= 256)):
                    add_diag("pap.package.schema", "error", "package", "invalid source mediaType")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if "digest" in s and not (isinstance(s["digest"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", s["digest"])):
                    add_diag("pap.package.schema", "error", "package", "invalid source digest")
                    schema_error_found = True
                    integrity_package = "FAIL"
            source_entries = srcs if isinstance(srcs, list) else []

        # claims
        claims = manifest_obj.get("claims", {})
        if "claims" in manifest_obj:
            if not isinstance(claims, dict):
                add_diag("pap.package.schema", "error", "package", "claims must be object")
                schema_error_found = True
                integrity_package = "FAIL"
                claims = {}
            else:
                allowed = {"provenance","relations","producerReport","reviews"}
                for k in claims:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown claim {k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                for k, v in claims.items():
                    if not isinstance(v, dict):
                        add_diag("pap.package.schema", "error", "package", f"claim {k} must be object")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    if set(v.keys()) != {"path","digest"}:
                        add_diag("pap.package.schema", "error", "package", f"claim {k} invalid keys")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    if not _path_grammar_ok(v.get("path","")):
                        add_diag("pap.package.path-invalid", "error", "package", f"invalid claim path {k}")
                        path_invalid_found = True
                        integrity_package = "FAIL"
                    else:
                        if not v["path"].startswith("claims/"):
                            add_diag("pap.package.path-invalid", "error", "package", f"claim path must start with claims/ {k}")
                            path_invalid_found = True
                            integrity_package = "FAIL"
                        else:
                            declared_paths.append((v["path"], "claim"))
                    if not (isinstance(v.get("digest"), str) and re.fullmatch(r"sha256:[0-9a-f]{64}", v["digest"])):
                        add_diag("pap.package.schema", "error", "package", f"invalid claim digest {k}")
                        schema_error_found = True
                        integrity_package = "FAIL"
                claims_declared = claims if isinstance(claims, dict) else {}

        # profile
        if "profile" in manifest_obj:
            prof = manifest_obj["profile"]
            if not isinstance(prof, dict):
                add_diag("pap.package.schema", "error", "package", "profile must be object")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                allowed = {"id","version","closureDigest"}
                for k in prof:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field profile.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                if "id" not in prof or "version" not in prof:
                    add_diag("pap.package.schema", "error", "package", "profile missing id/version")
                    schema_error_found = True
                    integrity_package = "FAIL"
                else:
                    if not isinstance(prof.get("id"), str) or not (1 <= len(prof["id"]) <= 256):
                        add_diag("pap.package.schema", "error", "package", "invalid profile.id")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if not isinstance(prof.get("version"), str) or not (1 <= len(prof["version"]) <= 128):
                        add_diag("pap.package.schema", "error", "package", "invalid profile.version")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "closureDigest" in prof and not (isinstance(prof["closureDigest"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", prof["closureDigest"])):
                    add_diag("pap.package.schema", "error", "package", "invalid profile.closureDigest")
                    schema_error_found = True
                    integrity_package = "FAIL"
                profile_obj = prof

        # checkSpecs
        cs = manifest_obj.get("checkSpecs")
        if "checkSpecs" in manifest_obj:
            if not isinstance(cs, list) or len(cs) < 1:
                add_diag("pap.package.schema", "error", "package", "checkSpecs must be non-empty array")
                schema_error_found = True
                integrity_package = "FAIL"
                cs = []
            for c in cs:
                if not isinstance(c, dict):
                    add_diag("pap.package.schema", "error", "package", "checkSpec must be object")
                    schema_error_found = True
                    integrity_package = "FAIL"
                    continue
                allowed = {"id","version","required"}
                for k in c:
                    if k not in allowed:
                        add_diag("pap.package.unknown-field", "error", "package", f"unknown field checkSpec.{k}")
                        unknown_field_found = True
                        integrity_package = "FAIL"
                if "id" not in c or "version" not in c:
                    add_diag("pap.package.schema", "error", "package", "checkSpec missing id/version")
                    schema_error_found = True
                    integrity_package = "FAIL"
                    continue
                if not (isinstance(c["id"], str) and re.fullmatch(r"pap\.check\.[a-z0-9-]+/[0-9]+", c["id"])):
                    add_diag("pap.package.schema", "error", "package", "invalid checkSpec.id")
                    schema_error_found = True
                    integrity_package = "FAIL"
                if not (isinstance(c["version"], str) and re.fullmatch(r"(0|[1-9][0-9]*)", c["version"])):
                    add_diag("pap.package.schema", "error", "package", "invalid checkSpec.version")
                    schema_error_found = True
                    integrity_package = "FAIL"
                # version suffix mismatch
                if isinstance(c.get("id"), str) and isinstance(c.get("version"), str):
                    suffix = c["id"].rsplit("/", 1)[-1]
                    if suffix != c["version"]:
                        add_diag("pap.package.schema", "error", "package", "checkSpec version suffix mismatch")
                        schema_error_found = True
                        integrity_package = "FAIL"
                if "required" in c and not isinstance(c["required"], bool):
                    add_diag("pap.package.schema", "error", "package", "invalid required")
                    schema_error_found = True
                    integrity_package = "FAIL"
            check_specs = cs if isinstance(cs, list) else []

        # extensions
        if "extensions" in manifest_obj:
            exts = manifest_obj["extensions"]
            if not isinstance(exts, dict):
                add_diag("pap.package.schema", "error", "package", "extensions must be object")
                schema_error_found = True
                integrity_package = "FAIL"
            else:
                for k, v in exts.items():
                    if not (isinstance(k, str) and re.fullmatch(r"^[a-z0-9]+(\.[a-z0-9-]+)+$", k)):
                        add_diag("pap.package.schema", "error", "package", "invalid extension key")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    if not isinstance(v, dict):
                        add_diag("pap.package.schema", "error", "package", "extension must be object")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    if set(v.keys()) - {"version","critical","data"} or "version" not in v or "critical" not in v:
                        add_diag("pap.package.schema", "error", "package", "invalid extension fields")
                        schema_error_found = True
                        integrity_package = "FAIL"
                        continue
                    if not isinstance(v.get("version"), str) or not (1 <= len(v["version"]) <= 128):
                        add_diag("pap.package.schema", "error", "package", "invalid extension version")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if not isinstance(v.get("critical"), bool):
                        add_diag("pap.package.schema", "error", "package", "invalid extension critical")
                        schema_error_found = True
                        integrity_package = "FAIL"
                    if "data" in v and not isinstance(v["data"], dict):
                        add_diag("pap.package.schema", "error", "package", "invalid extension data")
                        schema_error_found = True
                        integrity_package = "FAIL"
            extensions_obj = exts if isinstance(exts, dict) else {}

        # requiredFeatures
        if "requiredFeatures" in manifest_obj:
            rf = manifest_obj["requiredFeatures"]
            if not isinstance(rf, list):
                add_diag("pap.package.schema", "error", "package", "requiredFeatures must be array")
                schema_error_found = True
                integrity_package = "FAIL"
                rf = []
            # unique
            if len(set(rf)) != len(rf):
                add_diag("pap.package.schema", "error", "package", "requiredFeatures not unique")
                schema_error_found = True
                integrity_package = "FAIL"
            for f in rf:
                if not isinstance(f, str) or not re.fullmatch(r"pap\.[a-z0-9.-]+", f):
                    add_diag("pap.package.schema", "error", "package", "invalid requiredFeature")
                    schema_error_found = True
                    integrity_package = "FAIL"
            required_features = rf if isinstance(rf, list) else []

        # duplicate ids/paths
        # collect ids
        ids = []
        if isinstance(artifact_entries, list):
            for a in artifact_entries:
                if isinstance(a, dict) and "id" in a:
                    ids.append(a["id"])
        if isinstance(input_entries, list):
            for it in input_entries:
                if isinstance(it, dict) and "id" in it:
                    ids.append(it["id"])
        if isinstance(source_entries, list):
            for s in source_entries:
                if isinstance(s, dict) and "id" in s:
                    ids.append(s["id"])
        # checkSpecs ids? not in same duplicate set? RFC duplicate identifier detection maybe includes checkSpec? We'll skip.
        if len(ids) != len(set(ids)):
            add_diag("pap.package.duplicate-id", "error", "package", "duplicate id")
            duplicate_id_found = True
            integrity_package = "FAIL"

        # declared paths duplicate/case collision
        paths = [p for p, _ in declared_paths]
        lower = [p.lower() for p in paths]
        if len(paths) != len(set(paths)) or len(lower) != len(set(lower)):
            add_diag("pap.package.path-duplicate", "error", "package", "duplicate or case-colliding path")
            path_duplicate_found = True
            integrity_package = "FAIL"

        # manifest self-reference
        if "assurance-package.json" in paths:
            add_diag("pap.package.manifest-self-reference", "error", "package", "manifest self reference")
            integrity_package = "FAIL"

        # path invalid already added during validation

        # compatibility diagnostics
        if isinstance(pv, str) and re.fullmatch(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", pv):
            if pv == "0.1":
                pass
            else:
                major, minor = pv.split(".")
                if major == "0" and int(minor) > 1:
                    add_diag("pap.compat.minor-newer", "warning", "package", "newer minor version")
                else:
                    add_diag("pap.compat.version-unsupported", "warning", "package", "unsupported version")

        # extensions diagnostics
        if isinstance(extensions_obj, dict):
            for k, v in extensions_obj.items():
                if isinstance(v, dict) and v.get("critical") is True:
                    add_diag("pap.extension.critical-unsupported", "error" if False else "warning", "package", f"critical extension unsupported: {k}")
                elif isinstance(v, dict) and v.get("critical") is False:
                    add_diag("pap.extension.ignored", "warning", "package", f"ignored extension: {k}")
                    limitations.append("pap.extension.ignored")

        # required features diagnostics
        if isinstance(required_features, list):
            for f in required_features:
                add_diag("pap.feature.unsupported", "warning", "package", f"unsupported feature: {f}")

    # If manifest parse failed, integrity_package already FAIL.

    # Undeclared file scan
    declared_path_set = set(p for p, _ in declared_paths)
    # signature envelopes conventional
    try:
        all_files = []
        for dirpath, dirnames, filenames in os.walk(root):
            # avoid following symlinks
            dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
            for fn in filenames:
                full = Path(dirpath) / fn
                if full.is_symlink():
                    continue
                if not full.is_file():
                    continue
                rel = full.relative_to(root).as_posix()
                all_files.append(rel)
        # budget
        if len(all_files) > 100000:
            scan_complete = False
            add_diag("pap.package.undeclared-scan-incomplete", "warning", "package", "scan budget exceeded")
            limitations.append("pap.package.undeclared-scan-incomplete")
        else:
            for rel in all_files:
                if rel == "assurance-package.json":
                    continue
                if rel in declared_path_set:
                    continue
                # signature envelope conventional
                if rel.startswith("signatures/") and rel.endswith(".dsse.json"):
                    continue
                # undeclared
                add_diag("pap.package.undeclared-file", "warning", "package", f"undeclared file: {rel}")
    except Exception as e:
        scan_complete = False
        add_diag("pap.package.undeclared-scan-incomplete", "warning", "package", str(e))
        limitations.append("pap.package.undeclared-scan-incomplete")

    # Read declared payloads
    # We'll read artifacts, sources, inputs, claims in order
    # track limit exceeded
    limit_exceeded_payload = False
    total_bytes_read = 0

    # helper to read a declared file
    def read_declared(rel, class_name):
        nonlocal total_bytes_read, limit_exceeded_payload
        # returns (bytes_or_None, diag_code_or_None)
        # path grammar already validated; if invalid, skip
        if not _path_grammar_ok(rel):
            return None, "pap.package.path-invalid"
        target = _safe_resolve(root, rel)
        if target is None:
            return None, "pap.package.path-escape"
        if target.is_symlink():
            return None, "pap.package.symlink"
        if not target.exists():
            return None, "pap.package.declared-file-missing"
        if not target.is_file():
            return None, "pap.package.non-regular"
        size = target.stat().st_size
        # per-file limit
        if size > FILE_BYTES_LIMIT:
            limit_exceeded_payload = True
            return None, "pap.package.limit-exceeded"
        # total limit
        if total_bytes_read + size > TOTAL_PAYLOAD_BYTES_LIMIT:
            limit_exceeded_payload = True
            return None, "pap.package.limit-exceeded"
        try:
            data = target.read_bytes()
        except Exception:
            return None, "pap.package.io"
        total_bytes_read += len(data)
        return data, None

    # artifacts processing
    artifacts_computed = []  # list of {id, declared, computed}
    artifact_bytes_map = {}
    if isinstance(artifact_entries, list) and not manifest_parse_failed:
        # count limit
        if len(artifact_entries) > PAYLOAD_FILES_LIMIT:
            limit_exceeded_payload = True
            add_diag("pap.package.limit-exceeded", "error", "package", "payload files limit exceeded")
            # read none
            for a in artifact_entries:
                if isinstance(a, dict):
                    artifacts_computed.append({"id": a.get("id"), "declared": a.get("digest"), "computed": None})
        else:
            for a in artifact_entries:
                if not isinstance(a, dict):
                    continue
                aid = a.get("id")
                path = a.get("path")
                declared_digest = a.get("digest")
                declared_bytes = a.get("bytes")
                data, err = read_declared(path, "artifact")
                computed = None
                if err:
                    if err == "pap.package.limit-exceeded":
                        add_diag("pap.package.limit-exceeded", "error", "package", f"limit exceeded reading {path}")
                    elif err == "pap.package.declared-file-missing":
                        add_diag("pap.package.declared-file-missing", "error", "package", f"missing declared file {path}")
                    elif err == "pap.package.symlink":
                        add_diag("pap.package.symlink", "error", "package", f"symlink declared file {path}")
                    elif err == "pap.package.non-regular":
                        add_diag("pap.package.non-regular", "error", "package", f"non-regular declared file {path}")
                    elif err == "pap.package.path-escape":
                        add_diag("pap.package.path-escape", "error", "package", f"path escapes root {path}")
                    elif err == "pap.package.path-invalid":
                        add_diag("pap.package.path-invalid", "error", "package", f"invalid path {path}")
                    else:
                        add_diag("pap.package.io", "error", "package", f"io error reading {path}")
                    # package/artifact integrity fail
                    integrity_package = "FAIL" if err != "pap.package.limit-exceeded" else integrity_package
                    if err != "pap.package.limit-exceeded":
                        integrity_package = "FAIL"
                    integrity_artifacts = "FAIL" if err != "pap.package.limit-exceeded" else integrity_artifacts
                else:
                    computed = sha256_domain("pap.artifact.v1", data)
                    artifact_bytes_map[aid] = (data, computed)
                artifacts_computed.append({"id": aid, "declared": declared_digest, "computed": computed})
                # compare for integrity.artifacts
                # determine after all

    # Determine integrity.artifacts status
    # If manifest parse failed or schema invalid -> NOT_EVALUATED
    if manifest_parse_failed or unknown_field_found or schema_error_found:
        integrity_artifacts = "NOT_EVALUATED"
    else:
        # check all artifacts read and match
        if limit_exceeded_payload:
            # if any artifact unread due to limit -> NOT_EVALUATED
            if any(ac["computed"] is None for ac in artifacts_computed):
                integrity_artifacts = "NOT_EVALUATED"
        # compare
        fail = False
        for a, ac in zip(artifact_entries, artifacts_computed):
            if not isinstance(a, dict):
                continue
            if ac["computed"] is None:
                # missing/limit -> fail or not evaluated handled
                if not limit_exceeded_payload:
                    fail = True
                continue
            if ac["computed"] != a.get("digest"):
                fail = True
            if isinstance(a.get("bytes"), int) and not isinstance(a.get("bytes"), bool):
                if len(artifact_bytes_map.get(a.get("id"), (b"",))[0]) != a["bytes"]:
                    fail = True
        if not limit_exceeded_payload and any(ac["computed"] is None for ac in artifacts_computed):
            # missing declared file -> fail
            fail = True
        if fail:
            integrity_artifacts = "FAIL"
        else:
            if len(artifacts_computed) == 0:
                integrity_artifacts = "NOT_EVALUATED"
            else:
                integrity_artifacts = "PASS"

    if (path_invalid_found or path_duplicate_found or duplicate_id_found) and integrity_artifacts != "NOT_EVALUATED":
        integrity_artifacts = "FAIL"

    # sources processing
    sources_computed = []
    source_bytes_map = {}
    if isinstance(source_entries, list) and not manifest_parse_failed:
        if len(source_entries) > PAYLOAD_FILES_LIMIT:
            limit_exceeded_payload = True
            add_diag("pap.package.limit-exceeded", "error", "package", "payload files limit exceeded")
            for s in source_entries:
                if isinstance(s, dict):
                    sources_computed.append({"id": s.get("id"), "declared": s.get("digest"), "computed": None})
        else:
            for s in source_entries:
                if not isinstance(s, dict):
                    continue
                sid = s.get("id")
                path = s.get("path")
                declared_digest = s.get("digest")
                if not path:
                    # referenced-only
                    sources_computed.append({"id": sid, "declared": declared_digest, "computed": None})
                    continue
                data, err = read_declared(path, "source")
                computed = None
                if err:
                    if err == "pap.package.limit-exceeded":
                        add_diag("pap.package.limit-exceeded", "error", "package", f"limit exceeded reading {path}")
                    elif err == "pap.package.declared-file-missing":
                        add_diag("pap.package.declared-file-missing", "error", "package", f"missing declared file {path}")
                    elif err == "pap.package.symlink":
                        add_diag("pap.package.symlink", "error", "package", f"symlink declared file {path}")
                    elif err == "pap.package.non-regular":
                        add_diag("pap.package.non-regular", "error", "package", f"non-regular declared file {path}")
                    elif err == "pap.package.path-escape":
                        add_diag("pap.package.path-escape", "error", "package", f"path escapes root {path}")
                    elif err == "pap.package.path-invalid":
                        add_diag("pap.package.path-invalid", "error", "package", f"invalid path {path}")
                    else:
                        add_diag("pap.package.io", "error", "package", f"io error reading {path}")
                    if err != "pap.package.limit-exceeded":
                        integrity_package = "FAIL"
                else:
                    computed = sha256_domain("pap.source.raw.v1", data)
                    source_bytes_map[sid] = (data, computed)
                sources_computed.append({"id": sid, "declared": declared_digest, "computed": computed})

    # sources.integrity status
    if manifest_parse_failed or unknown_field_found or schema_error_found:
        sources_integrity = "NOT_EVALUATED"
    else:
        if len(source_entries) == 0:
            sources_integrity = "NOT_EVALUATED"
        else:
            fail = False
            unavailable = False
            for s, sc in zip(source_entries, sources_computed):
                if not isinstance(s, dict):
                    continue
                if s.get("path"):
                    if sc["computed"] is None:
                        if not limit_exceeded_payload:
                            fail = True
                    else:
                        if sc["computed"] != s.get("digest"):
                            fail = True
                else:
                    # referenced-only
                    unavailable = True
            if fail:
                sources_integrity = "FAIL"
            elif limit_exceeded_payload and any(sc["computed"] is None and s.get("path") for s, sc in zip(source_entries, sources_computed)):
                sources_integrity = "NOT_EVALUATED"
            elif unavailable:
                sources_integrity = "UNAVAILABLE"
            else:
                sources_integrity = "PASS"

    if path_invalid_found and sources_integrity not in ("NOT_EVALUATED",):
        sources_integrity = "FAIL"

    # sources.availability
    # required source-dependent checks?
    required_checks_list = []
    for cs in check_specs:
        if isinstance(cs, dict) and cs.get("required", True):
            required_checks_list.append(cs.get("id"))
    required_checks_list = required_checks_list + [c for c in policy_required_checks if c not in required_checks_list]
    source_dependent_required = any(rc in ("pap.check.digest-integrity/1","pap.check.source-quote/1") for rc in required_checks_list)
    if not source_dependent_required:
        sources_availability = "NOT_APPLICABLE"
    else:
        # if any required source lacks snapshot
        missing_snap = False
        for s in source_entries:
            if isinstance(s, dict) and not s.get("path"):
                missing_snap = True
        if missing_snap:
            sources_availability = "UNAVAILABLE"
        else:
            sources_availability = "PASS"

    # inputs processing
    inputs_computed = []
    input_norm_map = {}
    if isinstance(input_entries, list) and not manifest_parse_failed:
        if len(input_entries) > PAYLOAD_FILES_LIMIT:
            limit_exceeded_payload = True
            add_diag("pap.package.limit-exceeded", "error", "package", "payload files limit exceeded")
            for it in input_entries:
                if isinstance(it, dict):
                    inputs_computed.append({"id": it.get("id"), "declared": it.get("digest"), "computed": None})
        else:
            for it in input_entries:
                if not isinstance(it, dict):
                    continue
                iid = it.get("id")
                path = it.get("path")
                declared_digest = it.get("digest")
                norm = it.get("normalization", "lf")
                data, err = read_declared(path, "input")
                computed = None
                if err:
                    if err == "pap.package.limit-exceeded":
                        add_diag("pap.package.limit-exceeded", "error", "package", f"limit exceeded reading {path}")
                    elif err == "pap.package.declared-file-missing":
                        add_diag("pap.package.declared-file-missing", "error", "package", f"missing declared file {path}")
                    elif err == "pap.package.symlink":
                        add_diag("pap.package.symlink", "error", "package", f"symlink declared file {path}")
                    elif err == "pap.package.non-regular":
                        add_diag("pap.package.non-regular", "error", "package", f"non-regular declared file {path}")
                    elif err == "pap.package.path-escape":
                        add_diag("pap.package.path-escape", "error", "package", f"path escapes root {path}")
                    elif err == "pap.package.path-invalid":
                        add_diag("pap.package.path-invalid", "error", "package", f"invalid path {path}")
                    else:
                        add_diag("pap.package.io", "error", "package", f"io error reading {path}")
                    if err != "pap.package.limit-exceeded":
                        integrity_package = "FAIL"
                else:
                    nb = normalize_input_bytes(data, norm)
                    computed = input_file_digest(path, nb)
                    input_norm_map[iid] = (path, nb, computed)
                inputs_computed.append({"id": iid, "declared": declared_digest, "computed": computed})

    # input digest mismatch affects package integrity
    if not manifest_parse_failed:
        for it, ic in zip(input_entries, inputs_computed):
            if not isinstance(it, dict):
                continue
            if ic["computed"] is None:
                if not limit_exceeded_payload:
                    # missing -> fail
                    integrity_package = "FAIL"
            else:
                if ic["computed"] != it.get("digest"):
                    add_diag("pap.integrity.input-mismatch", "error", "package", "input digest mismatch")
                    integrity_package = "FAIL"

    # normalized input digest
    normalized_input_digest = None
    if input_entries:
        # compute set digest if all read
        recs = []
        all_read = True
        for it in input_entries:
            if not isinstance(it, dict):
                continue
            iid = it.get("id")
            path = it.get("path")
            norm = it.get("normalization", "lf")
            # find bytes
            # re-read not needed; use input_norm_map
            if iid in input_norm_map:
                p, nb, _ = input_norm_map[iid]
                recs.append((path, nb))
            else:
                all_read = False
        if all_read and recs:
            normalized_input_digest = normalized_input_set_digest(recs)
        # compare with build.normalizedInputDigest
        build = manifest_obj.get("build", {}) if isinstance(manifest_obj, dict) else {}
        if isinstance(build, dict) and build.get("normalizedInputDigest"):
            if normalized_input_digest is not None and normalized_input_digest != build["normalizedInputDigest"]:
                add_diag("pap.integrity.input-mismatch", "error", "package", "normalized input digest mismatch")
                integrity_package = "FAIL"
    # if no inputs, normalized_input_digest None

    # claim files processing
    claim_files_present = {}
    if isinstance(claims_declared, dict) and not manifest_parse_failed:
        for kind, ref in claims_declared.items():
            if not isinstance(ref, dict):
                continue
            path = ref.get("path")
            declared_digest = ref.get("digest")
            data, err = read_declared(path, "claim")
            if err:
                if err == "pap.package.declared-file-missing":
                    add_diag("pap.package.declared-file-missing", "error", "package", f"missing declared claim {path}")
                elif err == "pap.package.limit-exceeded":
                    add_diag("pap.package.limit-exceeded", "error", "package", f"limit exceeded reading {path}")
                else:
                    add_diag("pap.package.io", "error", "package", f"io error reading claim {path}")
                if err != "pap.package.limit-exceeded":
                    integrity_package = "FAIL"
                else:
                    limit_exceeded_payload = True
                claim_files_present[kind] = None
                continue
            computed_cd = sha256_domain("pap.claims.v1", data)
            if computed_cd != declared_digest:
                add_diag("pap.integrity.claim-mismatch", "error", "package", f"claim digest mismatch {path}")
                integrity_package = "FAIL"
                claim_files_present[kind] = None
                continue
            # parse strict
            try:
                cobj, _ = parse_strict(data, JSON_NESTING_LIMIT, JSON_STRING_LIMIT)
            except JCSError as e:
                msg = str(e)
                if "limit" in msg or "depth" in msg or "size" in msg:
                    add_diag("pap.package.limit-exceeded", "error", "package", msg)
                    limit_exceeded_payload = True
                else:
                    add_diag("pap.package.claim-invalid", "error", "package", msg)
                    claim_invalid = True
                    integrity_package = "FAIL"
                claim_files_present[kind] = None
                continue
            except Exception as e:
                add_diag("pap.package.claim-invalid", "error", "package", str(e))
                claim_invalid = True
                integrity_package = "FAIL"
                claim_files_present[kind] = None
                continue
            # papClaimsVersion check
            if not isinstance(cobj, dict):
                add_diag("pap.package.claim-invalid", "error", "package", "claim not object")
                claim_invalid = True
                integrity_package = "FAIL"
                claim_files_present[kind] = None
                continue
            v = cobj.get("papClaimsVersion")
            if v is None:
                add_diag("pap.package.claim-invalid", "error", "package", "missing papClaimsVersion")
                claim_invalid = True
                integrity_package = "FAIL"
                claim_files_present[kind] = None
                continue
            if v != "0.1":
                add_diag("pap.claim.unsupported-version", "warning", "package", f"unsupported claim version {v}")
                claim_files_present[kind] = ("unsupported", cobj)
                continue
            claim_files_present[kind] = ("ok", cobj)

    # integrity.package final adjustments
    if manifest_parse_failed:
        integrity_package = "FAIL"
    # if limit exceeded on manifest already FAIL
    # if schema errors etc already FAIL
    # if any declared file missing for artifacts/sources/inputs/claims already set FAIL
    # if limit_exceeded_payload affected inputs, integrity.package may be NOT_EVALUATED if no FAIL? RFC: limit on inputs -> package NOT_EVALUATED
    # Determine if integrity.package should be NOT_EVALUATED due to input limit
    # We'll check: if no hard FAIL from schema/missing/invalid but limit_exceeded_payload and input unread
    # Simpler: if integrity_package != 'FAIL' and limit_exceeded_payload and any(ic['computed'] is None for ic in inputs_computed):
    #    integrity_package = 'NOT_EVALUATED'
    # But if manifest invalid, already FAIL.

    # Actually if integrity_package currently 'FAIL' due to missing declared file, keep FAIL.
    # If limit exceeded on inputs only, set NOT_EVALUATED.
    hard_fail = (manifest_parse_failed or unknown_field_found or schema_error_found or
                 path_invalid_found or path_duplicate_found or duplicate_id_found or
                 claim_invalid)
    # also claim digest mismatch sets integrity_package FAIL already; check if 'FAIL'
    if integrity_package == "FAIL" and not hard_fail and not manifest_parse_failed:
        # could be due to missing files etc; keep FAIL
        pass

    # If limit exceeded affected inputs and no hard fail, set NOT_EVALUATED
    if limit_exceeded_payload and integrity_package != "FAIL" and any((isinstance(ic, dict) and ic.get("computed") is None) for ic in inputs_computed):
        integrity_package = "NOT_EVALUATED"

    # If manifest parsed but no inputs and no fail, keep PASS if not already FAIL
    if not manifest_parse_failed and integrity_package not in ("FAIL", "NOT_EVALUATED"):
        # if there were missing declared files, already FAIL
        integrity_package = "PASS"

    # If manifest parse failed, package identity null, pap_version maybe null
    if manifest_parse_failed:
        package_identity = None
        pap_version = None

    # extension closure identity from profile
    ext_closure = None
    if isinstance(profile_obj, dict) and profile_obj.get("closureDigest"):
        ext_closure = profile_obj["closureDigest"]

    # required checks outcomes
    # determine compatibility
    newer_minor = False
    version_unsupported = False
    if isinstance(pap_version, str):
        if pap_version != "0.1":
            major, minor = pap_version.split(".")
            if major == "0" and int(minor) > 1:
                newer_minor = True
            else:
                version_unsupported = True

    # map manifest check specs to required flags
    declared_checks = []  # list of (id, required)
    for cs in check_specs:
        if isinstance(cs, dict) and isinstance(cs.get("id"), str):
            declared_checks.append((cs["id"], cs.get("required", True)))

    # policy-only required checks
    for pc in policy_required_checks:
        if pc not in [d[0] for d in declared_checks]:
            declared_checks.append((pc, True))

    # determine outcome for each declared check
    check_outcomes = {}  # id -> outcome
    for cid, req in declared_checks:
        if cid not in KNOWN_CHECKS:
            check_outcomes[cid] = "UNSUPPORTED"
        elif newer_minor:
            check_outcomes[cid] = "NOT_EVALUATED"
        elif version_unsupported:
            check_outcomes[cid] = "NOT_EVALUATED"
        elif manifest_parse_failed or integrity_package in ("FAIL", "NOT_EVALUATED") or claim_invalid:
            check_outcomes[cid] = "NOT_EVALUATED"
        elif limit_exceeded_payload:
            check_outcomes[cid] = "NOT_EVALUATED"
        else:
            # check spec known but not implemented -> UNSUPPORTED
            check_outcomes[cid] = "UNSUPPORTED"

    # Actually for a valid package, known checks not implemented -> UNSUPPORTED. Good.

    # required set
    required_checks = [cid for cid, req in declared_checks if req]
    # unique preserve order
    seen = set()
    req_checks_unique = []
    for c in required_checks:
        if c not in seen:
            seen.add(c)
            req_checks_unique.append(c)
    required_checks = req_checks_unique

    # required dimensions implied
    implied_dims = set()
    for rc in required_checks:
        if rc == "pap.check.digest-integrity/1":
            implied_dims.update(["integrity", "checks"])
        elif rc == "pap.check.source-quote/1":
            implied_dims.update(["sources", "checks"])
        elif rc == "pap.check.relation-consistency/1":
            implied_dims.update(["checks"])
        else:
            implied_dims.update(["checks"])
    required_dimensions = sorted(set(policy_required_dims) | implied_dims)

    # empty required set diagnostic
    if len(required_checks) == 0 and len(required_dimensions) == 0:
        add_diag("pap.package.empty-check-specs", "warning", "package", "no required checks")

    # diagnostics for check outcomes
    for cid, req in declared_checks:
        if req:
            oc = check_outcomes.get(cid)
            if oc == "UNSUPPORTED":
                add_diag("pap.check.unsupported", "warning", "check", f"unsupported check {cid}")
            if oc == "NOT_EVALUATED":
                # add not-evaluated diagnostic for required checks
                if req:
                    add_diag("pap.check.not-evaluated", "warning", "check", f"check not evaluated {cid}")

    # critical extension diagnostic already added as warning; ensure code
    # (we added pap.extension.critical-unsupported as warning above)

    # build dimensions.checks.results
    # all declared checks (not just required) included; policy-only appended
    results_list = []
    for cid, req in declared_checks:
        results_list.append({"checkId": cid, "outcome": check_outcomes.get(cid, "NOT_EVALUATED"), "required": bool(req)})

    # dimensions
    # integrity.artifacts status maybe adjust if limit
    if limit_exceeded_payload and integrity_artifacts == "PASS":
        # if any artifact unread, NOT_EVALUATED
        if any(ac["computed"] is None for ac in artifacts_computed):
            integrity_artifacts = "NOT_EVALUATED"

    dimensions = {
        "integrity": {
            "package": integrity_package,
            "artifacts": integrity_artifacts,
        },
        "sources": {
            "integrity": sources_integrity,
            "availability": sources_availability,
        },
        "signature": {
            "validity": "NOT_APPLICABLE",
        },
        "trust": {
            "signerIdentity": "NOT_APPLICABLE",
            "policyDecision": "NOT_EVALUATED" if trust_policy_path else "NOT_EVALUATED",
            "checkerRecognition": "NOT_EVALUATED" if trust_policy_path else "NOT_EVALUATED",
            "profileRecognition": ("NOT_EVALUATED" if (trust_policy_path and profile_obj) else "NOT_APPLICABLE" if not profile_obj else "NOT_EVALUATED"),
        },
        "checks": {
            "results": results_list,
        },
        "humanReview": {
            "status": "NOT_APPLICABLE",
        },
        "semanticTruth": "NOT_EVALUATED",
        "legalEnforceability": "NOT_EVALUATED",
    }
    if trust_policy_path is None:
        dimensions["trust"]["policyDecision"] = "NOT_EVALUATED"
        dimensions["trust"]["checkerRecognition"] = "NOT_EVALUATED"
        dimensions["trust"]["profileRecognition"] = "NOT_APPLICABLE" if not profile_obj else "NOT_EVALUATED"

    # policy state stale -> maybe trust policyDecision STALE? We set policy_state. If stale, set policyDecision STALE.
    if trust_policy_path and policy_state == "STALE":
        dimensions["trust"]["policyDecision"] = "STALE"

    # Add policy-absent diagnostic if no policy
    if trust_policy_path is None:
        add_diag("pap.trust.policy-absent", "info", "package", "no trust policy supplied")

    # coverage
    # decided helper
    def is_decided_dim(dim_name):
        if dim_name == "integrity":
            return dimensions["integrity"]["package"] in ("PASS", "FAIL") and dimensions["integrity"]["artifacts"] in ("PASS", "FAIL")
        if dim_name == "integrity.package":
            return dimensions["integrity"]["package"] in ("PASS", "FAIL")
        if dim_name == "integrity.artifacts":
            return dimensions["integrity"]["artifacts"] in ("PASS", "FAIL")
        if dim_name == "sources":
            si = dimensions["sources"]["integrity"]
            sa = dimensions["sources"]["availability"]
            si_dec = si in ("PASS", "FAIL", "UNAVAILABLE")  # UNAVAILABLE not decided? Wait list says UNAVAILABLE not decided. Fix below.
            return False
        return False

    # We'll implement decided more carefully:
    def decided_status(dim_name):
        if dim_name == "integrity":
            return dimensions["integrity"]["package"] in ("PASS", "FAIL") and dimensions["integrity"]["artifacts"] in ("PASS", "FAIL")
        if dim_name == "integrity.package":
            return dimensions["integrity"]["package"] in ("PASS", "FAIL")
        if dim_name == "integrity.artifacts":
            return dimensions["integrity"]["artifacts"] in ("PASS", "FAIL")
        if dim_name == "sources":
            si = dimensions["sources"]["integrity"]
            sa = dimensions["sources"]["availability"]
            # both decided
            si_dec = si in ("PASS", "FAIL")  # UNAVAILABLE not decided
            sa_dec = sa in ("PASS", "NOT_APPLICABLE")  # UNAVAILABLE not decided
            return si_dec and sa_dec
        if dim_name == "sources.integrity":
            return dimensions["sources"]["integrity"] in ("PASS", "FAIL")
        if dim_name == "sources.availability":
            return dimensions["sources"]["availability"] in ("PASS", "NOT_APPLICABLE")
        if dim_name == "signature":
            return dimensions["signature"]["validity"] in ("VALID", "INVALID", "NOT_APPLICABLE")
        if dim_name == "signature.validity":
            return dimensions["signature"]["validity"] in ("VALID", "INVALID", "NOT_APPLICABLE")
        if dim_name == "trust":
            t = dimensions["trust"]
            # all four decided
            def dec(field, val):
                if field == "signerIdentity":
                    return val in ("TRUSTED", "UNTRUSTED", "NOT_APPLICABLE")
                if field == "policyDecision":
                    return val in ("ACCEPTED", "REJECTED", "STALE")
                if field in ("checkerRecognition", "profileRecognition"):
                    return val in ("PASS", "UNTRUSTED", "NOT_APPLICABLE")
                return False
            return all(dec(f, t[f]) for f in ("signerIdentity","policyDecision","checkerRecognition","profileRecognition"))
        if dim_name == "trust.signerIdentity":
            return dimensions["trust"]["signerIdentity"] in ("TRUSTED", "UNTRUSTED", "NOT_APPLICABLE")
        if dim_name == "trust.policyDecision":
            return dimensions["trust"]["policyDecision"] in ("ACCEPTED", "REJECTED", "STALE")
        if dim_name == "trust.checkerRecognition":
            return dimensions["trust"]["checkerRecognition"] in ("PASS", "UNTRUSTED", "NOT_APPLICABLE")
        if dim_name == "trust.profileRecognition":
            return dimensions["trust"]["profileRecognition"] in ("PASS", "UNTRUSTED", "NOT_APPLICABLE")
        if dim_name == "checks":
            # decided only when every required check PASS or FAIL
            return all(check_outcomes.get(c) in ("PASS", "FAIL") for c in required_checks)
        if dim_name == "humanReview":
            return dimensions["humanReview"]["status"] in ("PASS", "NOT_APPLICABLE")
        return False

    dims_evaluated = sum(1 for d in required_dimensions if decided_status(d))

    checks_passed = sum(1 for c in required_checks if check_outcomes.get(c) == "PASS")
    checks_failed = sum(1 for c in required_checks if check_outcomes.get(c) == "FAIL")
    checks_unsupported = sum(1 for c in required_checks if check_outcomes.get(c) == "UNSUPPORTED")
    checks_not_evaluated = sum(1 for c in required_checks if check_outcomes.get(c) == "NOT_EVALUATED")
    checks_evaluated = checks_passed + checks_failed

    full = (checks_not_evaluated == 0 and checks_unsupported == 0 and
            dims_evaluated == len(required_dimensions) and scan_complete and
            len(required_checks) > 0 and len(required_dimensions) > 0)
    # limit exceeded stops full
    if limit_exceeded_payload:
        full = False

    coverage = {
        "requiredChecks": required_checks,
        "checksEvaluated": checks_evaluated,
        "checksPassed": checks_passed,
        "checksFailed": checks_failed,
        "checksUnsupported": checks_unsupported,
        "checksNotEvaluated": checks_not_evaluated,
        "requiredDimensions": required_dimensions,
        "dimensionsEvaluated": dims_evaluated,
        "full": full,
    }

    # verdict
    # policy stale
    policy_stale = (policy_state == "STALE")
    # required feature unsupported
    feature_unsupported = len(required_features) > 0
    # critical extension unsupported
    critical_ext_unsupported = False
    if isinstance(extensions_obj, dict):
        for k, v in extensions_obj.items():
            if isinstance(v, dict) and v.get("critical") is True:
                critical_ext_unsupported = True

    verdict = None
    # rule 1 FAIL
    if (any(check_outcomes.get(c) == "FAIL" for c in required_checks) or
        integrity_package == "FAIL" or integrity_artifacts == "FAIL" or
        sources_integrity == "FAIL" or claim_invalid):
        verdict = "FAIL"
    # signature invalid required not applicable
    # rule 2 UNTRUSTED (none)
    elif False:
        verdict = "UNTRUSTED"
    # rule 3 UNSUPPORTED
    elif (any(check_outcomes.get(c) == "UNSUPPORTED" for c in required_checks) or
          feature_unsupported or critical_ext_unsupported or
          version_unsupported or newer_minor or
          (version_unsupported)):
        # newer_minor -> UNSUPPORTED per rule 3
        verdict = "UNSUPPORTED"
    # rule 4 INCOMPLETE
    elif (any(required_dimensions and not decided_status(d) for d in required_dimensions) or
          any(check_outcomes.get(c) == "NOT_EVALUATED" for c in required_checks) or
          (len(required_checks) == 0 and len(required_dimensions) == 0) or
          not full or limit_exceeded_payload or policy_stale or
          (required_checks == [] and required_dimensions == [])):
        verdict = "INCOMPLETE"
    # rule 5 NOT_EVALUATED
    elif len(required_checks) > 0 and all(check_outcomes.get(c) == "NOT_EVALUATED" for c in required_checks) and checks_evaluated == 0 and not any(check_outcomes.get(c) in ("PASS","FAIL") for c in required_checks):
        # degenerate
        verdict = "NOT_EVALUATED"
    else:
        # PASS conditions
        if (all(check_outcomes.get(c) == "PASS" for c in required_checks) and
            full and not limit_exceeded_payload):
            verdict = "PASS"
        else:
            verdict = "INCOMPLETE"

    # If newer_minor, rule3 already UNSUPPORTED (set). Good.
    # If empty required set, verdict INCOMPLETE (handled by rule4 empty).

    # Now report dict
    # identities artifacts/sources lists
    identities_artifacts = []
    for a, ac in zip(artifact_entries if isinstance(artifact_entries, list) else [], artifacts_computed):
        if not isinstance(a, dict):
            continue
        identities_artifacts.append({
            "id": a.get("id"),
            "declared": a.get("digest"),
            "computed": ac.get("computed"),
        })
    # if no artifact entries but artifacts_computed exist
    if not identities_artifacts and artifacts_computed:
        for ac in artifacts_computed:
            identities_artifacts.append({"id": ac.get("id"), "declared": ac.get("declared"), "computed": ac.get("computed")})

    identities_sources = []
    for s, sc in zip(source_entries if isinstance(source_entries, list) else [], sources_computed):
        if not isinstance(s, dict):
            continue
        identities_sources.append({
            "id": s.get("id"),
            "declared": s.get("digest"),
            "computed": sc.get("computed"),
        })
    if not identities_sources and sources_computed:
        for sc in sources_computed:
            identities_sources.append({"id": sc.get("id"), "declared": sc.get("declared"), "computed": sc.get("computed")})

    report = {
        "reportVersion": "0.1",
        "verifier": {
            "id": impl_digest and VERIFIER_ID,
            "version": VERIFIER_VERSION,
            "implementationDigest": impl_digest,
            "checkerIdentities": [checker_identity],
        },
        "package": {
            "identity": package_identity,
            "papVersion": pap_version,
            "path": str(root),
        },
        "policy": {
            "id": policy_id,
            "digest": policy_digest,
            "state": policy_state,
            "path": str(Path(trust_policy_path).resolve()) if trust_policy_path else None,
        },
        "evaluatedAt": evaluated_at,
        "identities": {
            "packageIdentity": package_identity,
            "artifacts": identities_artifacts,
            "sources": identities_sources,
            "normalizedInputDigest": normalized_input_digest,
            "extensionClosureDigest": ext_closure,
            "checkerIdentity": checker_identity,
            "verificationRecordIdentity": "sha256:" + "0" * 64,
        },
        "dimensions": dimensions,
        "checks": [],
        "coverage": coverage,
        "limitations": limitations,
        "verdict": verdict,
        "diagnostics": diagnostics,
    }

    # compute verification record identity
    # build identity form
    form = json.loads(json.dumps(report))
    # remove excluded fields
    form.pop("evaluatedAt", None)
    form.pop("durationMs", None)
    if isinstance(form.get("package"), dict):
        form["package"].pop("path", None)
    if isinstance(form.get("policy"), dict):
        form["policy"].pop("path", None)
    form.pop("producerClaims", None)
    # diagnostics message removal
    for d in form.get("diagnostics", []):
        if isinstance(d, dict):
            d.pop("message", None)
    for c in form.get("checks", []):
        if isinstance(c, dict):
            for dd in c.get("diagnostics", []):
                if isinstance(dd, dict):
                    dd.pop("message", None)
            for w in c.get("witnesses", []):
                if isinstance(w, dict):
                    w.pop("quoteBase64", None)
    # placeholder already set
    form["identities"]["verificationRecordIdentity"] = "sha256:" + "0" * 64
    try:
        canon = canonicalize(form)
        vri = sha256_domain("pap.report.v1", canon.encode("utf-8"))
    except Exception:
        vri = "sha256:" + "0" * 64
    report["identities"]["verificationRecordIdentity"] = vri

    return report, verdict
