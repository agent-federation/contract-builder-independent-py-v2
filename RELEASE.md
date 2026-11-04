# PAP Phase 2a experimental — Python release

- package: `pap-verifier` `0.1.0a2`; module `pap_verifier`
- experiment: `PAP-PY-P2A-003`; Gate 3 result commit: `58f368c`
- scope: Phase 2a only; not full PAP/Tier B conformance
- license: MIT

## Build

```bash
python3 -m build
```

## Usage

```bash
PYTHONPATH=. python3 -m pap_verifier verify <package> --format json
```

## Evidence

- 19/19 full + 36/36 identity, zero comparison findings;
- external Gate 3 audit: APPROVED UNCONDITIONALLY (Phase 2a);
- `pyproject.toml` is in the checker closure, so this metadata release has a new checker identity;
  the Gate 3 tag remains `pap-py-p2a-003-result`.
