import argparse
import json
import sys
from pathlib import Path

from .verifier import verify, UsageError, PackageNotFound


def _exit_code_for_verdict(verdict):
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 2, "NOT_EVALUATED": 2,
            "UNTRUSTED": 3, "UNSUPPORTED": 4}.get(verdict, 70)


def _make_parser():
    p = argparse.ArgumentParser(prog="pap")
    p.add_argument("package")
    p.add_argument("--trust-policy", dest="trust_policy", default=None)
    p.add_argument("--format", dest="fmt", default="json", choices=["json", "text"])
    p.add_argument("--now", dest="now", default=None)
    return p


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "verify":
        argv = argv[1:]
    parser = _make_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 64

    try:
        report, verdict = verify(args.package, now_str=args.now, trust_policy_path=args.trust_policy)
    except PackageNotFound as e:
        sys.stderr.write(f"pap: pap.package.not-found: {e}\n")
        return 74
    except UsageError as e:
        sys.stderr.write(f"pap: {e}\n")
        return 64
    except Exception as e:
        sys.stderr.write(f"pap: pap.internal.error: {e}\n")
        return 70

    if args.fmt == "json":
        sys.stdout.write(json.dumps(report, separators=(",", ":"), ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(f"verdict: {verdict}\n")
    return _exit_code_for_verdict(verdict)


if __name__ == "__main__":
    sys.exit(main())
