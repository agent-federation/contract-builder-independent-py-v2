# PAP v0.1 conformance corpus

This directory is the static corpus from RFC §12. Each `F<NN>-<slug>/` directory
is a complete package copy; nothing is generated or mutated at test time.

- `base/` — the Appendix F package. Its package identity, artifact/source/quote,
  input and claim digests are the Appendix E.1/E.2 literals.
- `F01-…`–`F61-…` — one package per normative case. A case differs from `base/`
  only in the defect or variation it names.
- `trust-policy/` — the fixed Appendix B policies. `invalid.json` is intentionally
  schema-invalid; `relations-only-lowered.json` is the F61 policy.
- `signatures/` — shared DSSE envelopes. The keys are test fixtures; no private
  key is committed. `trusted.dsse.json` and `unknown.dsse.json` are signed over
  the base canonical manifest; `invalid.dsse.json` has one corrupted signature.
- `cases.json` — the case index consumed by
  `pap/tests/conformance.test.ts`.

Run the corpus:

```bash
bun test pap/tests/conformance.test.ts
```

The harness runs each `command` (argv after `pap`) with the case directory as cwd,
a fixed `--now`, a hostile `TZ`/`LC_ALL`, a producer-free `PATH` with sentinel
`bun`/`node`/`contract-builder` shims, and asserts the projection in
`cases.json`: exit code, verdict, constrained dimensions, check outcomes,
diagnostic and limitation code sets, coverage, effective limits, identity
relations, Appendix C schema validity, JCS bytes and deterministic reruns.

## Limit cases

`F52` and `F61` exercise `fileBytes: 64`. Files under `artifacts/`, `sources/` and
`inputs/` are bounded by `fileBytes`/`totalPayloadBytes`/`payloadFiles`; claim
files are bounded by the JSON document limits. A limit that makes a required
check unevaluable stops the required check set; optional checks that do not need
the limited class may still run. No limit can produce `PASS`: both cases are
`INCOMPLETE` with `coverage.full: false`.

## Matrix note

`F46` and `F59` complete a failing relation check and therefore report
`coverage.full: true`: RFC §7.5 counts an evaluated `FAIL` as evaluated. This was
confirmed by the maintainer on PR #64 and the RFC matrix rows were updated to
match; the verdict remains `FAIL`.
