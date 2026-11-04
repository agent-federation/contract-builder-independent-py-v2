# RFC: Portable Assurance Package v0.1 and an independent verifier CLI

**Status:** accepted by the maintainer on 2026-11-02. D1–D12 are accepted and recorded in §16;
OD-1–OD-7 are accepted as recommended in the Gate 1 audit. Acceptance covers the v0.1
specification as written: items explicitly deferred or outside v0.1 remain deferred or outside
scope, and acceptance does not settle every possible extension or future decision.
**Issue:** [#44](https://github.com/agent-federation/contract-builder/issues/44) — «Specify
Portable Assurance Package v0.1 and independent verifier CLI».
**Roadmap:** [#43](https://github.com/agent-federation/contract-builder/issues/43) Phase 1.
**Baseline:** `f1ddcf7` (main after #46).
**Document version:** 0.1
**Gate 1 audit:** [`pap-v0.1-gate1-decision-audit.md`](pap-v0.1-gate1-decision-audit.md) reviews
D1–D12 and every §13.8 area. Its recommendations were accepted by the maintainer on 2026-11-02;
§16 and the decision record on #57 are authoritative. A Gate 1 PASS records specification
readiness for independent implementation only; it is not Gate 3.
**Implementation status:** Phase 2 verifier implementation is merged into `main` via PR #64 and
available under `pap/`; independent interoperability validation remains pending. Gate 0 is recorded
COMPLETE on #43.
**Conformance status:** Gate 3 is **OPEN**; no cross-implementation agreement or independent
verification is claimed.

**Related:** [`docs/architecture/build-identity.md`](build-identity.md) (implemented
`inputDigest`), [`docs/architecture/provenance-hardening-rfc.md`](provenance-hardening-rfc.md)
(accepted source digest and paragraph locators, not yet implemented),
[`docs/architecture/engine-public-contract.md`](engine-public-contract.md) §3.1, §6, §8, §10,
§13, and issues [#35](https://github.com/agent-federation/contract-builder/issues/35),
[#36](https://github.com/agent-federation/contract-builder/issues/36),
[#37](https://github.com/agent-federation/contract-builder/issues/37),
[#38](https://github.com/agent-federation/contract-builder/issues/38),
[#41](https://github.com/agent-federation/contract-builder/issues/41).

> **Reading statuses.**
> `accepted` — recorded as accepted by the maintainer in the decision register (§16).
> `proposed` — a recommendation for maintainer review, not accepted.
> `directed` — already accepted in an existing decision record and merely restated here.
> `deferred` — deliberately outside v0.1, with a condition to revisit. No choice is marked
> accepted on the author's own judgment.

---


## 1. Summary

A recipient of a normative artifact should be able to answer four different questions without
trusting the producer, contacting it, or running its code:

1. Are the bytes I received the bytes the package declares?
2. Do the packaged sources and the artifact's provenance claims mechanically agree?
3. Who signed the package, and does my local trust policy accept that signer?
4. What exactly was checked, what failed, and what remains unsupported or unverifiable?

Today Contract Builder can build a specification and expose a deterministic `inputDigest`
([#42](https://github.com/agent-federation/contract-builder/issues/42)), but there is no
portable package format, no independent consumer contract, and no way to separate package
integrity from producer claims or signer trust. A package assembled by one party is, for a
different party, hostile input until proven otherwise.

This RFC specifies **Portable Assurance Package v0.1** and the contract for an **independent
open-source verifier CLI**. It is the accepted v0.1 specification: it defines formats, identities,
status semantics, checks, threats and conformance cases precisely enough for two independent
implementations, and it deliberately does not implement either side.

| Area | Accepted v0.1 specification | Section |
|---|---|---|
| Package | directory with fixed `assurance-package.json`, declared artifacts, optional input/source snapshots, untrusted claims, optional DSSE signatures | §4 |
| Canonical form | RFC 8785 JCS over an I-JSON subset; SHA-256 with domain separation | §5 |
| Identities | package, artifact, raw source, normalized input, extension closure, checker, verification record — kept distinct | §5 |
| Trust | explicit local offline trust policy; signature validity, signer identity, policy decision are separate dimensions | §6 |
| Results | independent dimensions and statuses, no single `verified` boolean; coverage and limitations always reported | §7 |
| Checks | three bounded mechanical checks: digest integrity, source/quote span, relation consistency | §8 |
| CLI | `pap verify`, `pap inspect`, `pap explain`; explicit exit codes; machine-readable report | §9 |
| Threats | directory-only parsing, no symlinks, ASCII paths, resource limits, no producer or profile execution | §10 |
| Signatures | optional DSSE/Ed25519 adapter; in-toto mapping; Sigstore/SCITT/OCI deferred | §11 |
| Conformance | 61 normative fixture cases with expected dimensions, verdict, exit code and diagnostics | §12 |
| Independence | second implementation from this RFC, schemas and vectors only; first demo unsigned | §13 |

The package is a **transport and evidence envelope**, not the engine's internal IR. It carries
artifacts, optional inputs and sources, provenance/relation claims, producer diagnostics and
optional signatures. The verifier never renders Markdown, never imports Contract Builder, never
loads a producer profile and never executes package-supplied code. A valid signature does not
establish semantic truth, legal enforceability or signer authority; those remain separate
dimensions that v0.1 never evaluates.

### 1.1 Decisions at a glance

All rows are `accepted`; §16 records alternatives, rationale and consequences.

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Directory-only packages in v0.1; archive transport deferred | adopt |
| D2 | Canonical JSON is RFC 8785 JCS over an I-JSON subset (integers only) | adopt |
| D3 | SHA-256 with explicit domain separation; no algorithm agility in v0.1 | adopt |
| D4 | Source snapshots optional in format, required for a source-dependent `PASS` | adopt |
| D5 | Strict core schema plus `extensions` namespace and `requiredFeatures` | adopt |
| D6 | Producer claims and verifier records are separate files, schemas and namespaces | adopt |
| D7 | Independent dimensions with defined statuses; verdict precedence; coverage never collapses | adopt |
| D8 | Trust policy is a local, offline, self-contained input; signatures optional | adopt |
| D9 | Three checks in v0.1: digest integrity, source/quote span, relation consistency | adopt |
| D10 | `pap verify/inspect/explain`, exit codes 0/1/2/3/4, deterministic JSON report | adopt |
| D11 | `papVersion` major.minor; core schema frozen within a major | adopt |
| D12 | Second implementation from the RFC alone; first interop demo unsigned | adopt |

---


## 2. Current state and boundaries (at baseline f1ddcf7)

This section records what the engine does at baseline `f1ddcf7` (`feat: add an independent example
profile and end-to-end fixture (#46)`), the commit this RFC is written against. Every statement
below was checked against that commit, and the source path and line range or the command used is
cited so a reviewer can reproduce it. Where an accepted document and the code disagree, this
section says which one the statement rests on.

The checkout has no tracked file differing from `f1ddcf7`. The commit immediately before it is
`b5e316a` (the provenance-hardening RFC for #45, documentation only); `f1ddcf7` added
`profiles/example/`, `tests/fixtures/example-project*` and `tests/example-profile.test.ts` without
touching `spec/lib/` (verified with `git show f1ddcf7 --numstat`). The engine identities described
here are therefore the same identities the provenance RFC measured at `e8c917f`.

> **Reading the citations.** `path:line` means the behaviour was read there at `f1ddcf7`. Issue
> status was read with `gh issue view` on 2026-11-02. The documentation headers are not a source of
> truth for implementation state: both `docs/architecture/engine-public-contract.md:7` and
> `docs/architecture/m1-implementation-plan.md:7` still say `Implementation status: not started`
> although the M1 PRs have merged and #39 exists to reconcile exactly this drift. Claims in this RFC
> rest on code, tests, merged work and decision records, not on those headers.

### 2.1 What the engine already provides

| Surface | Behaviour at `f1ddcf7` | Verified at | PAP bearing |
|---|---|---|---|
| Build identity result | `BuildResult.identity` has exactly `projectId`, `engineVersion`, `manifestVersion`, `inputDigest`, `extensions[]` (kind/id/version of used profile, adapters, renderer). It is `null` when the build stops before identity; it is never rendered into an artifact. | `spec/lib/identity.ts:29–35`; `spec/lib/build.ts:45–54`, `:195–208`; `docs/architecture/build-identity.md:11–27`; `tests/identity.test.ts:603–609` | The PAP `build` block MAY carry the engine version, manifest version, input digest and extension list as producer claims. PAP's `packageIdentity` is not this value. |
| `inputDigest` | One SHA-256 over the ASCII envelope `contract-builder/input-digest/v1\n` and length-prefixed records in fixed order: canonical manifest; each loaded declared input (declared path, LF-normalized bytes) in manifest order; each loaded source (`id`, adapter id, LF-normalized bytes) in manifest order; profile (`id`, `version`, `profileDigest`); distinct adapters sorted by id; the renderer. Emitted as `sha256:<hex>`. | `spec/lib/identity.ts:358–477` (envelope `:70–71`, framing `:151–164`, digest `:474`); `docs/architecture/build-identity.md:32–50` | A single producer-side build identity. PAP separates package identity, normalized inputs and extension closures (§5); the verifier cannot recompute this digest (Appendix I). |
| Canonical manifest | Object keys are sorted recursively (the build-identity record calls this code-point order), arrays keep declared order and are never sorted, absent optional properties are omitted, `external: true` is preserved. Declared paths stay manifest-relative; the project root is not inserted; there is no insignificant whitespace. | `spec/lib/identity.ts:143–149`, `:1118–1130`; `docs/architecture/build-identity.md:52–62` | PAP defines its own canonical form, RFC 8785 JCS over an I-JSON subset (§5). The engine does not claim JCS, so PAP identities are never computed from the engine's canonical form. |
| LF normalization | Declared text inputs and extension files are UTF-8 decoded (fatal) and `CRLF`/`CR` become `LF`. Source documents follow the same rule when their bytes decode as UTF-8 and contain no NUL; otherwise they are hashed raw (binary fallback). Declared input paths become POSIX and lose a leading `./`. | `spec/lib/identity.ts:124–141`; `docs/architecture/build-identity.md:63–72` | PAP's `normalizedInputDigest` covers packaged inputs only and uses its own domain; PAP's `rawSourceDigest` covers raw bytes separately (§5, Appendix I). |
| Extension closures | Profile closure declared in `profiles/core001/profile.json` (`files`, `dependencies: nunjucks 3.2.4`); adapters and renderers declare an optional `closure: {root, files, dependencies}` where `root` is a locator and is never hashed. `closureDigest` covers declared files sorted by normalized relative path (LF-normalized) plus the complete pinned `bun.lock` closure (name, exact version, integrity). The profile closure is validated before profile modules are imported; an undeclared or unpinned import is `core.extension.unpinned-dependency`. The static import scan is a guard, not a sandbox. | `spec/lib/identity.ts:166–189`, `:344–355`, `:489+`; `profiles/core001/profile.json:119–151`; `spec/lib/extension.ts:1–18`; `spec/lib/build.ts:65–69`, `:342–366`; `docs/architecture/build-identity.md:95–147` | PAP's `extensionClosureDigest` is a new identity under a PAP domain; it is not the engine's `closureDigest`, and PAP never executes profile, adapter or renderer code (§8, §10). |
| Source identity and provenance | A manifest source declares `identity: {document, revision}`; M1 validates exactly those two fields and rebuilds the object. The identity is passed to the adapter. The profile checks only that the first 500 characters of the source contain `"<document> (Rev <revision>)"`. The core binds provenance from profile mappings; the adapter verifies quote location with `#<section>`, `#<section>/table/<column>` or `#<section>/<item>` grammar. | `spec/contract-builder.json:47–53`; `spec/lib/manifest.ts:22–28`, `:383–399`; `spec/lib/ir.ts:188–220`; `profiles/core001/checks/source.ts:11–18`; `spec/lib/provenance.ts:1–71`; `spec/lib/adapters/markdown.ts:31–72`; `spec/lib/source.ts:11–22`; contract §11:1004–1006 | PAP source identity is a raw-byte digest recomputed from an optional snapshot; declared identity metadata is a claim. PAP quote checks use exact byte ranges (§8), not adapter grammar. |
| Diagnostics and exit codes | Diagnostics are collected, never thrown: `{severity: error\|warning\|review, code, file, pointer, message}` in a deterministic order. `BuildResult.exitCode` is 0 when `blockedBy` is null and 1 otherwise; release blocks on error and review; `--strict` promotes warnings; usage errors also exit 1. The contract's exit code 2 for I/O, usage and internal errors is an M2 correction not implemented today. | `spec/lib/diagnostics.ts:1–9`, `:27–46`, `:55–67`, `:90–93`; `spec/lib/build.ts:45–54`, `:250–261`, `:468–486`; `spec/build.ts:113–121`; contract §7.2:762–771; contract §18:1218–1227 | PAP has an independent report and exit-code contract (§7, §9). No PAP code is derived from the engine's `exitCode` or `blockedBy`. |
| CLI shape | One script: `bun spec/build.ts [--mode draft\|release] [--spec <dir>] [--check] [--no-write] [--strict] [--json]`; npm scripts wrap the common cases (`bun run build\|build:release\|check\|test\|typecheck`). `--json` prints a JSON object including `identity` and diagnostics; human output is localized. The contract's `contract-builder validate\|build\|check` surface is a future target, and M1 explicitly does not change the CLI. | `spec/build.ts:16–17`, `:112–149`; `package.json:10–16`; contract §10:930–945; contract §16:1115–1116 | The PAP verifier CLI is a separate executable with its own commands and exit-code contract (§9); it does not reuse the builder CLI's command surface, flags or paths, and its exit codes are defined by §9, not by the builder. |
| CI and tests | CI runs install, typecheck, tests and the artifact check on Bun 1.4.2. Identity behaviour is covered by `tests/identity.test.ts`; the independent example profile by `tests/example-profile.test.ts`; the golden artifact and diagnostics snapshots are asserted. | `.github/workflows/ci.yml:21–31`; `tests/identity.test.ts`; `tests/example-profile.test.ts`; `tests/golden.test.ts` | PAP conformance is defined independently (§12, §13); the engine suite is not PAP conformance. |

The engine's guarantees are conditional and bounded, and PAP must not inherit stronger ones. Byte
determinism holds only for the same `engineVersion`, `inputDigest` and extension identities,
provided every trusted extension honours its deterministic contract; extensions run in-process and
are not sandboxed (`docs/architecture/engine-public-contract.md:807–856`; contract D28:1212).
`inputDigest` is a deterministic fingerprint, not a proof of correctness, security, hermeticity or
trustworthiness (`docs/architecture/build-identity.md:7–9`; `:145–147`). PAP therefore treats
package integrity and build reproducibility as different dimensions (§6, §7).

#### 2.1.1 What the engine does not provide

The negative space matters as much as the positive one. Each absence below was checked by
inspection of `spec/` and `profiles/` (path existence and search, no matches) at `f1ddcf7`; an
absence claim is evidence of a search, not a proof that no such logic exists elsewhere. At
`f1ddcf7` the engine has:

- no package format, no package directory or archive, and no fixed package entry point;
- no standalone verifier product: the build API is internal to this repository, used by the
  CLI and the tests; there is no independently installable consumer;
- no trust policy input, signer identity model, signature verification or DSSE/in-toto handling;
- no source snapshots: sources are read in place and never copied into an output;
- no coverage vocabulary: diagnostics carry severity and a mode-dependent block decision, not
  per-dimension statuses such as `UNAVAILABLE`, `UNSUPPORTED` or `NOT_EVALUATED`;
- no checker identity and no verification-record identity;
- no report schema: `--json` prints `BuildResult` fields, which are engine-internal types;
- no hostile-input contract for a package: no archive, path-traversal, symlink, duplicate-path or
  size-limit rules for untrusted package contents.

Every missing item is specified by this RFC (§4–§13). None of it is inferred from an existing
behaviour: where PAP reuses an engine rule (LF normalization, length-prefixed framing, path
containment as a safety principle), the reuse is stated and the rule is given its own PAP domain.

### 2.2 Accepted but not implemented

The provenance-hardening RFC is the decision record for #4. It was accepted by the maintainer on
2026-11-02 (the provenance RFC's own Q1–Q11 labels, with its Q5 tightened), merged in
`b5e316a`, and states
`Implementation status: not started`
(`docs/architecture/provenance-hardening-rfc.md:3–11`, `:895–919`, `:922–940`). Its
accepted-but-unshipped content is:

| Accepted design item | What it will add | State at `f1ddcf7` |
|---|---|---|
| `sources[].identity.sha256` | 64 lowercase hex characters, SHA-256 over the raw source bytes as read; verified by the core before provenance binding. Mismatch is `core.provenance.digest` in draft and release; absence with mapped provenance is `core.provenance.digest-missing` (draft warning, release and `--strict` block). | Not implemented. `ManifestSource.identity` is typed `{document?, revision?}`, and `validateSources` rebuilds the object with only those two fields, so an added `sha256` member would be dropped silently (`spec/lib/manifest.ts:22–28`, `:383–399`). No standalone SHA-256 of the raw source bytes exists in the build path, and no `.gitattributes` LF pin exists. |
| Paragraph locators | `#<section>/p<n>` and `#<section>/p<s>-p<e>`, a new `unknown-block` locator outcome, `ERR_SOURCE_BLOCK_UNKNOWN`, and a table locator narrowed from the whole row to value cells. | Not implemented. `parseLocator` accepts only section, table and ordered-item forms; `LocatorResult` has four values (`spec/lib/adapters/markdown.ts:31–56`; `spec/lib/source.ts:11`). |
| Digest-absence release gate | A per-mode blocking rule so release and `--strict` cannot publish provenance whose source is not pinned. | Not implemented; the release gate today is error/review only (`spec/lib/build.ts:250–261`). |
| Contract, plan and data follow-ups | Contract and M1-plan amendments, `.gitattributes`, the CORE-001 migration to atomic locators, and a deliberate golden update (provenance RFC §4.7, §8). | None applied; the merged provenance RFC changed no code, data or generated artifact (`b5e316a` is documentation only). |

Consequence for this RFC: every item above is **accepted, not available producer behaviour**.
PAP does not depend on it: PAP defines its own `rawSourceDigest`, its own quote-range check and its
own statuses (§5, §7, §8, §9). A producer that later ships the provenance work MAY additionally embed
the plain `identity.sha256` as a claim, but PAP MUST NOT require it and MUST NOT treat the field as
a PAP identity (Appendix I.2). #4 remains open.

### 2.3 Open issues that bound this design

| Issue | Ask | Why it matters to PAP | State at `f1ddcf7` |
|---|---|---|---|
| #35 | Define and enforce the trust boundary for executable profiles: distinguish declarative data from executable hooks; require an explicit trust decision; no claim that schema validation is sandboxing. | It is Gate 0's minimum security gate (#43). PAP's verifier must never execute producer-controlled code, so the producer's profile trust model must not leak into the verifier. | Open. The accepted contract documents the trust assumption (contract §8.1:828–831; D28:1212), but the loader imports profile modules unconditionally (`spec/lib/build.ts:342–366`) and no opt-in policy or rejection test was found. |
| #36 | Validate relation inverse declarations as a bidirectional contract: unique names, inverse exists, endpoints and cardinality compatible, deterministic diagnostics. | PAP's `pap.check.relation-consistency/1` is a relation witness on `claims/relations.json`; it must not be confused with a fix to the producer's resolver. | Open. The resolver writes the declared inverse onto targets and uses a first-match declaration lookup; it does not validate reciprocity (`spec/lib/relations.ts:54`, `:118–130`). |
| #37 | Separate provenance binding from provenance verification, with source identity and a verification record. | A PAP provenance claim is a binding; a PAP check record is verification. PAP implements the distinction for packages, but engine outputs still do not carry it. | Open. `bindProvenance` binds mapped selectors and checks completeness only (`spec/lib/provenance.ts:1–71`); no verification record, method or status exists in engine outputs. |
| #38 | Align `manifest.render[]` with the implementation: support all declared targets or constrain M1 to exactly one, loudly. | A package format must not inherit an ambiguous producer contract; PAP declares an `artifacts[]` array explicitly instead. | Open. The builder reads `render[0]` (`spec/lib/build.ts:174`, `:295`) and requires exactly one rendered artifact (`:219–226`), while the contract's `RenderDecl[]` is an array (contract §3.1:131–138). |
| #39 | Publish an implementation-status matrix with separate decision, implementation and verification dimensions, and reconcile stale status statements. | This RFC cites implementation state; it must not repeat the drift #39 documents. | Open. Both `docs/architecture/engine-public-contract.md:7` and `docs/architecture/m1-implementation-plan.md:7` still say `Implementation status: not started` although the M1 PRs landed. |

Beyond these, #4 (a source locator and document hash) is open with its decision record accepted as
#45 and is described in §2.2; #41 is the architecture epic that consolidated the gaps; #43 is the
roadmap that orders them. None of these is a PAP blocker for drafting or review, but #35 and #37
bound what a PAP producer may claim honestly, and the remaining gaps are recorded as limitations in
the package report model (§7). At the baseline they also gated Phase 2 implementation; §2.4 records
the current status. PAP does not claim to close any of them.

### 2.4 Relationship to roadmap #43 Phases 0–3

> **Baseline versus current status.** The `State at f1ddcf7` column is historical. The RFC has
> since been accepted (2026-11-02), Gate 1 PASS is recorded, and Gate 0 is recorded COMPLETE on
> #43 (comment 6570952005) on the basis of the merged #36–#38 work and the previously completed
> #32/#33/#35. The maintainer then authorized Phase 2 verifier implementation. A Phase 2
> implementation is merged into `main` via PR #64 and available under `pap/`; independent
> interoperability validation remains pending. Gate 3 remains OPEN. This note cites those records
> and does not independently re-audit Gate 0.

| Phase | Content | State at `f1ddcf7` | PAP implication |
|---|---|---|---|
| Phase 0 | Close engine and trust-boundary gaps: #35 (minimum security gate), #37, #32, #36, #38, #33; record remaining gaps as limitations. | At the baseline, #32 was closed and merged as #42; #33 was closed and merged as #46 (independent example profile). #35, #36, #37 and #38 were open. Gate 0 was **not** satisfied: the executable-profile boundary was still the open minimum gate, and binding vs verification was still not separated in engine outputs. Artifact and build-identity semantics were documented (`docs/architecture/build-identity.md`). | This RFC records the remaining gaps as limitations (§6, §7, §14) and defines PAP so that none of its claims depends on the missing engine behaviour. |
| Phase 1 | Specify PAP v0.1 and its verifier CLI: layout, schemas, versioning, extension rules, separated digests, claims vs records, coverage vocabulary, trust policy, signatures as extension points, path safety and limits. Gate 1 requires a format implementable without importing the producer, with explicit compatibility, threat model and test vectors. | This document (then proposed; accepted 2026-11-02). Gate 1 was not yet met at the baseline. | Appendix H is the completeness map; §12, §13 and Appendix E are the implementability evidence. |
| Phase 2 | Implement the standalone verifier CLI and its `verify`, `inspect` and `explain` behaviour. | Not started at the baseline. Sequencing in #43: Phase 2 was not to begin before the RFC was reviewed and Gate 0's minimum trust boundary was satisfied. | This RFC is a design input to Phase 2 only; it promises no implementation. |
| Phase 3 | Adversarial corpus and an independent implementation that agrees on the declared subset. | Not started; it is part of proving Phase 2, not optional polish. | PAP defines the matrix (§12), vectors (Appendix E) and independence criteria (§13). |

Gate 0, quoted from #43: *executable profiles are explicitly trusted/opted into rather than
silently executed; artifact/build identity semantics are documented; provenance binding is not
represented as verification. Any remaining gaps are recorded as limitations in the RFC and package
coverage.* Measured against that text at `f1ddcf7`:

- **Executable profiles**: not satisfied. #35 is open; the loader imports profile modules
  unconditionally, and the contract states the trust assumption without an explicit opt-in
  decision point (`spec/lib/build.ts:342–366`; contract §8.1).
- **Artifact/build identity semantics**: documented, and #32 is closed (`docs/architecture/
  build-identity.md`; contract §8.1).
- **Binding vs verification**: not satisfied for engine outputs. #37 is open; the engine binds
  provenance and delegates quote location to the adapter without emitting a verification record
  (`spec/lib/provenance.ts:1–71`; contract §11).
- **Remaining gaps as limitations**: recorded by this RFC in §6, §7, §14 and §15.3, and by the package
  report's `limitations[]` (§7).

#44 says RFC drafting may proceed in parallel with Phase 0, but implementation must respect Gate 0
and the RFC's acceptance. At the baseline, acceptance of this document did not authorize Phase 2,
and Phase 2 could not begin while #35 remained open. Subsequently, Gate 0 was recorded COMPLETE on
#43 (comment 6570952005) on the basis of the merged #36–#38 work and the previously completed
#32/#33/#35. The maintainer's 2026-11-02 decision then authorized Phase 2 verifier implementation
under the accepted contract (#57). The Phase 2 implementation is merged into `main` via PR #64 and
available under `pap/`; independent interoperability validation remains pending. This document cites
those records and does not independently re-audit Gate 0.

### 2.5 A new product track, not M1

PAP is a **new product track, not part of M1**. M1 is the current milestone: prove separability of
CORE-001 policy into a profile with a byte-identical artifact, while explicitly excluding the
package split, the public API, new diagnostic codes, multi-source, review dimensions and CLI
changes (`docs/architecture/engine-public-contract.md:1094–1130`, `:1115–1116`). #43 states that
the roadmap *does not replace #41 or the existing M1 plan* and defines *the next product track
after and alongside the relevant foundation work* (#43, "Related work"). #44 explicitly keeps
*changing the current M1 plan without an explicit owner decision* out of scope.

Consequences for this RFC:

- No M1 acceptance criterion depends on PAP, and no PAP requirement changes M1 behaviour. This RFC
  changes no code, data or generated artifact.
- PAP MAY be produced by Contract Builder later, but the producer is a consumer of the format.
  The format is not defined by the producer's current output, and PAP MUST NOT extend its schema
  with producer IR structures when the producer cannot express something; that case becomes a
  claim or a recorded limitation.
- The package format MUST NOT reuse the producer's internal IR: PAP's unit is a directory of
  serialized documents governed by its own schema and versioning rules (§4, §5). A verifier
  written only from this RFC, its schemas and published vectors MUST be able to parse the package
  without `ProjectModel`, entity/relation indexes, diagnostic types or any other engine type. The
  engine's identities appear in a package only as producer claims (`build.inputDigest`), never as
  PAP-defined fields.

### 2.6 Engine identity versus PAP identity

The four engine identity artefacts have PAP counterparts that answer a related but different
question. None may be compared by string equality, and none may be copied into a PAP identity.

| Engine identity at `f1ddcf7` | PAP field(s) covering the question | Why the values are deliberately different | Comparison rule |
|---|---|---|---|
| `inputDigest`, one digest over canonical manifest + LF-normalized inputs + LF-normalized sources + profile closure + adapter/renderer closures (`spec/lib/identity.ts:358–477`). | `build.inputDigest` (optional producer claim), `packageIdentity`, `normalizedInputDigest`, per-extension `extensionClosureDigest` (§5). | PAP separates three questions the engine answers with one value: which manifest this is (`packageIdentity` over the PAP manifest), which packaged inputs are present (`normalizedInputDigest` over `inputs/` only), and which extensions are declared (per-extension closures). It uses different domains, envelopes and record sets. | Not comparable. A verifier cannot recompute the engine digest: the PAP manifest is a different schema, and the producer's canonical manifest, closure declarations and lockfile are not in the package. `build.inputDigest` is a claim and is never a check input. |
| Profile/extension `closureDigest`, SHA-256 over `contract-builder/extension-closure/v1\n` + declared files + pinned dependency records (`spec/lib/identity.ts:166–189`). | `extensionClosureDigest` for the `profile`, `extension` and `checker` jobs, plus the optional `profile.closureDigest` claim (§5). | Same question, different algorithm domain, and possibly a different declared file/dependency set. The engine's closure is one producer-side computation, not the PAP definition. | Not comparable. Equality would be a producer claim; a conforming verifier computes PAP closures under PAP rules only. |
| Raw source-byte digest. Absent at baseline; accepted as `sources[].identity.sha256` by the provenance RFC, not implemented (§2.2). | `rawSourceDigest` per source: H(`pap.source.raw.v1`, raw bytes), recomputed by the verifier when a snapshot is packaged (§5). | The provenance field is a plain SHA-256 over the bytes read at build time, owned by the project. PAP's digest is domain-separated, declared by the package and recomputable by the verifier only from a packaged snapshot. Same bytes, different value. | Only by recomputation. A producer-supplied `identity.sha256` claim may be compared with a plain SHA-256 recomputed from the snapshot as a claim comparison; the comparison never changes the verdict (D6, §7). |
| Artifact digest: `Artifact.sha256`, a plain SHA-256 of the renderer-returned bytes (`spec/lib/render.ts:52–58`). The written artifact is normalized afterwards, so the file on disk is not necessarily hashed bytes (`render.ts:65–68`). | `artifactDigest` per declared artifact: H(`pap.artifact.v1`, raw packaged artifact bytes) (§5). | PAP hashes the exact packaged bytes with a domain; the engine hashes pre-normalization renderer output and does not package artifacts. Different bytes and different domains. | Only by recomputation over the packaged file. Plain SHA-256 of the file is not `artifactDigest`, and `artifactDigest` is not the engine's `Artifact.sha256`. |

Rule for the verifier: where a producer supplies an engine identity, the verifier reports
`NOT_COMPARABLE` or `UNVERIFIABLE` unless it can recompute the compared value from packaged bytes
under PAP rules. Agreement or disagreement between a producer claim and a verifier value is a
claim comparison, never a check outcome (D6, §7, §8).

---


## 3. Scope, requirements and non-goals

### 3.1 Scope of this document

This RFC specifies **Portable Assurance Package (PAP) v0.1**: a directory format for a package of
artifacts, declared inputs, optional source snapshots, producer claims and verification-relevant
metadata, together with the contract for an independent verifier CLI that consumes it offline.
The document is normative for the format and for verifier behaviour; it is the accepted v0.1
specification and it changes no code, data or generated artifact.

The design is bounded by the decisions recorded in §16 (D1–D12, accepted by the maintainer on
2026-11-02): a directory-only package, JCS canonical JSON over an I-JSON subset, SHA-256 with
domain separation, optional source snapshots, a strict core schema with an extension namespace,
separation of producer claims from verifier results, independent status dimensions, an explicit
local trust policy, three v0.1 checks, a standalone `pap` CLI, and a versioned compatibility
policy.

The producer and the verifier are separate products. A package is untrusted input to the verifier;
the verifier MUST NOT import the producer runtime, execute producer or profile code, or use the
network in v0.1. This RFC does not implement either product. The maintainer accepted the v0.1
specification on 2026-11-02; Gate 0 is recorded COMPLETE on #43 (comment 6570952005); and Phase 2
was then authorized. The Phase 2 implementation is merged into `main` via PR #64 and available
under `pap/`; independent interoperability validation remains pending. This status cites those
records and does not independently re-audit Gate 0 (§2.4; #43; #44).

The document is organised as follows. §4 defines the package layout and the manifest; §5 the
identities, hash domains and digest rules; §6 the trust model and the local policy input; §7 the
status, coverage and report semantics; §8 the check and witness contract; §9 the verifier CLI;
§10 the threat model and parser safety; §11 the signature and transparency extension points;
§12 the conformance matrix; §13 the requirements for an independent implementation. Appendices
A–F and J hold the normative schemas, vectors and diagnostic codes; Appendix H maps this document
onto #44; Appendix I relates it to the engine identities.

### 3.2 Requirements R1–R12

The requirements below derive from the issue #44 acceptance criteria and deliverables. Each is
traced to the issue text and to the section that resolves it. Normative keywords are used in the
RFC 2119 sense.

| ID | Requirement | Source in #44 | Resolved in |
|---|---|---|---|
| R1 | The package layout, manifest schema, versioning and compatibility rules, canonical serialization and digest rules MUST be specified precisely enough for two independent implementations to agree byte for byte. | Deliverable 1; AC 1; decisions D1–D5, D11 | §4, §5, §12, §15.1, Appendix A, Appendix J |
| R2 | Raw source, normalized input, artifact, package/manifest, extension-closure, checker and verification-record identities MUST be defined and kept distinct, with exact bytes, hash domains, path rules and no self-reference. | Deliverable 2; AC 2; decision D3 | §5, Appendix I |
| R3 | The report MUST distinguish package/artifact integrity, source integrity and availability, signature validity, signer identity and trust-policy decision, profile/checker recognition, mechanical checks, human-review evidence, semantic truth and legal enforceability; a valid signature MUST NOT establish truth or authority. | Deliverable 3; AC 3; decision D8 | §6, §7, Appendix B |
| R4 | Per-dimension statuses and aggregation rules MUST NOT turn unsupported, incomplete or not-evaluated checks into an unqualified success; the report MUST expose exact coverage and limitations and MUST contain no `verified` boolean. | Deliverable 4; AC 4; decision D7 | §7, Appendix C |
| R5 | Producer-supplied claims and verifier-generated results MUST differ in file, schema and namespace, and claims MUST be labelled untrusted wherever the report shows them. | Deliverables 1 and 3; AC 5; decision D6 | §4, §7, Appendix C, Appendix D |
| R6 | The check/witness contract MUST define check-specification id and version, subject digests, checker identity, declared scope, outcome, independently recomputable witnesses, diagnostics and behaviour for unsupported or incomplete checks; v0.1 declares a deliberately small check set. | Deliverable 5; AC 1, AC 4, AC 8; decision D9 | §8, Appendix D |
| R7 | The CLI contract MUST define commands, arguments, exit codes, stdout/stderr behaviour, the machine-readable report schema, deterministic output, offline operation and the absence of any producer-runtime dependency. | Deliverable 6; AC 7; decision D10 | §9, Appendix C |
| R8 | The document MUST model packages as hostile input: path traversal, absolute and symlinked paths, duplicate or case-colliding paths, archive bombs and resource exhaustion, malformed manifests, digest substitution, unknown mandatory extensions, compromised checkers/profiles, trust-root substitution, stale/replayable status and fake verification records, with safe defaults and explicit in/out-of-scope statements. | Deliverable 7; AC 6; decisions D1, D8 | §10, §4 |
| R9 | DSSE/in-toto and Sigstore-compatible envelopes MUST be treated as optional adapters, not as a bespoke format and not as mandatory for a useful unsigned package; revocation and transparency services MUST be declared deferred with their consequences. | Deliverable 8; AC 10; decision D8 | §11, §14 |
| R10 | A normative conformance matrix MUST give positive and negative fixtures with expected per-dimension results, aggregate verdict, CLI exit code and diagnostics, and published vectors for the supported subset. | Deliverable 9; AC 8 | §12, Appendix E, Appendix F |
| R11 | Independence MUST be operational: schemas, algorithms and vectors published; no private producer dependency; language-neutral algorithms; explicit criteria for what counts as an independent implementation; underspecified areas listed as blockers. | Deliverable 10; AC 9; decision D12 | §13, Appendix E |
| R12 | This RFC MUST be reviewed and accepted before Phase 2 begins, and Gate 0's minimum trust boundary MUST be satisfied first; neither condition may be waived silently. | AC 11; #43 sequencing; #44 relationship to roadmap | Document status, §2.4, Appendix H.2 row 11, #43 Gate 0 record, #57 |

R1–R12 are the acceptance surface for review: if a section does not let a reader decide whether
its requirement is met, the gap is in the section, not in this table. R12 is the process
requirement and is resolved by the document status together with §2.4 and §16.

R12's two conditions are recorded as met, not waived: the RFC was accepted on 2026-11-02, and
Gate 0 is recorded COMPLETE on #43 (comment 6570952005) on the basis of the merged #36–#38 work and
the previously completed #32/#33/#35. The maintainer's #57 decision then authorized Phase 2. This
RFC cites those records and does not independently re-audit Gate 0.

### 3.3 Non-goals N1–N12

None of the following is in scope for this RFC or for PAP v0.1. Each is either excluded by #44 or
deferred by a decision recorded in §16; a later revision that wants one MUST record an explicit decision in
§16 rather than extending the format silently.

| ID | Non-goal | Why excluded / where recorded |
|---|---|---|
| N1 | Implementing the package producer. | #44 out of scope; this RFC is a specification. |
| N2 | Implementing the verifier CLI in this RFC. | #43 Phase 2; §9 defines the contract only. |
| N3 | Sigstore, SCITT or OCI integration. | #44 out of scope; evaluated as extension points only (§11, §14). |
| N4 | A temporal dependency graph or assumption-impact journal. | #43 Phase 4; a separate component with explicit boundaries (§14). |
| N5 | Commitment mandates or an authorization service. | #43 Phase 5; deliberately last, not part of the verifier MVP (§14). |
| N6 | Determining legal enforceability. | Explicit non-goal; `legalEnforceability` is always `NOT_EVALUATED` (§7, §14). |
| N7 | Determining semantic truth. | Schema validity is not truth; `semanticTruth` is always `NOT_EVALUATED` (§7). |
| N8 | Changing M1, its plan or its acceptance criteria. | #44 out of scope without an owner decision; PAP is a separate track (§2.5). |
| N9 | A universal evidence envelope for every possible evidence type. | #44 prefers a small testable v0.1; extensions are namespaced and optional (§4, §14). |
| N10 | Archive transport and safe archive extraction. | Directory-only in v0.1 (D1); archive rules are listed in §10.7 and referenced from §14.1. |
| N11 | A hosted verification service. | #44 excludes a hosted service; the verifier is a local, offline executable (§9, §10). |
| N12 | Production key management, revocation or transparency infrastructure. | The trust policy is a local operator-supplied file; offline limitations are explicit (D8, §6, §14). |

### 3.4 Design constraints C1–C10 and how the design respects them

Issue #44 states eight design constraints; two of them are split below because each half is a
separate design rule with a different failure mode. A change that violates any of C1–C10 requires
an explicit decision in §16, not a silent extension.

| ID | Constraint | How PAP v0.1 respects it | Sections |
|---|---|---|---|
| C1 | Keep the package format separate from Contract Builder's internal IR. | The package has its own schema and versioning; no engine type, entity model or relation index is part of the format. The verifier needs only the RFC, schemas and vectors. | §4, §5, §13, §2.5 |
| C2 | Do not make Markdown rendering a core invariant. | Artifacts are declared as `{id, path, mediaType, bytes, digest}`; Markdown is one media type. Verification renders nothing. | §4, §8, §9 |
| C3 | Do not make signatures a core invariant. | An unsigned package is a valid package; signature validity is an optional dimension, and signature mode (`disabled\|optional\|required`) is local policy. | §6, §11 |
| C4 | Do not require OCI transport. | The package is a local directory; there is no registry or transport dependency in v0.1. | §4, §9, §10 |
| C5 | Do not require a hosted service. | The verifier is a local offline executable; v0.1 has no network code. | §9, §10 |
| C6 | Do not execute arbitrary profile hooks during verification. | The verifier never executes producer, profile or checker-supplied code; checks are verifier-side; profile and extension identities are values, not loadable modules. | §8, §10, §11, Appendix I.4 |
| C7 | Do not treat schema validity as semantic truth. | The strict schema establishes only structural validity; `semanticTruth` is always `NOT_EVALUATED`, and `limitations[]` says so. | §7, §10 |
| C8 | Do not conflate provenance binding with provenance verification. | A binding is an untrusted claim in `claims/provenance.json`; a verification is a check record with an independently recomputable witness; statuses distinguish bound-but-unverified. | §4, §7, §8, Appendix I.3 |
| C9 | Do not claim legal enforceability. | Explicit non-goal N6; `legalEnforceability` is always `NOT_EVALUATED`. | §7, §14 |
| C10 | Prefer a small, testable v0.1 over a universal envelope for every evidence type. | Directory-only package, three checks, a fixed status vocabulary, optional namespaced extensions, no archive, no Sigstore, no temporal graph. | §4, §8, §14, Appendix E |

---


## 4. Package format and layout

### 4.1 Design principles

The package format is intentionally independent of Contract Builder's IR, profile model and
Markdown renderer. Five rules shape it:

1. **Producer ≠ verifier.** Every value written by the producer is a claim. A claim can be
   checked, but it is never a result.
2. **Portable ≠ trusted.** Package integrity, source integrity, signer identity, signer trust,
   mechanical checks, human approval and semantic truth are independent.
3. **No silent success.** Missing, unsupported, unavailable, stale and not-evaluated states are
   reported as such; a partial check can never be rendered as a pass.
4. **No arbitrary code execution.** A package contains data only. Verification never executes
   producer-, profile- or package-supplied code, including templates, hooks and checkers.
5. **Bounded guarantees.** A package carries evidence for a declared scope. The verifier reports
   exactly what that scope was and what it did not cover.

The package is also not a build-reproduction format. It can carry the producer's build identity
as a claim and the raw inputs as snapshots, but the verifier does not rebuild the artifact and
does not claim byte-for-byte reproducibility of the producer's build.

### 4.2 Directory layout

A v0.1 package is a directory. `assurance-package.json` is the only fixed file name; every other
payload file is declared by the manifest (signature envelopes are the sole convention-based
exception, §11.2).

```text
PACKAGE/
  assurance-package.json            required   package manifest
  artifacts/                        required   at least one declared artifact
    <artifact files>
  inputs/                           optional   declared build-input snapshots
    <input files>
  sources/                          optional   embedded source snapshots
    <source files>
  claims/                           optional   untrusted producer claims
    provenance.json                 optional   declared by manifest
    relations.json                  optional   declared by manifest
    producer-report.json            optional   declared by manifest
    reviews.json                    optional   declared by manifest
  signatures/                       optional   optional DSSE envelopes
    <name>.dsse.json                optional   discovered by convention
```

| Path | Presence | Declared in manifest | Read by verifier |
|---|---|---|---|
| `assurance-package.json` | required | — (it is the manifest) | yes |
| `artifacts/**` | required, ≥ 1 | `artifacts[].path` + digest + byte count | yes |
| `inputs/**` | optional | `inputs[].path` + digest | yes, for identity checks |
| `sources/**` | optional | `sources[].path` + digest | yes, for source checks |
| `claims/*.json` | optional | `claims.<kind>` = `{path, digest}` | yes, as untrusted data |
| `signatures/*.dsse.json` | optional | not listed in manifest (§11.2) | yes, as untrusted-by-default envelopes |

Directories that are absent are treated as empty. A directory with an unexpected name is an
undeclared file (§4.3.3). The package MUST NOT contain a nested package manifest.

### 4.3 Paths and file constraints

#### 4.3.1 Path grammar

All declared paths are relative to the package root and MUST match:

```text
path := segment ("/" segment)*
segment := [A-Za-z0-9._-]+
```

Additional rules:

- no leading or trailing `/`, no empty segment, no `.` or `..` segment;
- maximum 16 segments and 255 bytes per path; maximum 255 bytes per segment;
- ASCII only in v0.1. This removes Unicode-normalization and case-folding ambiguity between
  case-insensitive filesystems; a later minor version may relax it with explicit collision
  rules;
- declared roots are fixed per file class: `artifacts/`, `inputs/`, `sources/`, `claims/`;
  signatures live only under `signatures/`. A declared payload path therefore has at least two
  segments (root plus file), which Appendix A enforces; the universal grammar above allows one
  segment for non-payload uses;
- the path is the identity of a payload file. Two declarations with the same path, or paths that
  differ only by case, are `INVALID` even on a case-sensitive filesystem, so a package behaves
  identically when copied to a case-insensitive one. The duplicate and case-fold rules apply to all
  declared payload paths as one set, not per class. Because the declared root is fixed per class, a
  well-formed package cannot contain one package-relative path in two classes. No separate
  cross-class collision rule is required; a verifier that already applies the global duplicate set
  is conformant. A declaration whose path does not start with its class root is
  `pap.package.path-invalid`; the duplicate rule is still evaluated over the same declaration set,
  so a malformed declaration may additionally produce `pap.package.path-duplicate` when it equals
  another declaration.

A declared path is validated against this grammar before the Appendix A schema pattern is applied.
A grammar violation is reported as `pap.package.path-invalid` (and a duplicate or case collision as
`pap.package.path-duplicate`), never as `pap.package.schema`, even though the schema pattern also
rejects the same string; Appendix A's pattern is a second line of defence, not a second diagnostic
rule.

#### 4.3.2 File types and reading rules

- Every payload path MUST resolve to a regular file inside the package directory. Symbolic links
  and non-regular files (directories where a file is declared, sockets, FIFOs, devices) are
  rejected. Hard links cannot be detected portably and are outside the v0.1 guarantee.
- The package root is the directory named by the `PACKAGE` argument after operating-system path
  resolution. A `PACKAGE` that is a symbolic link to a directory is permitted: the verifier
  resolves it once and uses the resolved directory as the root for every containment check in this
  section. A `PACKAGE` that does not resolve is `pap.package.not-found` (exit 74, no report); a
  `PACKAGE` that resolves to something other than a directory is a usage error
  (`pap.cli.usage`, exit 64, no report). Symbolic links at or below a declared payload path remain
  rejected by the first bullet; resolving the operator-supplied root is not a payload read.
- The verifier opens each path without following symlinks where the platform supports it, reads
  the bytes once, and hashes exactly the bytes read. It MUST NOT resolve a path outside the
  package root.
- File bytes are read as opaque octets. Only claim/JSON files are parsed as UTF-8; artifacts,
  inputs and sources may be arbitrary bytes.
- Empty files are allowed only where the manifest permits them; an empty artifact is allowed if
  its declared digest and byte count match, but an empty source or input is usually a sign of a
  packaging error and is reported by the relevant check rather than rejected by the parser.

#### 4.3.3 Declared, undeclared and missing files

- Only declared payloads are read. A present regular file under `artifacts/`, `inputs/`,
  `sources/` or `claims/` that the manifest does not declare is a warning
  (`pap.package.undeclared-file`), is never opened, and does not affect identities. A file may be
  declared at most once; two declarations of one path (or a case-folded duplicate) are
  `pap.package.path-duplicate`.
- The verifier enumerates the package tree to report undeclared files. It MUST NOT open an
  undeclared file. If the package root itself, or any directory under it, cannot be enumerated,
  the verifier MUST emit `pap.package.undeclared-scan-incomplete` (warning) with scope `package`,
  add the same code to `limitations[]`, and set `coverage.full: false`; the verdict is at most
  `INCOMPLETE` and MUST NOT be `PASS`. This includes a root that is readable through a known
  manifest path but cannot be listed; it does not include a root that cannot be resolved
  (`pap.package.not-found`/74) or a manifest that cannot be read (`pap.package.io` with a `FAIL`
  report). The affected scope is the undeclared-file scan, whose status is `NOT_EVALUATED`.
  Because the report has no separate per-scope status field for that scan, the report represents
  that status with the diagnostic, the limitation and `coverage.full: false`; no dimension is
  changed to `NOT_EVALUATED` solely by this condition. A `PASS` is impossible because §7.4 rule 6
  requires `coverage.full: true`, and this rule sets it false. An independently established
  `FAIL` (for example an artifact digest mismatch) remains `FAIL` under §7.4 rule 1: this rule
  contributes only the coverage condition of rule 4 and cannot downgrade a higher-precedence
  verdict. This is a report-level outcome for a package that was otherwise evaluated, not the
  exit-74 CLI I/O failure of §9.7: resolving the root still uses `pap.package.not-found` (74) when
  the `PACKAGE` does not exist, and an unreadable or missing manifest still uses `pap.package.io`
  with a `FAIL` report (§7.7). This rule does not apply to a declared payload: a missing,
  unreadable or non-regular declared payload remains
  `pap.package.declared-file-missing`/`pap.package.io` and `FAIL` (the declared-payload bullet;
  §7.3).
- v0.1 does not define a limit on the number of filesystem entries visited by the undeclared-file
  scan. A verifier MAY use an internal robustness budget to bound its own scan. If that budget
  stops the scan on entry count, traversal depth or any other private bound, the verifier MUST
  report the scan as incomplete under this section (`pap.package.undeclared-scan-incomplete`,
  `coverage.full: false`, verdict at most `INCOMPLETE`) and MUST NOT report it as
  `pap.package.limit-exceeded`, which is reserved for the §4.3.4 limits. The same code therefore
  covers both an I/O enumeration failure and a private scan stop; it never means a declared
  payload failed. No conformance case may assert a specific internal budget, and no `PASS` may be
  reported when the scan did not complete. An implementation that chooses not to bound its scan
  accepts the no-wall-clock residual of §10.5.
- A declared file that is missing, unreadable, or not a regular file is an error
  (`pap.package.declared-file-missing`, `pap.package.io`). A package with a missing declared
  payload cannot be verified for integrity.
- The manifest MUST NOT declare itself as a payload.
- Signature envelopes are the only files not declared in the manifest. Envelopes under
  `signatures/` with suffix `.dsse.json` are read; other files there are undeclared.

#### 4.3.4 Resource limits

Defaults are normative for v0.1. A verifier MAY allow an operator to lower them, and MUST report
the effective limits in the report when they are lower than the defaults. Exceeding a limit is
`pap.package.limit-exceeded`; it makes the affected scope unverifiable rather than invalid, and
the verdict is `INCOMPLETE` (limits are a verifier safety boundary, not a producer defect). One
exception is a limit that prevents the manifest itself from being read or parsed: then no
package identity is computable, `integrity.package` is `FAIL`, and the verdict is `FAIL` (§9.11,
§7.7).

| Limit | Default |
|---|---|
| manifest bytes | 1 MiB |
| payload files | 4 096 |
| bytes per file | 256 MiB |
| total package payload bytes | 1 GiB |
| path segments / path bytes / segment bytes | 16 / 255 / 255 |
| JSON nesting depth | 64 |
| JSON string bytes | 16 MiB |
| claims files | 16 |
| provenance bindings | 100 000 |
| relation entities / edges | 100 000 / 1 000 000 |
| signature envelopes | 32 |

Enforcement points and reporting are normative:

- Only a limit that prevents the manifest from being read or parsed — the manifest byte limit and
  the JSON nesting/string limits applied to the manifest — yields `FAIL`: `package.identity: null`,
  `integrity.package: FAIL`, verdict `FAIL`, exit 1 (§9.11). Every other limit hit stops only the
  affected scope.
- When a payload byte limit is hit, declared files read before the stop keep their computed
  identity; every unread declaration reports `computed: null`; the affected dimension is
  `NOT_EVALUATED` (`integrity.artifacts` for artifacts, `sources.integrity` for sources,
  `integrity.package` for inputs), `coverage.full` is `false`, the verdict is `INCOMPLETE`, and the
  exit code is 2. `integrity.artifacts` therefore has a `NOT_EVALUATED` status (§7.3), because a
  verifier safety limit is not a producer defect.
- When the number of declarations in one payload class exceeds its count limit, the verifier reads
  none of that class rather than an arbitrary prefix: every declaration in the class reports
  `computed: null`, and the affected dimension is `NOT_EVALUATED` as above. This keeps the limit
  independent of manifest order.
- Payloads are read in a fixed order: artifacts in manifest order, then embedded sources in
  manifest order, then inputs in manifest order, then claims in manifest order. The total-byte
  limit therefore stops at a deterministic point, and two implementations report the same
  `computed` values for the files read before the stop. Multiple limits may be exceeded in one
  run; each emits `pap.package.limit-exceeded`, the affected scopes are their union, and the first
  stop in this order decides which identities are computed.
- A `pap.package.limit-exceeded` that leaves any declared payload, required check or signature
  envelope unevaluated sets `coverage.full: false` and makes the verdict at most `INCOMPLETE` —
  never `PASS` — even when the affected dimension is not listed in the policy's
  `requiredDimensions` (§7.4 rule 4).

Limit interaction summary (normative):

| Limit hit | Affected result | `coverage.full` | Verdict ceiling |
|---|---|---|---|
| manifest bytes, or manifest JSON nesting/string | no package identity, `integrity.package: FAIL`, no check set | `false` | `FAIL` |
| payload byte or count (artifacts/sources/inputs) | affected dimension `NOT_EVALUATED`, unread `computed: null`, dependent checks `NOT_EVALUATED` | `false` | `INCOMPLETE` |
| claim-file JSON nesting/string | dependent check `NOT_EVALUATED`; `integrity.package` not failed by the limit | `false` | `INCOMPLETE` |
| signature envelopes (only when mode is `optional`/`required`) | signature and trust `NOT_EVALUATED` | `false` | `INCOMPLETE` |
| trust policy `limits` parsing | no report, exit 64 (`pap.trust.policy-invalid`) | — | — |

Several limits may combine; the table's most severe outcome applies, and every affected scope is
reported. `effectiveLimits` lists every lowered limit that produced the run; it does not change
these rules. No limit row can produce `PASS`.
- A limit hit while parsing a claim file makes that claim unusable: `pap.package.limit-exceeded`,
  the dependent check is `NOT_EVALUATED`, and `integrity.package` is not failed by the verifier's
  limit. A limit hit while parsing the trust policy is a policy error (exit 64, §6.3.2).
- A verifier MAY allow an operator to lower a limit and MUST NOT allow one to be raised (§6.3.2).
  Lowered limits are reported in the report's `effectiveLimits` object (§7.7, Appendix C): it lists
  the effective value for every limit the operator lowered and is absent when all limits are at
  their defaults. A result computed under non-default limits MUST NOT be presented as computed
  under the defaults.
- The claims-files limit is larger than the four claim kinds Appendix A can declare, so it never
  binds in v0.1; it is kept as a forward-compatibility bound. The limits that can bind in a
  well-formed package are the manifest, payload count, per-file/total byte, nesting/string and
  envelope limits.

### 4.4 Manifest

The manifest is a JSON object. Its normative JSON Schema is Appendix A. It is identified by the
fixed file name `assurance-package.json` and media type
`application/vnd.pap.manifest.v0.1+json`.

#### 4.4.1 Top-level fields

| Field | Required | Meaning |
|---|---|---|
| `papVersion` | yes | Package-format version, exactly `"0.1"` in this RFC. |
| `package` | yes | Package label and producer metadata; **not** an identity. |
| `subject` | no | Project identifier and revision the artifact is about (claim). |
| `build` | no | Producer's build claims (`inputDigest`, normalized input digest, engine version, extensions). Never trusted. |
| `artifacts` | yes | Non-empty array of exported artifact subjects (§4.4.2). |
| `inputs` | no | Declared build-input snapshots (§4.5.1). |
| `sources` | no | Declared source snapshots (§4.5.2). |
| `claims` | no | Paths and digests of untrusted claim files (§4.7). |
| `profile` | no | Profile identity only: `{id, version, closureDigest?}`; no profile code is included or executed. |
| `checkSpecs` | yes | Non-empty array of check specifications the package asks the verifier to evaluate. |
| `extensions` | no | Reverse-DNS namespace for optional, non-core data. |
| `requiredFeatures` | no | Feature identifiers the verifier must support before a `PASS` is possible. |

`package` contains `id` (a non-empty stable label such as `urn:pap:acme:2026-01`, not a digest),
`title` (optional), `createdAt` (optional RFC 3339 timestamp), and `producer` (optional
`{name, version}`). `package.id` never replaces `packageIdentity`; two packages with the same
label and different bytes are different packages.

#### 4.4.2 Artifact entries

Each artifact entry declares:

```json
{
  "id": "artifact:acme-supplier",
  "path": "artifacts/ACME-SUPPLIER.draft.md",
  "mediaType": "text/markdown; charset=utf-8",
  "bytes": 1234,
  "digest": "sha256:<64 lowercase hex>"
}
```

- `id` is unique within the package and stable enough for claims to reference it;
- `path` follows §4.3 and MUST start with `artifacts/`;
- `mediaType` is an advisory IANA-style media type. The verifier MUST NOT render, parse or
  execute the artifact based on it; Markdown is not a core invariant;
- `bytes` is the exact octet count, checked alongside the digest;
- `digest` is `artifactDigest` from §5.4.

At least one artifact is required. Multiple artifacts are allowed. Artifacts are not required to
be text; arbitrary media types are permitted, and the verifier treats all artifact bytes as
opaque.

#### 4.4.3 Check specifications

`checkSpecs` is a non-empty array of `{id, version, required}`. `id` matches
`^pap\.check\.[a-z0-9-]+/[0-9]+$` and `version` matches the suffix. `required` defaults to
`true`. `version` MUST equal the version suffix of `id`; a mismatch is `pap.package.schema`. The
package declares **which checks it asks for**, not their results. The verifier's
policy may require additional checks; the union of package-required and policy-required checks is
evaluated, and any required check the verifier does not implement makes a `PASS` impossible
(`UNSUPPORTED`, §7.4).

The verifier evaluates every declared check, required or optional, and reports its outcome in
`dimensions.checks.results[]`; only required checks gate the verdict and the coverage counts. A
package whose `checkSpecs` (after the union with policy `requiredChecks`) contains no required
check is structurally valid but has an empty required set: the verdict is `INCOMPLETE` with
`pap.package.empty-check-specs` and `coverage.full: false` (§7.4 rule 4, §8.8). It is never a
vacuous `PASS`.

### 4.5 Inputs and sources

#### 4.5.1 Input snapshots

An input entry declares a build input (for example a YAML or JSON source of the producer's
model) and embeds it:

```json
{
  "id": "input:requirements",
  "path": "inputs/requirements.yml",
  "mediaType": "application/yaml",
  "digest": "sha256:<64 lowercase hex>",
  "normalization": "lf"
}
```

`normalization` is `"lf"` or `"none"`. `"lf"` means: decode as UTF-8 with fatal errors, replace
CRLF and lone CR with LF, and hash the resulting UTF-8 bytes. If the bytes are not valid UTF-8
or contain a NUL octet, the verifier treats them as binary and hashes them raw, exactly as
`docs/architecture/build-identity.md` specifies for declared inputs. `"none"` hashes raw bytes.
`inputs[].digest` is the per-file digest from §5.6. Unlike a source snapshot, an input is always
embedded in v0.1: `path` is required and there is no referenced-only input, so the normalized
input digest always has bytes to hash.

The normalized input digest (§5.6) is computed over all packaged inputs. If the package declares
no inputs, the verifier reports `normalizedInputDigest: null`; input integrity is then part of
`integrity.package` and is not separately reported. This is not a failure by itself, but it makes
any claim that depends on input identity unverifiable.

#### 4.5.2 Source snapshots and acquisition metadata

A source entry declares a source document and MAY embed its exact bytes:

```json
{
  "id": "SRC-ACME",
  "path": "sources/acme-policy.md",
  "mediaType": "text/markdown; charset=utf-8",
  "digest": "sha256:<64 lowercase hex>",
  "acquiredAt": "2026-11-01T12:00:00Z",
  "acquisition": {
    "method": "git",
    "uri": "https://example.invalid/acme/policy.git",
    "revision": "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
  }
}
```

- `digest` is the raw-source digest (`H("pap.source.raw.v1", bytes)`), never the LF-normalized
  input digest. CRLF changes the digest (§5.5).
- `path` is optional. When present, the snapshot is embedded and the verifier can recompute the
  digest and evaluate source-dependent checks. When absent, the source is **referenced-only**:
  its identity is declared but unverifiable offline, source integrity is `UNAVAILABLE`, and
  source-dependent checks are `NOT_EVALUATED`.
- `acquiredAt` and `acquisition` are acquisition records. They are producer claims; they do not
  affect build identity and are not evidence that the source was actually retrieved from the
  declared URI. The verifier reports them as claims.
- A source used by a required check and lacking a snapshot makes `PASS` impossible (§7.4). A
  package that never claims source-dependent checks may omit sources entirely.

### 4.6 Media types and artifact subjects

The manifest identifies artifacts by `id`, path, media type, byte count and digest. These five
values are the **artifact subject**. The verifier reports subjects in the same order as the
manifest and recomputes each digest. Media types are advisory labels, not parser instructions:
a `text/markdown` artifact is not rendered, a `application/json` artifact is not schema-checked
unless a check explicitly says so, and no media type can cause the verifier to execute content.

### 4.7 Claims

Claims are producer-supplied data. They live in separate files, are declared by path and digest,
and are never merged into verifier results. Each claim file has `papClaimsVersion: "0.1"` and a
schema in Appendix D.

#### 4.7.1 Claim kinds

| Claim file | Purpose | Schema |
|---|---|---|
| `claims/provenance.json` | Bindings from artifact entities/assertions to an exact source byte range and a verbatim quote. | Appendix D.1 |
| `claims/relations.json` | Explicit entities, relation declarations and edges to be checked for consistency. | Appendix D.2 |
| `claims/producer-report.json` | Producer's own check outcomes and diagnostics. | Appendix D.3 |
| `claims/reviews.json` | Human approval/rejection evidence. | Appendix D.4 |

The manifest declares each present claim file as `claims.<kind>: {path, digest}` where `digest`
is `H("pap.claims.v1", raw file bytes)`. A claim file not declared in the manifest is an
undeclared file and is never read. A declared claim file with a digest mismatch makes the package
integrity `FAIL`.

A declared claim file is parsed only after its declared digest matches (§10.5). If its bytes are
not valid JSON, it violates its Appendix D schema, or it breaks a claim cross-field invariant —
duplicate claim/entity/relation/approval ids, a provenance binding that names a source the
manifest does not declare, a producer-report `checkVersion` that does not match its `checkId`
suffix — the claim is `INVALID`: `pap.package.claim-invalid` and `integrity.package: FAIL`. An
invalid declared claim is a producer defect, never a `NOT_EVALUATED` check limitation. A claim
file with an unknown `papClaimsVersion` is different: it is `UNSUPPORTED`
(`pap.claim.unsupported-version`), the dependent check is `UNSUPPORTED`/`NOT_EVALUATED`, and
package integrity is not failed (§8.1, Appendix D).

#### 4.7.2 Provenance claims are bindings, not verification

A provenance claim records that the producer **asserts** a binding: entity or assertion →
source id → exact byte range → quote digest. It is a `ProvenanceBinding` in the sense of
[#37](https://github.com/agent-federation/contract-builder/issues/37). It is not a
`ProvenanceVerification`. The verifier may mechanically confirm that the range exists and that
the recorded quote digest matches the bytes in that range; it does not establish that the quote
supports the assertion, that the range was chosen fairly, or that the artifact's normalized text
is a faithful representation. Those remain producer review obligations, and the report says so.

#### 4.7.3 Producer report

`claims/producer-report.json` contains producer-generated check records and diagnostics. It is
stored under `claims/` and rendered only in the report's `producerClaims` block, clearly labelled
as untrusted. It is never used to compute a check outcome, a dimension status or the verdict.
The verifier MAY compare each claim with its own result and report `AGREES`, `DISAGREES`,
`UNVERIFIABLE` or `NOT_COMPARABLE`; a disagreement is informational evidence about the producer,
not a verifier failure, and a producer-claimed `PASS` cannot override an independent `FAIL`.

#### 4.7.4 Review evidence

`claims/reviews.json` records human approvals or rejections with a declared scope, decision,
timestamp and reviewer identity. Its optional `evidence` object is opaque producer data: v0.1 does
**not** validate approval signatures and does not interpret `evidence` as a cryptographic binding;
`evidence.path` is never opened or resolved. The `humanReview` dimension is `NOT_APPLICABLE` unless
the trust policy requires human approval; if required, the verifier checks structure, scope,
freshness and that the reviewer identity is recognized by the policy (§6.7). Signed human-review
approvals are a recorded blocker (§14.1, §16.1): v0.1 defines no policy field that can require one,
and a future signed-approval policy needs a review-attestation mechanism and reviewer authority
model before it can be expressed. The verifier does not evaluate whether the reviewer was right.

### 4.8 Profiles, extensions and checkers

- `profile` is identity metadata only: `{id, version, closureDigest?}`. The profile's executable
  hook, renderer and template are **not** part of a package and are never loaded. A profile
  entry lets the verifier and policy recognize which producer configuration was used; it does
  not make that configuration trustworthy.
- `extensions` is a namespaced map. Each key is a reverse-DNS name; each value is
  `{version, critical, data?}`. Extensions are opaque data. A verifier that does not understand
  an extension MUST NOT interpret `data`; it reports the extension and applies §4.9.
- Checkers are verifier-side implementations. The package cannot ship or select an executable
  checker. It selects check specifications by id/version; the verifier's registry decides which
  implementation satisfies them, and the report records the checker identity that ran (§5.8).

### 4.9 Unknown fields, extensions and compatibility

The core schema is strict: an unknown field in any core object is `INVALID`
(`pap.package.unknown-field`). This is deliberate — a verifier must not silently ignore a field
that might be security-relevant.

Forward compatibility is carried by three mechanisms:

1. **`extensions`**: optional non-core data. Unknown extension with `critical: false` is
   ignored, reported with `pap.extension.ignored`, and listed in `limitations`. Unknown
   extension with `critical: true` is `UNSUPPORTED`.
2. **`requiredFeatures`**: a package lists semantic features a verifier must implement. Every
   entry is required by definition; v0.1 has no optional-feature list, and optional
   forward-compatible data belongs in `extensions` with `critical: false`. An unknown entry is
   `UNSUPPORTED` (`pap.feature.unsupported`).
3. **`papVersion` major/minor**: within a major version, the core schema is frozen. A minor
   release may add optional extensions/features, not new required core fields. A verifier that
   supports exactly `0.1` MUST report an `UNSUPPORTED` verdict for any other version rather than
   guess: a newer minor (`0.2`+) yields `pap.compat.minor-newer`; an older supported-major minor
   (`0.0`) or a different major (`1.0`+) yields `pap.compat.version-unsupported`. Appendix A
   admits any canonical `major.minor` string, so an unsupported-version manifest that uses only
   0.1 core fields is structurally readable (`integrity.package: PASS`) but still `UNSUPPORTED`
   at the verdict level, because the verifier does not know the declared version's semantics; a
   version string with leading zeros (`0.01`) is not canonical and is `pap.package.schema`.
   A manifest that uses unknown core fields fails the strict core check (`FAIL`); that is an
   honest rejection, not a compatibility claim. Required checks on a newer-minor package are
   `NOT_EVALUATED`, not silently run under the older version's semantics.

The complete compatibility policy is in §15; unknown extension handling is normative for the
verdict in §7.4.

### 4.10 Canonicalization and serialization

The manifest is stored as UTF-8 JSON without a BOM. It need not be written in canonical form:
formatting, indentation and key order are irrelevant. Its identity (§5.3) is computed over the
canonical JSON form defined in §5.2, so two byte-different but semantically identical manifests
have the same package identity. The same applies to claim files, check records, trust policies
and reports.

Producers SHOULD write canonical JSON to make review and diffs easier, but the verifier MUST
accept any JSON that decodes to the same value and obeys the I-JSON subset. Duplicate object keys
are invalid, not a last-wins situation.

### 4.11 Complete minimal example

Appendix F contains a complete package with every file's content and a field-by-field
walkthrough. It is a valid v0.1 package with one unsigned artifact, one embedded source, two
inputs, three claims and a producer report. The example is normative for field usage and
informative for content.

### 4.12 What the package is not

- It is not the engine's IR, profile or render model. No field is defined by Contract Builder
  internals; a different producer can emit the same format.
- It is not a signature. Integrity checking works on unsigned packages.
- It is not a proof of semantic truth, legal enforceability or signer authority.
- It is not a build-reproduction guarantee. It carries build claims and input snapshots; the
  verifier does not rebuild.
- It is not a hosted service or an OCI artifact. v0.1 is a directory read from local storage.

---


## 5. Digest and identity model

The package has several identities that answer different questions. Conflating them is the most
likely source of false assurance: a matching artifact digest says nothing about source identity,
and a matching source digest says nothing about signer trust.

### 5.1 Identity taxonomy

| Identity | Computed as | Covers | Does not cover |
|---|---|---|---|
| `packageIdentity` | `H("pap.package.v1", JCS(manifest))` | the canonical manifest, including every declared digest and claim path | payload bytes themselves, signatures, trust policy, verifier |
| `artifactDigest` | `H("pap.artifact.v1", raw artifact bytes)` | exact artifact octets | source, inputs, producer claims |
| `rawSourceDigest` | `H("pap.source.raw.v1", raw source bytes)` | exact source octets (CRLF significant) | LF-normalized form, quote position |
| `normalizedInputDigest` | `H("pap.input.set.v1", framed input records)` | packaged inputs after declared normalization | sources, extension code, engine version |
| `extensionClosureDigest` | `H("pap.extension.closure.v1", framed closure records)` | declared extension files + pinned dependency closure | runtime behaviour outside the declared set |
| `checkerIdentity` | `H("pap.checker.identity.v1", JCS({id, version, implementationDigest}))` | the verifier implementation that produced a record | package content, trust policy |
| `verificationRecordIdentity` | `H("pap.report.v1", JCS(report identity form))` | the semantic content of one verification report | wall-clock time, absolute paths, report formatting |

None of these is a signature, and none establishes truth. They make different tampering and
mismatch cases visible.

### 5.2 Hash function, domain separation and framing

v0.1 uses SHA-256 only. A digest is encoded as `sha256:` followed by 64 lowercase hexadecimal
digits. The verifier MUST reject any other algorithm identifier in a digest field
(`pap.package.schema`); algorithm agility is deferred (§5.14).

Every digest is computed with an explicit domain:

```text
H(domain, octets) = SHA-256( ASCII(domain) || 0x00 || octets )
```

`domain` is a fixed ASCII string from the table below and contains no NUL. The NUL terminator
prevents a domain string from being extended ambiguously.

| Domain | Payload | Used by |
|---|---|---|
| `pap.package.v1` | canonical manifest JSON | `packageIdentity` |
| `pap.artifact.v1` | raw artifact bytes | `artifactDigest` |
| `pap.source.raw.v1` | raw source bytes | `rawSourceDigest` |
| `pap.input.file.v1` | one framed input record | `inputs[].digest` |
| `pap.input.set.v1` | concatenated framed input records | `normalizedInputDigest` |
| `pap.extension.closure.v1` | framed closure records | `extensionClosureDigest` |
| `pap.checker.identity.v1` | canonical checker identity JSON | `checkerIdentity` |
| `pap.check.record.v1` | canonical check record JSON | check record identity (internal) |
| `pap.claims.v1` | raw claim file bytes | `claims.<kind>.digest` |
| `pap.report.v1` | canonical report identity form | `verificationRecordIdentity` |
| `pap.trust-policy.v1` | canonical trust policy JSON | policy digest reported to the operator |
| `pap.quote.v1` | exact quote bytes | quote digest in provenance claims |

Structured payloads use a length-prefixed record framing. It is exactly the framing already used
by [`docs/architecture/build-identity.md`](build-identity.md), repeated here so an independent
implementation does not need to read producer code:

```text
record := u32be tagLength
          tag[tagLength]                       (UTF-8)
          u32be partCount
          partCount × ( u32be partLength, part[partLength] )

payload := record record ...                  (no separator)
```

Lengths are unsigned 32-bit big-endian. A part may be text (encoded UTF-8 by the writer) or
bytes. The length prefixes make concatenation unambiguous: two different logical record
sequences cannot produce the same pre-hash byte stream by boundary shifting.

Framing rules:

- `inputs[].digest`: `H("pap.input.file.v1", record("input", [path, normalizedBytes]))`.
- `normalizedInputDigest`: `H("pap.input.set.v1", record("input", [path, normalizedBytes]) ...)`
  for every packaged input, sorted by `path` in ascending UTF-8 byte order. `path` is the
  manifest-declared path with POSIX separators and no leading `./`.
- `extensionClosureDigest`: `H("pap.extension.closure.v1", records)` where records are, in
  order: one `record("extension", [kind, id, version])`; one `record("file", [path,
  normalizedTextBytes])` per declared file sorted by path; one `record("dependency", [name,
  version, integrity])` per dependency in the complete dependency closure, sorted by name then
  version. `kind` is `profile`, `extension` or `checker`. File bytes are LF-normalized text
  (UTF-8; CRLF/CR → LF); binary declared files are an author error in v0.1.
- `claims.<kind>.digest`: the raw file bytes are the payload; no framing.

The verifier recomputes every digest from the bytes it actually read. A declared digest is an
expectation, not evidence.

### 5.3 Package identity

```text
packageIdentity = H("pap.package.v1", JCS(manifest))
```

The manifest is canonicalized with RFC 8785 JCS over the I-JSON subset (§5.3.1 below). The
canonical form is the identity: whitespace, key order, duplicate keys and number spelling do not
create alternative identities.

Consequences:

- `package.createdAt` is inside the manifest and therefore inside `packageIdentity`. Re-exporting
  a package with a new timestamp creates a new package identity even when payloads are
  unchanged. That is intended: the package is the unit that claims, paths and timestamps belong
  to. Build identity is a separate producer claim (`build.inputDigest`).
- There is no manifest field for the package's own identity. The verifier computes it and reports
  it. A package cannot declare a self-digest, so there is no self-reference and no digest
  substitution through a self-declared identity field.
- A signature envelope signs the canonical manifest bytes; the identity it must name is
  `packageIdentity` (§11).

#### 5.3.1 Canonical JSON profile (JCS)

v0.1 uses RFC 8785 JSON Canonicalization Scheme restricted to I-JSON:

- input is UTF-8 without a byte-order mark;
- object member names are sorted by UTF-16 code unit order, as JCS specifies;
- arrays preserve order; no array is sorted;
- numbers are integers in the range `[-(2^53 - 1), 2^53 - 1]`; floating-point numbers, `-0`,
  `NaN` and infinities are invalid in v0.1 core and claim objects. A number token is accepted only
  if it matches `-?(0|[1-9][0-9]*)` and its value is in range: fraction or exponent spelling
  (`1.0`, `1e3`) is invalid even when the mathematical value is integral, and so is `-0`;
- strings are valid Unicode scalar sequences; lone surrogates are invalid; no Unicode
  normalization is applied or required;
- duplicate object member names are invalid;
- output uses JCS whitespace (none), string escaping and number spelling.

Implementations MAY accept non-canonical JSON on disk and MUST canonicalize before hashing; the
canonicalizer MUST reject the invalid cases above rather than silently coerce them.

### 5.4 Artifact digest

```text
artifactDigest = H("pap.artifact.v1", raw artifact bytes)
```

Raw bytes are hashed exactly as stored: no newline conversion, no UTF-8 decoding, no rendering.
The declared `bytes` count is checked independently of the digest; both must match or package
integrity fails. A mismatch is `pap.integrity.artifact-mismatch`.

### 5.5 Raw source digest

```text
rawSourceDigest = H("pap.source.raw.v1", raw source bytes)
```

Raw source bytes are hashed exactly, so CRLF and LF spellings of the same text have different
digests. This is deliberately stricter than the normalized input digest: a source is an
independent document whose exact bytes are the evidence, while build inputs are normalized for
reproducibility. The distinction mirrors the accepted source-digest decision in the provenance
RFC (§4.4.2) and must not be collapsed.

### 5.6 Normalized input digest

Inputs are build inputs, not sources. They follow the LF normalization rules of
`docs/architecture/build-identity.md`:

1. If the bytes contain a NUL octet, treat them as binary and use raw bytes.
2. Else decode as UTF-8 with fatal errors. On failure, treat them as binary and use raw bytes.
3. Replace every `CRLF` and lone `CR` with `LF`; encode back to UTF-8.

For `normalization: "none"` the raw bytes are used at step 3's place. Each input's per-file
digest and the set digest are defined in §5.2. Sorting inputs by path makes the set digest
independent of the manifest array order; changing an input's path, bytes or normalization
changes the set digest.

If the manifest declares `build.normalizedInputDigest`, the verifier compares it with its own
computation. A mismatch is `pap.integrity.input-mismatch` and makes package integrity fail. If
the manifest has no inputs, no set digest is reported and the corresponding claim is
`NOT_EVALUATED`.

### 5.7 Extension closure and profile identity

An extension closure digest covers the declared files and the complete pinned dependency closure:

```text
extensionClosureDigest = H("pap.extension.closure.v1", records as defined in §5.2)
```

For a profile, the `profile.closureDigest` field uses this scheme with `kind: "profile"`. The
verifier cannot recompute it without the profile files, so it reports it as a declared identity
and does not claim to have verified it. `identities.extensionClosureDigest` in a report is exactly
the declared `profile.closureDigest` when one is declared, and `null` otherwise; the verifier's own
checker closure is reported separately as `verifier.implementationDigest` and `checkerIdentity`
(§5.8), never in `identities.extensionClosureDigest`. Profile recognition is a trust-policy
decision (§6.6), not a digest recomputation.

### 5.8 Checker identity

A checker is verifier-side code. Its identity is:

```text
implementationDigest = extensionClosureDigest(kind: "checker", id, version, files, dependencies)
checkerIdentity      = H("pap.checker.identity.v1", JCS({id, version, implementationDigest}))
```

The verifier reports its own checker identities in `verifier` and in every check record. The
trust policy may allowlist checker identities (§6.4). Because the check record includes the
checker identity, `verificationRecordIdentity` differs between implementations; that is
expected, and cross-implementation comparison uses the package-derived identities and the
semantic result fields (Appendix I, §13).

### 5.9 Verification record identity

```text
verificationRecordIdentity = H("pap.report.v1", JCS(identity form of the report))
```

The identity form is built deterministically from the complete Appendix C report:

1. start from the report object exactly as it validates against Appendix C;
2. remove exactly the fields listed below — no other field is removed, renamed or added;
3. replace `identities.verificationRecordIdentity` with the fixed 64-zero digest
   `sha256:0000000000000000000000000000000000000000000000000000000000000000` (a record cannot
   contain its own hash; the placeholder is part of the form, not an excluded field);
4. canonicalize with JCS over the I-JSON subset (§5.3.1) and hash with `pap.report.v1`.

Excluded fields:

| Field | Why it is excluded |
|---|---|
| `evaluatedAt`, `durationMs` | wall-clock and timing values; `evaluatedAt` is fixed only when `--now` is fixed |
| `package.path`, `policy.path` | absolute or host-specific locations |
| the whole `producerClaims` block | informational, producer-supplied and optional; it is compared semantically (§7.6) and never part of the verifier's record |
| `diagnostics[].message` | human wording may legitimately differ; codes, severities and scopes stay in the form |
| `checks[].diagnostics[].message` | the same rule for per-check diagnostics; the check record itself stays in the form |
| `checks[].witnesses[].quoteBase64` | optional informational convenience field (RFC 4648 base64 of the extracted span); `quoteDigest` and `extractedDigest` already pin the same bytes, so the convenience encoding must not create identity differences |

Everything else is in the identity form, including `verdict`, every dimension status,
`coverage`, `limitations[]`, `diagnostics[].code`/`severity`/`scope`, package-derived identities,
the policy digest/state, and every top-level `checks[]` record with its `subjectDigests`,
`scope`, `checker`, `outcome`, `witnesses` (except the excluded `quoteBase64`) and diagnostics.
Appendix E.4 is a complete identity form, including the three check records.

This is deliberate evidence coverage, not only result coverage:

- changing a check outcome, a `subjectDigests` value, a `scope` count/list, the `checker`
  identity, a witness's `subject`, `range`, `declared`/`computed`/`sourceDigest`/`quoteDigest`/
  `extractedDigest`, or a violation entry changes `verificationRecordIdentity`;
- changing only a human message or the optional `quoteBase64` convenience field does not, because
  both are presentation of a result that the remaining fields already pin;
- therefore two records can share an identity only when their semantic results and their
  recomputable check evidence (other than excluded presentation) are identical. The exclusion
  cannot hide a different verdict, dimension, check outcome, subject, scope, checker or witness
  range/digest.

Recomputing the same verification with the same checker, policy and `--now` value produces the
same `verificationRecordIdentity`; witness formatting that v0.1 requires is deterministic
(§8.2–§8.6). The identity is not a signature and not an attestation by the verifier; it names one
record.

`verificationRecordIdentity` is compared only within one verifier build, because it includes
`checkerIdentity` (§5.8, §13.6). A consumer auditing evidence outside the identity must still read
`checks[]` directly; the identity proves that two reports match, not that a report is true.

### 5.10 Self-reference avoidance

The package identity is computed from the manifest. The manifest does not contain the package
identity, any artifact digest of the manifest file, or any signature envelope digest. It does
contain artifact, source and input digests and claim-file digests; those files do not contain
hashes of the manifest, so the dependency graph is acyclic. Signature envelopes are outside the
manifest and sign the canonical manifest; a signature therefore covers `packageIdentity`
without creating a circular declaration.

If a future extension wants a self-digest, it must use the "signature envelope" pattern (a
sibling file excluded from the manifest) rather than a manifest field.

### 5.11 Timestamps and clocks

| Value | Location | In build identity? | In package identity? | In record identity? |
|---|---|---|---|---|
| producer build timestamp | not defined in v0.1; MAY appear in `package.createdAt` | no | yes | yes (as package content) |
| `package.createdAt` | manifest | no | yes | yes |
| source `acquiredAt` | manifest source entry | no | yes | yes |
| `claims.checkedAt` | producer report claim | no | indirect (claim file digest) | yes (as claim comparison input) |
| `reviews.decidedAt` | review claim | no | indirect | yes |
| `report.evaluatedAt` | verifier report envelope | no | no | **no** (excluded) |
| trust policy `issuedAt`/`expiresAt` | policy file | no | no | yes (policy digest includes them; freshness uses local clock) |

The verifier never uses a package timestamp to decide freshness of the package itself. Freshness
exists only for trust policy and review evidence, and is evaluated against the verifier's clock
(or the injected `--now` value). A package's `createdAt` cannot prove when it was verified, and a
producer report's `checkedAt` cannot prove that a check happened.

### 5.12 Test vectors

Appendix E contains canonical test vectors: exact canonical manifest bytes and expected digests
for package, artifact, raw source, normalized inputs, extension closure, checker identity and a
verification record, plus a framing-ambiguity vector. They are normative: an implementation that
disagrees with them has a bug or a different profile version, not a permitted variation.

### 5.13 Non-conflation rules

These rules are normative for documentation and report fields:

1. `build.inputDigest` is a producer claim about the producer's build. It is not
   `packageIdentity`, not `normalizedInputDigest` and not proof that the package contains those
   inputs. The verifier copies it only into `producerClaims`.
2. `packageIdentity` covers the manifest, not payload bytes; a matching package identity with a
   mismatched artifact digest is a failed package, not a contradiction.
3. `rawSourceDigest` and `normalizedInputDigest` answer different questions and are never
   interchangeable. The first is exact source evidence; the second is normalized build input.
4. `checkerIdentity` identifies the verifier, not the package. Two verifiers may report the same
   verdict with different checker identities.
5. `verificationRecordIdentity` identifies one verification record. It is not a signature, not a
   package identity and not comparable across implementations when checker identities differ.
6. No field named `verified` exists. The report uses `verdict` and per-dimension statuses (§7).

### 5.14 Algorithm agility

v0.1 defines SHA-256 only. A different algorithm requires a new package format minor/major and a
new domain namespace; it is not negotiable per package in v0.1. This avoids algorithm-confusion
attacks and keeps the first implementation small. A future version may allow a `digestAlgorithm`
field with an explicit allowlist, but only with a version bump and conformance vectors for every
algorithm.

---


## 6. Trust model and verification semantics

This section defines what the verifier can establish about a package, what a recipient may and may
not conclude from a positive status, and how an operator's local trust policy enters the process.
The status vocabularies are normative in §7.3 and the verdict rules in §7.4; this section states
the semantics behind those statuses, the non-implications, and the decisions a relying party must
make before `PASS` carries any meaning. The report schema is Appendix C; the trust-policy schema is
Appendix B.

Three rules frame everything below: (1) **trust is supplied, not discovered** — anchors, signer
identities, checker/profile pins, required dimensions and freshness windows come only from the
operator's local policy, and no package field contributes to them (§4.7, §5.13); (2) **every
positive status is scoped** — it describes one dimension and one declared scope, never the package
as a whole and never `verified`; (3) **absence of evidence is a status, not a pass** — missing,
unsupported, unavailable, stale and not-evaluated states are reported and keep `PASS` impossible
where the property is required (§7.4).

The verifier answers one question: *for the package as supplied, which mechanical properties hold,
and what does the operator's supplied policy decide?* It does not answer *should you rely on this
package?* — that is the operator's decision, made from the dimensions, coverage and limitations and
recorded outside the verifier (§6.9). Diagnostic severity here is an impact marker, not a verdict:
`error` means a required property was disproved or a required input/tool is unusable (`FAIL`,
`UNTRUSTED`, `UNSUPPORTED`); `warning` means a required evaluation is incomplete or evidence is not
established (`INCOMPLETE`); `info` records a limitation that changes no dimension by itself.

### 6.1 The eight dimensions and what each does not prove

The report always carries all eight dimensions, even when several are trivially satisfied. A
verifier MUST NOT derive one dimension's status from another dimension or from producer claims
(§4.7). §7.3 defines each status's positive meaning; the table below adds the non-guarantee.

| Dimension | Report field | A positive status means | It does **not** prove |
|---|---|---|---|
| Integrity | `dimensions.integrity.{package,artifacts}` | the directory was parsed safely; declared files exist, are regular, paths are valid and unique; the manifest schema holds; package and artifact digests match declarations | that the payloads mean anything, that the producer is honest, or that the package is complete |
| Sources | `dimensions.sources.{integrity,availability}` | embedded source bytes match the declared raw digest; every source used by a required check has a snapshot | that the snapshot is the source really used, that referenced-only sources are authentic, or that evidence selection is complete (§4.5.2) |
| Signature | `dimensions.signature.validity` | cryptographic verification succeeded for the policy-required envelope set over the canonical manifest (§11) | signer authority, intent, correctness, that the signer is trusted, or that anything outside the manifest was signed |
| Trust | `dimensions.trust.{signerIdentity,policyDecision,checkerRecognition,profileRecognition}` | the signing key maps to a policy identity/role allowed for this package; the policy snapshot is fresh and accepts the signer set; checker and profile identities match operator pins | that the policy is correct, the operator is authorized, keys are uncompromised or unrevoked, or that the policy file was not substituted |
| Checks | `dimensions.checks.results[]` | every required check ran to completion on its declared scope and each required assertion held | semantic truth, completeness of evidence, or that a check's choice of scope was fair |
| Human review | `dimensions.humanReview.status` | required approval evidence is present, structurally valid, in scope, fresh, names a policy-recognized reviewer, and is reported as an unverified claim (`basis: unbound-claim`) | that the reviewer was right, competent, independent, that the approval is authenticated, or that the whole package was reviewed |
| Semantic truth | `dimensions.semanticTruth` | nothing: always `NOT_EVALUATED` in v0.1 | any statement about meaning, correctness or conformity of the content |
| Legal enforceability | `dimensions.legalEnforceability` | nothing: always `NOT_EVALUATED` in v0.1 | any statement about validity, binding effect or liability |

A verifier that cannot evaluate a dimension MUST report the vocabulary's absence status rather than
`PASS`: `NOT_EVALUATED`, `UNAVAILABLE`, `UNKNOWN`, `INCOMPLETE` or `NOT_APPLICABLE` as the
dimension permits (§7.3). `NOT_APPLICABLE` is used only where the dimension genuinely does not
apply (no signature and none required; no approval and none required), never as a substitute for an
unevaluable requirement.

### 6.2 Non-implications

The dimensions are independent, and the joins between them are the places where assurance is
usually overstated. The following implications are invalid; a report, a recipient and downstream
tooling MUST NOT make them.

| The report may say | A recipient must not conclude | Why not |
|---|---|---|
| `integrity.package: PASS` | "the package is trustworthy" | it says the directory parsed safely and declared digests matched; the producer is not a trust anchor |
| `signature.validity: VALID` | "the signer is trusted" | signature validity is cryptography over bytes; trust is a separate policy decision (`trust.signerIdentity`) |
| `trust.signerIdentity: TRUSTED` | "the content is true" or "the producer is authorized to bind the recipient" | the policy says which identity may sign; it says nothing about the truth of the signed claims |
| `checks.results[]: PASS` | "the evidence is complete or representative" | a producer can omit evidence; checks cover declared scope only |
| `humanReview: PASS` | "a human approved this content correctly" | the verifier checks evidence structure, scope, freshness and recognized reviewer identity, not judgement |
| `humanReview: PASS` | "the approval is cryptographically authenticated or authorizes action" | the approval is a producer claim; v0.1 has no signed-review binding, and `humanReview.basis: unbound-claim` plus `pap.review.unbound` record that |
| `packageIdentity` matches a pinned value | "the payload bytes are the same" | `packageIdentity` covers the manifest, not the payloads; artifact digests are separate (§5.13) |
| `sources.integrity: PASS` | "the source is authentic or authoritative" | a digest is an integrity pin, not authorship; anyone who can rewrite the package can rewrite the digest |
| producer claim says `PASS` | "the independent check passed" | producer claims are untrusted data; only verifier-generated check records carry outcomes (§4.7.3, §8) |
| `trust.checkerRecognition: PASS` | "the checker implementation is correct or bug-free" | recognition only matches an operator pin on identity/version/digest |
| `policy.state: FRESH` and `verdict: PASS` | "the package is current, not replayed, and appropriate for this transaction" | the verifier is stateless and has no network; freshness belongs to the operator's reliance process (§6.5) |

Corollaries that the report and CLI MUST honour:

- a `PASS` is a statement about the required mechanical set only. With a policy, it means every
  required check ran and passed and every required dimension is in a positive state; without a
  policy, it means the same for the package-required set and says nothing about trust;
- text output MUST print `NOT A PASS` (or an equivalent unambiguous phrase) for every non-`PASS`
  verdict, MUST NOT render a producer claim with verifier formatting (§7.8), and MUST report a
  status even when another dimension already makes the aggregate verdict obvious; a consumer must
  be able to recompute the verdict from `dimensions`, `coverage` and the policy required set (§7.4).

### 6.3 Trust policy input

A trust policy is a local, offline JSON document supplied by the operator as an explicit input:

```text
pap verify PACKAGE --trust-policy FILE
```

Its file name is `trust-policy.json` by convention, but the verifier reads exactly the path given
on the command line. The policy is optional: a verifier invoked without one still performs
integrity, source, claim and check evaluation. Its structure is Appendix B; its digest is
`H("pap.trust-policy.v1", JCS(policy))` under §5.2, and the report records
`policy.{id,digest,state}` (Appendix C). The policy is never modified by the verifier and never
written into the report.

| Policy field | Meaning | Effect when absent or misconfigured |
|---|---|---|
| `trustPolicyVersion` | schema version, `"0.1"` | must be `"0.1"`; otherwise the policy is invalid (§6.3.1) |
| `id` | operator-assigned snapshot label | not present; the verifier cannot cite the snapshot |
| `issuedAt`, `expiresAt` | validity window of this snapshot | required; freshness is `FRESH` or `STALE` (§6.5) |
| `signature.mode` | `disabled`, `optional` or `required` | required field; controls whether a signature is part of the required set (§11) |
| `signature.minimumValidSigners` | minimum count of distinct authorized valid signers when mode is `required` (default 1); ignored in `optional` and `disabled` mode | a higher count raises the bar; it never makes an unauthorized signer acceptable, and it never turns an optional signature into a requirement |
| `keys[]` | the only key material the verifier will use: `{keyId, algorithm: "ed25519", publicKey}` | no keys means signatures cannot be verified at all |
| `signers[]` | operator-enrolled identities: `{keyIds, identity, allowedRoles, allowedPackageIds?, allowedPackageIdentities?}`; a signer applies to this package only if every present binding list matches (role `producer` for manifests, `reviewer` for approvals) | a key not mapped here is `UNKNOWN`; an identity not allowed for this package/role is `UNTRUSTED` |
| `checkers[]` | operator pins on checker implementations (`id`, `version`, `implementationDigest`) | recognition is `NOT_APPLICABLE` when the list is empty |
| `profiles[]` | operator pins on producer profiles (`id`, `version`, optional `closureDigest`) | recognition is `NOT_APPLICABLE` when the list is empty |
| `requiredChecks[]` | check specifications the operator requires, unioned with package `checkSpecs` required entries (§7.4) | no check is added; a required check the verifier does not implement makes `PASS` impossible |
| `requiredDimensions[]` | root or dotted sub-dimension names the operator requires (root or dotted; Appendix B enumerates them) | at least one is required; the evaluable set excludes semantic truth and legal enforceability |
| `humanReview` | `{required, maxAgeSeconds}` | if `required` is false, review evidence is informational only (§6.7) |
| `limits` | optional tighten-only resource limits | absent means the verifier defaults apply (§4.3.4, §10.5); values may only lower the defaults |

#### 6.3.1 The package cannot supply or override its own policy

The trust policy is an operator input, not package data. This is a boundary, not a preference:

- the manifest has no trust-policy field, no policy digest field and no policy URL;
- the verifier MUST NOT discover a policy inside the package, from the environment, from the
  network or from a producer-declared location. Only the explicit `--trust-policy` input counts;
- a file named `trust-policy.json` inside the package is an ordinary undeclared file (or a declared
  payload if the manifest says so), is never read as a policy (`pap.package.undeclared-file`);
- the policy digest in the report is computed by the verifier over the bytes it read; it is not a
  package declaration and cannot be provided by the producer;
- no package field can widen an operator's required set, lower a required count, disable a chosen
  dimension or add a trust anchor. Authority is one-way: policy constrains the package verdict.

Trust anchors are supplied out of band: the operator must deliver the policy over a channel they
trust. The policy is not signed in v0.1, so a local attacker who replaces the policy file can change
the trust decision; that is an explicit out-of-scope boundary (§10.6). The report records the policy
`id`, `digest` and `state`; a consumer retaining a verdict SHOULD retain those values with it.

#### 6.3.2 Invalid policy fails closed

A policy that cannot be parsed or that violates Appendix B — including a duplicate `keyId`, a
`signers[].keyIds` entry missing from `keys[]`, a required dimension outside the evaluable set, a
limit above the verifier default, `minimumValidSigners` above the configured signer count when
mode is `required`, or an unusable validity window — MUST NOT be silently repaired into a weaker
policy. The verifier exits
`64` (usage error), emits `pap.trust.policy-invalid` on stderr, and produces no package report.
A syntactically valid policy that is outside its validity window is *not* an error: it produces a
report with `policy.state: STALE` and `trust.policyDecision: STALE` (§6.5).

This split is deliberate: a malformed policy is an operator defect, not a package verdict; an
expired snapshot is a real, reportable trust state.

### 6.4 Absent, fresh and stale policy snapshots

An absent policy leaves the report fully usable for mechanical evidence but trust-unevaluated:

| `policy.state` | Condition | What the verifier reports |
|---|---|---|
| `ABSENT` | no `--trust-policy` supplied | `trust.*` are `NOT_EVALUATED` or `NOT_APPLICABLE`; no key material exists, so any present envelope has `signature.validity: NOT_EVALUATED`; `limitations[]` records `pap.trust.policy-absent` |
| `FRESH` | policy supplied and `evaluatedAt` lies within `[issuedAt, expiresAt]` | trust dimensions are evaluated against this snapshot |
| `STALE` | policy supplied but `evaluatedAt` is before `issuedAt` or after `expiresAt` | cryptography and recognition still run, but `trust.policyDecision` is `STALE`; the report records `pap.trust.policy-not-yet-valid` when `issuedAt` is in the future or `pap.trust.policy-stale` when `expiresAt` has passed, and a limitation |

A trust snapshot is the exact policy file plus its digest, id and window. Snapshots are immutable:
rotating a key, enrolling a signer, narrowing a pin or revoking an identity means issuing a new
policy file with a new `id`/window and re-running verification. There is no revocation list, online
status endpoint or transparency log in v0.1, so "no revocation is visible" and "no revocation
exists" are indistinguishable offline; this is recorded as a limitation (§15.3, §16.1).

Freshness is evaluated against the verifier's clock (or the injected `--now` value, §9) and never
derived from package timestamps (§5.11): `createdAt` cannot prove when a package was produced, and
a producer report's `checkedAt` cannot prove a check happened. The validity window is closed at
both ends — `evaluatedAt == issuedAt` and `evaluatedAt == expiresAt` are both `FRESH` — and there
is no clock-skew grace period for policy freshness: an instant one second outside the window is
`STALE`, with `pap.trust.policy-not-yet-valid` before `issuedAt` and `pap.trust.policy-stale`
after `expiresAt`. The 300-second future-skew allowance of §6.7 applies only to producer-claimed
review timestamps, never to operator-supplied policy timestamps. A `STALE` policy does not
invalidate signatures cryptographically — `signature.validity` may remain `VALID` — but it cannot
support `PASS`: `trust.policyDecision` is `STALE` and §7.4 rule 4 yields `INCOMPLETE`.

### 6.5 Signer outcomes: valid, unknown, untrusted, absent

The verifier evaluates each envelope independently and reports one entry per `(path, keyId)` in
`dimensions.signature.signatures[]` (Appendix C). The aggregate `dimensions.signature.validity`
is computed over the policy-required set, not by "any valid signature wins":

| Situation | Per-entry `validity` | `signerIdentity` | `policyDecision` | Diagnostic | Aggregate effect |
|---|---|---|---|---|---|
| no policy, envelope present | `NOT_EVALUATED` | `NOT_EVALUATED` | `NOT_EVALUATED` | `pap.trust.policy-absent` (`info`) | signature cannot be verified; recorded as a limitation |
| policy mode `disabled` | not reported | `NOT_APPLICABLE` | `NOT_EVALUATED` | none | signatures are outside the required set; text output states the mode |
| mode `optional`, no envelope | — | `NOT_APPLICABLE` | `NOT_EVALUATED` | `pap.signature.absent` (`info`) | `NOT_APPLICABLE`; package is legitimately unsigned |
| envelope `keyId` not in `keys[]` | `NOT_EVALUATED` | `UNKNOWN` | `REJECTED` | `pap.trust.signer-unknown` (`warning`) | signer set is not acceptable; `UNTRUSTED` by §7.4 rule 2 |
| key present but identity/role/package not allowed | `VALID` (cryptography is independent of authorization) | `UNTRUSTED` | `REJECTED` | `pap.trust.signer-untrusted` or `pap.trust.package-not-allowed` (`warning`) | `UNTRUSTED` |
| key present in `keys[]` but mapped by no `signers[]` entry | `VALID` | `UNKNOWN` | `REJECTED` | `pap.trust.signer-unknown` (`warning`) | `UNTRUSTED` by §7.4 rule 2 |
| key known, signature does not verify | `INVALID` | `NOT_EVALUATED` | `REJECTED` | `pap.signature.invalid` (`error`) | `INVALID` when required (`FAIL`, rule 1); `UNTRUSTED` otherwise |
| valid, authorized, quorum met | `VALID` | `TRUSTED` | `ACCEPTED` | none | `VALID`; trust can be positive |
| mode `required`, no envelope | — | `NOT_APPLICABLE` | `NOT_EVALUATED` | `pap.signature.absent` (`warning`) | `NOT_EVALUATED` → `INCOMPLETE` |
| mode `required`, fewer than `minimumValidSigners` | `VALID` for the envelopes that verify | `TRUSTED` for the valid, authorized ones | `NOT_EVALUATED` (required count not met) | `pap.signature.absent` (`warning`) | `INCOMPLETE` |
| stale policy, otherwise valid | `VALID` | `TRUSTED` | `STALE` | `pap.trust.policy-stale` (`warning`) | `INCOMPLETE` by §7.4 rule 4 |

Aggregation rules, normative for this dimension:

- **Mode `disabled`** means signature evaluation is out of scope: envelopes are not read, no
  `signatures[]` entries are produced, `signature.validity` is `NOT_APPLICABLE`, and no trust
  decision is made from them. This is the one case in which a present envelope is intentionally
  not evaluated — the operator's policy, not the package, turned it off. In `optional` and
  `required` modes every present envelope is read, evaluated and reported (§11.5).
- **`signature.validity`** is cryptographic and independent of authorization. In mode `required`,
  `INVALID` if any evaluated entry is `INVALID`; otherwise `VALID` if at least one envelope
  verifies; otherwise `NOT_EVALUATED` (including no envelope at all). In mode `optional`, `VALID`
  when at least one envelope verifies, `NOT_EVALUATED` when envelopes exist but none verifies,
  `NOT_APPLICABLE` when none exists. Mode `disabled` is always `NOT_APPLICABLE`. `minimumValidSigners`
  counts distinct authorized valid signers for `trust.policyDecision`; it does not change the
  cryptographic aggregate.
- **`trust.signerIdentity`**: `TRUSTED` only when every present envelope's key maps to an
  authorized signer for this package and role, even if that envelope's signature failed
  cryptographically — cryptographic validity is the separate `signature.validity` field;
  `UNTRUSTED` if any present key is mapped but not allowed; `UNKNOWN` if any present key is
  unmapped and none is `UNTRUSTED`; `NOT_EVALUATED` only when no present key can be mapped at all;
  `NOT_APPLICABLE` if no envelope exists. This is why F56 reports `TRUSTED` together with an
  invalid envelope and a `REJECTED` policy decision.
- **`trust.policyDecision`**: `ACCEPTED` only when the required signer set is satisfied and every
  present signer is acceptable; `REJECTED` when a present signer is unknown, unauthorized or its
  signature failed, or when the required set is otherwise refused (`pap.trust.policy-rejected`
  records the aggregate decision when no more specific diagnostic explains it); `STALE` when the
  snapshot is outside its window; `NOT_EVALUATED` when no policy is supplied, no envelope was
  evaluated, or a required signature is simply absent.
- **No policy with a present envelope** is an explicit case: envelope validity is `NOT_EVALUATED`
  (no key material), `trust.signerIdentity` is `NOT_EVALUATED`, `policyDecision` is
  `NOT_EVALUATED`, and the envelope is a recorded limitation, never a `PASS` input.
- Distinct signers are counted by policy `signers[]` entry, deduplicated by `keyId`; two envelopes
  carrying the same `keyId` count once and produce `pap.signature.duplicate-signer` (`warning`).
- An envelope from a signer the policy does not authorize is never silently ignored: it is
  reported with its own entry and makes the signer set unacceptable. The fix is to remove the
  envelope or to enrol the signer; there is no "ignore extra signatures" switch.

An unauthorized or unknown signer is `UNTRUSTED`/`UNKNOWN` respectively; the verifier MUST NOT
fall back to a weaker reading such as "signature present, trust not checked, therefore pass".

### 6.6 Checker and profile recognition

Recognition answers one question only: *is this exact identity, version and digest explicitly
allowed by the operator's policy?* It says nothing about quality.

- **Checker identity** is verifier-side (§4.8, §5.8). The package requests check specifications;
  the verifier's registry decides which implementation runs, and the check record names that
  checker. Policy `checkers[]` pins the accepted implementation. `PASS` means the verifier's own
  checker identity matched a pin; `UNTRUSTED` means id/version matched but `implementationDigest`
  did not (`pap.trust.checker-untrusted`); `UNSUPPORTED` means no entry matched
  (`pap.trust.checker-unknown`); `NOT_EVALUATED` means no policy; `NOT_APPLICABLE` means the policy
  pins no checkers (the verifier binary as a whole is then the anchor, recorded as a limitation).
- **Profile identity** is a package declaration (`profile.{id,version,closureDigest?}`); the
  profile's code is never present and never executed (§4.8). `PASS` means the declared identity
  matches a policy entry; when the policy entry carries `closureDigest`, the package must declare
  it and it must match. `UNSUPPORTED` means no matching id/version, or a pinned `closureDigest`
  with none declared (`pap.trust.profile-unknown`); `UNTRUSTED` means the declared digest
  contradicts the pin (`pap.trust.profile-untrusted`); `NOT_EVALUATED` means no policy;
  `NOT_APPLICABLE` means no profile is declared or none is pinned.

Recognition is required only when the policy says so (`requiredDimensions` contains `trust`, or
`trust.checkerRecognition`/`trust.profileRecognition`); §7.4 maps a required `UNSUPPORTED` to the
`UNSUPPORTED` verdict and a required `UNTRUSTED` to `UNTRUSTED`. A recognition `PASS` never
upgrades a check outcome, an integrity status or a producer claim.

### 6.7 Human review evidence

Human approval is a producer-supplied claim (`claims/reviews.json`, Appendix D.4) checked against
the operator's policy; it is not an attestation by the verifier. v0.1 evaluates four things:

1. **Requirement** — `humanReview.required` in the policy. If false, any review evidence is
   informational and the dimension is `NOT_APPLICABLE`.
2. **Structure and scope** — the claim must be structurally valid and must bind the reviewed
   subject. An approval binds this package when `scope.packageIdentity` is present and equals the
   computed `packageIdentity`, or, when `scope.packageIdentity` is absent, when `scope.artifacts`
   is present and set-equals the declared artifact ids. `scope.packageId` alone is a label, not an
   identity, and does not bind. Evidence with no usable subject, or a subject that does not match
   this package, does not approve it (`pap.review.binding-invalid`, `warning`; `INCOMPLETE`).
3. **Freshness** — `decidedAt` must be no older than `humanReview.maxAgeSeconds` relative to
   `evaluatedAt`: an age exactly equal to `maxAgeSeconds` is fresh, one second older is stale.
   `decidedAt` is a producer claim, not authenticated time; an unparseable value or one later than
   `evaluatedAt + 300 s` (the future-skew allowance, inclusive) is unusable (`pap.review.stale`,
   `warning`; `INCOMPLETE`).
4. **Reviewer identity recognized** — the reviewer identity named by the claim must match exactly a
   policy `signers[]` entry whose `allowedRoles` contains `reviewer`; `reviewer.keyId` is reserved
   and ignored in v0.1. An unrecognized reviewer yields `UNKNOWN` (`pap.review.unknown-reviewer`,
   `warning`).

`humanReview: PASS` therefore requires the policy to require review, at least one approval that
satisfies rules 1–4, and no in-scope `rejected` decision. A single `rejected` decision in scope
makes the dimension `INCOMPLETE` even when another approval is valid; v0.1 has no review-quorum
field, so one valid approval is sufficient. A reviews claim with an unsupported
`papClaimsVersion` makes the evidence unusable (`INCOMPLETE` with `pap.review.missing`), never a
silent pass.

**`PASS` is an unverified claim, never authenticated approval.** The approval is producer-supplied
data (§4.7.4); v0.1 has no signed-review binding and no authority model beyond policy recognition
of the reviewer identity. Whenever `humanReview.status` is `PASS`, the report MUST set
`dimensions.humanReview.basis: "unbound-claim"`, MUST emit `pap.review.unbound` as an `info`
diagnostic and as a limitation, and text output MUST label the status as an unverified producer
claim. A consumer MUST NOT read `PASS` as confirmed authorization, cryptographically
authenticated approval, or evidence that the reviewer was competent, independent or correct; a
future signed-approval policy is required before any of those can be reported.

| Situation | `humanReview` status | Diagnostic |
|---|---|---|
| policy does not require review | `NOT_APPLICABLE` | none |
| required, no in-scope approval evidence | `INCOMPLETE` | `pap.review.missing` (`warning`) |
| required, evidence stale or timestamp unusable | `INCOMPLETE` | `pap.review.stale` (`warning`) |
| evidence does not bind this package/artifact set | `INCOMPLETE` | `pap.review.binding-invalid` (`warning`) |
| reviewer identity not recognized by the policy | `UNKNOWN` | `pap.review.unknown-reviewer` (`warning`) |
| an in-scope approval decision is `rejected` | `INCOMPLETE` | `pap.trust.review-required` (`warning`) |
| required, valid, in scope, fresh, recognized reviewer | `PASS` | `pap.review.unbound` (`info`) records that the approval is a claim |

Cryptographic binding of approvals is deferred in v0.1: the review claim's opaque `evidence` field
MUST NOT be interpreted as a verified signature, and the verifier MUST NOT report an approval as
cryptographically bound. An approval is a claim about who reviewed what; policy recognition of the
reviewer identity is the only authority signal, and it is only as good as the operator's process.
If future policy demands signed approvals, a v0.1 verifier reports `INCOMPLETE`/`UNSUPPORTED`
rather than manufacture a `PASS` (§16.1).

`humanReview: PASS` does not prove the reviewer was competent, independent or correct, that
self-review did not occur, or that the whole package was reviewed; it records fresh, in-scope
approval evidence naming a policy-recognized reviewer. A consumer needing more must add a process,
not a status.

### 6.8 What an operator must decide before a `PASS` is meaningful

`PASS` is always relative to a stated reliance question. Before treating it as evidence, the
operator MUST have decided all of the following and SHOULD record the answers with the report:

| Decision | Expressed in | If left unset |
|---|---|---|
| What the reliance question is, and which package labels/identities it covers | operator's acceptance record, policy `signers[].allowedPackageIds`/`allowedPackageIdentities` | no signer is bound to a package; any valid signer can sign any package |
| Who may sign, in which role, with which keys | policy `keys[]`, `signers[]`, `allowedRoles` | signatures cannot be evaluated; trust stays `NOT_EVALUATED` |
| Whether a signature is not required, optional or required, and how many signers | policy `signature.mode`, `minimumValidSigners` | no signature requirement beyond what the package requests (a package cannot request one) |
| Which checks and checker implementations are accepted | policy `requiredChecks[]`, `checkers[]`; package `checkSpecs` | only package-requested checks run; checker identity is not pinned |
| Which profiles and closures are accepted | policy `profiles[]` | profile recognition is `NOT_APPLICABLE`; the declared profile is informational |
| Which dimensions must be positive for this use | policy `requiredDimensions[]` | only the dimensions implied by required checks are gating |
| How fresh trust and approval must be | policy `issuedAt`/`expiresAt`, `humanReview.maxAgeSeconds`, re-verification cadence | a stale snapshot cannot be detected as stale relative to the operator's intent |
| What each verdict means for the process | operator's gate: which statuses block release, acceptance, payment or execution | `INCOMPLETE`/`UNSUPPORTED` may be mistaken for success by a caller that reads only an exit code |
| Who judges semantic truth, legal effect and approver authority | human/legal process outside the verifier | nothing in the report answers these questions |
| How the policy and the verifier binary are obtained and protected | organisational channel, configuration management, release pinning | a substituted policy or verifier silently changes the decision (out of scope to prevent, §10.6) |

A recipient SHOULD retain, as the reliance record, at least: `packageIdentity`, artifact ids and
digests, `policy.{id,digest,state}`, verifier `{id,version,implementationDigest}`, `evaluatedAt`,
`verdict`, all eight dimensions, `coverage.full`, and the accepted `limitations[]`; that record is
what a later reviewer can reconstruct, and the package alone is not. `PASS` then means precisely:
*every check required by the policy and the package ran to completion and passed, every required
dimension is in a positive state, the signature requirement (if any) is satisfied, and coverage is
full*. Without a policy, `PASS` means the same for the package-required mechanical set and says
nothing about signer trust, approval or authority; in neither case does `PASS` mean that the
content is true, complete or legally enforceable.

### 6.9 Report fields and limitations

Trust information appears in exactly these report locations (Appendix C):

- `policy.{id,digest,state}` — which snapshot decided, its canonical digest, and `FRESH`, `STALE`
  or `ABSENT`;
- `dimensions.signature.validity`, `dimensions.signature.signatures[]` and the four
  `dimensions.trust.*` fields — aggregate and per-envelope results (§11.5);
- `dimensions.humanReview.status`; `dimensions.semanticTruth` and
  `dimensions.legalEnforceability`, always `NOT_EVALUATED`;
- `coverage.requiredDimensions` and `coverage.full` — what was required and whether it was all
  evaluated; and `limitations[]` — `{code, detail}` entries that explain every non-positive
  required status.

A verifier MUST emit a stable-code limitation for every required dimension that is not positive
(`NOT_EVALUATED`, `UNAVAILABLE`, `UNKNOWN`, `STALE`, `INCOMPLETE`, `UNTRUSTED`, `INVALID`) and
wherever evaluation was narrower than the package declares. `PASS` requires `coverage.full: true`;
a report that cannot explain a non-positive status is non-conformant. The diagnostic registry is
Appendix J; messages may change, codes are stable.

---


## 7. Status and coverage vocabulary

### 7.1 Why there is no single boolean

A single `verified` boolean forces every situation into success or failure. That is wrong in at
least four ways:

- a package may be structurally valid but incomplete (no source snapshot);
- a check may be unsupported by the verifier (a different subset), which is not a producer
  failure;
- a signature may be cryptographically valid but the signer unknown or untrusted;
- human approval may be absent, stale or out of scope.

v0.1 therefore reports independent dimensions, per-check outcomes and a coverage object. The
aggregate `verdict` is a convenience for gates, not a substitute for the dimensions: `PASS`
requires positive evidence on every required dimension and every required check. Any other
verdict carries the reason in `limitations[]` and the relevant dimension statuses.

### 7.2 Check outcomes

Every evaluated check produces exactly one outcome:

| Outcome | Meaning |
|---|---|
| `PASS` | The check ran to completion on its declared scope and every assertion held. |
| `FAIL` | The check ran to completion and at least one required assertion did not hold. |
| `UNSUPPORTED` | The verifier does not implement the check specification/id/version, or cannot evaluate a required feature. |
| `NOT_EVALUATED` | The check did not run because its inputs are missing/unavailable, a limit stopped it, or the package declared it optional and the verifier did not run it. The reason is recorded in a diagnostic and in `limitations`. |

`INCOMPLETE` is an aggregate/dimension status, not a check outcome. A check that runs on a partial
scope MUST NOT return `PASS`; it returns `NOT_EVALUATED` with the missing scope recorded, or
`FAIL` if it was required to cover that scope. Silent partial coverage is forbidden.

### 7.3 Dimensions and their statuses

The report contains eight dimensions. Each has a fixed status vocabulary; a status not in the
dimension's allowed set is a verifier defect.

| Dimension | Fields and allowed statuses |
|---|---|
| `integrity` | `package`: `PASS\|FAIL\|NOT_EVALUATED`; `artifacts`: `PASS\|FAIL\|NOT_EVALUATED` |
| `sources` | `integrity`: `PASS\|FAIL\|UNAVAILABLE\|NOT_EVALUATED`; `availability`: `PASS\|UNAVAILABLE\|NOT_APPLICABLE` |
| `signature` | `validity`: `VALID\|INVALID\|NOT_EVALUATED\|NOT_APPLICABLE`; optional `signatures[]` entries are `{path, keyId?, algorithm?, validity, signerIdentity, policyDecision}` |
| `trust` | `signerIdentity`: `TRUSTED\|UNTRUSTED\|UNKNOWN\|NOT_EVALUATED\|NOT_APPLICABLE`; `policyDecision`: `ACCEPTED\|REJECTED\|STALE\|NOT_EVALUATED`; `checkerRecognition`: `PASS\|UNSUPPORTED\|UNTRUSTED\|NOT_EVALUATED\|NOT_APPLICABLE`; `profileRecognition`: `PASS\|UNSUPPORTED\|UNTRUSTED\|NOT_EVALUATED\|NOT_APPLICABLE` |
| `checks` | one entry per declared or policy-required check specification: outcome from §7.2, in `checkSpecs` order followed by policy-only required checks by `checkId` |
| `humanReview` | `status`: `PASS\|INCOMPLETE\|UNKNOWN\|NOT_APPLICABLE`; `basis`: `unbound-claim` required when `status` is `PASS` |
| `semanticTruth` | `NOT_EVALUATED` (always in v0.1) |
| `legalEnforceability` | `NOT_EVALUATED` (always in v0.1) |

Meaning of the less obvious statuses:

- `integrity.package`: `PASS` means the directory tree was parsed safely, every declared file
  exists and is a regular file, paths are valid and unique, declared input and claim digests match,
  the manifest schema and cross-field invariants hold, and every declared claim file is
  structurally valid. Artifact and source digest outcomes belong to `integrity.artifacts` and
  `sources.integrity`, not to this field. `NOT_EVALUATED` means the manifest parsed but a resource
  limit prevented reading every declared input, so package-level input integrity could not be
  checked (§4.3.4); the verdict is then `INCOMPLETE`. A manifest that cannot be parsed is `FAIL`,
  never `NOT_EVALUATED`. It does not mean payloads are meaningful.
- `integrity.artifacts`: `PASS` means every declared artifact was read and its bytes and digest
  match the declaration. `FAIL` means a declared artifact is missing, unreadable, a symlink,
  non-regular, its path declaration is invalid or duplicated, or its digest/count mismatches:
  these are payload-level defects. `NOT_EVALUATED` means no artifact declaration is usable — the
  manifest failed parsing, schema or cross-field validation, so `integrity.package` is `FAIL` and
  payloads are not read — or a resource limit stopped reading (§4.3.4). `NOT_EVALUATED` is never a
  `PASS`; a limit alone is a verifier safety boundary rather than a producer defect, so it does not
  by itself fail the package.
- `sources.integrity`: `PASS` means every embedded source digest matches. `UNAVAILABLE` means at
  least one source referenced by a required source check has no snapshot. `NOT_EVALUATED` means
  no source integrity could be checked (for example no sources declared).
- `sources.availability`: `PASS` means every source used by a required check has an embedded
  snapshot; `UNAVAILABLE` means at least one does not; `NOT_APPLICABLE` means no source-dependent
  check is required.
- `signature.validity`: `VALID`/`INVALID` are cryptographic outcomes; `NOT_EVALUATED` means a
  signature is present but could not be processed (for example no supported envelope or no
  policy key); `NOT_APPLICABLE` means no signature is present and none is required. When one or
  more envelopes exist, `signature.signatures[]` reports each envelope independently with its own
  `path`, `keyId`, `algorithm`, `validity`, `signerIdentity` and `policyDecision`; the aggregate
  `validity` is computed over the policy-required set (§7.4).
- `trust.signerIdentity`: `TRUSTED` means the signing key maps to an identity that the supplied
  policy authorizes for this package; `UNTRUSTED` means the key/identity is known but not
  authorized; `UNKNOWN` means the key or identity is not in the policy; `NOT_EVALUATED` means no
  trust decision could be made; `NOT_APPLICABLE` means no signature.
- `trust.policyDecision`: `ACCEPTED`/`REJECTED` are the policy's decision on the whole package
  identity/signer set; `STALE` means the policy snapshot is outside its freshness window;
  `NOT_EVALUATED` means no policy was supplied or no signature was evaluated.
- `trust.checkerRecognition` and `profileRecognition`: `PASS` means the identity is explicitly
  allowed by the policy; `UNSUPPORTED` means the verifier does not know the identity; `UNTRUSTED`
  means the policy knows it and rejects it; `NOT_EVALUATED` means no policy; `NOT_APPLICABLE`
  means the package declares no such identity.
- `humanReview`: `PASS` means required approval evidence is present, in scope, fresh and names a
  policy-recognized reviewer; it is an **unverified producer claim**, and `basis: "unbound-claim"`
  plus `pap.review.unbound` must accompany it. `INCOMPLETE` means approval was required but
  evidence is missing/invalid/stale; `UNKNOWN` means a policy-relevant review decision could not be
  made; `NOT_APPLICABLE` means the policy does not require human approval and no approval is
  claimed (or approval evidence is present but optional — it is reported as an informational
  claim).

### 7.4 Verdict precedence and aggregation

The verdict is computed from the required set: the union of checks required by the package's
`checkSpecs` and by the trust policy's `requiredChecks`, and the union of dimensions required by
the policy. A dimension is "required" when the policy names it or when a required check depends
on it. The implied dimensions are fixed, so every implementation computes the same
`coverage.requiredDimensions`:

| Required check | Implied dimensions |
|---|---|
| `pap.check.digest-integrity/1` | `integrity`, `checks` |
| `pap.check.source-quote/1` | `sources`, `checks` |
| `pap.check.relation-consistency/1` | `checks` |
| an unknown required check (reported `UNSUPPORTED`) | `checks` |

`requiredDimensions` is the union of those implied dimensions with the policy's
`requiredDimensions` list, sorted ascending. For example, the Appendix F package with no policy
requires `integrity`, `sources` and `checks`, which is the identity form in Appendix E.4.

Rules are applied in order; the first matching rule determines the verdict:

1. **`FAIL`** — any required check is `FAIL`; or `integrity.package`/`integrity.artifacts` is
   `FAIL`; or `sources.integrity` is `FAIL`; or `signature.validity` is `INVALID` while the
   policy's signature mode is `required`; or a declared claim file's digest mismatches, violates
   its schema, or breaks a claim cross-field invariant. A verifier resource limit never triggers
   this rule (§4.3.4).
2. **`UNTRUSTED`** — no `FAIL` rule matched, and `trust.signerIdentity` is `UNTRUSTED`, or
   `trust.policyDecision` is `REJECTED`, or `trust.checkerRecognition`/`trust.profileRecognition`
   is `UNTRUSTED` for a recognition the policy requires (§6.6). A recognition that is not required
   is reported but does not move the verdict.
3. **`UNSUPPORTED`** — no higher rule matched, and a required check is `UNSUPPORTED`, or a
   required feature/extension is unsupported, or checker/profile recognition is `UNSUPPORTED` and
   the policy requires recognition, or the package declares a newer/unsupported `papVersion`
   (`pap.compat.minor-newer` / `pap.compat.version-unsupported`).
4. **`INCOMPLETE`** — no higher rule matched, and any required dimension is
   `NOT_EVALUATED`/`UNKNOWN`/`UNAVAILABLE`/`STALE`/`INCOMPLETE`, or a required check is
   `NOT_EVALUATED`, or signature mode is `required` and validity is `NOT_EVALUATED`, or human
   review is required and is not `PASS`, or `coverage.full` is false, or a
   `pap.package.limit-exceeded` stopped evaluation of any declared payload, required check or
   signature envelope (§4.3.4), or `policy.state` is `STALE` (a supplied policy outside its window never supports
   `PASS`, whether or not the policy requires `trust`), or the required set is empty (every
   declared check is optional and the policy adds no required check or dimension), which is
   reported with `pap.package.empty-check-specs` (§4.4.3, §8.8).
5. **`NOT_EVALUATED`** — no rule above matched, but no required check could be evaluated at all
   (degenerate report; the package still parsed). This is a report-shape error in practice and is
   listed for completeness.
6. **`PASS`** — all required checks are `PASS`, all required dimensions are in their positive
   states (`PASS`, `VALID`, `TRUSTED`, `ACCEPTED`, `NOT_APPLICABLE` where allowed),
   `coverage.full` is `true`, and no `pap.package.limit-exceeded` stopped evaluation of a declared
   payload, required check or signature envelope.

Additional invariants:

- A `PASS` is impossible when any required check is `UNSUPPORTED`, `NOT_EVALUATED` or missing.
- `signature.validity: NOT_APPLICABLE` is allowed for `PASS` only when the policy mode is
  `disabled` or `optional`, or when no policy is supplied; `optional` with no signature is
  recorded as a limitation.
- `semanticTruth` and `legalEnforceability` are never required for `PASS` because v0.1 always
  reports them `NOT_EVALUATED`; the report must state that a `PASS` is a mechanical/integrity
  verdict and not a statement about truth.
- The aggregate `signature.validity` is a cryptographic result, independent of signer
  authorization. In mode `required` it is `INVALID` if any evaluated envelope is `INVALID`,
  otherwise `VALID` if at least one envelope's signature verifies cryptographically, otherwise
  `NOT_EVALUATED` (including no envelope). In mode `optional` it is `VALID` if at least one
  envelope verifies, `NOT_EVALUATED` when envelopes exist but none verifies, and
  `NOT_APPLICABLE` when none exists. Mode `disabled` is `NOT_APPLICABLE`.
  `minimumValidSigners` governs the `trust.policyDecision` (distinct authorized valid signers),
  not `signature.validity`; per-envelope entries never override the aggregate.
- The verdict MUST be recomputable from the reported dimensions/coverage without reading
  producer claims. Implementations that disagree on the verdict for the same dimension values are
  non-conformant.

### 7.5 Coverage

`coverage` makes the scope explicit and prevents a partial pass from being presented as full
verification:

```json
{
  "requiredChecks": ["pap.check.digest-integrity/1", "pap.check.source-quote/1"],
  "checksEvaluated": 2,
  "checksPassed": 2,
  "checksFailed": 0,
  "checksUnsupported": 0,
  "checksNotEvaluated": 0,
  "requiredDimensions": ["integrity", "sources", "checks"],
  "dimensionsEvaluated": 3,
  "full": true
}
```

- `full` is `true` only when every required check was evaluated, every required dimension was
  evaluated, and the undeclared-file scan completed; `PASS` requires `full: true`.
- The check counters partition the required check set and are computed from the required set, not
  from optional checks: `checksPassed` (`PASS`), `checksFailed` (`FAIL`), `checksUnsupported`
  (`UNSUPPORTED`) and `checksNotEvaluated` (`NOT_EVALUATED`). `checksEvaluated` is
  `checksPassed + checksFailed`; a check counts as evaluated only when it ran to completion.
- `dimensionsEvaluated` counts the entries of `requiredDimensions` whose referenced status is
  decided. `NOT_EVALUATED`, `UNKNOWN`, `UNAVAILABLE`, `INCOMPLETE` and `UNSUPPORTED` are not
  decided; `STALE`, `UNTRUSTED` and `INVALID` are decided (they are produced states, even when
  negative), and `NOT_APPLICABLE` is decided where that dimension allows it. A `checks` entry is
  decided only when every required check has a `PASS` or `FAIL` outcome. A root-dimension entry
  (`integrity`, `sources`, `signature`, `trust`, `checks`, `humanReview`) is decided only when every
  sub-status the report carries for it is decided; `PASS` and `FAIL` count for `integrity`,
  `sources` and `checks`, and the navigable 4-field `trust` object counts as decided only when all
  four fields are decided. `full` is then `checksNotEvaluated == 0`, `checksUnsupported == 0`,
  `dimensionsEvaluated == len(requiredDimensions)`, the undeclared-file scan completed, and the
  required set is not empty. It is `false` when the required set is empty (no required check and
  no required dimension): the empty-required-set case is `INCOMPLETE` by §7.4 rule 4, never a
  vacuously full coverage. It is also `false` whenever a `pap.package.limit-exceeded` stopped
  evaluation of any declared payload, required check or signature envelope, even if the affected
  dimension is not in `requiredDimensions`, and whenever the undeclared-file scan is incomplete.
- `requiredChecks` follows `checkSpecs` order for declared checks and appends policy-only required
  checks in ascending `checkId` order. `requiredDimensions` follows the Appendix B enumerable order
  (`integrity`, `integrity.package`, `integrity.artifacts`, `sources`, `sources.integrity`,
  `sources.availability`, `signature`, `signature.validity`, `trust`, `trust.signerIdentity`,
  `trust.policyDecision`, `trust.checkerRecognition`, `trust.profileRecognition`, `checks`,
  `humanReview`), filtered to the required entries; this is why Appendix E.4 lists `integrity`,
  `sources`, `checks`. `coverage` is computed from the required set, not from what happened to run.
  A verifier that silently skips a required check cannot set `full: true`.
- The top-level `limitations[]` lists stable codes explaining every non-positive status (for
  example `pap.source.unavailable`, `pap.trust.policy-absent`, `pap.extension.ignored`).
  Human-readable details belong in `diagnostics`.

### 7.6 Producer claims in the report

If `claims/producer-report.json` is present, the report includes:

```json
{
  "present": true,
  "trusted": false,
  "comparison": [
    {"checkId": "pap.check.digest-integrity/1", "claimed": "PASS", "independentOutcome": "FAIL",
     "relation": "DISAGREES"}
  ]
}
```

`relation` is `AGREES`, `DISAGREES`, `UNVERIFIABLE` (no independent outcome) or
`NOT_COMPARABLE` (unknown check). Producer claims never contribute to dimensions or verdict;
they are evidence about the producer, and a disagreement is a warning
(`pap.claims.producer-mismatch`), not a failure reason by itself. The report MUST render the
block under a heading that says the values are producer-supplied and unverified.

### 7.7 Report shape and diagnostics

Appendix C is the normative report schema. Every result carries:

- `reportVersion: "0.1"`;
- `verifier` identity (`id`, `version`, `implementationDigest`, `checkerIdentities[]`);
- `package.identity` (or `null` if the manifest could not be parsed; then verdict `FAIL` and
  integrity `FAIL`);
- `policy` (`id`, `digest`, `state`: `FRESH|STALE|ABSENT`); the reason is carried by a
  diagnostic/limitation, not by an extra field;
- `evaluatedAt`;
- `identities` (package, artifacts, sources, normalized inputs, extension closure, checker,
  verification record);
- `dimensions`, `checks[]`, `coverage`, `limitations[]`, `verdict`, `diagnostics[]`, and
  `producerClaims` when a producer report is present (§7.6);
- `effectiveLimits` when the operator lowered one or more §4.3.4 limits: an object mapping each
  lowered limit name to its effective integer value; absent when every limit is at its default
  (§4.3.4, Appendix C).

A declared claim file that violates its schema or a claim cross-field invariant fails
`integrity.package` (§4.7.1) and therefore the verdict under §7.4 rule 1, even when the check that
would have consumed it is `NOT_EVALUATED`.

Diagnostics are `{code, severity: "error"|"warning"|"info", scope, message}`. Codes are stable
`pap.*` identifiers listed in Appendix J; messages may vary. There is no separate `disposition`
axis in the verifier report: the verdict and dimensions carry the decision, and each diagnostic's
severity says whether it is a hard failure, a limitation, or informational.

### 7.8 Anti-patterns

The following are non-conformant and should fail review or tests:

- returning `PASS` when a declared check is `UNSUPPORTED` or missing;
- presenting `integrity: PASS` as "the package is verified";
- merging `signature.validity` and `trust.signerIdentity` into one status;
- using producer claims to upgrade a status;
- omitting `limitations` for `NOT_EVALUATED`/`UNAVAILABLE`/`STALE` statuses;
- a text output that prints "verified" or a green check for a non-`PASS` verdict.

---


## 8. Witness and check contract

### 8.1 Check specifications and registry

A check specification is a named, versioned, bounded mechanical procedure. v0.1 defines three:

| Check id | Required by default | Purpose |
|---|---|---|
| `pap.check.digest-integrity/1` | yes, when declared in `checkSpecs` or policy | Recompute every declared digest and compare. |
| `pap.check.source-quote/1` | yes, when declared in `checkSpecs` or policy | Verify source byte-range/quote claims against embedded source bytes; when `claims/provenance.json` is absent the check is `NOT_EVALUATED` (§8.1, §8.5), not a vacuous pass. |
| `pap.check.relation-consistency/1` | yes, when declared in `checkSpecs` or policy | Verify entity/relation/edge consistency; when `claims/relations.json` is absent the check is `NOT_EVALUATED` (§8.1, §8.6). |

The package declares its required checks in `checkSpecs`; the trust policy may add more. The
verifier has a registry mapping `(id, version)` to an implementation. An unknown required
specification is `UNSUPPORTED` (§7.2), never silently skipped. A verifier MAY implement a check
with the same id/version and report its own `checkerIdentity`; the identity is part of the
check record, so a consumer can see which implementation produced it.

A required check whose claim file is absent is **not a structural error**: the check is
`NOT_EVALUATED` (`pap.check.not-evaluated`) and the verdict is `INCOMPLETE` (§7.4 rule 4), because
the package is incomplete for that scope. The manifest need not declare a claim file merely
because its check is required; if the claim file is declared, its digest must match the bytes
(§8.4). This is distinct from a missing declared file, which is `FAIL`.

### 8.2 Check record

A verifier-generated check record has this shape (schema in Appendix D.5):

```json
{
  "checkId": "pap.check.digest-integrity/1",
  "checkVersion": "1",
  "subjectDigests": {
    "package": "sha256:...",
    "artifacts": [{"id": "artifact:acme", "digest": "sha256:..."}],
    "sources": [{"id": "SRC-ACME", "digest": "sha256:..."}],
    "inputs": [{"id": "input:requirements", "digest": "sha256:..."}]
  },
  "scope": {"artifacts": ["artifact:acme"], "sources": ["SRC-ACME"],
            "bindings": 2, "entities": 1, "edges": 1},
  "checker": {"id": "pap.verifier.reference", "version": "0.1.0",
              "implementationDigest": "sha256:..."},
  "outcome": "PASS",
  "witnesses": [
    {"type": "recomputed-digest", "subject": {"kind": "artifact", "id": "artifact:acme"},
     "algorithm": "sha256", "declared": "sha256:...", "computed": "sha256:..."}
  ],
  "diagnostics": []
}
```

Rules:

- `subjectDigests` names the exact inputs the check consumed, so a record can be audited without
  guessing. Digests are the identities from §5.
- `scope` states what was covered (counts and ids). A `PASS` on an empty scope is invalid: an
  empty required check is `NOT_EVALUATED`, not a vacuous pass.
- `checker` is the verifier implementation identity (§5.8).
- `outcome` is one of §7.2.
- `witnesses` are recomputable evidence, never producer claims. Producer-supplied `PASS` values
  are structurally impossible to place in a witness (the schema rejects `claimedOutcome`).
- A check record contains no timestamps. Time belongs to the report envelope, so a check record
  is deterministic given its inputs.
- The check-record identity is `H("pap.check.record.v1", JCS(record))`; it is not a report field,
  but the record itself is part of the report's `checks[]` and therefore part of
  `verificationRecordIdentity` (§5.9). `pap explain` MAY surface the record identity (§9.5).
- Witness emission is deterministic: one `recomputed-digest` per compared subject in the order
  artifacts, embedded sources, inputs, declared claims (each in manifest order); one `source-span`
  per evaluated binding in provenance-claim order; one `relation-violation-list` per record with
  violations sorted by `(code, subject, detail)`. Implementations MUST NOT aggregate, deduplicate
  or reorder witnesses, because the check record is inside the verification-record identity
  (§5.9). The only witness field outside that identity is the optional `quoteBase64` (§8.3).
v0.1 pins each record's evidence content so E.4 is reproducible. A record MUST NOT add a subject
array or scope count that its check did not consume:

| Check | `subjectDigests` | `scope` | Witnesses |
|---|---|---|---|
| `digest-integrity/1` | `package`; every declared `artifacts`, `sources`, `inputs`, `claims` entry | `artifacts`, `sources` | one `recomputed-digest` per compared subject |
| `source-quote/1` | `package`; `sources` used; `claims` limited to `provenance` | `sources`, `bindings`, `evaluated`, `unavailable` | one `source-span` per evaluated binding |
| `relation-consistency/1` | `package`; `claims` limited to `relations` | `entities`, `edges` | one `relation-violation-list` |

- The report's top-level `checks[]` contains one record per check the verifier evaluated or
  attempted against a computable package identity, including `NOT_EVALUATED`; a check the verifier
  does not implement (`UNSUPPORTED`) has no checker implementation to name, so it appears in
  `dimensions.checks.results[]` but has no record in `checks[]`. When the manifest itself cannot be
  parsed there is no package identity and no declared check set, so `checks[]` and
  `dimensions.checks.results[]` are both empty and coverage records no required check. A manifest
  that parses but fails schema or cross-field validation keeps its declared check set: every
  declared check is `NOT_EVALUATED` and none is run. Records follow `checkSpecs` order, with
  policy-only required checks appended by `checkId` (§9.9).

### 8.3 Witness types

v0.1 defines three minimal witness types:

| Type | Fields | Independently checkable because |
|---|---|---|
| `recomputed-digest` | `subject`, `algorithm`, `declared`, `computed` | Both values are hashes of bytes the verifier read; anyone can recompute from the package. |
| `source-span` | `sourceId`, `sourceDigest`, `range {start,end}`, `quoteDigest`, `extractedDigest`, `quoteBase64?` | The range and extracted bytes are deterministic; `quoteBase64` is the standard base64 (RFC 4648 §4) encoding of the extracted span, optional and informational for auditability, and is excluded from `verificationRecordIdentity` because the two digests already pin the bytes. |
| `relation-violation-list` | `violations[]` with `code`, `subject`, `detail` | Each violation names ids/edges in the packaged claims; anyone can re-check them. |

A witness MUST be expressible without executing producer code and without reading producer
internals. It MUST be deterministic: same package bytes → same witness value. A witness that
requires a clock, randomness, network or the producer's runtime is not a v0.1 witness.

### 8.4 `pap.check.digest-integrity/1`

Inputs: the parsed manifest, every declared file's bytes, and the declared digests.

Procedure:

1. Recompute `packageIdentity` from the canonical manifest and compare with the report's
   computed identity (there is no declared self-digest; this is reported, not compared).
2. For each artifact: recompute `artifactDigest` and byte count; compare.
3. For each embedded source: recompute `rawSourceDigest`; compare.
4. For each input: recompute `pap.input.file.v1` digest; compare.
5. Recompute `normalizedInputDigest` and compare with `build.normalizedInputDigest` if declared.
6. Recompute each declared claim file digest; compare.

Outcome: `FAIL` if any comparison mismatches; `NOT_EVALUATED` if a required subject is missing
(for example, a declared file cannot be read); otherwise `PASS`.

Witness: one `recomputed-digest` per compared subject, in this order — artifacts in manifest
order, embedded sources in manifest order, inputs in manifest order, declared claims in manifest
order. The `subject.kind` is `artifact`, `source`, `input` or `claim`; for a claim, `id` is the
manifest claim key (`provenance`, `relations`, `producerReport`, `reviews`). Do not aggregate or
deduplicate witnesses, even when several failures are identical. The package identity is not a
compared subject: it has no declared self-digest and is reported in `identities.packageIdentity`,
so the `recomputed-digest` subject kind does not include `package` (Appendix D.5). Diagnostic codes: `pap.integrity.artifact-mismatch`,
`pap.integrity.source-mismatch`, `pap.integrity.input-mismatch`, `pap.integrity.claim-mismatch`,
`pap.package.declared-file-missing`.

What it proves: the packaged bytes match the declared bytes. What it does not prove: that those
bytes are correct, complete, representative or truthful.

### 8.5 `pap.check.source-quote/1`

Inputs: `claims/provenance.json`, embedded source snapshots.

A binding is:

```json
{
  "id": "binding:REQ-1:fragment-1",
  "entityId": "REQ-1",
  "sourceId": "SRC-ACME",
  "locator": {"kind": "byte-range", "start": 120, "end": 178},
  "quote": {"normalization": "none", "digest": "sha256:..."}
}
```

Procedure for each binding:

1. Resolve `sourceId` to a **declared** source (§4.5.2). A `sourceId` that names no declared
   source is a claim cross-field violation — `pap.package.claim-invalid`,
   `integrity.package: FAIL` (Appendix D.1) — not a `NOT_EVALUATED` binding. A declared source
   without an embedded snapshot makes the binding `NOT_EVALUATED` with `pap.source.unavailable`.
2. Check `0 <= start <= end <= sourceByteLength`; otherwise `FAIL` with
   `pap.check.span-out-of-range`.
3. Extract exactly `sourceBytes[start..end)`. Hash it with `H("pap.quote.v1", bytes)` and compare
   with `quote.digest`. Mismatch is `FAIL` with `pap.check.quote-mismatch`.
4. Emit one `source-span` witness with both digests and the range, in provenance-claim order. A
   binding whose range fails step 2 emits no span (its diagnostic records the failure). The
   optional `quoteBase64` may accompany the witness but is excluded from the record identity
   (§5.9).

Outcome: `PASS` if every binding verifies; `FAIL` if any binding's range is invalid or quote
mismatches; `NOT_EVALUATED` if `claims/provenance.json` is absent while the check is required, or
if no binding could be evaluated because all sources are unavailable. A mix of verified and
unavailable bindings yields `NOT_EVALUATED` with `pap.check.partial`, `coverage.full: false` and
verdict `INCOMPLETE`; v0.1 has no policy switch that turns partial coverage into `FAIL`, because a
partial evaluation is a verifier/evidence limitation, not a disproved assertion (partial coverage
never passes).

`quote.normalization` is `"none"` in v0.1: the range's exact bytes are the quote. Producers that
only have whitespace-collapsed matches must locate an exact byte range themselves; the package
does not import a Markdown adapter and the verifier does not implement one.

What it proves: the declared span exists and its bytes match the declared quote digest. What it
does not prove: that the quote supports the entity's claim, that the span is the *only* or
*best* evidence, or that the artifact's rendered text is faithful. That is the binding-vs-
verification boundary of #37.

### 8.6 `pap.check.relation-consistency/1`

Inputs: `claims/relations.json`, shape:

```json
{
  "papClaimsVersion": "0.1",
  "entities": [{"id": "REQ-1", "kind": "requirement"}],
  "relations": [{"name": "examples", "from": "requirement", "to": "example",
                 "inverse": "requirement"}],
  "edges": [{"relation": "examples", "from": "REQ-1", "to": "EXAMPLE-1"}]
}
```

Procedure:

1. Entity ids are unique (`pap.claim.duplicate-entity`).
2. Relation names are unique (`pap.claim.relation-duplicate`).
3. Every edge's `relation` is declared (`pap.claim.relation-unknown`).
4. Every edge endpoint resolves to a declared entity (`pap.claim.edge-unknown-entity`).
5. `from`/`to` entity kinds match the relation declaration (`pap.claim.relation-kind-mismatch`).
6. For every relation `R` that declares `inverse: S`: `S` is declared
   (`pap.claim.inverse-missing`); `S.inverse` is exactly `R`
   (`pap.claim.inverse-not-reciprocal`); and `S.from` equals `R.to` with `S.to` equal to
   `R.from` (`pap.claim.inverse-kind-mismatch`). This is the package-level counterpart of
   the engine's bidirectional inverse contract (#36).
7. For every edge `(R, from, to)` where `R` declares inverse `S`, a reciprocal edge
   `(S, to, from)` exists (`pap.claim.inverse-missing`).

Outcome: `PASS` if no violation; `FAIL` if any violation; `NOT_EVALUATED` if the claim file is
absent while the package declares the check required.

Witness: exactly one `relation-violation-list` per record, with the exact violating ids/edges
sorted deterministically by `(code, subject, detail)`; for `PASS` the list is present and empty.
Do not split, merge or reorder records.

What it proves: the declared relation claims are internally consistent. What it does not prove:
that the relations are semantically correct or complete.

### 8.7 Reproducibility requirements

A conforming check:

- is a pure function of its declared inputs (package bytes, trust policy, `--now`);
- uses no network, no clock except `--now`, no randomness, no environment-dependent ordering;
- sorts every output collection by an explicit key (code, id, path) and never by filesystem
  order or locale;
- is bounded by the resource limits in §4.3.4 and fails as `NOT_EVALUATED` (with
  `pap.package.limit-exceeded`) rather than exhausting memory;
- emits stable diagnostic codes; messages may vary;
- has no side effects on the package directory (verification is read-only).

### 8.8 Unsupported and incomplete behaviour

- A required check that is not in the registry is `UNSUPPORTED` and the verdict is `UNSUPPORTED`
  (or higher precedence rule).
- A required check whose inputs are missing is `NOT_EVALUATED` and the verdict is `INCOMPLETE`.
  v0.1 has no policy switch that promotes missing evidence to a hard failure: absence of evidence
  is reported as incompleteness, never as a disproved or a passed assertion.
- A partial evaluation (some bindings/sources evaluated, some unavailable) never yields `PASS`;
  it yields `NOT_EVALUATED` and `coverage.full: false`, with each unavailable item in
  `limitations`.
- The verifier evaluates every declared check, optional or required, and reports its outcome
  (`dimensions.checks.results[]`); only required checks gate the verdict. A package whose required
  set is empty — every declared check optional and no policy requirement — is `INCOMPLETE` with
  `pap.package.empty-check-specs`; there is no basis for `PASS` (§4.4.3, §7.4 rule 4).

### 8.9 Producer claims are never sufficient

The producer can claim `PASS` in `claims/producer-report.json`; the verifier parses it as data
only. The schema of a producer claim has `claimedOutcome`, never `outcome`/`witnesses`; a check
record's schema has `outcome`/`witnesses`, never `claimedOutcome`. A producer-claimed `PASS`
while an independent check fails produces `FAIL` for the verdict and a
`pap.claims.producer-mismatch` diagnostic in the comparison block. There is no code path in
which producer data updates a dimension status.

### 8.10 What the checks do not prove

The three checks prove only the properties above. They do not prove that the artifact is a
correct or complete contract, that the source snapshot is authentic or from the claimed origin,
that the quoted span supports the entity, that relations are semantically right, or that a human
approved anything. The report must preserve this boundary; the `semanticTruth` and
`legalEnforceability` dimensions make it explicit.

---


## 9. CLI contract

The verifier command is `pap`: a single-purpose consumer that parses a package directory, computes
identities, evaluates the v0.1 checks, optionally applies an operator-supplied trust policy, and
reports what it found. It never produces a package. This section defines the command surface,
streams, exit codes, output contract, clock handling, determinism and offline behaviour. It does
not itself authorize an implementation; the Phase 2 authorization is recorded in §2.4 (§13,
roadmap #43 Phases 2–3).

Command names, flags, exit codes and required output lines are normative. Human wording, column
widths, progress display and implementation language are not. Where this section and §4–§8
disagree about package or result semantics, those sections win.

### 9.1 Position, distribution and packaging

`pap` is a **separate open-source project** from the producer: its own repository, maintainers,
release cadence and licence, versioned independently of the package format. The producer MUST NOT
ship the verifier as a subcommand of its own CLI.

| Version surface | Owner | Meaning |
|---|---|---|
| verifier version | `pap` project | semver of the tool; changes with implementation, not format |
| `papVersion` support range | `pap` project | format versions accepted (`0.1` here) |
| `reportVersion` support | `pap` project | report-schema versions emitted (`0.1` here) |
| trust-policy schema | Appendix B | policy document accepted |
| `papVersion` | producer / this RFC | format version in the manifest |

1. Each platform release MUST publish a **pinned artifact**, a published **SHA-256 checksum** and
   instructions that verify it. A release that cannot be checked against a published checksum is
   not a conforming distribution; a release signature is encouraged but optional in v0.1
   (key management is deferred, §14.1).
2. The artifact MUST NOT depend on Contract Builder: no source, package, service, runtime or
   subcommand. The only shared artifacts are this RFC, Appendices A–E, the §12 fixtures and
   Appendix J.
3. No runtime is required by the contract. A reference implementation may be a standalone
   Bun/TypeScript binary, an OS package or a container image; conformance is §4–§12 plus the
   vectors, not the build form.
4. Installation and verification MUST work offline: no updates, trust roots, schemas or policy
   material fetched at verification time. Updating the binary through the operator's package
   channel is outside this contract.
5. Post-install, the binary MUST be invocable as `pap` on `PATH`. A library may also be published;
   this contract applies to the executable entry point. The binary and policy are inside the
   operator's trust base (§15.3); their compromise is a limitation, not a security certificate.

### 9.2 Command surface, options, `--version`, `--help`

```text
pap verify PACKAGE [--trust-policy FILE] [--format text|json] [--now RFC3339]
pap inspect PACKAGE [--format text|json]
pap explain PACKAGE --check CHECK_ID [--format text|json]
pap --version
pap --help
```

- `PACKAGE` is exactly one positional argument naming an existing directory. A symbolic link to a
  directory names an existing directory and is permitted after resolution (§4.3.2); a link that
  does not resolve is `pap.package.not-found` (exit 74). v0.1 is directory-only (D1): archive
  files, OCI references, URLs and `-` are not packages.
- Options follow the command in any order; `--flag value` and `--flag=value` are both accepted;
  `--` ends option parsing so a path may start with `-`. `--format` accepts exactly `text`
  (default) or `json`, for all three commands.
- `--trust-policy FILE` is accepted only by `verify` (one local Appendix B file). `inspect` and
  `explain` MUST reject it: they are not verification commands and MUST NOT substitute for
  `verify`. `--now RFC3339` is accepted only by `verify` (it fixes the evaluation clock, §9.8);
  `inspect` and `explain` have no report envelope and no clock-dependent status.
- `--check CHECK_ID` is accepted only by `explain`, exactly once, and MUST match
  `^pap\.check\.[a-z0-9-]+/[0-9]+$`. It MUST name a check declared in the package's `checkSpecs`;
  a well-formed id naming nothing in the package is a usage error (`pap.cli.unknown-check`).
- Repeated single-valued options, unknown options, missing option values, missing/extra
  positionals and empty arguments are usage errors: exit 64, `pap.cli.usage` on stderr, no report.
- No environment variable and no discovered configuration file may change a verdict; locale,
  timezone, `PATH` and `HOME` MUST NOT matter. Only the two path arguments may legitimately
  depend on the caller's environment. v0.1 has no colour flag and MUST NOT emit ANSI colour by
  default; `NO_COLOR` is irrelevant. `pap` alone or an unknown command prints the synopsis to
  stderr and exits 64; stdin is never read by any command.
- `pap --version` prints to stdout, one line each, exit 0: `pap <verifier-version>`,
  `papVersion support: 0.1`, `reportVersion support: 0.1`,
  `implementationDigest: sha256:<64 lowercase hex>`. The support line lists the exact supported
  `major.minor` values, comma-separated ascending, with no spaces; v0.1 prints `0.1`. The printed
  digest is `verifier.implementationDigest`, the binary's own checker closure, equal to the
  `implementationDigest` of its checker identity when one binary implements every check (§5.8); it
  is the value a policy `checkers[]` pin compares, and the full checker identity also appears in
  every check record. `pap --version` MUST NOT read a package or policy. `pap --help` prints the
  synopsis and §9.7 exit-code table to stdout, exit 0; `pap <command> --help` prints that command's
  synopsis, exit 0. The help and version forms are the only ones that do not require `PACKAGE`;
  `pap --help verify` is a usage error.

### 9.3 `pap verify`

Inputs: `PACKAGE`; optional policy file; format; optional fixed clock. Steps are normative in
§4–§8: validate the command line; read `assurance-package.json` within the §4.3.4 limits;
validate against Appendix A and the strict-core/extension rules (§4.9) with JCS (§4.10, §5.2);
read each declared payload once and compute the §5 identities; evaluate the required checks
(§8.1, §8.4–§8.6); if a policy is supplied, validate it, apply freshness/recognition and evaluate
envelopes when its signature mode is not `disabled` (§6, §11); compute dimensions, coverage and
verdict (§7.3–§7.5); render the report (§9.6) and exit per §9.7.

Trust-policy handling:

| Policy situation | Behaviour |
|---|---|
| no `--trust-policy` | report produced; `policy.state: "ABSENT"`; trust dimensions `NOT_EVALUATED` (or `signerIdentity: NOT_APPLICABLE` for an unsigned package); `signature.validity: NOT_APPLICABLE` for an unsigned package and `NOT_EVALUATED` when an envelope is present (no key material); limitation `pap.trust.policy-absent`. `PASS` is possible only because no policy requires signatures or trust. |
| missing, unreadable, invalid JSON or failing Appendix B | **fail closed**: exit 64, `pap.trust.policy-invalid` on stderr, **no package report**. The verifier MUST NOT fall back to absent-policy behaviour — that would silently downgrade trust. |
| present and fresh | `policy.state: "FRESH"`; recognitions/signer decisions evaluated; `policy.digest` reported (`pap.trust-policy.v1`), supplied by the operator and not overridable by the package. |
| present, outside its validity window | report produced; `policy.state: "STALE"`, `policyDecision: "STALE"`; verdict `INCOMPLETE` (exit 2). A stale policy never supports `PASS`. |
| fails checker/profile recognition | `trust.checkerRecognition`/`profileRecognition` per §7.3; verdict per §7.4. |

A valid signature never establishes truth, authority or intent; §6 and §7.3 keep those
distinctions. Multiple envelopes are reported per envelope in
`dimensions.signature.signatures[]` (`path`, `keyId`, `algorithm`, `validity`, `signerIdentity`,
`policyDecision`); the aggregate `dimensions.signature.validity` covers the policy-required set
(Appendix C). A present envelope that is `INVALID`, or whose signer is `UNKNOWN`/`UNTRUSTED`, blocks
`PASS` even under signature mode `optional`. In mode `disabled` envelopes are not read at all
(§6.5); that is the operator opting out of signature evaluation, not the verifier ignoring evidence
it was asked to weigh. If the manifest cannot be parsed, the report still exists:
`package.identity: null`, `integrity.package: FAIL`, verdict `FAIL`, exit 1 (§7.7); the verifier
invents no identity.

### 9.4 `pap inspect`

`inspect` describes what the package declares and what the verifier can read, without producing a
verification result.

- Accepts `PACKAGE` and `--format` only; rejects `--trust-policy` and `--now` (exit 64). It MUST
  NOT evaluate trust, signatures, checks or dimensions, and MUST NOT print `VERDICT:`, `NOT A
  PASS`, or any verification-looking text. Text starts with
  `INSPECTION: COMPLETE|PARTIAL|INVALID|UNSUPPORTED` and contains `NOT A VERIFICATION`; the word
  `verified` is forbidden here as everywhere.
- It lists declared payloads (`artifacts`, `inputs`, `sources`, `claims`, signature envelope
  names), computes §5 identities for readable bytes, and reports declared-versus-computed digests
  as data. A digest mismatch is displayed and noted but does not become a verdict.
- Unreadable declared payloads or a limit stop make the inspection `PARTIAL`; manifest schema,
  path-grammar, duplicate-path or unsafe-file violations make it `INVALID`; unknown required
  features/critical extensions make it `UNSUPPORTED`. A digest mismatch alone changes neither.
- JSON output is one JCS document: `inspectionVersion: "0.1"`, `verifier`, `package`,
  `declared[]` (`{kind, id?, path, declared, computed, bytes?}`, `kind` ∈
  `artifact|input|source|claim|signature`, `computed: null` if unread), `identities`,
  `inspection`, `limitations[]`. The full inspection schema is published with the verifier
  (§13.7); Appendix C remains the `verify` report schema.
- Exit: 0 complete, 2 partial, 1 invalid structure, 4 unsupported required feature/extension,
  plus global 64/70/74. Never 3: `inspect` makes no trust decision. The document is authoritative
  and the exit code a summary; `inspect` output MUST NOT be quoted as a pass.

### 9.5 `pap explain`

`explain` explains one check specification's inputs, procedure, outcome and evidence.

- Accepts `PACKAGE`, `--check CHECK_ID` exactly once, and `--format`; rejects `--trust-policy` and
  `--now`. The three v0.1 checks are mechanical functions of package bytes (§8.4–§8.6), so no
  policy or clock is needed; trust recognition is a `verify`-level dimension. An id not declared
  in `checkSpecs` → exit 64, `pap.cli.unknown-check`, no document. Declared but unimplemented →
  `UNSUPPORTED`, exit 4; declared but inputs unavailable (missing source snapshot/claim file,
  limit) → `NOT_EVALUATED`, exit 2.
- Text MUST NOT print a package verdict and MUST say so. It contains at least `CHECK: <id>`,
  `OUTCOME: <outcome>`, `subjectDigests`, `scope`, `checker`, each `witness` (`source-span`: range
  and both digests; `relation-violation-list`: violations), and every diagnostic with severity.
- JSON output is one JCS document:
  `{explanationVersion: "0.1", package, checkRecord, limitations}`, `checkRecord` per Appendix D.5.
  Exit follows the explained outcome: `PASS` 0, `FAIL` 1, `NOT_EVALUATED` 2, `UNSUPPORTED` 4;
  never 3; global 64/70/74 unchanged.

### 9.6 Streams, formats and text output

- **stdout** carries only the report, inspection or explanation document. With `--format json` it
  is exactly **one JCS document followed by exactly one LF**: no BOM, no pretty-printing, no text
  before or after the object, no log lines. With `--format text` it is the human rendering and
  nothing else.
- **stderr** carries usage messages and hard-failure diagnostics (exit 64/70/74). On any report
  run (exit 0–4) stderr MUST be empty. Diagnostics that belong to a result — failures, unsupported
  features, missing evidence, limitations — live in `diagnostics[]`/`limitations[]`, never on
  stderr. stdin is never read. Output is UTF-8 without BOM, LF line endings, `evaluatedAt` in UTC
  `Z`, integers only (D2), no locale- or language-specific formatting.
- For `verify`, JSON validates against Appendix C (which includes the
  `dimensions.signature.signatures[]` entries of §9.3). `inspect` and `explain` emit the documents
  of §9.4–§9.5. A consumer parses them with any I-JSON parser plus the published schema; it MUST
  NOT need the verifier's source.
- Text output for `verify`: (1) first line exactly `VERDICT: <verdict>` with the upper-case §7.4
  token; (2) for every non-`PASS` verdict the next line begins with the exact token
  `NOT A PASS`, followed by nothing or by ` — ` and one reason clause on the same line, and it
  MUST NOT appear for `PASS`; (3) a dimension table listing every Appendix C dimension path
  (`integrity.package`, `integrity.artifacts`, `sources.integrity`, `sources.availability`,
  `signature.validity`, `trust.signerIdentity`, `trust.policyDecision`,
  `trust.checkerRecognition`, `trust.profileRecognition`, `humanReview.status`,
  `semanticTruth`, `legalEnforceability`) with its exact §7.3 status token, plus one line per
  required and optional check showing the exact `checkId` and §7.2 outcome token; (4) all
  `coverage` integer counters, `requiredChecks`, `requiredDimensions` and the `full` flag;
  (5) every limitation's `code` and `detail`, or `none` explicitly; (6) producer claims under the
  exact heading `PRODUCER CLAIMS (UNTRUSTED — NOT VERIFICATION RESULTS)`, showing `claimed`,
  `independentOutcome` and `relation`, never in the dimension table; (7) package identity,
  `papVersion`, verifier version, policy id/digest/state, `evaluatedAt`, and `effectiveLimits`
  when present; (8) when `humanReview.status` is `PASS`, the line
  `humanReview.basis: unbound-claim — unverified producer claim, not authenticated approval`;
  (9) no absolute host paths, duration, colour, check-mark glyphs or the word `verified` as a
  result. Text is fixed-layout and TTY-independent: the same
  semantic report renders identical bytes regardless of `TERM`, `COLUMNS` or redirection. Wording
  beyond these lines, column widths and abbreviations are non-normative; machine consumers use
  `--format json`, and `inspect`/`explain` text requirements are in §9.4–§9.5.

### 9.7 Exit codes and precedence

| Condition | Exit | Document on stdout |
|---|---|---|
| verdict `PASS` | 0 | yes |
| verdict `FAIL` | 1 | yes |
| verdict `INCOMPLETE`, or aggregate `NOT_EVALUATED` | 2 | yes |
| verdict `UNTRUSTED` | 3 | yes |
| verdict `UNSUPPORTED` | 4 | yes |
| usage error, including invalid/unreadable trust policy, a `PACKAGE` that is not a directory, or `explain` without/with an undeclared `--check` | 64 | no |
| internal verifier failure | 70 | no |
| `PACKAGE` missing or unresolvable, or an I/O failure such as output unwritable | 74 | no |

- `NOT_EVALUATED` is a §7.4 aggregate verdict, not a check outcome, and has no dedicated code; it
  maps to 2 (neither pass nor package failure). Consumers needing the distinction read `verdict`.
  64, 70 and 74 produce **no** report. Exit 74 uses `pap.package.not-found` when the `PACKAGE` is
  missing or does not resolve, and `pap.io.error` for any other I/O failure such as an unwritable
  output; the remaining codes are `pap.cli.usage` and `pap.internal.error` (plus
  `pap.trust.policy-invalid` or `pap.cli.unknown-check` where they apply), written to stderr as
  `pap: <code>: <message>` and MUST NOT be parsed as a report.
- A resolved `PACKAGE` whose manifest is readable but whose root, or a directory under it, cannot
  be listed is not an exit-74 I/O failure: it is the §4.3.3 undeclared-file scan-incomplete
  condition (`pap.package.undeclared-scan-incomplete`, `coverage.full: false`, verdict at most
  `INCOMPLETE`), and a report is produced. A manifest that cannot be read is likewise a
  report-level `pap.package.io` failure with verdict `FAIL` (§7.7), not exit 74.
- **The report is authoritative; the exit code is a gate.** The exit code summarises the verdict
  and collapses multiple causes by §7.4 precedence: a failed check plus an untrusted signer exits
  1 and the report carries both. A consumer MUST NOT infer "package invalid" from a non-zero exit;
  it reads `verdict`, `dimensions` and `diagnostics`.
- The mapping is exhaustive and exact: `PASS`↔0, `FAIL`↔1, `INCOMPLETE`/`NOT_EVALUATED`↔2,
  `UNTRUSTED`↔3, `UNSUPPORTED`↔4. No other meanings. Exit 0 MUST NOT be returned for a non-`PASS`
  verdict. The exit code is not a security boundary and never replaces the report.

### 9.8 Clock, freshness and `--now`

- The evaluation clock is the **local system clock**, read once per run, unless `--now` is given.
  The local clock is operator-controlled and trusted only to the extent the policy already trusts
  the binary and policy (§15.3).
- `--now RFC3339` fixes the clock for that run and MUST match the Appendix A `date-time` profile
  `YYYY-MM-DDTHH:MM:SS[.fraction](Z|±HH:MM)`: the fraction, when present, is 1–9 digits; `:60`
  (leap second) is rejected; offsets are normalised to UTC; the value is compared as an instant.
  It is used both as `evaluatedAt` and for every freshness decision. Unparsable input is a usage
  error (64, `pap.cli.usage`). `evaluatedAt` is the normalised UTC instant rendered with `Z`, with
  the fraction preserved and trailing zeros stripped; without `--now` it is the local clock read
  once per run, rendered the same way.
- Policy issuance/expiry and review freshness use the evaluation clock (§5.11). `--now` exists for
  deterministic tests and reproductions; production use is an open question (§16.1(6)), not made
  safe by this format. Package timestamps are records of claims, never evidence about when
  verification happened, and never override the clock.
- Host timezone MUST NOT affect status decisions; the clock renders in UTC. The validity window
  is closed at both ends and has no clock-skew tolerance (§6.4): an instant equal to `issuedAt` or
  `expiresAt` is fresh, and one second outside the window is `STALE` with the directional code.
  Cases F47–F49 pin the boundary; the future-skew allowance for producer-claimed review
  timestamps is separate (§6.7).

### 9.9 Determinism

The report is a pure function of package bytes, policy bytes (if any), the fixed clock and the
verifier build; the following rules make that reproducible.

- JSON is JCS, so key order and whitespace are canonical. Arrays are ordered by explicit keys,
  never by filesystem or hash-map iteration: `checks[]` and `dimensions.checks.results[]` in
  `checkSpecs` order with policy-only required checks appended by `checkId`;
  `diagnostics[]` by severity rank (`error` < `warning` < `info`), then `code`, then `scope`;
  `limitations[]` by `code` then `detail`; `coverage.requiredChecks` in `checkSpecs` order then
  policy-only required checks by `checkId`; `coverage.requiredDimensions` in the Appendix B
  enumerable order (§7.5); `dimensions.signature.signatures[]` by `path` then `keyId`;
  `verifier.checkerIdentities[]` ascending; `producerClaims.comparison[]` by `checkId`;
  `identities.artifacts[]` and `identities.sources[]` in manifest declaration order; `inspect`'s
  `declared[]` by `kind` then `path`.
- Check records contain no timestamps (§8.2). No field carries a random value, host name, user
  name, process id, temporary path, locale-formatted number, or a duration in text.
- The fields excluded from `verificationRecordIdentity` (§5.9) are `evaluatedAt`, `durationMs`,
  host-specific `package.path`/`policy.path`, human `diagnostics[].message` and
  `checks[].diagnostics[].message` wording, the informational `producerClaims` block and the
  optional `checks[].witnesses[].quoteBase64`. Every check record, outcome, subject, scope,
  checker and required witness field stays in the identity, so a fixed implementation renders the
  same record identically for the same inputs. v0.1 text omits durations and paths, so fixing the
  clock fixes the text.
- Same package bytes, policy bytes, verifier build and `--now` → byte-identical JSON after removing
  identity-excluded fields, identical text, identical `verificationRecordIdentity`. Without
  `--now`, only `evaluatedAt` (and `durationMs` if emitted) may differ; record identity still
  agrees.
- Verification is read-only: no lock, cache or temporary file, and the package directory is
  unchanged after the run.

### 9.10 Offline operation and absence of a producer runtime

During any command the verifier:

1. MUST NOT open a network socket, resolve a name, read proxy/credential material or contact a
   producer, registry, transparency log or status service. Networking disabled MUST not change
   output or exit code.
2. MUST NOT import, link, spawn, shell out to or depend on Contract Builder — its CLI, library,
   runtime, package manager or service. A host without the producer installed MUST produce
   identical output. The producer is an input author, not a dependency.
3. MUST NOT execute package-supplied code: no profile hook, renderer, template, Markdown adapter,
   module, script, wasm, plugin or expression. Media types are advisory (§4.6); payloads are
   opaque bytes. MUST NOT create subprocesses or load native extensions from the package: file
   reads are limited to the package tree, the explicitly named policy file and process resources;
   no configuration discovery from environment, home or current directory; no writes outside
   stdout/stderr; no path outside the package root is followed (§4.3.2). Resolving the
   operator-supplied `PACKAGE` argument to its real path (§4.3.2) is not “following a path outside
   the package root” for this rule; after resolution, no declared payload path may leave the
   resolved root.

Conformance case F40 checks this with a producer-free environment, sentinel `PATH` shims and
network denial; a verifier needing network, a producer import or package-supplied code is
non-conformant, and such a dependency invalidates the §13.4 independence claim.

### 9.11 Resource limits

Numeric defaults are normative in §4.3.4; this section fixes the CLI-visible behaviour.

- Limits MUST be enforced while reading, before a payload can exhaust memory: stop at the limit,
  never crash, hang or allocate unboundedly; hashing may stream, and the limit applies to bytes
  admitted. Exceeding a limit yields `pap.package.limit-exceeded` with the limit name and observed
  value. When the manifest still parses, affected dimensions/checks become `NOT_EVALUATED`,
  `coverage.full` is `false`, verdict `INCOMPLETE` (exit 2). If the limit prevents parsing the
  manifest, `package.identity: null`, `integrity.package: FAIL`, verdict `FAIL`, exit 1 (§7.7) —
  still no crash.
- A limit MUST NOT be silently raised, ignored or converted into `PASS`; a policy may only lower
  a default (§6.3.2), and a raised limit is a policy error. Lowered limits are reported in the
  report's `effectiveLimits` object (§4.3.4, Appendix C), and a result computed under non-default
  limits MUST NOT be presented as computed under the defaults.
- A violation of the output contract (for example a stdout write failure) is an I/O failure
  (exit 74), not a package verdict.

### 9.12 Worked transcripts

Examples use the Appendix F package (fixture `F01-unchanged`). `sha256:…` abbreviates a full
64-hex digest in this document only; the verifier prints full digests. The package identity is
the Appendix E vector `sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020`.

PASS — package verifies, policy fresh, signature mode `disabled`:

```text
$ pap verify fixtures/pap-v0.1/F01-unchanged \
    --trust-policy fixtures/pap-v0.1/trust-policy/unsigned-valid.json \
    --now 2026-11-02T00:00:00Z
VERDICT: PASS
package: sha256:77a8d1d0…9020 (papVersion 0.1)
verifier: pap 0.1.0  policy: sha256:… state: FRESH  evaluatedAt: 2026-11-02T00:00:00Z
dimensions
  integrity.package PASS
  integrity.artifacts PASS
  sources.integrity PASS
  sources.availability PASS
  signature.validity NOT_APPLICABLE
  trust.signerIdentity NOT_APPLICABLE
  trust.policyDecision NOT_EVALUATED
  trust.checkerRecognition NOT_APPLICABLE
  trust.profileRecognition NOT_APPLICABLE
  humanReview.status NOT_APPLICABLE
  semanticTruth NOT_EVALUATED
  legalEnforceability NOT_EVALUATED
checks
  pap.check.digest-integrity/1 PASS
  pap.check.source-quote/1 PASS
  pap.check.relation-consistency/1 PASS
coverage: checksEvaluated 3, checksPassed 3, checksFailed 0, checksUnsupported 0,
  checksNotEvaluated 0, dimensionsEvaluated 3, full: true
limitations: none
PRODUCER CLAIMS (UNTRUSTED — NOT VERIFICATION RESULTS)
  pap.check.digest-integrity/1 claimed PASS independent PASS AGREES
$ echo $?
0
```

INCOMPLETE — source declared but referenced-only, so source-dependent checks cannot run:

```text
$ pap verify fixtures/pap-v0.1/F27-referenced-source --now 2026-11-02T00:00:00Z
VERDICT: INCOMPLETE
NOT A PASS — required checks were not evaluated
package: sha256:… (papVersion 0.1)  verifier: pap 0.1.0  policy: none state: ABSENT
evaluatedAt: 2026-11-02T00:00:00Z
dimensions
  integrity.package PASS
  integrity.artifacts PASS
  sources.integrity UNAVAILABLE
  sources.availability UNAVAILABLE
  signature.validity NOT_APPLICABLE
  trust.signerIdentity NOT_APPLICABLE
  trust.policyDecision NOT_EVALUATED
  trust.checkerRecognition NOT_EVALUATED
  trust.profileRecognition NOT_EVALUATED
  humanReview.status NOT_APPLICABLE
  semanticTruth NOT_EVALUATED
  legalEnforceability NOT_EVALUATED
checks
  pap.check.digest-integrity/1 NOT_EVALUATED
  pap.check.source-quote/1 NOT_EVALUATED
  pap.check.relation-consistency/1 PASS
coverage: checksEvaluated 1, checksPassed 1, checksFailed 0, checksUnsupported 0,
  checksNotEvaluated 2, dimensionsEvaluated 1, full: false
limitations
  pap.source.unavailable — source SRC-ACME-POLICY has no embedded snapshot
  pap.check.not-evaluated — required checks have no evaluable source input
$ echo $?
2
```

FAIL — one artifact byte changed while the manifest still declares the old digest:

```text
$ pap verify fixtures/pap-v0.1/F02-artifact-byte --now 2026-11-02T00:00:00Z
VERDICT: FAIL
NOT A PASS — a required integrity assertion did not hold
package: sha256:… (papVersion 0.1)  verifier: pap 0.1.0  policy: none state: ABSENT
dimensions
  integrity.package PASS
  integrity.artifacts FAIL
  sources.integrity PASS
  sources.availability PASS
  signature.validity NOT_APPLICABLE
  trust.signerIdentity NOT_APPLICABLE
  trust.policyDecision NOT_EVALUATED
  trust.checkerRecognition NOT_EVALUATED
  trust.profileRecognition NOT_EVALUATED
  humanReview.status NOT_APPLICABLE
  semanticTruth NOT_EVALUATED
  legalEnforceability NOT_EVALUATED
checks
  pap.check.digest-integrity/1 FAIL
  pap.check.source-quote/1 PASS
  pap.check.relation-consistency/1 PASS
coverage: checksEvaluated 3, checksPassed 2, checksFailed 1, checksUnsupported 0,
  checksNotEvaluated 0, dimensionsEvaluated 3, full: true
diagnostics
  pap.integrity.artifact-mismatch error artifact:acme-supplier:
  declared sha256:5f521a6b…dd51, computed sha256:0b7e…
$ echo $?
1
```

---


## 10. Threat model and package parser safety

A package is hostile input. This section states the assets, adversaries, assumptions, threats with
mitigations and residual risks, and the concrete safe defaults and resource limits. The
directory-only decision (D1, §4.2) removes a large class of parser attacks up front; the remaining
threats are mostly bounded resource use, identity and policy substitution, and misleading evidence.

### 10.1 Assets

| Asset | Why it matters | Primarily exposed by |
|---|---|---|
| A1 — verdict and report integrity | the report is the relying party's evidence; a forged or over-optimistic report defeats the format | producer claims, dimension conflation, report confusion |
| A2 — operator's trust anchors and policy | trust decisions are only as good as the keys, identities and pins the operator chose | policy substitution, key mix-up |
| A3 — artifact and payload bytes | integrity claims are about these exact bytes | digest substitution, TOCTOU, path tricks |
| A4 — source and human-review evidence | provenance and approval claims are checked against them | misleading snapshots, scope binding, stale evidence |
| A5 — verifier host availability | a malicious package must not exhaust memory, CPU or disk | archive bombs, oversized/deep JSON, unbounded arrays |
| A6 — confidentiality of package content | the verifier should not leak package content or paths beyond the report | diagnostics and text output that echo arbitrary bytes |
| A7 — auditability of a past decision | a later reviewer must reconstruct what was checked and which policy decided | missing policy digest, missing limitations, non-deterministic reporting |
| A8 — verifier binary and its dependencies | a compromised verifier can say anything | supply chain, build provenance (out of scope v0.1) |

The assets are reported evidence, not the subject matter. The verifier does not protect the truth
of the artifact; it protects the accuracy of its own limited statements.

### 10.2 Adversaries and capabilities

| Adversary | Capability assumed | Goal | Handled in v0.1? |
|---|---|---|---|
| Malicious package author | can craft every file, path, claim and manifest field; cannot run code in the verifier | get a favourable verdict for a package that does not deserve it | yes |
| Compromised producer | can emit internally consistent packages and misleading claims; may not hold a signing key | misrepresent evidence | partly: claims are untrusted, but a consistent lie is not detectable |
| Compromised signer | holds a valid signing key; can sign arbitrary manifests as that key | pass a policy that trusts that key | no: key compromise and revocation are out of scope |
| Malicious checker or profile **author** | can influence producer-side tooling and package metadata; cannot inject code into the verifier | fake check outcomes, profile identity substitution | yes: no producer code runs; checker is verifier-side; profile is data |
| Network attacker | can intercept or modify transfers | substitute package, policy or binary | not applicable offline; out of scope |
| Local attacker with write access | can replace the package, policy, verifier or clock | change any decision | out of scope, stated residual |
| Operator misconfiguration | can accept too much (empty allowlist, stale policy, `disabled` mode where trust is assumed) | false assurance without an attacker | partly: safe defaults, diagnostics, limitations |
| Verifier supply-chain attacker | can tamper with the verifier binary or its dependencies | arbitrary false results | out of scope v0.1; recorded as a limitation |

### 10.3 Assumptions

The v0.1 threat model relies on these assumptions; each is stated as a limitation in the report or
in §15.3 where it affects a verdict:

1. The verifier binary was obtained through a channel the operator trusts and is not modified
   locally; the operating system, filesystem and CPU provide the isolation and memory safety the
   verifier relies on, so parser memory-safety defects remain a residual risk (§10.6).
2. The verifier's clock (or an injected `--now`) is correct within a reasonable skew; policy and
   review freshness depend on it. There is no authenticated time in v0.1.
3. The trust policy reached the verifier through a channel the operator trusts; the policy is not
   signed in v0.1 and can be replaced by a local attacker.
4. The package directory is attacker-controlled in content but is not being mutated concurrently
   by a hostile process; a local writer with the operator's privileges is out of scope.
5. SHA-256 is collision-resistant and Ed25519 signatures are unforgeable under the policy keys;
   the underlying cryptographic libraries are correct.
6. The JSON parser, canonicalizer and digest implementations conform to the RFC and pass
   Appendix E vectors; a divergence is a verifier defect, not a permitted variation.
7. The consumer reads `verdict`, `dimensions` and `limitations[]` from the report and does not act
   on an exit code or a text line alone (§7.7).
8. No network is available or used; URL-like values in package data are never fetched.
9. Package paths are ASCII and directory-only (§4.3.1): an archive or non-ASCII path is not part of
   v0.1, so Unicode/case-folding attacks are outside the parsed surface.

### 10.4 Threat table

Every bullet of issue #44 §7 is represented. The "scope" column says whether the threat is
mitigated in v0.1, accepted as residual, or explicitly deferred.

| ID | Threat | Attack surface | Default mitigation / limit | Residual risk | Scope v0.1 |
|---|---|---|---|---|---|
| T1 | Path traversal: `..`, empty segments, leading `/`, backslashes, NUL | declared paths in the manifest and claim references | full path grammar validated before any filesystem access (§4.3.1); reject with `pap.package.path-invalid`; only declared paths are opened; no path is ever joined before validation | none known on the validated surface | in scope |
| T2 | Absolute paths, drive letters, UNC prefixes, URLs | any declared path or claim path | grammar admits only `[A-Za-z0-9._-]` segments and `/`; everything else is invalid (`pap.package.path-invalid`); URL-like strings in claims are data, never fetched | none known | in scope |
| T3 | Symlink escape: a payload path is a symlink to an outside file or to a special file | package directory entries | open without following symlinks where the platform supports it; `lstat`/regular-file check; reject `pap.package.symlink` or `pap.package.non-regular`; verify the resolved path stays under the package root (`pap.package.path-escape`); only regular files are read | hard links are not detectable portably (stated); a local attacker racing the filesystem is out of scope | in scope |
| T4 | Duplicate or case-colliding paths; two declarations for one file | manifest arrays, filesystem case rules | path identity enforced across all declared payloads; duplicate and case-folded duplicates are invalid (`pap.package.path-duplicate`); manifest name cannot be a payload (`pap.package.manifest-self-reference`) | a case-insensitive filesystem may alias names before the verifier's comparison, but the declared path set is still checked; no content is chosen by ambiguity | in scope |
| T5 | Archive bomb / decompression bomb / infinite extraction | none in v0.1 (directory only); deferred if an archive is adopted | no archive parser exists; directory limits cap files, file bytes, total bytes and paths (§4.3.4); if archive transport is ever added, the deferred rules in §10.7 apply | archive attacks cannot occur because archives are not parsed; the deferred rules must be implemented before that changes | out of scope (deferred) |
| T6 | Malformed or ambiguous manifest; canonicalization disagreement | manifest JSON bytes and claims JSON | strict closed schema (§4.9, Appendix A); duplicate keys invalid; I-JSON subset with integers only; verifier computes JCS itself and never trusts on-disk canonical form; nesting and string limits; `pap.package.schema`, `pap.package.unknown-field`; Appendix E vectors pin the canonicalizer | a verifier with a non-conforming JCS implementation could disagree; caught by vectors, not by the format | in scope |
| T7 | Digest substitution: reusing a package/claim/report digest in a payload-digest field | all `sha256:` digest fields | domain separation (§5.2): each digest is `H(domain, bytes)` with a fixed domain; declared digests are expectations only and are always recomputed; digest syntax is closed to `sha256:` + 64 hex; an artifact digest cannot satisfy package identity and vice versa | SHA-256 collisions are out of scope; a producer can still compute correct digests over malicious content, which is not a substitution | in scope |
| T8 | Self-reference: manifest hashes itself, or a digest includes its own value | manifest fields, signature envelope placement | no manifest self-digest field; manifest cannot be declared as a payload (`pap.package.manifest-self-reference`); signature envelopes are excluded from the manifest and sign the canonical manifest instead (§5.10); report identity excludes `evaluatedAt` and durations (§5.9) | none known; a future extension wanting a self-digest must use the sibling-file pattern | in scope |
| T9 | Unknown mandatory extension or feature silently ignored | `extensions`, `requiredFeatures`, `papVersion` | unknown `critical: true` extension or unknown required feature is `UNSUPPORTED` (`pap.extension.critical-unsupported`); unknown non-critical extensions are ignored, reported (`pap.extension.ignored`) and listed in limitations; newer minor version is `UNSUPPORTED` (`pap.compat.minor-newer`) | a producer can mark security-relevant data as non-critical or omit an extension entirely; that is a semantic misrepresentation, not detectable by the parser | in scope |
| T10 | Malicious or compromised checker/profile supply chain | verification code path, policy `checkers[]`/`profiles[]`, package `profile` | the verifier never loads or executes package, profile or checker code (§4.8); checkers are verifier-side; the check record names the actual checker identity and digest; the policy pins accepted checker implementations; recognition mismatch is `UNTRUSTED`/`UNSUPPORTED` (`pap.trust.checker-*`, `pap.trust.profile-*`) | a compromised verifier binary or a compromised trusted checker implementation is out of scope; profile data only affects claims and recognition, never execution | in scope |
| T11 | Trust-root or policy substitution: a package or attacker supplies a different policy | `--trust-policy`, package files, key material | policy only from explicit operator input; the package cannot declare, discover or override it (§6.3.1); a `trust-policy.json` inside the package is an ordinary undeclared file; no key material is ever read from the package; the report records the policy digest; invalid policy fails closed with exit 64 (`pap.trust.policy-invalid`) | a local attacker who can replace the policy file or the verifier changes the decision; the policy itself is unsigned in v0.1; operator channel and binary custody are out of scope | in scope (package side); operator side out of scope |
| T12 | Replay, stale status or misleading timestamps | package timestamps, policy window, review `decidedAt` | `evaluatedAt` is recorded; policy freshness is evaluated against the local clock or `--now`; package timestamps are claims and never freshness inputs (§5.11); review freshness is bounded by `maxAgeSeconds` with a future-skew allowance; the report has no "latest" or nonce concept, so replay cannot be hidden, only unaddressed | a fresh policy can accept an old package; no authenticated time; no online revocation; replay protection belongs to the operator's reliance process (§6.8, §15.3) | partly in scope; freshness protocol deferred |
| T13 | Producer-supplied fake verification records | `claims/producer-report.json` and any claim file | claims and results have separate files, schemas and namespaces (§4.7, Appendix D); claim *contents* never produce dimensions, check outcomes or verdict; a claim file using verifier-result vocabulary is rejected as an invalid claim file (`pap.claims.spoofed-result`), which fails package integrity like any invalid declared claim file; comparisons are informational (`pap.claims.producer-mismatch`); text output labels claims as untrusted | a human may still misread a claim; mitigated by layout and labelling, not eliminated | in scope |
| T14 | Arbitrary code execution through package content | artifacts, media types, claim strings, manifest strings, profile/extension data, text output | every package value is data; the verifier MUST NOT eval, import, execute, template-render or subprocess producer-controlled content; media types never select a parser; no producer-recommended tool or command is run; text output escapes control characters and does not pass ANSI/OSC sequences | memory-safety defects in JSON/parse code are a residual risk (§10.6); terminal emulators can still mis-handle escaped output | in scope |
| T15 | Decompression or archive parser attack | not parsed in v0.1 | no archive input path exists; adopting one requires the §10.7 rules first | none, because the surface does not exist | out of scope (deferred) |
| T16 | TOCTOU: package mutates between the check and the read | filesystem reads | each file is opened once and hashed from the same descriptor; byte counts and digests come from that read; the policy file is read once and digested; no re-read by path | a local writer can still race a path before the open; that adversary is out of scope and requires filesystem isolation | in scope (package content); local attacker out of scope |
| T17 | Resource exhaustion through deep nesting, huge strings, many claims or edges | JSON parser, claim arrays, relation graph | nesting ≤ 64, JSON string ≤ 16 MiB, claims files ≤ 16, provenance bindings ≤ 100 000, relation entities/edges ≤ 100 000/1 000 000, envelope count ≤ 32; streamed hashing; over-limit is `pap.package.limit-exceeded` | CPU and memory can still be consumed up to the limits; no wall-clock budget in v0.1 (recorded as a limitation) | in scope |
| T18 | Output injection through untrusted text (ANSI escapes, control characters, bidi marks) | diagnostics, limitations, package labels in text output | escape control characters in text mode; never pass ANSI/OSC through; JSON mode emits escaped strings; no terminal hyperlinks from package data | consumer-specific terminal behaviour is outside the verifier's control | in scope |
| T19 | Identity substitution: untrusted checker/profile identity claim | package `profile`, policy pins | profile identity is a package claim, never an executed artifact; recognition compares id/version/closure digest against operator pins; a pin mismatch is `UNTRUSTED`, an unknown identity is `UNSUPPORTED`; checker identity comes from the verifier, not the package | an operator who does not pin checkers/profiles gets `NOT_APPLICABLE`; that is visible in the report and is an operator decision | in scope |
| T20 | Clock manipulation or `--now` misuse | local clock, injected time, policy window | `evaluatedAt` is recorded and excluded from record identity; `--now` is for reproducible tests (§9); freshness is evaluated only against that clock; a mismatch between wall clock and an injected time may be recorded as a limitation by the CLI | a wrong clock shifts `STALE` in either direction; production use of `--now` is an open question (§16.1) | in scope (reporting); trusted time out of scope |

Coverage check against issue #44 §7 bullets: path traversal and absolute paths → T1, T2; symlink
escape → T3; duplicate/case-colliding paths → T4; archive bombs and resource exhaustion → T5, T17;
malformed/ambiguous manifests and canonicalization → T6; digest substitution and self-reference →
T7, T8; unknown mandatory extensions → T9; malicious checker/profile supply chain → T10;
trust-root/policy substitution → T11; replay/stale status and misleading timestamps → T12;
producer-supplied fake verification records → T13; arbitrary code execution → T14 (also T15).

### 10.5 Safe defaults and resource limits

Defaults are normative for v0.1 and match §4.3.4. A verifier MUST enforce every limit while
reading; a policy MAY lower a limit through its `limits` object but MUST NOT raise one, because a
raised limit is a producer-controlled denial-of-service surface. Effective limits lower than the
defaults are reported in the report's `effectiveLimits` object (§4.3.4, Appendix C) and as a
`pap.limit.lowered` `info` diagnostic and limitation.

| Limit | Default | Enforcement point |
|---|---|---|
| Manifest bytes | 1 MiB (1 048 576) | read manifest with a capped reader; oversized manifest is `pap.package.limit-exceeded` |
| Payload files | 4 096 | count declarations before opening; declarations beyond the limit stop evaluation |
| Bytes per payload file | 256 MiB (268 435 456) | streamed hash with a running counter; abort at the cap |
| Total payload bytes | 1 GiB (1 073 741 824) | running total across declared payloads |
| Path segments / path bytes / segment bytes | 16 / 255 / 255 | path grammar validation (§4.3.1) before any open |
| JSON nesting depth | 64 | parser depth counter on every JSON document |
| JSON string bytes | 16 MiB | parser string counter; oversized string aborts the document |
| Claims files | 16 | manifest declaration count |
| Provenance bindings | 100 000 | claim array count and check scope |
| Relation entities / edges | 100 000 / 1 000 000 | relation claim count before graph construction |
| Signature envelopes | 32 | `signatures/*.dsse.json` discovery count |
| Policy keys / signers / checkers / profiles | 64 each | policy validation; larger list is `pap.trust.policy-invalid` (exit 64) |
| Policy required checks / dimensions | 32 / 16 | policy validation |

Additional safe defaults, normative:

- **Validate before open.** Every path is validated against §4.3.1 before any filesystem call; only
  declared paths and `signatures/` are read, and undeclared files are never opened
  (`pap.package.undeclared-file`).
- **No symlinks, no non-regular files.** A declared payload that is a symlink, directory, socket,
  FIFO or device is an error (`pap.package.symlink` / `pap.package.non-regular` /
  `pap.package.declared-file-missing`); the verifier opens without following links where the
  platform supports it and re-checks the object.
- **ASCII-only, case-folded uniqueness.** Paths are ASCII and unique under case folding
  (`pap.package.path-duplicate`); no Unicode normalization or case ambiguity is parsed.
- **Streamed hashing.** Payloads are hashed from the read stream; the verifier MUST NOT buffer a
  whole payload to hash it and MUST NOT report a partial digest.
- **Hard fail, never silent truncation.** Exceeding a limit stops evaluation of the affected scope,
  records `pap.package.limit-exceeded`, sets `coverage.full: false`, and yields `INCOMPLETE` (the
  package is unverifiable, not necessarily invalid; limits are a verifier safety boundary,
  §4.3.4). If the manifest itself cannot be read or parsed within the limit, the report has
  `package.identity: null`, `integrity.package: FAIL` and verdict `FAIL` (§9.11, §7.7). A limit
  hit MUST NOT be reported as `PASS` or a quietly shortened report.
- **Parse after digest.** A claim file is parsed only after its declared digest is verified, and
  parsing is bounded; parsing never upgrades a claim to evidence.
- **No network, no subprocess, no producer code.** The verifier performs no network I/O, spawns no
  producer-supplied command, and imports nothing from the package (§4.1 rule 4).
- **No archive parsing, no wall-clock timeout.** Directory-only v0.1 (§10.7); CPU is bounded by the
  JSON and collection limits, and a wall-clock budget is deferred and recorded as a limitation.
- **No normative scan-entry limit.** The undeclared-file scan has no §4.3.4 entry-count limit in
  v0.1. A verifier may bound its own scan; that bound is an implementation robustness measure, not
  a producer-facing limit, and a stop is reported as an incomplete scan (§4.3.3), never as
  `pap.package.limit-exceeded`.

### 10.6 Scope boundary and residual risk

The following are outside the v0.1 threat model. They are not claims that the risks do not exist;
they are statements about what a package verifier cannot defend.

| Out of scope | Why | What would be needed |
|---|---|---|
| Compromised verifier binary or its dependencies | a verifier that lies cannot be checked by itself | reproducible builds, independent binary verification, measured boot |
| Compromised operating system, filesystem or CPU | the verifier runs with the trust of the host | host attestation, hardware root of trust |
| Compromised or substituted trust policy | the policy is the trust anchor and is unsigned in v0.1 | signed policies, policy transparency, operator key custody |
| Key revocation, expiry of keys, transparency logs, online trust status | no network and no status service in v0.1 | an offline revocation snapshot with authenticated time, or an online status channel with a defined offline fallback |
| Authenticated time / timestamping | local clock is trusted within skew | RFC 3161-style timestamp authority or log-stamped time |
| Semantic truth, legal enforceability, correctness of human judgement | not mechanical properties | human, legal and domain review outside the verifier |
| Local attacker with write access (package, policy, binary, clock, TOCTOU) | same-privilege attacker defeats any local verifier | filesystem isolation, immutable media, privilege separation |
| Network attacker | v0.1 performs no network I/O | secure transport and authenticated distribution if a network channel is added |
| Side channels, hardware faults, supply-chain of the verifier's build | outside the format | build provenance, hardware measures, operational controls |
| Denial of service against the host beyond the bounded CPU/memory limits | a host-level concern | resource isolation and operating-system controls |
| Correctness of the relying party's decision after a correct report | the report is evidence, not a decision | operator process (§6.8) |

### 10.7 Deferred archive requirements

If an archive transport is adopted, these requirements are mandatory before its parser is trusted,
and are listed so directory-only can be revisited without re-deriving them:

1. exactly one top-level package directory (or a declared root) after extraction; no second manifest;
2. no symlinks, hard-link aliases, device nodes or special files in or after extraction;
3. reject absolute paths, `..`, empty segments, backslashes, NUL and non-ASCII/ambiguous entry names
   before any write;
4. reject duplicate and case-colliding entries, including entries that collide only after platform
   path normalization;
5. declared uncompressed and compressed size limits per entry and in total, enforced before
   extraction;
6. streamed extraction with bounded buffers; never extend an entry of unknown size beyond the limit;
7. extraction into a fresh directory owned by the verifier; no implicit overwrite and no path chosen
   by the producer;
8. the same schema, path grammar, ASCII restriction and digest rules as the directory form; archive
   headers are untrusted and never override the manifest;
9. decompression algorithms limited to an allowlist and, where practical, disallowed entirely.

Until then, an archive is not a package: the verifier MUST reject it as a usage error (§9.7),
never attempt a best-effort extraction.

---


## 11. Signature and transparency extension points

Signatures are an optional layer, not a core invariant. This section specifies the v0.1 DSSE
adapter, the in-toto mapping, where results enter the report, and what is deferred; it defines no
bespoke format — v0.1 adopts existing specifications and restricts algorithms.

Signing MUST NOT be mandatory for the base package. An unsigned package is a valid v0.1 package;
the verifier's integrity, source, claim and check evaluation is useful without any signature
(§4.12). Whether a signature is required is a property of the operator's trust policy, never of
the package.

### 11.1 Adapter model and constraints

A signature mechanism enters PAP as an **adapter** with four obligations:

1. a declared envelope location and file suffix;
2. a declared `payloadType` (or equivalent type discriminator) and an exact payload rule — which
   canonical bytes are signed;
3. a fixed algorithm allowlist and an exact key-identification rule against the operator's policy;
4. an exact mapping into `dimensions.signature` and `dimensions.trust` and a diagnostic set.

v0.1 defines one adapter (DSSE over the canonical manifest, Ed25519 only) and one optional mapping
(in-toto Statement). Any future adapter — Sigstore bundles, SCITT receipts, X.509-based signatures
— MUST add a payload type and keep the existing package fields unchanged; the manifest is not
extended with signature fields, and a package still cannot require a signature.

Further constraints for v0.1: the verifier MUST NOT use the network to obtain keys, certificates,
transparency proofs or revocation status; MUST NOT import or execute producer-supplied code; MUST
parse every envelope as untrusted package data under the same path and size rules as other
payloads; and MUST keep signing out of package-derived identities — `packageIdentity` is computed
from the manifest (§5.3), envelopes are outside it (§4.2, §5.10), and a signature cannot add,
remove or reinterpret a manifest field.

### 11.2 Optional DSSE envelope adapter (v0.1)

**Location and discovery.** Envelopes live under `signatures/` with suffix `.dsse.json`; the
directory and files are discovered by convention, not declared in the manifest (this avoids a
self-reference and lets a signer add an envelope without changing the package identity). The
number of envelopes is bounded by `signatureEnvelopes` (§4.3.4, §10.5). Only regular files directly
under `signatures/` whose name matches `[A-Za-z0-9._-]+\.dsse\.json` are envelopes; a subdirectory,
symlink or other file there is undeclared (`pap.package.undeclared-file`) and is not read.
Envelopes are evaluated in ascending UTF-8 byte order of their path, which fixes the order of
`dimensions.signature.signatures[]` (§9.9). When the policy mode is `optional` or `required` and
more envelope files are present than the limit, the verifier reads none of them rather than an
arbitrary prefix: it reports `pap.package.limit-exceeded`, leaves signature and trust
`NOT_EVALUATED`, and the verdict is `INCOMPLETE`. Mode `disabled` reads no envelope at all, so the
envelope limit does not apply there (§6.5). The envelope file is a JSON object with exactly the DSSE fields:

```json
{
  "payloadType": "application/vnd.pap.manifest.v0.1+json",
  "payload": "<base64 of the canonical manifest bytes>",
  "signatures": [{ "keyid": "<policy keyId>", "sig": "<base64 of the 64-byte Ed25519 signature>" }]
}
```

Additional envelope fields are rejected (`pap.signature.envelope-invalid`); `signatures` MUST be a
non-empty array; `payload` and `sig` use standard base64 (RFC 4648 §4) with padding, and the
verifier MUST reject malformed encodings. Encodings are canonical: only the standard alphabet,
correct `=` padding, no whitespace or line breaks, no extra characters; a non-canonical encoding is
`pap.signature.envelope-invalid`. The `keyid` is an opaque operator-assigned identifier:
the verifier matches it byte-for-byte against a policy `keys[].keyId`; it never derives trust from
a self-asserted key identifier.

**Signed payload.** The payload is the canonical manifest: the exact UTF-8 bytes produced by
applying JCS over the I-JSON subset to the manifest value (§5.2, §4.10), with no BOM and no
trailing newline. The verifier canonicalizes the manifest itself and requires byte equality with
the decoded payload before verifying the signature. A payload that decodes to a different JSON
value, or to the same value with different bytes, is `pap.signature.payload-mismatch`; the
envelope does not cover this package.

**Payload type.** For the PAP manifest adapter, `payloadType` MUST be exactly
`application/vnd.pap.manifest.v0.1+json` (38 ASCII bytes). A different, unknown or
in-toto payload type is handled by §11.3 or reported as `pap.signature.unsupported-format`; type
confusion across payloads is exactly what pinning the string prevents.

**Pre-authentication encoding.** DSSE signs a domain-separated encoding of the payload type and
payload, not either alone. The exact encoding is the DSSE specification's Pre-Authentication
Encoding (PAE), reproduced here:

```text
PAE(payloadType, payload) =
    "DSSEv1" SP LEN(payloadType) SP payloadType SP LEN(payload) SP payload
```

`SP` is one 0x20 byte; `LEN` is an ASCII decimal byte length with no leading zeros and no padding;
`payload` is the exact payload bytes. For this adapter the prefix is therefore
`DSSEv1 38 application/vnd.pap.manifest.v0.1+json <len> ` followed by the payload; for an
(illustrative, not schema-valid) payload `{}` the PAE bytes are
`DSSEv1 38 application/vnd.pap.manifest.v0.1+json 2 {}`. The normative implementation reference is
the DSSE specification's "Pre-Authentication Encoding (PAE)" section
(<https://github.com/secure-systems-lab/dsse/blob/master/protocol.md>). Appendix E holds the
normative PAP PAE vector; a verifier that disagrees with it is non-conformant.

**Algorithm and keys.** Ed25519 only (JWS name `EdDSA`; the envelope does not carry an algorithm
field, so the algorithm is fixed by this adapter and by the policy key entry
`algorithm: "ed25519"`). The signature is the 64-byte Ed25519 signature over the PAE bytes. The
base64-decoded `sig` MUST be exactly 64 bytes; a different length is
`pap.signature.envelope-invalid`. Verification follows RFC 8032 §5.1.7, including the canonical-`S`
check; a verification failure, including a non-canonical `S`, is `pap.signature.invalid`. The
verifier MUST NOT accept other algorithms (`pap.signature.algorithm-unsupported`, entry
`NOT_EVALUATED`). The public key is the policy's `keys[].publicKey`, canonical base64url of the raw
32-byte key; an envelope never carries key material.

**Verification steps** (order matters for diagnostics and determinism): (1) parse the envelope
with the package limits; shape failure is `pap.signature.envelope-invalid` and the entry is
`INVALID`; (2) check `payloadType`; an unsupported type is `pap.signature.unsupported-format`
with entry `NOT_EVALUATED`; (3) decode `payload`; malformed base64 is
`pap.signature.envelope-invalid` with entry `INVALID`; (4) canonicalize the manifest and require
byte equality with the payload; failure is `pap.signature.payload-mismatch` with entry `INVALID`;
(5) for each signature entry require a non-empty `keyid` (`pap.signature.keyid-missing`, entry
`NOT_EVALUATED`), find the policy key (`pap.trust.signer-unknown` if absent, entry
`NOT_EVALUATED`), verify Ed25519 over PAE (`pap.signature.invalid` on failure) and apply
signer/role/package authorization (§6.5); (6) report one entry per `(path, keyId)` and aggregate
per §6.5.

The verifier MUST continue after a failing envelope so that the report names every problem
(no fail-fast across envelopes), and MUST NOT let an envelope failure affect integrity, source or
check dimensions. A valid signature over a manifest whose artifact digest does not match is a
normal outcome: `signature.validity: VALID` and `integrity.artifacts: FAIL`.

### 11.3 in-toto statement mapping (optional adapter)

An in-toto Statement is an existing evidence format; PAP maps it as an optional adapter, not as a
core requirement. A DSSE envelope with `payloadType` `application/vnd.in-toto+json` carries a
Statement as its payload (decoded payload bytes MUST equal JCS of the parsed Statement, checked
exactly like §11.2). The Statement's fields are then interpreted as follows:

| Statement field | PAP mapping |
|---|---|
| `_type` | MUST be `"https://in-toto.io/Statement/v1"`; otherwise `unsupported-format` |
| `subject` | exactly one subject carries the package binding: `name` is the `package.id` label, `digest` contains `{"pap.package.v0.1": "<64 lowercase hex of packageIdentity>"}`. Additional subjects are informational |
| `predicateType` | the PAP attestation type `urn:pap:attestation:v0.1`; any other type is `pap.signature.predicate-unrecognized` (`info`) and the statement is still signature-verified |
| `predicate` | producer-supplied, informational data (`papVersion`, package label, artifact digests/ids, declared check specifications). The verifier MUST NOT use the predicate to change any dimension, check outcome or verdict |

The binding is checked by recomputing `packageIdentity` and comparing the hex value, never by
trusting the subject name. A mismatch is `pap.signature.subject-mismatch` (`error`) and the
envelope is `INVALID` for this package. The custom digest key `pap.package.v0.1` is used precisely
because `packageIdentity` is not a raw SHA-256 of the manifest bytes; labelling it `sha256` would
be a false claim (§5.13).

in-toto layouts, link metadata, SLSA predicates and policy engines are deferred. The adapter gives
interoperability with an existing statement format without making any of it a PAP invariant.

The mapping is **outside the mandatory v0.1 conformance subset** (§13.1): a v0.1 verifier MAY
implement it, and a verifier that does not MUST report `pap.signature.unsupported-format` with the
entry `NOT_EVALUATED`. Because both outcomes are conforming, no §12 case may require in-toto
handling; an in-toto envelope in a conforming package is permitted but its acceptance is not part
of the v0.1 contract.

### 11.4 Deferred integrations and why

| Deferred mechanism | What it would add | Why deferred from v0.1 | Revisit condition |
|---|---|---|---|
| Sigstore bundles, Rekor, Fulcio, keyless/OIDC identity | transparency log inclusion, short-lived identities, public auditability | requires network verification, a log/CA dependency, OIDC identity and root updates; incompatible with an offline verifier and with the "no key management service" v0.1 boundary | an online trust-status channel with an offline fallback is specified; a real distribution need is demonstrated |
| SCITT receipts and transparency statements | countersignatures and log receipts for supply-chain evidence | specification maturity and log/network dependency; no offline receipt semantics defined | SCITT and its offline verification story stabilise |
| OCI/registry transport and referenced blobs | standard distribution, content-addressed storage | transport only; adds a registry, network and a second content-addressing scheme; does not improve verification | a concrete distribution channel requires it; archive rules (§10.7) are agreed first |
| TUF root updates, key distribution | secure key rotation and delegation | requires a hosted/network update channel and a root of trust; v0.1 keeps anchors in a local policy | a multi-organisation trust service is in scope |
| X.509 PKI, certificate chains, OCSP/CRL | named identities and revocation | chain validation, trust stores and online status are a larger trust model than v0.1; no offline revocation guarantee | an identity model beyond enrolled Ed25519 keys is required |
| RFC 3161-style timestamp authorities | authenticated time for signatures and reviews | requires a timestamp authority and its trust anchor; freshness currently relies on the local clock | authenticated time is required for a relying decision |
| Transparency logs for PAP reports/policies | public, append-only audit of attestations and policy snapshots | no log service, no log proof format, no privacy model; the report already records policy/verifier identities for local audit | an audit requirement is demonstrated; a log proof adapter fits the §11.1 model |
| Multiple signature algorithms | agility, interoperability with non-Ed25519 signers | algorithm confusion and additional vectors; v0.1 pins Ed25519 only (§5.14) | a versioned allowlist with vectors exists |
| Signed human-review approvals | cryptographically bound reviewer identity | no review payload type, no reviewer key delegation and no answer to what an approval covers; §16.1 records it as a blocker | a review attestation format and reviewer authority model are specified |

The common reason is structural: v0.1 is offline with a local policy and no key service. Sigstore,
SCITT and OCI assume a network or hosted component; adopting them without offline semantics would
either add a network dependency or let a receipt be "verified" against a log the verifier never
saw. Transparency stays an extension point; `policy.digest` and the verifier identity are the hooks
a future adapter would bind.

### 11.5 Where signature results enter the report

Signature outcomes appear only in the signature and trust dimensions and in diagnostics; they
never alter integrity, sources, checks, human review, semantic truth or legal enforceability.

| Report field | Contents | Aggregation |
|---|---|---|
| `dimensions.signature.validity` | cryptographic aggregate over the evaluated envelope set | mode `required`: `INVALID` if any evaluated entry is `INVALID`; else `VALID` if at least one envelope verifies; else `NOT_EVALUATED` (including no envelope). Mode `optional`: `VALID` if an envelope verifies; else `NOT_EVALUATED` when envelopes exist; `NOT_APPLICABLE` when none exists and mode is not `required`. Signer authorization and `minimumValidSigners` belong to `trust.policyDecision` |
| `dimensions.signature.signatures[]` | one independent entry per envelope signature: `{path, keyId?, algorithm: "ed25519"?, validity, signerIdentity, policyDecision}` | entries are never merged; each cites the same vocabulary as the trust dimension |
| `dimensions.trust.signerIdentity` | aggregate signer trust | worst-of over present entries (§6.5) |
| `dimensions.trust.policyDecision` | policy decision on the signer set and snapshot | `ACCEPTED`, `REJECTED`, `STALE` or `NOT_EVALUATED` (§6.5) |
| `coverage.requiredDimensions` / `coverage.full` | whether signature/trust were required and evaluated | `PASS` requires full coverage of the required set |
| `limitations[]`, `diagnostics[]` | one stable code per reason | every non-positive required status is explained (§6.9) |

Multiple signatures are reported as independent entries, and the policy decides the required set
(`signature.mode`, `signature.minimumValidSigners`, `signers[]` allowlists). In required mode there
is no "any valid signature wins" shortcut: an envelope from an unknown or unauthorized signer is
reported and makes the signer set unacceptable, while an extra authorized signature beyond the
required count is an additional entry that does not move the aggregate by itself. Optional mode
does not make a present bad envelope harmless: it is still reported, its signer status still
applies, and the policy decision can still reject the package. The verifier MUST report every
envelope it evaluated; a report that omits one it read is non-conformant. A malformed envelope is
reported as `INVALID` (`pap.signature.envelope-invalid`); an unsupported format or an unknown key
is reported as `NOT_EVALUATED` with `UNKNOWN` signer identity, and the aggregate and verdict follow
§6.5 and §7.4.

### 11.6 What a signature does not cover

- **The trust policy.** A signature says what the signer attested, not whether the operator's policy
  is correct, fresh or authorized; `policy.digest` records which policy decided, nothing signs it.
- **The verifier or the report.** A package signature cannot certify the verifier's behaviour,
  the report's correctness, or a later claim that verification happened. The report's identity
  (`verificationRecordIdentity`) and verifier identity are separate; neither is signed by the
  package.
- **Undeclared files and the envelope set.** Only the manifest is signed; files the manifest does
  not declare are ignored and are not covered. One envelope does not cover another envelope.
- **Payload bytes directly.** A signature covers the manifest, which contains artifact, source and
  input digests. That is a transitive claim about bytes whose digests the verifier must still
  recompute; a valid signature over a manifest with a stale artifact digest yields
  `signature.validity: VALID` together with `integrity.artifacts: FAIL`.
- **Truth, authority, approval or legal effect.** A valid signature proves that a key signed
  canonical bytes. The policy decides whether that key's identity is allowed to sign for this
  package; nothing in the report decides whether the signed content is correct, whether the signer
  had authority over the subject matter, or whether a human approved it.
- **Time.** Ed25519 signatures have no timestamp. Freshness comes only from the policy window and
  the verifier's clock (§6.4); a signature cannot prove when it was made.

These limits are why §6.2's non-implications are normative: signature validity, signer trust,
content truth and approval are four separate questions, and v0.1 answers only the first two.

---


## 12. Conformance and acceptance tests

This section is the **normative v0.1 test matrix**: what a conforming verifier must report for a
fixed set of packages. Fixture packages are committed in Phase 2/3a of roadmap #43 (§13.9); this RFC PR commits no fixture directory or `cases.json`, but
their expected results are normative now, so two independent implementations can be compared
against one contract before code exists.

Scope: `papVersion "0.1"`, directory packages, the three §8 checks, Appendix B policy, the §9
CLI. Anything deferred in §14.1 is out of matrix scope. `verificationRecordIdentity` is compared
only within one verifier build; diagnostic messages are never compared across implementations
(§13.6).

### 12.1 Fixture set layout

```text
fixtures/pap-v0.1/
  README.md               fixture policy and how to run the matrix
  cases.json              machine-readable case index and expected assertions
  base/                   canonical valid package; bytes equal to Appendix F
    assurance-package.json  artifacts/ACME-SUPPLIER.draft.md  inputs/project.yml
    sources/acme-policy.md  claims/{provenance,relations,producer-report}.json
  F01-unchanged/ … F61-…/ one complete static package copy per case
  trust-policy/           unsigned-valid.json  signature-required.json
                          signature-optional.json  expired.json  invalid.json
                          not-authorized-role.json  package-not-allowed.json
                          unknown-signer.json  profile-pinned.json  review-required.json
                          lowered-limits.json
  signatures/             trusted.dsse.json  untrusted.dsse.json  invalid.dsse.json
```

`cases.json` references the Appendix E literals directly, so no separate `vectors/` copy is
needed. The trust-policy fixtures have these normative semantics. Each is one fixed file: a
fixture is normative data, so an "either shape is allowed" description would be a conformance
defect.

| Fixture | Required content and behaviour |
|---|---|
| `unsigned-valid.json` | `signature.mode: "disabled"`, `requiredDimensions: ["integrity","sources","checks"]`, empty `checkers[]`/`profiles[]`, `humanReview.required: false`; `PASS` with an unsigned package, with `trust.checkerRecognition`/`trust.profileRecognition` `NOT_APPLICABLE` (F01, F14, F34). No fixture may pin the reference implementation's checker identity: an independent verifier has a different `implementationDigest`, and §13.6 compares every dimension status, so a pinned fixture would fail for every implementation but the reference. |
| `signature-required.json` | `signature.mode: "required"`, `minimumValidSigners: 1`, `keys`/`signers` enrolling the key that signed `signatures/trusted.dsse.json`, `requiredDimensions` containing `signature` and `trust`; `PASS` with that envelope (F13). |
| `signature-optional.json` | `signature.mode: "optional"`, `keys`/`signers` enrolling the key behind `signatures/trusted.dsse.json`, `requiredDimensions: ["integrity","sources","checks"]`; a present invalid envelope still makes the policy decision `REJECTED` (F56). |
| `expired.json` | Same shape as `signature-required.json` but `expiresAt` before the fixture `--now`; `policy.state: STALE`, verdict `INCOMPLETE` (F15). |
| `invalid.json` | Violates Appendix B (for example `requiredDimensions: ["semanticTruth"]` or a `limits` value above the §4.3.4 maximum); fail closed, exit 64, no report (F41). |
| `not-authorized-role.json` | `signature.mode: "required"`; the envelope key is in `keys[]` and mapped by a `signers[]` entry whose `allowedRoles` is `["reviewer"]`, so a producer-role manifest signature is `UNTRUSTED`/`REJECTED` (`pap.trust.signer-untrusted`, F11). |
| `package-not-allowed.json` | Same as `signature-required.json` but the signer's `allowedPackageIdentities` excludes the fixture package; the envelope signer is `UNTRUSTED`/`REJECTED` (`pap.trust.package-not-allowed`, F17). |
| `unknown-signer.json` | `signature.mode: "required"` enrolling only the key behind `signatures/trusted.dsse.json`; any other envelope `keyId` is absent from `keys[]`, so its signer is `UNKNOWN`/`REJECTED` (`pap.trust.signer-unknown`, F16, F18). |
| `profile-pinned.json` | `signature.mode: "disabled"`, `requiredDimensions` containing `trust`, and `profiles[]` pinning `{id: "acme-supplier", version: "0.1.0"}`; a package declaring another profile version gets `profileRecognition: UNSUPPORTED` (F43). |
| `review-required.json` | `signature.mode: "disabled"`, the three mechanical checks in `requiredChecks`, `requiredDimensions: ["integrity","sources","checks","humanReview"]`, `humanReview: {required: true, maxAgeSeconds: 2592000}`, and a `signers[]` entry with `allowedRoles: ["reviewer"]` matching the reviewer identity in `claims/reviews.json` (F55). |
| `lowered-limits.json` | `signature.mode: "disabled"`, `limits: {fileBytes: 64}`; F52 reports `effectiveLimits.fileBytes: 64`, `pap.limit.lowered`, `integrity.artifacts: NOT_EVALUATED` and `INCOMPLETE`. |

Rules:

- Each case directory is a **complete static package copy**. Tests MUST NOT build cases by
  mutating `base/` at run time: v0.1 has no mutation scripts, no generators and no "edit, then
  recompute the digest" helper. A case differs from `base/` only in the defect it names, and all
  internal digests are consistent unless the case is specifically about a declared-versus-computed
  mismatch.
- Directory names follow `F<NN>-<short-slug>/`; paths obey §4.3.1 (ASCII, relative, no symlinks,
  no executable content); fixtures contain no secrets, credentials or personal data and are never
  fetched from the network. `trust-policy/` and `signatures/` are shared versioned inputs, and
  each case entry names the exact policy file (or says it runs without one).
- Tier A cases (every package without a `signatures/` envelope: F01–F10, F14, F19, F20–F55,
  F57–F61) are executable against a core verifier with the Appendix B policy; the envelope cases
  F11–F13, F15–F18 and F56 become executable when the §11 adapter exists (Tier B). Their expected
  results are normative now because they constrain the interface, not the schedule. Phase 3 may
  add cases; changing an existing case or expectation follows §12.5.

### 12.2 `cases.json`

A JCS JSON document: `{"fixtureSetVersion": "0.1", "baseCase": "F01", "cases": []}`. Each entry:

```json
{"caseId": "F05-quote-span", "package": "F05-quote-span",
 "command": ["verify", ".", "--trust-policy", "../trust-policy/unsigned-valid.json",
             "--format", "json", "--now", "2026-11-02T00:00:00Z"],
 "expect": {"exitCode": 1, "verdict": "FAIL",
   "dimensions": {"integrity.package": "PASS", "integrity.artifacts": "PASS",
                  "sources.integrity": "PASS",
                  "checks": {"pap.check.source-quote/1": "FAIL"}},
   "diagnosticCodes": ["pap.check.quote-mismatch"], "limitationCodes": [],
   "coverageFull": false,
   "identityRelations": {"packageIdentity": "differs-from-base"}}}
```

- `command` is argv after `pap`, executed with the fixture directory as working directory; paths
  are fixture-relative so the corpus and expectations are host-independent.
- `expect.exitCode` is exact (§9.7); `expect.verdict` is §7.4. `dimensions` lists only the
  statuses the case constrains, with check outcomes under `dimensions.checks`.
- `diagnosticCodes` is the **set** (not order/multiplicity) of `pap.*` codes that MUST appear in
  `diagnostics[]`; extra codes are allowed unless `"diagnosticCodesExact": true`. Messages are not
  compared; severity and scope are schema-checked. `limitationCodes` is the required set of
  `limitations[]` codes; `coverageFull` is the required `coverage.full`.
- `identityRelations` uses Appendix E literals, `equals-base`/`differs-from-base` (package
  identity, normalized input digest, per-artifact/source entries), or `null` when not computable.
  Appendices E literals cover `base/` and identity-vector cases, so mutated packages need no
  published digest literals.
- `expect.effectiveLimits` is an optional object of limit name → integer. Each named limit MUST
  equal the report's `effectiveLimits[name]`; a report with no `effectiveLimits` fails the case.
  Limits not named are unconstrained. F52 uses it to pin a lowered limit.
- `noReport: true` marks exit 64/70/74 cases: no document, and `stderrCodes` MUST appear on
  stderr. Cases for `inspect`/`explain` name `"document": "inspection"|"explanation"` and use
  `inspection` / `checkOutcome` instead of `verdict`.
- The harness is a generic projection-and-compare runner; it MUST NOT branch per case id.

### 12.3 Execution

For each case the harness runs the argv in a clean environment with: network denied; no producer
installed, plus sentinel `contract-builder`/`bun`/`node` shims that fail loudly if executed; the
`--now` from `command`; hostile `TZ`/`LC_ALL`; the fixture directory as cwd; a writable temp
directory outside the package.

For JSON `verify` cases it asserts: exactly one JSON object plus one LF on stdout, JCS-canonical
bytes, Appendix C validity, expected exit code, verdict, constrained dimensions, check outcomes,
diagnostic and limitation code sets, coverage, identity relations, empty stderr. The harness also
runs F01 (a `PASS`) and F02 (a `FAIL`) a second time with `--format text` and asserts the §9.6
required lines: the first line exactly `VERDICT: <verdict>`; `NOT A PASS` present when and only
when the verdict is non-`PASS`; every dimension path with its exact status token; one line per
check id with its exact outcome token; all coverage counters and the `full` flag; every limitation
code; and no colour, absolute path or `verified` result. Text layout beyond those lines is not
compared across implementations (§13.6). Every case runs twice to assert §9.9 determinism.

**Report-shape assertions (normative).** Every `verify` report MUST validate against Appendix C,
including the `humanReview.basis` conditional. A report with `humanReview.status: "PASS"` and no
`basis`, or with a `basis` other than `"unbound-claim"`, is schema-invalid and MUST NOT be emitted.
F55 asserts the valid shape (`PASS` + `"unbound-claim"`); the harness also validates a negative
form of F55's report with `basis` removed and requires validation to fail. This is a schema
assertion over emitted or candidate reports, not a CLI exit-code case.

### 12.4 Test matrix

Legend: `DI` = `pap.check.digest-integrity/1`, `SQ` = `pap.check.source-quote/1`,
`RC` = `pap.check.relation-consistency/1`; dimension names are Appendix C paths; `—` in the codes
column means the case asserts no diagnostic codes. Unsigned cases use
`trust-policy/unsigned-valid.json` unless stated. Status tokens are exact.

#### 12.4.1 Package content and mechanical checks

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F01 | `base/` unchanged, valid policy | `integrity.package=PASS`, `integrity.artifacts=PASS`, `sources.integrity=PASS`, `sources.availability=PASS`, `DI=SQ=RC=PASS`, `coverage.full=true` | `PASS` | 0 | — |
| F02 | one artifact byte changed, same length; manifest keeps old digest | `integrity.artifacts=FAIL`, `DI=FAIL`, `SQ=PASS`, `RC=PASS` | `FAIL` | 1 | `pap.integrity.artifact-mismatch` |
| F03 | one byte changed in `sources/acme-policy.md` outside every quoted span | `sources.integrity=FAIL`, `DI=FAIL`, `SQ=PASS` | `FAIL` | 1 | `pap.integrity.source-mismatch` |
| F04 | one byte changed in `inputs/project.yml`; declared input digest unchanged | `integrity.package=FAIL`, `DI=FAIL`, `SQ=PASS` | `FAIL` | 1 | `pap.integrity.input-mismatch` |
| F05 | binding `locator.start`/`end` shifted one byte; quote digest unchanged | `sources.integrity=PASS`, `DI=PASS`, `SQ=FAIL`, `RC=PASS` | `FAIL` | 1 | `pap.check.quote-mismatch` |
| F06 | relation edge points to an entity removed from `entities[]`; digests consistent | `integrity.package=PASS`, `DI=PASS`, `RC=FAIL` | `FAIL` | 1 | `pap.claim.edge-unknown-entity` |
| F07 | required `pap.check.unknown/1` added to `checkSpecs` | `checks[pap.check.unknown/1]=UNSUPPORTED`, `coverage.full=false` | `UNSUPPORTED` | 4 | `pap.check.unsupported` |
| F08 | `extensions["com.example.future"]={version:"1",critical:true}` | `integrity.package=PASS`, `DI=PASS`; unknown critical extension blocks | `UNSUPPORTED` | 4 | `pap.extension.critical-unsupported` |
| F09 | `checkSpecs` declares `pap.check.digest-integrity/2` (newer version) | `integrity.package=PASS`, `DI=PASS`, `checks[pap.check.digest-integrity/2]=UNSUPPORTED` | `UNSUPPORTED` | 4 | `pap.check.unsupported` |
| F10 | `papVersion: "0.2"`, otherwise 0.1-shaped manifest | `integrity.package=PASS` (the 0.1 core subset is structurally readable); required checks `NOT_EVALUATED` rather than run under unknown semantics; `coverage.full=false` | `UNSUPPORTED` | 4 | `pap.compat.minor-newer`, `pap.check.not-evaluated` |

F09 note: `profile.id`/`version` is metadata, not a verifier capability (§4.8); an unknown profile
version is not by itself a failure. When a policy requires profile recognition, the §6.5
recognition status applies; that sub-case belongs to §6/§11. F10's `integrity.package` is `PASS`
because the directory is structurally readable as a 0.1-core package; §4.9 and §7.4 rule 3 make
the verdict `UNSUPPORTED` and required checks `NOT_EVALUATED`.

#### 12.4.2 Trust, signatures and producer claims

Per-envelope `dimensions.signature.signatures[]` entries are asserted; aggregate
`signature.validity` covers the policy-required set (§11, Appendix C).

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F11 | valid envelope; signer known but not authorized (issue bullet "valid signature from untrusted signer"); policy `not-authorized-role.json` | `signature.validity=VALID`, `signatures[0].signerIdentity=UNTRUSTED`, `trust.signerIdentity=UNTRUSTED`, `trust.policyDecision=REJECTED` | `UNTRUSTED` | 3 | `pap.trust.signer-untrusted` |
| F12 | envelope signature corrupted in one byte; policy mode `required` | `signature.validity=INVALID`, `signatures[0].validity=INVALID` | `FAIL` | 1 | `pap.signature.invalid` |
| F13 | valid envelope; key authorized for this `packageIdentity` and role | `signature.validity=VALID`, `signatures[0].signerIdentity=TRUSTED`, `trust.signerIdentity=TRUSTED`, `trust.policyDecision=ACCEPTED` | `PASS` | 0 | — |
| F14 | no `--trust-policy`; unsigned package | `policy.state=ABSENT`, trust `NOT_EVALUATED` (`signerIdentity=NOT_APPLICABLE`), `signature.validity=NOT_APPLICABLE`, `coverage.full=true` | `PASS` | 0 | `pap.trust.policy-absent` |
| F15 | policy present; `--now` after `expiresAt` | `policy.state=STALE`, `trust.policyDecision=STALE`, `trust.signerIdentity=TRUSTED`, `signature.validity=VALID` (crypto independent of freshness) | `INCOMPLETE` | 2 | `pap.trust.policy-stale` |
| F16 | envelope with a `keyId` absent from the policy's key material; policy `unknown-signer.json` | `signature.validity=NOT_EVALUATED`, `signatures[0].signerIdentity=UNKNOWN`, `trust.signerIdentity=UNKNOWN`, `trust.policyDecision=REJECTED` | `UNTRUSTED` | 3 | `pap.trust.signer-unknown` |
| F17 | valid envelope; key present in `keys[]` and enrolled, but its policy binding names a different `packageIdentity`; policy `package-not-allowed.json` | `signature.validity=VALID`, `signatures[0].signerIdentity=UNTRUSTED`, `trust.policyDecision=REJECTED` | `UNTRUSTED` | 3 | `pap.trust.package-not-allowed` |
| F18 | two envelopes: one trusted-and-authorized, one valid with unknown key; mode `required`; policy `unknown-signer.json` | `signatures[0]` `TRUSTED`/`ACCEPTED`, `signatures[1]` `UNKNOWN`/`REJECTED`; aggregate validity `VALID`, aggregate trust blocked | `UNTRUSTED` | 3 | `pap.trust.signer-unknown` |
| F19 | policy mode `required`, no envelope present | `signature.validity=NOT_EVALUATED`, required signature missing, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.signature.absent` |
| F20 | producer report claims `PASS` for `DI` while an artifact byte mismatch makes `DI=FAIL` | `integrity.artifacts=FAIL`, `DI=FAIL`, `producerClaims.trusted=false`, relation `DISAGREES`; verdict unaffected by the claim | `FAIL` | 1 | `pap.integrity.artifact-mismatch`, `pap.claims.producer-mismatch` |

F14 note: `PASS` means every **required** check and dimension was evaluated and positive; trust was
not evaluated and the report says so (`policy.state: ABSENT`, limitation, dimension statuses) —
it is not a statement that the package is trusted.

#### 12.4.3 Package safety, claims and malformed input

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F21 | `assurance-package.json` truncated mid-object (invalid JSON) | `package.identity=null`, `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`; no identity or check set invented | `FAIL` | 1 | `pap.package.manifest-json` |
| F22 | artifact path `../outside.md`; nothing outside the root is opened | `integrity.package=FAIL`, `integrity.artifacts=FAIL` | `FAIL` | 1 | `pap.package.path-invalid` |
| F23 | declared artifact path is a symlink outside the package | `integrity.package=FAIL`, `integrity.artifacts=FAIL`; symlink not followed | `FAIL` | 1 | `pap.package.symlink` |
| F24 | two declared paths equal modulo case (`artifacts/A.md`, `artifacts/a.md`) | `integrity.package=FAIL`, `integrity.artifacts=FAIL`; no payload read twice | `FAIL` | 1 | `pap.package.path-duplicate` |
| F25 | `PACKAGE` is a regular `.tar` file | no document; archive transport deferred (§4.1, §14.1) | — | 64 | `pap.cli.usage` |
| F26 | declared artifact file removed | `integrity.package=FAIL`, `integrity.artifacts=FAIL`, `DI=NOT_EVALUATED` | `FAIL` | 1 | `pap.package.declared-file-missing`, `pap.check.not-evaluated` |
| F27 | source declared without `path` (referenced-only); source checks required | `sources.integrity=UNAVAILABLE`, `sources.availability=UNAVAILABLE`, `DI=NOT_EVALUATED`, `SQ=NOT_EVALUATED`, `RC=PASS`, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.source.unavailable`, `pap.check.not-evaluated` |
| F28 | policy requires human review; `claims/reviews.json` absent | `humanReview=INCOMPLETE`, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.review.missing` |
| F29 | duplicate JSON key inside the `package` object of the manifest | `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`; duplicate keys are invalid, not last-wins (§4.10) | `FAIL` | 1 | `pap.package.duplicate-key` |
| F30 | artifact entry carries unknown core field `sha256` | `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED` (§4.9 strict core) | `FAIL` | 1 | `pap.package.unknown-field` |
| F31 | undeclared file `notes/extra.txt` added; declarations unchanged | `integrity.package=PASS`, `DI=PASS`, `coverage.full=true`; file not read | `PASS` | 0 | `pap.package.undeclared-file` |

F26 and F27 differ deliberately: a **missing declared file** is a package defect (`FAIL`), while a
**referenced-only source** is a format-permitted offline limitation (`UNAVAILABLE`/`INCOMPLETE`).
Collapsing them would turn legitimate offline use into a failure. F22 relies on the §4.3.1
precedence rule: a path-grammar violation is `pap.package.path-invalid`, not `pap.package.schema`,
even though Appendix A's pattern also rejects the same string. F26 requires
`pap.check.not-evaluated` because a `NOT_EVALUATED` check must record its reason in a diagnostic
(§7.2).

#### 12.4.4 Extensions, canonical form, limits, determinism and CLI surface

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F32 | non-critical unknown extension `com.example.optional` | all required positive; extension ignored and reported, `coverage.full=true` | `PASS` | 0 | `pap.extension.ignored` |
| F33 | `requiredFeatures: ["pap.feature.future"]` | package requires an unimplemented feature | `UNSUPPORTED` | 4 | `pap.feature.unsupported` |
| F34 | manifest pretty-printed, keys reordered, same JSON value as `base/` | `package.identity` equals the base Appendix E literal; statuses as F01 | `PASS` | 0 | — |
| F35 | manifest exceeds the 1 MiB manifest limit (§4.3.4) | `package.identity=null`, `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`; no crash | `FAIL` | 1 | `pap.package.limit-exceeded` |
| F36 | same command as F01, executed twice with fixed `--now` | byte-identical JSON after removing identity-excluded fields; identical text; identical `verificationRecordIdentity` | `PASS` | 0 | — |
| F37 | `pap inspect` with `--trust-policy`, with `--now`, or without `PACKAGE` | no inspection document; inspection never accepts verification inputs (§9.4) | — | 64 | `pap.cli.usage` |
| F38 | `pap explain` with no `--check` or with two `--check` flags | no explanation document (§9.5) | — | 64 | `pap.cli.usage` |
| F39 | `pap explain --check pap.check.absent/1` (id names no declared check) | no explanation document | — | 64 | `pap.cli.unknown-check` |
| F40 | `pap verify` producer-free, sentinel shims on `PATH`, network denied | result identical to F01; sentinels never executed; no socket opened | `PASS` | 0 | — |
| F41 | `--trust-policy trust-policy/invalid.json` (fails Appendix B) | fail closed: no package report, no absent-policy fallback (§9.3) | — | 64 | `pap.trust.policy-invalid` |
| F42 | `pap explain PACKAGE --check pap.check.digest-integrity/1` on `base/` | explanation document; `checkOutcome=PASS`; no `VERDICT` line | — | 0 | — |
| F43 | profile declared as `acme-supplier@0.2.0`; policy `profile-pinned.json` pins `0.1.0`, requires `trust` | `trust.profileRecognition=UNSUPPORTED`, `coverage.full=false` | `UNSUPPORTED` | 4 | `pap.trust.profile-unknown` |

F36 also asserts the weaker guarantee without `--now`: two runs may differ only in `evaluatedAt`
(and `durationMs` if emitted), while `verificationRecordIdentity` is unchanged. F34 proves
canonicalization is a property of the JSON value, not the file bytes.

#### 12.4.5 Additional claim and relation cases

These cases separate "claim file absent" (a completeness limitation) from "missing declared
file" (a package defect), and pin the reciprocal inverse-declaration rule of §8.6.

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F44 | `checkSpecs` requires `source-quote/1`; manifest declares no `claims.provenance`; source snapshot present | `integrity.package=PASS`, `DI=PASS`, `SQ=NOT_EVALUATED`, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.check.not-evaluated` |
| F45 | `checkSpecs` requires `relation-consistency/1`; manifest declares no `claims.relations`; provenance and source unchanged | `integrity.package=PASS`, `DI=PASS`, `SQ=PASS`, `RC=NOT_EVALUATED`, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.check.not-evaluated` |
| F46 | relations claim declares `A.inverse = B`, but `B.inverse` is absent or names a third relation | `integrity.package=PASS`, `DI=PASS`, `RC=FAIL`, `coverage.full=true` | `FAIL` | 1 | `pap.claim.inverse-not-reciprocal` |

F44 and F45 differ from F26/F27 deliberately: an absent claim file is format-permitted and
reported as an incomplete scope, while a missing declared file is a package defect. F46 is the
package-level counterpart of the engine's bidirectional inverse contract (#36) and does not
duplicate F06, which covers an edge to an unknown entity.


#### 12.4.6 Gate 1 clarification cases

These cases assert behaviour pinned by the Gate 1 audit (D1–D12 and §13.8). They add no new feature:
each one removes an implementation choice that could otherwise produce divergent results.

| Case | Fixture / mutation | Expected statuses (relevant) | Verdict | Exit | Codes |
|---|---|---|---|---|---|
| F47 | `base/` with `unsigned-valid.json`, `--now` exactly the policy `expiresAt` (`2026-12-01T00:00:00Z`) | `policy.state=FRESH`, all required positive, `coverage.full=true` | `PASS` | 0 | — |
| F48 | `base/` with `unsigned-valid.json`, `--now` exactly the policy `issuedAt` (`2026-11-01T00:00:00Z`) | `policy.state=FRESH`, all required positive, `coverage.full=true` | `PASS` | 0 | — |
| F49 | `base/` with `unsigned-valid.json`, `--now` one second after `expiresAt` (`2026-12-01T00:00:01Z`) | `policy.state=STALE`, `trust.policyDecision=STALE`, `coverage.full=true` (the required mechanical scope was fully evaluated; the stale policy, not missing scope, makes the verdict `INCOMPLETE`) | `INCOMPLETE` | 2 | `pap.trust.policy-stale` |
| F50 | manifest begins with a UTF-8 BOM | `package.identity=null`, `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`; no check set | `FAIL` | 1 | `pap.package.manifest-json` |
| F51 | artifact `bytes` spelled `1e2` (a JSON number token that is not an integer literal) | `package.identity=null`, `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED` | `FAIL` | 1 | `pap.package.manifest-json` |
| F52 | `base/` with `lowered-limits.json` (`fileBytes: 64`); every payload exceeds it | `integrity.package=PASS`, `integrity.artifacts=NOT_EVALUATED`, all checks `NOT_EVALUATED`, `coverage.full=false`, `effectiveLimits.fileBytes=64` | `INCOMPLETE` | 2 | `pap.package.limit-exceeded`, `pap.limit.lowered` |
| F53 | `checkSpecs[0]` has `id: "pap.check.digest-integrity/1"` but `version: "2"` | `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`, identity differs from base | `FAIL` | 1 | `pap.package.schema` |
| F54 | every `checkSpecs` entry has `required:false`; no policy | checks run and are `PASS`, required set empty, `coverage.full=false` | `INCOMPLETE` | 2 | `pap.package.empty-check-specs` |
| F55 | `base/` plus `claims/reviews.json` with one fresh in-scope approval by a reviewer enrolled in `review-required.json` | `humanReview.status=PASS`, `humanReview.basis=unbound-claim`, `coverage.full=true`; `pap.review.unbound` is both a diagnostic and a required limitation | `PASS` | 0 | `pap.review.unbound` |
| F56 | `base/` plus a trusted valid envelope and an invalid envelope; policy `signature-optional.json` (`mode: "optional"`) | `signature.validity=VALID` (one verifies), invalid entry `INVALID`, `trust.policyDecision=REJECTED`, `trust.signerIdentity=TRUSTED` | `UNTRUSTED` | 3 | `pap.signature.invalid` |
| F57 | `papVersion: "1.0"`, otherwise 0.1-shaped manifest | `integrity.package=PASS`, required checks `NOT_EVALUATED`, `coverage.full=false` | `UNSUPPORTED` | 4 | `pap.compat.version-unsupported` |
| F58 | provenance binding names a `sourceId` the manifest does not declare | `integrity.package=FAIL` | `FAIL` | 1 | `pap.package.claim-invalid` |
| F59 | two relations in `claims/relations.json` share a `name` | `integrity.package=PASS`, `RC=FAIL`, `coverage.full=true` | `FAIL` | 1 | `pap.claim.relation-duplicate` |
| F60 | `assurance-package.json` absent from an otherwise valid directory | `package.identity=null`, `integrity.package=FAIL`, `integrity.artifacts=NOT_EVALUATED`; no check set | `FAIL` | 1 | `pap.package.io` |
| F61 | `base/` with only `relation-consistency/1` required (DI/SQ optional), policy requiring only that check, and `lowered-limits.json` (`fileBytes: 64`) | `integrity.artifacts=NOT_EVALUATED` although `integrity` is not required, `RC=PASS`, `coverage.full=false`; the limit forces `INCOMPLETE` rather than a vacuous `PASS` | `INCOMPLETE` | 2 | `pap.package.limit-exceeded`, `pap.limit.lowered` |

F47–F49 pin the closed policy window and the absence of clock-skew tolerance (§6.4, §9.8). F50–F51
pin the strict JSON/I-JSON subset of §4.10 and §5.3.1. F52 pins the limit branch of §4.3.4 and the
`effectiveLimits` report field. F53 pins the `checkSpecs` version invariant of §4.4.3. F54 pins
the empty-required-set rule of §4.4.3/§7.4. F55 is the positive human-review case that §13.8
previously deferred; §6.7 now defines the binding, freshness and reviewer rules it asserts. F56
pins the optional-mode aggregation rule of §6.5: a present bad envelope blocks `PASS` even when
one good envelope verifies. F57 pins unsupported-major handling (§4.9, §15.1). F58 pins the
undeclared-source rule of §4.7.1/§8.5. F59 pins the relation-name uniqueness rule of §8.6. F60
pins the missing-manifest branch of §9.7/Appendix J.1. F61 pins the rule that any limit that stops
payload evaluation forces `INCOMPLETE`, even when the affected dimension is not required (§4.3.4,
§7.4 rule 4).

Every case above is normative; the set is F01–F61. Phase 3 may add cases but may not remove one
to let an implementation pass.

### 12.5 Acceptance rules

1. **No fixture may be changed to make an implementation pass.** A fixture, its `cases.json`
   expectation, its policy file or its envelope is normative data. Changing one is a format
   change, not a test fix: it requires an RFC amendment recorded in the decision register (§16).
2. **A spec/fixture conflict is a blocker.** If §4–§9 and a case expectation disagree, no
   implementation may silently pick a side: record the conflict as a blocking question, mark the
   case blocked (not skipped), and stop on it until the RFC is amended.
3. No case may be skipped, marked expected-fail, or have its expectation weakened (for example
   `FAIL`→`INCOMPLETE`, or a diagnostic removed from the expected set) to get a green run. A
   verifier that cannot run a case reports it unsupported, never passed.
4. The matrix is identical for the reference verifier and every independent implementation
   (§13.4); there is no implementation-specific profile. Expectations are asserted from the JSON
   document, not text, except the separately asserted §9.6 lines. A no-report case MUST assert
   empty stdout and the expected stderr code.

### 12.6 Coverage of issue #44 §9

| Issue #44 §9 bullet | Cases |
|---|---|
| unchanged valid package | F01, F13, F34 |
| modified artifact bytes | F02, F20 |
| modified raw source bytes | F03 |
| changed normalized input | F04 |
| altered quote span | F05 |
| omitted required entity/subject | F06 |
| unsupported check or extension | F07, F08, F09 |
| unknown profile/checker version | F09 (newer check version), F10 (newer format version), F43 (policy-pinned profile mismatch); profile identity is metadata unless the policy requires recognition, see F09 note |
| valid signature from untrusted signer | F11, F17 |
| invalid signature | F12 |
| absent/unknown trust snapshot (incl. expired/STALE) | F14, F15, F16, F18 |
| producer claims PASS while independent check fails | F20 |
| malformed archive / path traversal / symlink / duplicate path | F21–F25 |
| incomplete package and missing source snapshot | F26–F28 |
| required check with absent claim file | F44, F45 |
| inverse declaration not reciprocal | F46 |
| duplicate JSON key | F29 |
| unknown core field | F30 |
| unknown non-critical extension | F32 |
| unknown required feature | F33 |
| non-canonical JSON accepted | F34 |
| extra undeclared file warning | F31 |
| resource limit exceeded | F35 |
| deterministic output with fixed `--now` | F36 |
| `inspect` / `explain` usage errors | F37, F38, F39 |
| `explain` positive check record | F42 |
| Gate 1 clarification cases | F47–F61 |
| producer-runtime absence check | F40 |

---


## 13. Independent implementation strategy

The format exists so a recipient can build a second, independent checker from the specification
and get the same answer. This section defines what is normative, what an implementer may read,
which algorithms are language-neutral, what independence means, how the first interoperability
demonstration runs, and what is recorded as underspecified rather than guessed. Implementation is
out of scope for this RFC (§13.9).

### 13.1 Normative surface versus reference-only material

Normative: §4 (layout, paths, limits, manifest, claims, extensions), §5 (identities, domains,
framing, canonicalization, clock model), §6 (trust model), §7 (statuses, dimensions, coverage,
verdict), §8 (check contracts, records, witnesses), §9 (CLI), §11 (signature extension points),
§12 (matrix and fixture policy), §15.1 (compatibility); Appendices A (manifest schema), B
(trust-policy schema), C (report schema), D (claim and check-record schemas), E (canonical
vectors), J (diagnostic registry); and the §12 fixture corpus with `cases.json`.

The v0.1 conformance contract has two tiers, so a conformance claim can state exactly what it
covers. A tier is a capability boundary, not a promise that the tier's guarantees are stronger
than its cases:

- **Tier A — core verifier.** Mandatory capabilities: directory parsing and path/limit safety;
  Appendix A validation; JCS and every §5 identity; the three §8 checks with records and witnesses;
  Appendix B policy parsing, freshness, checker/profile recognition and human-review evidence;
  `verify`, `inspect` and `explain` with their §9 streams, exit codes and determinism; and every
  Tier A case: F01–F10, F14, F19, F20–F55, F57–F61. Tier A does not implement the §11 DSSE
  adapter.
- **Tier B — signature-capable verifier.** Mandatory capabilities: everything in Tier A plus the
  §11.2 DSSE adapter and the signature/trust dimensions, and all F01–F61, adding the envelope
  cases F11–F13, F15–F18 and F56. A verifier claim of "PAP v0.1 conformance" without a tier
  qualifier means Tier B.
- The in-toto mapping (§11.3) is outside both tiers: it is optional and may not be required by a
  conformance case.

The boundary rules are normative:

1. A Tier A verifier that encounters `signatures/*.dsse.json` MUST NOT report a positive signature
   or signer result. It reports `signature.validity: NOT_EVALUATED` (with one
   `signatures[]` entry per envelope, `validity: NOT_EVALUATED`), `trust.signerIdentity:
   NOT_EVALUATED`, `pap.signature.unsupported-format` and a limitation. If the policy requires a
   signature or the `signature`/`trust` dimension, the verdict is `INCOMPLETE`, never `PASS`; if
   not required, an unsigned-package result may still be `PASS`, but the report carries the
   limitation and the unevaluated signature dimension. Tier A conformance cases do not include an
   envelope-bearing package precisely because its signature outcome is not part of that tier.
2. A capability outside a tier — an unimplemented check, a required feature, a critical extension
   or an optional adapter — is never a positive result. It is `UNSUPPORTED` (for a required
   check/feature/extension) or `NOT_EVALUATED`/`NOT_APPLICABLE` (for an optional or absent
   capability), the dimension is not positive, `coverage.full` is `false` where that capability is
   required, and the verdict cannot be `PASS`. `NOT_EVALUATED` is never reported as `PASS`.
3. Cross-implementation agreement (§13.6) is claimed only between implementations of the **same
   tier**. Tier A and Tier B must agree on every Tier A case; Tier B-only cases have no Tier A
   counterpart and are not compared against one. A Tier A result MUST NOT be presented as
   satisfying a Tier B case, and a Tier B result on an envelope case does not enlarge what a Tier A
   verifier claimed.

| Situation | Tier A report | Tier B report |
|---|---|---|
| envelope present, signature/trust not required | `signature.validity: NOT_EVALUATED`, `trust.signerIdentity: NOT_EVALUATED`, `pap.signature.unsupported-format`, limitation; no positive signature status | evaluate per §6.5 and §11.2 |
| envelope present, signature or trust required | as above, and `INCOMPLETE` (never `PASS`) | evaluate; `PASS` only if the required set is satisfied |
| required check, required feature or critical extension unsupported | `UNSUPPORTED`, `coverage.full: false`, never `PASS` | same |
| required source/input/claim unavailable or skipped by a limit | `NOT_EVALUATED`/`UNAVAILABLE`, `INCOMPLETE`, never `PASS` | same |
| optional capability absent | `NOT_EVALUATED`/`NOT_APPLICABLE` with a limitation; optional results never gate | same |

`NOT_EVALUATED` is never converted into a positive status in either tier: it keeps `coverage.full`
false where the capability is required and cannot support `PASS`.

Reference-only: any reference implementation's source, module layout, internal APIs, error types
and performance; its text layout beyond §9.6 required lines; diagnostic message wording (codes are
normative, messages are not); and any producer-internal model, IR, profile, renderer or template —
these are not part of the format and MUST NOT appear in a package (§4.12). The reference
implementation's language, runtime and libraries are also non-normative.

An independent implementer must work from the normative set alone. If a clause cannot be
implemented without reading reference code, that clause is a specification defect: record it as a
blocker (§13.8) and fix the RFC rather than copy code.

### 13.2 No producer-private code

The second implementation MUST NOT import, link, vendor or read Contract Builder source, its build
pipeline, internal IR, profile/checker implementations or generated artifacts as an authority; it
MUST NOT interpret a field through a producer-internal format. It MAY read producer output as test
input — a package is data — including the Appendix F example and the fixtures, and MAY use
standard JSON/SHA-256/file-I/O libraries, but MUST validate canonicalization and digests against
Appendix E rather than trust a library by assumption.

This is the separation guarantee: the verifier is implementable without the producer, and a
package is interpretable without the producer's model. A field defined by producer internals is a
design error to fix, not a feature to support.

### 13.3 Language- and runtime-neutral algorithms

| Algorithm | Normative source | Neutrality requirement |
|---|---|---|
| I-JSON decoding: duplicate keys rejected, no floats in core/claims, lone surrogates rejected, no BOM | §4.10, D2 | strict parser plus duplicate-key check; no reliance on last-wins defaults |
| RFC 8785 JCS canonicalization | §5.2, D2 | canonical bytes are the contract; a library that misses Appendix E vectors is wrong for this format |
| `H(domain, octets) = SHA-256(ASCII(domain) ‖ 0x00 ‖ octets)` | §5.2 | one hash call; fixed domain table; no language string encoding |
| Length-prefixed framing (`u32be` tag length, tag, `u32be` part count, parts) | §5.2 | exact pre-hash bytes; Appendix E framing-ambiguity vector must match |
| Path grammar, byte-wise duplicate/case rule, root confinement | §4.3.1–§4.3.2 | byte comparison on ASCII paths, no Unicode normalisation, no resolution outside the root |
| LF normalisation (`UTF-8` fatal decode → CRLF/CR→LF; binary fallback raw) | §4.5.1, §5.6 | implementable from text; Appendix E `crlf` vector pins raw and normalised digests |
| Byte-range quote check: `sourceBytes[start..end)`, `H("pap.quote.v1", bytes)`, bounds | §8.5 | exact half-open range; no Markdown parsing or whitespace collapsing |
| Status vocabulary and verdict precedence | §7.2–§7.5 | pure function of reported statuses; no policy logic beyond the stated rules |
| Report shape, JCS serialization, identity-form exclusions | §5.9, Appendix C | output validates against the schema; identity form explicit |
| Exit-code mapping and stream discipline | §9.6–§9.7 | table lookup, no interpretation beyond the table |

Streaming/buffering within §4.3.4 limits and non-required text rendering are implementation
choices; neither affects a verdict, identity or diagnostic code.

### 13.4 What "implementation independence" means

1. **Separate repository and ownership.** Its own repository, maintainer/team, review and release
   process. A fork of the reference implementation is not independent.
2. **Different language preferred; always a different codebase.** A different language probes for
   language-specific assumptions (numbers, strings, key order); same-language implementations MUST
   share no source, module, generated code or copy-paste.
3. **Spec-only inputs.** Authors work from this RFC, appendices, schemas, vectors and fixtures,
   with no access to reference internals and no copying beyond what normative text states.
4. **No shared runtime with producer or reference verifier.** No Contract Builder or
   reference-verifier library; third-party JSON/SHA-256 libraries are allowed, conformance proved
   by vectors.
5. **Separate test harness.** Runs the §12 corpus with its own runner in its own CI and publishes
   results; the reference harness is not its only evidence, because harness logic is part of what
   is being checked.
6. **Documented independence.** Repository records language, author/team separation, dependencies
   and the spec revision targeted, so a reviewer can verify the claim.

### 13.5 First interoperability demonstration (Phase 3 of #43)

Stage 1 — Tier A: parse/validate a `papVersion "0.1"` directory package per §4 and Appendix A;
JCS-canonicalize and compute `packageIdentity`, `artifactDigest`, `rawSourceDigest`,
`normalizedInputDigest` and declared claim digests per §5; run the three checks per §8.4–§8.6 with
check records and witnesses; parse Appendix B policies and evaluate freshness, checker/profile
recognition and human-review evidence per §6.4–§6.7; produce the Appendix C report and §9.7 exit
code for the Tier A cases (F01–F10, F14, F19, F20–F55, F57–F61), including safety and limit cases;
compare per §13.6.

Deliberately outside stage 1: the §11 signature adapter and signer trust (stage 2),
`inspect`/`explain` document comparison (shape defined, not asserted), text layout equality, and
any producer integration. Stage 2 adds the §11 DSSE adapter and the envelope cases F11–F13,
F15–F18 and F56; since signed expectations are already normative (§12.1), stage 2 does not reopen
the format or change a Tier A expectation.

### 13.6 Comparing results across implementations

Both implementations run the same `cases.json` command with the same `--now`, and compare the JSON
document, never the text:

| Compared | Rule |
|---|---|
| tier | equal: only results from implementations claiming the same tier are compared; Tier A and Tier B must agree on every Tier A case |
| exit code | exact |
| `verdict` | exact |
| every Appendix C dimension status | exact on every field |
| each check outcome | exact per `checkId`/`checkVersion` |
| `coverage` | equal `requiredChecks` set, `full`, counts |
| `diagnostics[].code` | superset of the case's required code set (§12.2); exact only when the case sets `diagnosticCodesExact`; messages/severities/scopes schema-checked, not compared |
| `limitations[].code` | superset of the case's required limitation set; `detail` wording not compared |
| package-derived identities: `packageIdentity`, `identities.artifacts[]`, `identities.sources[]`, `normalizedInputDigest`, `extensionClosureDigest` | exact (base pinned by Appendix E) |
| `effectiveLimits` | exact when either report has it; absent in both under default limits |
| `verificationRecordIdentity`, `checkerIdentity`, per-check `checker` | **not compared** — they include the verifier's own implementation identity (§5.8–§5.9, D12) |
| `evaluatedAt` | equal only under the same `--now` |
| `producerClaims.comparison` | relation values compared when both reports include the block; claimed/independent outcomes exact; presence of the block not compared |
| text output | not compared beyond §9.6 required lines |

Disagreement handling: a mismatch is a finding, not a tolerance — record the case, both values and
the normative clause that should decide it; classify as implementation bug, ambiguous clause, or
wrong fixture expectation. Ambiguous clauses and wrong expectations are RFC blockers (§12.5); fix
the RFC or the fixture, never normalise the comparison. Both implementations MUST agree on every
stage-1 case before a Gate 3 claim; partial agreement is reported as partial, with failing case
ids. Correctly out-of-scope differences (record identity, messages, text, `evaluatedAt` without a
fixed clock) MUST be excluded by an explicit, published exclusion list — never a silent filter.

### 13.7 Publication of schemas, vectors and fixtures

1. **Schemas**: Appendices A–D as JSON Schema documents with stable `$id`s
   (`urn:pap:0.1:assurance-package`, `:trust-policy`, `:verification-report`, claim/check-record
   schemas), in a versioned tagged location with checksums. The `inspect` and `explain` document
   shapes of §9.4–§9.5 are published with the verifier release; they are outside the v0.1
   conformance subset until stage 2.
2. **Vectors**: Appendix E as a machine-readable file — canonical manifest bytes, domain-separated
   digest vectors, framing-ambiguity vectors, CRLF/normalisation vectors, quote vectors, checker
   identity and a record-identity vector — each with exact input bytes and expected digest, usable
   from any language's test framework.
3. **Fixtures and registry**: the §12 corpus plus `cases.json` as inert data with a checksum
   manifest (no generation script required), and Appendix J codes with severity and meaning as
   data so both implementations can check code-set agreement.

Rules: immutable tagged releases (`pap-v0.1.0` and successors), open licence, checksums for every
artifact, no network required to verify. The reference implementation MAY be published, but it is
not conformance input and copying it is not independence (§13.4).

### 13.8 Underspecified areas: Gate 1 resolution

The Gate 1 audit (`docs/architecture/pap-v0.1-gate1-decision-audit.md`) reviewed every row below
against the normative text, schemas, vectors and matrix. The audit found no known undefined
required behaviour in these areas: each is resolved normatively or explicitly deferred. That is a
self-audit result, not proof; an independent implementer that still cannot implement a clause
reports it as a specification defect, and a disagreement on a deferred row is a known open
question, not an implementation bug. Implementations MUST NOT silently assume behaviour that this
table leaves deferred.

| Area | Resolution | Tests |
|---|---|---|
| Clock and freshness boundaries | **Resolved** by §6.4/§9.8: the policy window is closed at both ends and has no clock-skew tolerance; review future skew stays at 300 s and its age boundary is inclusive (§6.7). Production use of `--now` remains a CLI-project choice (§16.1(6)) that changes no verdict or identity field. | F47, F48, F49 |
| Error-message wording | **Deferred by design**: messages may differ and only codes are normative (§7.7, §9.6); text layout beyond the required lines is not compared (§13.6). | code-set assertions only; no message text is asserted |
| JSON parser strictness | **Resolved** by §4.10, §5.3.1 and the document-type mapping below: UTF-8 without BOM, duplicate keys invalid, integer-literal number tokens only, and a fixed diagnostic per document type. Parse failure of the manifest is never `INCOMPLETE`; a claim file fails the package while a limit stops the affected scope. | F29, F35, F50, F51, F58; F21 for truncated JSON |
| Resource-limit defaults and enforcement points | **Resolved** by §4.3.4 and §9.11: the manifest limit yields `FAIL`; every other limit yields `NOT_EVALUATED`/`INCOMPLETE` with `coverage.full: false` and is reported in `effectiveLimits`; limits may only be lowered, and the policy `limits` maximum equals the default. | F35, F52 |
| Undeclared-file scan completeness | **Resolved** by §4.3.3/§7.5: an enumeration failure yields `pap.package.undeclared-scan-incomplete`, `coverage.full: false` and `INCOMPLETE`; a declared-file failure remains `FAIL`. | a unit/hostile test; no portable static case (see below) |
| Human-review evidence semantics | **Resolved for v0.1** by §6.7: binding, freshness, reviewer recognition, single-approval sufficiency and rejection precedence are pinned. Signed approvals remain deferred because v0.1 has no policy field to require one (§14.1, §16.1(1)). | F28 (negative), F55 (positive) |
| Signature adapter details | **Resolved** by §11.2: DSSE profile, payload type, Ed25519 and canonical-`S` verification, canonical base64, envelope discovery/order/limit, and the exact policy key binding are fixed. The in-toto mapping stays optional and outside the conformance tiers (§11.3, §13.1). | Tier B: F11–F13, F15–F18, F56 |
| Multi-envelope aggregation | **Resolved** by §6.5: the aggregate covers every present envelope, an unknown/untrusted/invalid envelope blocks `PASS` in `optional` and `required` modes, and duplicate signers are counted once. | F18, F56 |
| Text-output layout | **Deferred by design**: layout, column widths and abbreviations beyond the §9.6 required lines remain implementation-defined; the required lines and tokens are now pinned and asserted. | F01 and F02 re-run with `--format text` (§12.3) |

Malformed-input mapping (normative; keeps each parse failure on one diagnostic):

| Document | Failure | Diagnostic | Effect |
|---|---|---|---|
| manifest | not UTF-8, BOM, trailing data, invalid JSON, duplicate key, non-I-JSON number/string, nesting/string limit | `pap.package.manifest-json`, `pap.package.duplicate-key` or `pap.package.limit-exceeded` per the first failing rule | `package.identity: null`, `integrity.package: FAIL`, verdict `FAIL` (a manifest limit is the only limit that yields `FAIL`, §4.3.4) |
| manifest | shape/pattern/enum violation, unknown core field, cross-field invariant (duplicate id/path, `checkSpecs` version suffix) | `pap.package.schema`, `pap.package.unknown-field`, `pap.package.path-invalid`, `pap.package.path-duplicate` or `pap.package.duplicate-id` | `integrity.package: FAIL`; identity is still computed when the manifest can be canonicalized |
| manifest | every declared check is optional and the policy requires none | `pap.package.empty-check-specs` (warning) | valid package, `integrity.package: PASS`, empty required set, verdict `INCOMPLETE`, `coverage.full: false` |
| claim file | invalid JSON, schema violation, duplicate claim id, undeclared source reference, `checkVersion`/`checkId` mismatch | `pap.package.claim-invalid` | `integrity.package: FAIL`, verdict `FAIL` |
| claim file | unknown `papClaimsVersion` | `pap.claim.unsupported-version` | claim not interpreted; dependent check `UNSUPPORTED`/`NOT_EVALUATED`; package integrity is not failed |
| trust policy | unreadable, invalid JSON, Appendix B or cross-field violation | `pap.trust.policy-invalid` on stderr | fail closed: exit 64, no report |
| any JSON document | nesting depth or string-size limit | `pap.package.limit-exceeded` | manifest: `FAIL`; claim: dependent check `NOT_EVALUATED`; policy: exit 64 |

The compatibility-refusal case is also closed: §4.9, §15.1 and F10/F57 fix a structurally readable
core with required checks `NOT_EVALUATED` and an `UNSUPPORTED` verdict (the package is not a
producer defect; the verifier simply does not know the newer minor's or major's semantics).

If two implementations still disagree on a deferred row, the interop report records it as a
blocker and escalates it; it is never resolved by adopting the reference behaviour.

### 13.9 Relation to roadmap #43 Phases 2–3 and scope statement

This RFC itself is **design only**: it adds no verifier, producer, CLI, fixture generator or test
code. The maintainer accepted the v0.1 specification on 2026-11-02 and authorized Phase 2 after
Gate 0 was recorded COMPLETE on #43 (comment 6570952005). The Phase 2 implementation is merged into
`main` via PR #64 and available under `pap/`; independent interoperability validation remains
pending. This document cites those records and does not independently re-audit Gate 0.

- **Phase 2** (independent verifier CLI) consumes §4–§9 and §12. Its gate is a recipient verifying
  offline with no Contract Builder service or runtime dependency; §12 cases are the evidence, with
  the Tier A cases executable before signatures and the envelope cases added in Phase 2d.
- **Phase 3** (adversarial corpus and independent implementation) consumes §12 and §13. Its gate
  requires agreement on the declared subset and no package reported as fully verified when
  required checks are missing, unsupported or producer-asserted only. This section defines the
  comparison and independence criteria; it is not the comparison itself.

The RFC's obligation ends at specifying the contract and its evidence; a later implementation PR
MUST be reviewable against this document, and a spec/fixture conflict found during implementation
is an RFC amendment, not a silent implementation choice.

---


## 14. Implementation sequencing after acceptance

This RFC authorizes no implementation by itself. With the decision register in §16 accepted,
Gate 0 recorded COMPLETE on #43, and Phase 2 authorized by the maintainer on 2026-11-02, the
following sequence keeps the format independently reviewable and matches roadmap #43 Phases 2–3.
The Phase 2 implementation is merged into `main` via PR #64 and available under `pap/`; independent
interoperability validation remains pending. The sequence is:

| Step | Work | Exit condition |
|---|---|---|
| RFC + decision | this document; maintainer records decisions | accepted decision register |
| 2a | verifier skeleton: directory walker, manifest schema, JCS, digests, report/exit codes | Appendix E vectors pass; parsing, digest and safety cases of §12 pass |
| 2b | checks: digest-integrity, source-quote, relation-consistency | all unsigned check cases of §12 pass, including F44–F46; no producer imports |
| 2c | CLI: `verify`, `inspect`, `explain`; text/JSON; trust policy parsing | unsigned CLI and safety cases of §12 pass; offline run in a clean environment |
| 2d | DSSE/Ed25519 adapter, signer trust, profile recognition and `explain` | envelope cases F11–F13, F15–F18 and F56 pass, plus F43 (profile recognition) and F42 (`explain`) |
| 3a | fixture corpus committed as full static packages with expected assertions | §12 matrix executable |
| 3b | independent second implementation (different language/author) | agreement on package-derived identities and verdict/dimensions/checks |
| gate | review of the first interop demonstration | Gate 3 of #43 |

A step MUST NOT start before the decisions it depends on are accepted. If implementation reveals
an underspecified area, the RFC is amended rather than the implementation choosing silently;
§16's decision register is the place to record the amendment.

### 14.1 Deferred integrations and non-goals

Explicitly deferred, with the condition for revisiting:

| Deferred item | Why | Revisit when |
|---|---|---|
| Archive transport (tar/zip) | directory-only removes zip-slip/duplicate/case-collision classes in v0.1 | a real distribution channel requires a single file; then apply §10's archive rules |
| Compression and OCI | no hosted/registry requirement in the roadmap | transport need is demonstrated |
| Sigstore bundles / transparency log / SCITT | require network or online status sources; v0.1 is offline | an online trust-status channel is designed and its offline fallback is specified |
| Key management, revocation, enrollment | operator-local policy is the v0.1 trust model | a multi-tenant trust service is in scope |
| Temporal assumption-impact journal | roadmap Phase 4 | stable identities from v0.1 exist |
| Commitment mandates / authorization | roadmap Phase 5 | a concrete partner use case exists |
| Multiple digest algorithms | algorithm confusion and implementation cost | a versioned allowlist and vectors exist |
| Unicode/case-insensitive package paths | v0.1 restricts to ASCII | portability requirements justify the complexity |
| Floating-point numbers in manifests | JCS number edge cases | a concrete field needs them, with vectors |
| Semantic truth, legal enforceability, human review correctness | out of scope for any mechanical verifier | never claimed by this format |
| Producer implementation | this RFC is design only | after Phase 2a |
| Markdown rendering / template execution | not a core invariant | never in the verifier |

---


## 15. Compatibility, risks and limitations

### 15.1 Versioning and compatibility policy

- `papVersion` is `major.minor`, each component a canonical decimal with no leading zeros
  (`^[0-9]+\.[0-9]+$`). v0.1 supports exactly the `0.1` core.
- Within major version `0`, a minor release MAY add optional extension keys, optional feature
  identifiers and optional claim kinds; it MUST NOT make an existing optional field required,
  change a status meaning, change a digest domain or change canonicalization.
- A verifier declares the exact `(major, minor)` values it supports (`0.1` for this RFC). Any
  other version is `UNSUPPORTED`: a newer `0.x` minor yields `pap.compat.minor-newer`; an older
  minor or a different major yields `pap.compat.version-unsupported`. The verifier never
  approximates unknown semantics. It may still report a structurally readable 0.1-core shape with
  `integrity.package: PASS`, but required checks are `NOT_EVALUATED` and the verdict is
  `UNSUPPORTED` (§4.9, F10, F57).
- A major release may change the core; old verifiers must report `UNSUPPORTED` with
  `pap.compat.version-unsupported` for it.
- Diagnostic codes are stable; new codes are additive. Removing or redefining a code is a major
  change.
- Deprecation: a deprecated field or status remains accepted for at least one minor release and
  produces a warning (`pap.compat.deprecated`), never a silent acceptance after removal.

### 15.2 Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A verifier is implemented from an ambiguous clause | two implementations disagree | conformance vectors (§5.12), fixture matrix (§12), decisions recorded before code |
| Operators treat `PASS` as semantic truth | misplaced reliance | explicit dimensions, `semanticTruth: NOT_EVALUATED`, text output says `NOT A PASS` only for non-PASS; docs repeat the boundary |
| A malicious package exploits a parser | code execution or DoS | data-only package, no hooks, no symlinks, ASCII paths, strict schemas, limits, no network |
| Trust policy is stale or substituted | false trust | policy supplied out of band, digest reported, expiry → `STALE`, package cannot override |
| Producer claims are mistaken for evidence | false assurance | separate files/schemas, report labels, comparison only, no verdict path |
| Missing evidence is read as success | silent partial pass | coverage `full`, `NOT_EVALUATED`, no `PASS` on partial scope |
| Signature adapter churn | interoperability loss | DSSE profile fixed, algorithm allowlist, vectors for envelope parsing; Sigstore deferred |
| Timestamp ambiguity offline | freshness disputes | timestamps are records, never build identity; policy expiry against local clock, `--now` for tests |
| Resource exhaustion | verifier unavailable | default limits, streamed hashing, bounded JSON |
| Independent implementation takes shortcuts | false independence | no shared code/imports, different language preferred, conformance agreed field-by-field |

### 15.3 Known limitations

- No revocation or online trust status in v0.1; a revoked key is still trusted if the local
  policy says so and has not expired.
- No proof that a source snapshot is the source the producer actually used, beyond the declared
  digest and acquisition claim.
- No completeness proof: a producer can omit evidence. The verifier can only report declared
  coverage, not whether the selected evidence is representative.
- Local verification cannot detect a compromised producer that generated a package with
  internally consistent but misleading evidence.
- The verifier binary and trust policy are within the operator's trust base; their compromise is
  out of scope.
- The verifier does not render or execute artifacts, so it says nothing about how they will be
  interpreted by a human or another tool.
- ASCII-only paths and directory-only transport are v0.1 restrictions.
- `producer-report.json` messages are not normative and may differ.

---


## 16. Decision register

All decisions D1–D12 are `accepted` by the maintainer on 2026-11-02. The "Selected" column is
the accepted choice; alternatives are retained for historical traceability. OD-1–OD-7 are also
accepted as recommended in the Gate 1 audit and recorded on #57. Explicitly deferred sub-parts:
signed/authenticated human-review approvals (D8/OD-2) and full text-output layout standardization
beyond required lines/tokens (D10/OD-3). Other v0.1 exclusions remain listed in §16.1 and the audit.

| ID | Decision | Status | Selected | Alternatives | Rationale | Consequence |
|---|---|---|---|---|---|---|
| D1 | Archive support | accepted | directory-only v0.1; archive deferred with safe-extraction rules | directory + tar/zip; OCI only | removes zip-slip, duplicate-entry, case-collision and bomb classes; offline directory is enough for the first demo | no single-file transport; §14 lists the condition to revisit |
| D2 | Canonical JSON | accepted | RFC 8785 JCS over I-JSON, integers only | custom canonical JSON; canonical CBOR | standard, testable, language-neutral; JCS covers number/string edge cases | verifier must implement JCS; floats rejected in core/claims |
| D3 | Hash and domains | accepted | SHA-256, `H(domain, bytes)` with fixed domains | SHA-512; BLAKE3; multi-algorithm negotiation | ubiquitous, fast, no agility attack surface in v0.1 | algorithm change is a format change; input digests use `pap.input.file.v1` (per file) and `pap.input.set.v1` (set) so one input cannot collide with the set, a refinement recorded during RFC integration |
| D4 | Source snapshots | accepted | optional in format, required for source-dependent PASS; embedded or referenced | always embed; always reference | offline verification requires bytes, but confidential sources need a referenced-only mode | missing snapshot → `UNAVAILABLE`/`INCOMPLETE`, never a pass |
| D5 | Unknown fields | accepted | strict core; `extensions` + `requiredFeatures`; unknown critical → `UNSUPPORTED` | permissive ignore; ignore-all-with-warning | security-relevant fields must not be silently ignored; forward compatibility is explicit | producers must namespace extensions; core schema frozen per major |
| D6 | Claims vs results | accepted | separate files, schemas, namespaces; claims never affect verdict | merge claims into report; producer-supplied results | producer output is untrusted; comparison is evidence, not authority | an extra report block and a comparison field |
| D7 | Status model | accepted | eight independent dimensions, check outcomes, verdict precedence, coverage `full` | single boolean; one aggregate enum | prevents partial/unsupported from becoming success; matches issue #44 | larger report; every status must be explained by a limitation code |
| D8 | Trust policy | accepted | local offline JSON, operator-supplied, optional signatures, expiry → `STALE` | signature mandatory; infer trust from package; online status | preserves integrity-only use; keeps authority out of the package | operator must supply a policy for trust decisions; no revocation |
| D9 | v0.1 checks | accepted | digest-integrity, source-quote (byte range), relation-consistency | also rendering checks; execute profile checks | smallest useful set; all independently checkable without producer code | source-quote requires exact byte ranges; Markdown adapters stay producer-side |
| D10 | CLI | accepted | `pap verify/inspect/explain`; exit 0/1/2/3/4; deterministic JSON | single `verify` command; `contract-builder verify` subcommand | single-purpose consumer; report authoritative; CI-friendly exits | new binary/project; TTY/format work |
| D11 | Compatibility | accepted | major.minor, core frozen within major, additive only | unversioned format; semver immutability | implementable by two teams; explicit `UNSUPPORTED` instead of guessing | minor releases limited to extensions/features |
| D12 | Independence | accepted | second implementation from spec + vectors, different language preferred, unsigned first | same-language port; shared library | only a genuinely separate implementation tests the spec | requires publishing schemas/vectors and a second team's time |

### 16.1 Open questions not resolvable in v0.1

These are recorded as blockers, not assumptions:

1. Human-review authority: v0.1 recognizes a reviewer identity only through a policy `signers[]`
   entry whose `allowedRoles` contains `reviewer` (§6.7), and it does not authenticate the
   approval. Whether an approval must be cryptographically signed, and what such a signature
   would cover, remains deferred: a future policy needs a review-attestation format and reviewer
   authority model before it can require one.
2. Trust-status freshness: offline v0.1 cannot distinguish "no revocation" from "revocation
   unknown"; a future online status channel must define an offline fallback before it is added.
3. Archive extraction: if a single-file transport is required, the exact streaming algorithm,
   duplicate-entry policy and platform-specific path handling must be specified before
   implementation.
4. Signature transparency: Sigstore/SCITT integration needs a decision on what an offline
   receipt means; not in v0.1.
5. Multiple artifacts and per-artifact policy: v0.1 reports all artifacts together; a future
   policy may require a subset or per-artifact trust decisions.
6. `--now` in production: it exists for deterministic tests and reproductions. Whether a
   production caller may supply it, and how that is signalled beyond `evaluatedAt`, is left to the
   CLI project; it changes no format field or identity (§9.8).

---


## Appendix A — Manifest JSON Schema (normative)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:assurance-package",
  "title": "Portable Assurance Package v0.1 manifest",
  "type": "object",
  "additionalProperties": false,
  "required": ["papVersion", "package", "artifacts", "checkSpecs"],
  "properties": {
    "papVersion": { "type": "string", "pattern": "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$" },
    "package": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id"],
      "properties": {
        "id": { "type": "string", "minLength": 1, "maxLength": 512 },
        "title": { "type": "string", "maxLength": 512 },
        "createdAt": { "$ref": "#/$defs/rfc3339" },
        "producer": {
          "type": "object",
          "additionalProperties": false,
          "required": ["name", "version"],
          "properties": {
            "name": { "type": "string", "minLength": 1, "maxLength": 256 },
            "version": { "type": "string", "minLength": 1, "maxLength": 128 }
          }
        }
      }
    },
    "subject": {
      "type": "object",
      "additionalProperties": false,
      "required": ["projectId"],
      "properties": {
        "projectId": { "type": "string", "minLength": 1, "maxLength": 512 },
        "revision": { "type": "string", "maxLength": 256 }
      }
    },
    "build": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "engineVersion": { "type": "string", "minLength": 1, "maxLength": 128 },
        "manifestVersion": { "type": "string", "minLength": 1, "maxLength": 64 },
        "inputDigest": { "$ref": "#/$defs/digest" },
        "normalizedInputDigest": { "$ref": "#/$defs/digest" },
        "extensions": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["kind", "id", "version"],
            "properties": {
              "kind": { "enum": ["profile", "adapter", "renderer", "checker"] },
              "id": { "type": "string", "minLength": 1, "maxLength": 256 },
              "version": { "type": "string", "minLength": 1, "maxLength": 128 }
            }
          }
        }
      }
    },
    "artifacts": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "path", "mediaType", "bytes", "digest"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "path": { "allOf": [{ "type": "string", "$ref": "#/$defs/path" }, { "type": "string", "pattern": "^artifacts/" }] },
          "mediaType": { "type": "string", "minLength": 1, "maxLength": 256 },
          "bytes": { "type": "integer", "minimum": 0 },
          "digest": { "$ref": "#/$defs/digest" }
        }
      }
    },
    "inputs": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "path", "mediaType", "digest", "normalization"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "path": { "allOf": [{ "type": "string", "$ref": "#/$defs/path" }, { "type": "string", "pattern": "^inputs/" }] },
          "mediaType": { "type": "string", "minLength": 1, "maxLength": 256 },
          "digest": { "$ref": "#/$defs/digest" },
          "normalization": { "enum": ["lf", "none"] }
        }
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "mediaType", "digest"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "path": { "allOf": [{ "type": "string", "$ref": "#/$defs/path" }, { "type": "string", "pattern": "^sources/" }] },
          "mediaType": { "type": "string", "minLength": 1, "maxLength": 256 },
          "digest": { "$ref": "#/$defs/digest" },
          "acquiredAt": { "$ref": "#/$defs/rfc3339" },
          "acquisition": {
            "type": "object",
            "additionalProperties": false,
            "required": ["method"],
            "properties": {
              "method": { "type": "string", "minLength": 1, "maxLength": 128 },
              "uri": { "type": "string", "maxLength": 2048 },
              "revision": { "type": "string", "maxLength": 512 }
            }
          }
        }
      }
    },
    "claims": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "provenance": { "$ref": "#/$defs/claimRef" },
        "relations": { "$ref": "#/$defs/claimRef" },
        "producerReport": { "$ref": "#/$defs/claimRef" },
        "reviews": { "$ref": "#/$defs/claimRef" }
      }
    },
    "profile": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "version"],
      "properties": {
        "id": { "type": "string", "minLength": 1, "maxLength": 256 },
        "version": { "type": "string", "minLength": 1, "maxLength": 128 },
        "closureDigest": { "$ref": "#/$defs/digest" }
      }
    },
    "checkSpecs": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "version"],
        "properties": {
          "id": { "$ref": "#/$defs/checkId" },
          "version": { "type": "string", "pattern": "^(0|[1-9][0-9]*)$" },
          "required": { "type": "boolean" }
        }
      }
    },
    "extensions": {
      "type": "object",
      "propertyNames": { "pattern": "^[a-z0-9]+(\\.[a-z0-9-]+)+$" },
      "additionalProperties": {
        "type": "object",
        "additionalProperties": false,
        "required": ["version", "critical"],
        "properties": {
          "version": { "type": "string", "minLength": 1, "maxLength": 128 },
          "critical": { "type": "boolean" },
          "data": { "type": "object" }
        }
      }
    },
    "requiredFeatures": {
      "type": "array",
      "uniqueItems": true,
      "items": { "type": "string", "pattern": "^pap\\.[a-z0-9.-]+$" }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
    "checkId": { "type": "string", "pattern": "^pap\\.check\\.[a-z0-9-]+/[0-9]+$" },
    "rfc3339": { "type": "string", "format": "date-time" },
    "path": {
      "type": "string",
      "maxLength": 255,
      "pattern": "^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+){1,15}$"
    },
    "claimRef": {
      "type": "object",
      "additionalProperties": false,
      "required": ["path", "digest"],
      "properties": {
        "path": { "allOf": [{ "type": "string", "$ref": "#/$defs/path" }, { "type": "string", "pattern": "^claims/" }] },
        "digest": { "$ref": "#/$defs/digest" }
      }
    }
  }
}
```

The schema validates shape and path grammar. The verifier additionally enforces cross-field
invariants that JSON Schema cannot express: unique artifact/source/input ids and paths, unique
check ids, unique claim paths, `checkSpecs[].version` equal to the version suffix of its `id`, and
either at least one required check or the empty-required-set rule of §4.4.3/§7.4. A required check
does **not** require its claim file to be declared: an absent claim file makes that check
`NOT_EVALUATED` (a completeness limitation, not a structural error, §8.1). A path-grammar
violation is reported as `pap.package.path-invalid`, not `pap.package.schema`, even though the
`path` pattern also rejects it (§4.3.1).

---


## Appendix B — Trust policy JSON Schema (normative)

The policy is supplied by the operator (`--trust-policy FILE`), never by the package (§6.3). It is
canonicalized as JCS over the I-JSON subset (§5.2) for `policy.digest`. `additionalProperties` is
`false` at every level: an unknown field is a policy error, reported as `pap.trust.policy-invalid`
with exit code `64` and no package report (§6.3.2). Cross-field invariants that JSON Schema cannot
express are normative in §6.3.1/§6.3.2: `keyId` values are unique; every `signers[].keyIds` entry
exists in `keys[]`; `minimumValidSigners` does not exceed the number of enrollable signers; a
`requiredDimensions` entry is unique and from the enumerated evaluable set; `limits` values never
exceed the §4.3.4 defaults. An orphan key — present in `keys[]` but referenced by no `signers[]`
entry — is permitted: an envelope signed by it is `UNKNOWN`/`REJECTED` (§6.5), never silently
trusted.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:trust-policy",
  "title": "Portable Assurance Package v0.1 trust policy",
  "type": "object",
  "additionalProperties": false,
  "required": ["trustPolicyVersion", "id", "issuedAt", "expiresAt", "signature", "keys",
               "signers", "checkers", "profiles", "requiredChecks", "requiredDimensions",
               "humanReview"],
  "properties": {
    "trustPolicyVersion": { "const": "0.1" },
    "id": {
      "type": "string", "minLength": 1, "maxLength": 128,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
    },
    "issuedAt": { "$ref": "#/$defs/rfc3339" },
    "expiresAt": { "$ref": "#/$defs/rfc3339" },
    "signature": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mode"],
      "properties": {
        "mode": { "enum": ["disabled", "optional", "required"] },
        "minimumValidSigners": { "type": "integer", "minimum": 1, "maximum": 64, "default": 1 }
      }
    },
    "keys": {
      "type": "array",
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["keyId", "algorithm", "publicKey"],
        "properties": {
          "keyId": { "$ref": "#/$defs/keyId" },
          "algorithm": { "const": "ed25519" },
          "publicKey": { "type": "string", "pattern": "^[A-Za-z0-9_-]{43}$" }
        }
      }
    },
    "signers": {
      "type": "array",
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["keyIds", "identity", "allowedRoles"],
        "properties": {
          "keyIds": {
            "type": "array", "minItems": 1, "maxItems": 8, "uniqueItems": true,
            "items": { "$ref": "#/$defs/keyId" }
          },
          "identity": { "$ref": "#/$defs/identity" },
          "allowedRoles": {
            "type": "array", "minItems": 1, "maxItems": 2, "uniqueItems": true,
            "items": { "enum": ["producer", "reviewer"] }
          },
          "allowedPackageIds": {
            "type": "array", "minItems": 1, "uniqueItems": true,
            "items": { "$ref": "#/$defs/packageId" }
          },
          "allowedPackageIdentities": {
            "type": "array", "minItems": 1, "uniqueItems": true,
            "items": { "$ref": "#/$defs/digest" }
          }
        }
      }
    },
    "checkers": {
      "type": "array",
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "version", "implementationDigest"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 128 },
          "version": { "type": "string", "minLength": 1, "maxLength": 128 },
          "implementationDigest": { "$ref": "#/$defs/digest" }
        }
      }
    },
    "profiles": {
      "type": "array",
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "version"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "version": { "type": "string", "minLength": 1, "maxLength": 128 },
          "closureDigest": { "$ref": "#/$defs/digest" }
        }
      }
    },
    "requiredChecks": {
      "type": "array", "minItems": 1, "maxItems": 32, "uniqueItems": true,
      "items": { "$ref": "#/$defs/checkId" }
    },
    "requiredDimensions": {
      "type": "array", "minItems": 1, "maxItems": 16, "uniqueItems": true,
      "items": { "$ref": "#/$defs/dimension" }
    },
    "humanReview": {
      "type": "object", "additionalProperties": false,
      "required": ["required", "maxAgeSeconds"],
      "properties": {
        "required": { "type": "boolean" },
        "maxAgeSeconds": { "type": "integer", "minimum": 1, "maximum": 31536000 }
      }
    },
    "limits": {
      "type": "object",
      "additionalProperties": false,
      "minProperties": 1,
      "properties": {
        "manifestBytes": { "type": "integer", "minimum": 1, "maximum": 1048576 },
        "payloadFiles": { "type": "integer", "minimum": 1, "maximum": 4096 },
        "fileBytes": { "type": "integer", "minimum": 1, "maximum": 268435456 },
        "totalPayloadBytes": { "type": "integer", "minimum": 1, "maximum": 1073741824 },
        "pathSegments": { "type": "integer", "minimum": 1, "maximum": 16 },
        "pathBytes": { "type": "integer", "minimum": 1, "maximum": 255 },
        "segmentBytes": { "type": "integer", "minimum": 1, "maximum": 255 },
        "jsonNesting": { "type": "integer", "minimum": 1, "maximum": 64 },
        "jsonStringBytes": { "type": "integer", "minimum": 1, "maximum": 16777216 },
        "claimsFiles": { "type": "integer", "minimum": 1, "maximum": 16 },
        "provenanceBindings": { "type": "integer", "minimum": 1, "maximum": 100000 },
        "relationEntities": { "type": "integer", "minimum": 1, "maximum": 100000 },
        "relationEdges": { "type": "integer", "minimum": 1, "maximum": 1000000 },
        "signatureEnvelopes": { "type": "integer", "minimum": 1, "maximum": 32 }
      }
    }
  },
  "allOf": [
    {
      "if": {
        "type": "object",
        "properties": {
          "signature": {
            "type": "object",
            "properties": { "mode": { "const": "required" } },
            "required": ["mode"]
          }
        }
      },
      "then": {
        "type": "object",
        "properties": {
          "keys": { "type": "array", "minItems": 1 },
          "signers": { "type": "array", "minItems": 1 }
        }
      }
    }
  ],
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
    "checkId": { "type": "string", "pattern": "^pap\\.check\\.[a-z0-9-]+/[0-9]+$" },
    "rfc3339": { "type": "string", "format": "date-time" },
    "keyId": {
      "type": "string", "minLength": 1, "maxLength": 64,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    },
    "identity": {
      "type": "string", "minLength": 1, "maxLength": 256,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$"
    },
    "packageId": { "type": "string", "minLength": 1, "maxLength": 512 },
    "dimension": {
      "enum": [
        "integrity", "integrity.package", "integrity.artifacts",
        "sources", "sources.integrity", "sources.availability",
        "signature", "signature.validity",
        "trust", "trust.signerIdentity", "trust.policyDecision",
        "trust.checkerRecognition", "trust.profileRecognition",
        "checks", "humanReview"
      ]
    }
  }
}
```

`requiredDimensions` deliberately has no `semanticTruth` or `legalEnforceability` value: those
dimensions are always `NOT_EVALUATED` in v0.1, and a policy that required them would be requiring
something no conforming verifier can produce, so it is rejected as `pap.trust.policy-invalid`
rather than silently weakening the requirement.

Schemas use `format: "date-time"`; implementations that assert formats must use RFC 3339. The
example below illustrates a policy that pins one checker implementation and one profile and
requires the three mechanical checks and no signature. The `unsigned-valid.json` fixture omits
`checkers[]`/`profiles[]` so that recognition is `NOT_APPLICABLE` for every implementation
(§12.1); pinning the reference implementation's digest would make the fixture fail for an
independent verifier.

```json
{
  "trustPolicyVersion": "0.1",
  "id": "policy-acme-unsigned-2026-11",
  "issuedAt": "2026-11-01T00:00:00Z",
  "expiresAt": "2026-12-01T00:00:00Z",
  "signature": {
    "mode": "disabled"
  },
  "keys": [],
  "signers": [],
  "checkers": [
    {
      "id": "pap.verifier.reference",
      "version": "0.1.0",
      "implementationDigest": "sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0"
    }
  ],
  "profiles": [
    {
      "id": "acme-supplier",
      "version": "0.1.0"
    }
  ],
  "requiredChecks": [
    "pap.check.digest-integrity/1",
    "pap.check.source-quote/1",
    "pap.check.relation-consistency/1"
  ],
  "requiredDimensions": [
    "integrity",
    "sources",
    "checks"
  ],
  "humanReview": {
    "required": false,
    "maxAgeSeconds": 2592000
  }
}
```

A policy with `signature.mode: "required"` must supply at least one key and one signer (Appendix B
`allOf`); the `signature-required.json` fixture enrols the key behind
`signatures/trusted.dsse.json` and adds `signature` and `trust` to `requiredDimensions`.

---


## Appendix C — Verification report JSON Schema (normative)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:verification-report",
  "title": "Portable Assurance Package v0.1 verification report",
  "type": "object",
  "additionalProperties": false,
  "required": ["reportVersion", "verifier", "package", "policy", "evaluatedAt",
               "identities", "dimensions", "checks", "coverage", "limitations", "verdict",
               "diagnostics"],
  "properties": {
    "reportVersion": { "const": "0.1" },
    "verifier": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "version", "implementationDigest", "checkerIdentities"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "version": { "type": "string", "minLength": 1 },
        "implementationDigest": { "$ref": "#/$defs/digest" },
        "checkerIdentities": { "type": "array", "items": { "$ref": "#/$defs/digest" } }
      }
    },
    "package": {
      "type": "object",
      "additionalProperties": false,
      "required": ["identity", "papVersion"],
      "properties": {
        "identity": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] },
        "papVersion": { "type": ["string", "null"] },
        "path": { "type": ["string", "null"] }
      }
    },
    "policy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["state"],
      "properties": {
        "id": { "type": ["string", "null"] },
        "digest": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] },
        "state": { "enum": ["FRESH", "STALE", "ABSENT"] },
        "path": { "type": ["string", "null"] }
      }
    },
    "evaluatedAt": { "type": "string", "format": "date-time" },
    "durationMs": { "type": "integer", "minimum": 0 },
    "effectiveLimits": {
      "type": "object",
      "minProperties": 1,
      "propertyNames": {
        "enum": ["manifestBytes", "payloadFiles", "fileBytes", "totalPayloadBytes",
                 "pathSegments", "pathBytes", "segmentBytes", "jsonNesting",
                 "jsonStringBytes", "claimsFiles", "provenanceBindings",
                 "relationEntities", "relationEdges", "signatureEnvelopes"]
      },
      "additionalProperties": { "type": "integer", "minimum": 1 }
    },
    "identities": {
      "type": "object",
      "additionalProperties": false,
      "required": ["packageIdentity", "artifacts", "sources", "normalizedInputDigest",
                   "extensionClosureDigest", "checkerIdentity", "verificationRecordIdentity"],
      "properties": {
        "packageIdentity": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] },
        "artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "declared", "computed"],
            "properties": {
              "id": { "type": "string" },
              "declared": { "$ref": "#/$defs/digest" },
              "computed": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] }
            }
          }
        },
        "sources": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "declared", "computed"],
            "properties": {
              "id": { "type": "string" },
              "declared": { "$ref": "#/$defs/digest" },
              "computed": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] }
            }
          }
        },
        "normalizedInputDigest": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] },
        "extensionClosureDigest": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] },
        "checkerIdentity": { "$ref": "#/$defs/digest" },
        "verificationRecordIdentity": { "$ref": "#/$defs/digest" }
      }
    },
    "dimensions": {
      "type": "object",
      "additionalProperties": false,
      "required": ["integrity", "sources", "signature", "trust", "checks", "humanReview",
                   "semanticTruth", "legalEnforceability"],
      "properties": {
        "integrity": {
          "type": "object",
          "additionalProperties": false,
          "required": ["package", "artifacts"],
          "properties": {
            "package": { "enum": ["PASS", "FAIL", "NOT_EVALUATED"] },
            "artifacts": { "enum": ["PASS", "FAIL", "NOT_EVALUATED"] }
          }
        },
        "sources": {
          "type": "object",
          "additionalProperties": false,
          "required": ["integrity", "availability"],
          "properties": {
            "integrity": { "enum": ["PASS", "FAIL", "UNAVAILABLE", "NOT_EVALUATED"] },
            "availability": { "enum": ["PASS", "UNAVAILABLE", "NOT_APPLICABLE"] }
          }
        },
        "signature": {
          "type": "object",
          "additionalProperties": false,
          "required": ["validity"],
          "properties": {
            "validity": { "enum": ["VALID", "INVALID", "NOT_EVALUATED", "NOT_APPLICABLE"] },
            "signatures": {
              "type": "array",
              "items": {
                "type": "object",
                "additionalProperties": false,
                "required": ["path", "validity"],
                "properties": {
                  "path": { "type": "string", "minLength": 1 },
                  "keyId": { "type": "string", "minLength": 1 },
                  "algorithm": { "const": "ed25519" },
                  "validity": { "enum": ["VALID", "INVALID", "NOT_EVALUATED"] },
                  "signerIdentity": { "enum": ["TRUSTED", "UNTRUSTED", "UNKNOWN",
                                               "NOT_EVALUATED", "NOT_APPLICABLE"] },
                  "policyDecision": { "enum": ["ACCEPTED", "REJECTED", "STALE",
                                               "NOT_EVALUATED"] }
                }
              }
            }
          }
        },
        "trust": {
          "type": "object",
          "additionalProperties": false,
          "required": ["signerIdentity", "policyDecision", "checkerRecognition",
                       "profileRecognition"],
          "properties": {
            "signerIdentity": { "enum": ["TRUSTED", "UNTRUSTED", "UNKNOWN",
                                         "NOT_EVALUATED", "NOT_APPLICABLE"] },
            "policyDecision": { "enum": ["ACCEPTED", "REJECTED", "STALE",
                                         "NOT_EVALUATED"] },
            "checkerRecognition": { "enum": ["PASS", "UNSUPPORTED", "UNTRUSTED",
                                             "NOT_EVALUATED", "NOT_APPLICABLE"] },
            "profileRecognition": { "enum": ["PASS", "UNSUPPORTED", "UNTRUSTED",
                                             "NOT_EVALUATED", "NOT_APPLICABLE"] }
          }
        },
        "checks": {
          "type": "object",
          "additionalProperties": false,
          "required": ["results"],
          "properties": {
            "results": {
              "type": "array",
              "items": {
                "type": "object",
                "additionalProperties": false,
                "required": ["checkId", "outcome"],
                "properties": {
                  "checkId": { "$ref": "#/$defs/checkId" },
                  "outcome": { "enum": ["PASS", "FAIL", "UNSUPPORTED", "NOT_EVALUATED"] },
                  "required": { "type": "boolean" }
                }
              }
            }
          }
        },
        "humanReview": {
          "type": "object",
          "additionalProperties": false,
          "required": ["status"],
          "properties": {
            "status": { "enum": ["PASS", "INCOMPLETE", "UNKNOWN", "NOT_APPLICABLE"] },
            "basis": {
              "const": "unbound-claim",
              "description": "Required when status is PASS: the approval is a producer claim, not an authenticated approval."
            }
          }
        },
        "semanticTruth": { "const": "NOT_EVALUATED" },
        "legalEnforceability": { "const": "NOT_EVALUATED" }
      }
    },
    "checks": {
      "type": "array",
      "items": { "$ref": "urn:pap:0.1:check-record" }
    },
    "producerClaims": {
      "type": "object",
      "additionalProperties": false,
      "required": ["present", "trusted"],
      "properties": {
        "present": { "type": "boolean" },
        "trusted": { "const": false },
        "comparison": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["checkId", "claimed", "independentOutcome", "relation"],
            "properties": {
              "checkId": { "$ref": "#/$defs/checkId" },
              "claimed": { "type": ["string", "null"] },
              "independentOutcome": { "type": ["string", "null"] },
              "relation": { "enum": ["AGREES", "DISAGREES", "UNVERIFIABLE",
                                     "NOT_COMPARABLE"] }
            }
          }
        }
      }
    },
    "coverage": {
      "type": "object",
      "additionalProperties": false,
      "required": ["requiredChecks", "checksEvaluated", "checksPassed", "checksFailed",
                   "checksUnsupported", "checksNotEvaluated", "requiredDimensions",
                   "dimensionsEvaluated", "full"],
      "properties": {
        "requiredChecks": { "type": "array", "items": { "$ref": "#/$defs/checkId" } },
        "checksEvaluated": { "type": "integer", "minimum": 0 },
        "checksPassed": { "type": "integer", "minimum": 0 },
        "checksFailed": { "type": "integer", "minimum": 0 },
        "checksUnsupported": { "type": "integer", "minimum": 0 },
        "checksNotEvaluated": { "type": "integer", "minimum": 0 },
        "requiredDimensions": { "type": "array", "items": { "type": "string" } },
        "dimensionsEvaluated": { "type": "integer", "minimum": 0 },
        "full": { "type": "boolean" }
      }
    },
    "limitations": { "type": "array", "items": { "$ref": "#/$defs/limitation" } },
    "verdict": { "enum": ["PASS", "FAIL", "UNTRUSTED", "UNSUPPORTED", "INCOMPLETE",
                          "NOT_EVALUATED"] },
    "diagnostics": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["code", "severity", "scope", "message"],
        "properties": {
          "code": { "type": "string", "pattern": "^pap\\.[a-z0-9.-]+$" },
          "severity": { "enum": ["error", "warning", "info"] },
          "scope": { "type": "string" },
          "message": { "type": "string" }
        }
      }
    }
  },
  "allOf": [
    {
      "if": {
        "type": "object",
        "required": ["dimensions"],
        "properties": {
          "dimensions": {
            "type": "object",
            "required": ["humanReview"],
            "properties": {
              "humanReview": {
                "type": "object",
                "required": ["status"],
                "properties": { "status": { "const": "PASS" } }
              }
            }
          }
        }
      },
      "then": {
        "type": "object",
        "required": ["dimensions"],
        "properties": {
          "dimensions": {
            "type": "object",
            "required": ["humanReview"],
            "properties": {
              "humanReview": {
                "type": "object",
                "required": ["basis"]
              }
            }
          }
        }
      }
    }
  ],
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
    "checkId": { "type": "string", "pattern": "^pap\\.check\\.[a-z0-9-]+/[0-9]+$" },
    "limitation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["code", "detail"],
      "properties": {
        "code": { "type": "string", "pattern": "^pap\\.[a-z0-9.-]+$" },
        "detail": { "type": "string" }
      }
    }
  }
}
```

The report schema references `urn:pap:0.1:check-record` (Appendix D.5). `durationMs` and
absolute paths are permitted in the report but excluded from the verification-record identity
(§5.9). `effectiveLimits` is present only when the operator lowered a limit and is part of the
identity form when present, because it changes what was evaluated. The `allOf` conditional makes
`dimensions.humanReview.basis` required exactly when `dimensions.humanReview.status` is `PASS`,
and its `const` makes the only accepted value `"unbound-claim"`; a report with `PASS` and no
`basis`, or with another value, is schema-invalid and MUST never be emitted. Consumers MUST use
`verdict` and `dimensions`, never an exit code alone.

---


## Appendix D — Claim and check-record schemas (normative)

All claim files are UTF-8 JSON; their `papClaimsVersion` is exactly `"0.1"`. The manifest
declares each present claim file with a digest over the raw file bytes (§5.2). A claim file with
an unknown `papClaimsVersion` is `UNSUPPORTED`; a claim file that violates its schema is
`INVALID` and makes the package integrity fail. Claims are data: the verifier never executes a
claim, never follows a claim-supplied path outside the package and never lets a claim-supplied
path become an output path.

### D.1 `claims/provenance.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:claims-provenance",
  "type": "object",
  "additionalProperties": false,
  "required": ["papClaimsVersion", "bindings"],
  "properties": {
    "papClaimsVersion": { "const": "0.1" },
    "bindings": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "entityId", "sourceId", "locator", "quote"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "entityId": { "type": "string", "minLength": 1, "maxLength": 256 },
          "sourceId": { "type": "string", "minLength": 1, "maxLength": 256 },
          "locator": {
            "type": "object",
            "additionalProperties": false,
            "required": ["kind", "start", "end"],
            "properties": {
              "kind": { "const": "byte-range" },
              "start": { "type": "integer", "minimum": 0 },
              "end": { "type": "integer", "minimum": 0 }
            }
          },
          "quote": {
            "type": "object",
            "additionalProperties": false,
            "required": ["normalization", "digest"],
            "properties": {
              "normalization": { "const": "none" },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        }
      }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" }
  }
}
```

Bindings are matched to sources by `sourceId`; a binding naming an undeclared source is an
`INVALID` claim — `pap.package.claim-invalid` and `integrity.package: FAIL` — not
`NOT_EVALUATED`: the reference is unresolvable, which is a producer defect (§8.5). A binding that
names a declared source with no embedded snapshot is the format-permitted offline case and stays
`NOT_EVALUATED`. The verifier checks unique binding ids and unique `(entityId, sourceId, range)`
tuples; duplicates make the check `FAIL` (`pap.claim.binding-duplicate`). The check itself is
§8.5.

### D.2 `claims/relations.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:claims-relations",
  "type": "object",
  "additionalProperties": false,
  "required": ["papClaimsVersion", "entities", "relations", "edges"],
  "properties": {
    "papClaimsVersion": { "const": "0.1" },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "kind"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "kind": { "type": "string", "minLength": 1, "maxLength": 128 }
        }
      }
    },
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "from", "to"],
        "properties": {
          "name": { "type": "string", "minLength": 1, "maxLength": 128 },
          "from": { "type": "string", "minLength": 1, "maxLength": 128 },
          "to": { "type": "string", "minLength": 1, "maxLength": 128 },
          "inverse": { "type": "string", "minLength": 1, "maxLength": 128 }
        }
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["relation", "from", "to"],
        "properties": {
          "relation": { "type": "string", "minLength": 1, "maxLength": 128 },
          "from": { "type": "string", "minLength": 1, "maxLength": 256 },
          "to": { "type": "string", "minLength": 1, "maxLength": 256 }
        }
      }
    }
  }
}
```

The verifier enforces relation-name uniqueness within the file
(`pap.claim.relation-duplicate`) and the consistency rules of §8.6. A duplicate relation name
makes the check `FAIL`, because an edge naming that relation would be ambiguous.
`relations[].inverse` names another relation declared in the same file; an inverse that is not
declared is `FAIL` (`pap.claim.inverse-missing`), and the two declarations must point back to each
other (`pap.claim.inverse-not-reciprocal`).

### D.3 `claims/producer-report.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:producer-report",
  "type": "object",
  "additionalProperties": false,
  "required": ["papClaimsVersion", "producer", "claims"],
  "properties": {
    "papClaimsVersion": { "const": "0.1" },
    "producer": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "version"],
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 256 },
        "version": { "type": "string", "minLength": 1, "maxLength": 128 }
      }
    },
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["checkId", "checkVersion", "claimedOutcome"],
        "properties": {
          "checkId": { "type": "string", "pattern": "^pap\\.check\\.[a-z0-9-]+/[0-9]+$" },
          "checkVersion": { "type": "string", "pattern": "^(0|[1-9][0-9]*)$" },
          "claimedOutcome": {
            "enum": ["PASS", "FAIL", "UNSUPPORTED", "NOT_EVALUATED"]
          },
          "checkedAt": { "type": "string", "format": "date-time" },
          "checker": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "version", "implementationDigest"],
            "properties": {
              "id": { "type": "string", "minLength": 1, "maxLength": 256 },
              "version": { "type": "string", "minLength": 1, "maxLength": 128 },
              "implementationDigest": { "$ref": "#/$defs/digest" }
            }
          }
        }
      }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" }
  }
}
```

The field is `claimedOutcome`; a producer report claiming `outcome` is invalid because it would
mimic a verifier record. `checkVersion` MUST equal the version suffix of `checkId`, and a report
may list each `checkId` at most once; a mismatch or duplicate is an invalid claim
(`pap.package.claim-invalid`, `integrity.package: FAIL`). The verifier parses claims, reports them
under `producerClaims` and MAY compare them; it never uses `claimedOutcome` for a dimension or the
verdict.

### D.4 `claims/reviews.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:claims-reviews",
  "type": "object",
  "additionalProperties": false,
  "required": ["papClaimsVersion", "approvals"],
  "properties": {
    "papClaimsVersion": { "const": "0.1" },
    "approvals": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "reviewer", "decision", "decidedAt"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 256 },
          "reviewer": {
            "type": "object",
            "additionalProperties": false,
            "required": ["identity"],
            "properties": {
              "identity": { "type": "string", "minLength": 1, "maxLength": 256, "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$" },
              "keyId": { "type": "string", "minLength": 1, "maxLength": 256 }
            }
          },
          "decision": { "enum": ["approved", "rejected"] },
          "decidedAt": { "type": "string", "format": "date-time" },
          "scope": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "packageId": { "type": "string", "minLength": 1, "maxLength": 512 },
              "artifacts": {
                "type": "array",
                "items": { "type": "string", "minLength": 1, "maxLength": 256 }
              },
              "packageIdentity": { "$ref": "#/$defs/digest" }
            }
          },
          "evidence": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "path": { "type": "string", "maxLength": 255 },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        }
      }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" }
  }
}
```

Reviews are evidence, not authority: an approval's reviewer identity is meaningful only if the
trust policy maps it to a trusted principal. Approval `id` values MUST be unique; a duplicate is an
invalid claim (`pap.package.claim-invalid`, `integrity.package: FAIL`). `reviewer.keyId` is
reserved and ignored in v0.1, and `evidence.path` is never opened. The optional `evidence` object
is opaque producer data; v0.1 does not validate approval signatures and must not describe an
approval as cryptographically bound (signed approvals are deferred, §14.1/§16.1). A review scoped to a
different `packageIdentity` does not apply to this package (`pap.review.binding-invalid`). A
rejection is not automatically a verification failure; the policy decides whether a rejection
blocks acceptance, and the `humanReview` dimension reports `INCOMPLETE` when a required approval
is missing.

### D.5 Check record (`urn:pap:0.1:check-record`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:pap:0.1:check-record",
  "type": "object",
  "additionalProperties": false,
  "required": ["checkId", "checkVersion", "subjectDigests", "scope", "checker",
               "outcome", "witnesses", "diagnostics"],
  "properties": {
    "checkId": { "type": "string", "pattern": "^pap\\.check\\.[a-z0-9-]+/[0-9]+$" },
    "checkVersion": { "type": "string", "pattern": "^(0|[1-9][0-9]*)$" },
    "subjectDigests": {
      "type": "object",
      "additionalProperties": false,
      "required": ["package"],
      "properties": {
        "package": { "$ref": "#/$defs/digest" },
        "artifacts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "digest"],
            "properties": {
              "id": { "type": "string", "minLength": 1 },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        },
        "sources": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "digest"],
            "properties": {
              "id": { "type": "string", "minLength": 1 },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        },
        "inputs": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "digest"],
            "properties": {
              "id": { "type": "string", "minLength": 1 },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        },
        "claims": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["kind", "digest"],
            "properties": {
              "kind": { "enum": ["provenance", "relations", "producerReport", "reviews"] },
              "digest": { "$ref": "#/$defs/digest" }
            }
          }
        }
      }
    },
    "scope": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "artifacts": { "type": "array", "items": { "type": "string" } },
        "sources": { "type": "array", "items": { "type": "string" } },
        "bindings": { "type": "integer", "minimum": 0 },
        "entities": { "type": "integer", "minimum": 0 },
        "edges": { "type": "integer", "minimum": 0 },
        "evaluated": { "type": "integer", "minimum": 0 },
        "unavailable": { "type": "integer", "minimum": 0 }
      }
    },
    "checker": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "version", "implementationDigest"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "version": { "type": "string", "minLength": 1 },
        "implementationDigest": { "$ref": "#/$defs/digest" }
      }
    },
    "outcome": { "enum": ["PASS", "FAIL", "UNSUPPORTED", "NOT_EVALUATED"] },
    "witnesses": {
      "type": "array",
      "items": {
        "oneOf": [
          { "$ref": "#/$defs/recomputedDigest" },
          { "$ref": "#/$defs/sourceSpan" },
          { "$ref": "#/$defs/relationViolations" }
        ]
      }
    },
    "diagnostics": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["code", "severity", "message"],
        "properties": {
          "code": { "type": "string", "pattern": "^pap\\.[a-z0-9.-]+$" },
          "severity": { "enum": ["error", "warning", "info"] },
          "message": { "type": "string" }
        }
      }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
    "recomputedDigest": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "subject", "algorithm", "declared", "computed"],
      "properties": {
        "type": { "const": "recomputed-digest" },
        "subject": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind"],
          "properties": {
            "kind": { "enum": ["artifact", "source", "input", "claim"] },
            "id": { "type": "string" }
          }
        },
        "algorithm": { "const": "sha256" },
        "declared": { "$ref": "#/$defs/digest" },
        "computed": { "oneOf": [{ "$ref": "#/$defs/digest" }, { "type": "null" }] }
      }
    },
    "sourceSpan": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "sourceId", "sourceDigest", "range", "quoteDigest",
                   "extractedDigest"],
      "properties": {
        "type": { "const": "source-span" },
        "sourceId": { "type": "string", "minLength": 1 },
        "sourceDigest": { "$ref": "#/$defs/digest" },
        "range": {
          "type": "object",
          "additionalProperties": false,
          "required": ["start", "end"],
          "properties": {
            "start": { "type": "integer", "minimum": 0 },
            "end": { "type": "integer", "minimum": 0 }
          }
        },
        "quoteDigest": { "$ref": "#/$defs/digest" },
        "extractedDigest": { "$ref": "#/$defs/digest" },
        "quoteBase64": {
          "type": "string",
          "description": "Standard base64 (RFC 4648 §4) of the extracted span; informational."
        }
      }
    },
    "relationViolations": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "violations"],
      "properties": {
        "type": { "const": "relation-violation-list" },
        "violations": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["code", "subject", "detail"],
            "properties": {
              "code": { "type": "string", "pattern": "^pap\\.[a-z0-9.-]+$" },
              "subject": { "type": "string" },
              "detail": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

A producer report cannot satisfy this schema: `claimedOutcome` is not a permitted property and
`outcome` requires a checker identity and witnesses. This is a structural guarantee, not a
convention (issue #44 deliverable 5).

---


## Appendix E — Canonical test vectors (normative)

These vectors fix the canonical form and every digest domain. An implementation that disagrees
with a vector has a bug or a different profile version; it is not a permitted variation. All
values were produced from the Appendix F package with the algorithm in §5.

### E.1 Canonical manifest (JCS bytes for `packageIdentity`)

The manifest object in Appendix F canonicalizes to the following single-line UTF-8 JSON. The
transcription below is normative: `packageIdentity` is `H("pap.package.v1", <these bytes>)`.

```json
{"artifacts":[{"bytes":80,"digest":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","id":"artifact:acme-supplier","mediaType":"text/markdown; charset=utf-8","path":"artifacts/ACME-SUPPLIER.draft.md"}],"build":{"engineVersion":"0.1.0","manifestVersion":"0.1","normalizedInputDigest":"sha256:fccf755793cf1a1b7982631c201282669924cdcf9d6b171bdff26513fc64d80b"},"checkSpecs":[{"id":"pap.check.digest-integrity/1","required":true,"version":"1"},{"id":"pap.check.source-quote/1","required":true,"version":"1"},{"id":"pap.check.relation-consistency/1","required":true,"version":"1"}],"claims":{"producerReport":{"digest":"sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95","path":"claims/producer-report.json"},"provenance":{"digest":"sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b","path":"claims/provenance.json"},"relations":{"digest":"sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab","path":"claims/relations.json"}},"inputs":[{"digest":"sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff","id":"input:project","mediaType":"application/yaml","normalization":"lf","path":"inputs/project.yml"}],"package":{"createdAt":"2026-11-02T00:00:00Z","id":"urn:pap:acme-supplier:2026-01","producer":{"name":"contract-builder","version":"0.1.0"},"title":"ACME supplier assurance package"},"papVersion":"0.1","profile":{"id":"acme-supplier","version":"0.1.0"},"sources":[{"acquiredAt":"2026-11-01T12:00:00Z","acquisition":{"method":"git","revision":"0f1e2d3c4b5a69788796a5b4c3d2e1f0","uri":"https://example.invalid/acme/policy.git"},"digest":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","id":"SRC-ACME-POLICY","mediaType":"text/markdown; charset=utf-8","path":"sources/acme-policy.md"}],"subject":{"projectId":"acme-supplier","revision":"1.0.0"}}
```

Expected identity:

| Value | Expected |
|---|---|
| `packageIdentity` | `sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020` |

### E.2 Payload digest vectors

| Subject | Bytes | Expected digest |
|---|---|---|
| artifact `artifacts/ACME-SUPPLIER.draft.md` | 80 | `sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51` |
| raw source `sources/acme-policy.md` | 127 | `sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd` |
| quote span `[24, 76)` | 52 | `sha256:619cb81063fff535c31b93b66e274e6df0a1cef4582d17c7a6362c98fac48909` |
| input `inputs/project.yml` (per file) | — | `sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff` |
| `normalizedInputDigest` (set) | — | `sha256:fccf755793cf1a1b7982631c201282669924cdcf9d6b171bdff26513fc64d80b` |
| claim `claims/provenance.json` | — | `sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b` |
| claim `claims/relations.json` | — | `sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab` |
| claim `claims/producer-report.json` | — | `sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95` |

The artifact bytes end with one LF; the source has a trailing LF that is **not** part of the
quote span `[24, 76)`. The quote is exactly
`REQ-001: every delivery MUST include a packing list.` (52 bytes).

### E.3 Checker identity vector

The checker closure in Appendix F declares two files and one pinned dependency:

| Field | Value |
|---|---|
| extension kind/id/version | `checker` / `pap.verifier.reference` / `0.1.0` |
| file `src/checks/digest.ts` | `export const checkId = "pap.check.digest-integrity/1";\n` |
| file `src/checks/source.ts` | `export const spanCheck = true;\n` |
| dependency | `zod` @ `3.23.8`, integrity `sha512-9K5fXZ0G8p3oUo4WQ9m2l1v0B9m3r7Yqk1s2V4pL6c0=` |

| Value | Expected |
|---|---|
| `implementationDigest` | `sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0` |
| `checkerIdentity` | `sha256:15a0b0149dc95f7b9711e7b28fc4189ed8539b03ffd2c96e967205316d75963f` |

The dependency integrity value is deliberately fictional test data, not a real registry digest;
it is present to fix the dependency-record framing.

### E.4 Verification record identity vector

`verificationRecordIdentity` for the Appendix F package verified by the reference checker with no
trust policy, fixed `--now`, and the identity form below (a `PASS`) is
`sha256:147aad0ab0f4b9274b7f66182de179ad69ae2924f311dcf723e67d39b07527ea`.

The identity form is the report from Appendix C with the excluded fields of §5.9 removed and the
fixed placeholder below. It includes the three top-level `checks[]` records, with their subjects,
scopes, checker, outcomes and witnesses, so the vector distinguishes different check evidence;
only the presentation fields of §5.9 (`diagnostics[].message`, `checks[].diagnostics[].message`
and the optional `quoteBase64`) are absent. It is shown here so an implementation can reproduce
the value without relying on its own report formatting:

```json
{"checks":[{"checkId":"pap.check.digest-integrity/1","checkVersion":"1","checker":{"id":"pap.verifier.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"},"diagnostics":[],"outcome":"PASS","scope":{"artifacts":["artifact:acme-supplier"],"sources":["SRC-ACME-POLICY"]},"subjectDigests":{"artifacts":[{"digest":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","id":"artifact:acme-supplier"}],"claims":[{"digest":"sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b","kind":"provenance"},{"digest":"sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab","kind":"relations"},{"digest":"sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95","kind":"producerReport"}],"inputs":[{"digest":"sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff","id":"input:project"}],"package":"sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020","sources":[{"digest":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","id":"SRC-ACME-POLICY"}]},"witnesses":[{"algorithm":"sha256","computed":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","declared":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","subject":{"id":"artifact:acme-supplier","kind":"artifact"},"type":"recomputed-digest"},{"algorithm":"sha256","computed":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","declared":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","subject":{"id":"SRC-ACME-POLICY","kind":"source"},"type":"recomputed-digest"},{"algorithm":"sha256","computed":"sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff","declared":"sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff","subject":{"id":"input:project","kind":"input"},"type":"recomputed-digest"},{"algorithm":"sha256","computed":"sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b","declared":"sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b","subject":{"id":"provenance","kind":"claim"},"type":"recomputed-digest"},{"algorithm":"sha256","computed":"sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab","declared":"sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab","subject":{"id":"relations","kind":"claim"},"type":"recomputed-digest"},{"algorithm":"sha256","computed":"sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95","declared":"sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95","subject":{"id":"producerReport","kind":"claim"},"type":"recomputed-digest"}]},{"checkId":"pap.check.source-quote/1","checkVersion":"1","checker":{"id":"pap.verifier.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"},"diagnostics":[],"outcome":"PASS","scope":{"bindings":1,"evaluated":1,"sources":["SRC-ACME-POLICY"],"unavailable":0},"subjectDigests":{"claims":[{"digest":"sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b","kind":"provenance"}],"package":"sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020","sources":[{"digest":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","id":"SRC-ACME-POLICY"}]},"witnesses":[{"extractedDigest":"sha256:619cb81063fff535c31b93b66e274e6df0a1cef4582d17c7a6362c98fac48909","quoteDigest":"sha256:619cb81063fff535c31b93b66e274e6df0a1cef4582d17c7a6362c98fac48909","range":{"end":76,"start":24},"sourceDigest":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","sourceId":"SRC-ACME-POLICY","type":"source-span"}]},{"checkId":"pap.check.relation-consistency/1","checkVersion":"1","checker":{"id":"pap.verifier.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"},"diagnostics":[],"outcome":"PASS","scope":{"edges":2,"entities":2},"subjectDigests":{"claims":[{"digest":"sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab","kind":"relations"}],"package":"sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020"},"witnesses":[{"type":"relation-violation-list","violations":[]}]}],"coverage":{"checksEvaluated":3,"checksFailed":0,"checksNotEvaluated":0,"checksPassed":3,"checksUnsupported":0,"dimensionsEvaluated":3,"full":true,"requiredChecks":["pap.check.digest-integrity/1","pap.check.source-quote/1","pap.check.relation-consistency/1"],"requiredDimensions":["integrity","sources","checks"]},"diagnostics":[],"dimensions":{"checks":{"results":[{"checkId":"pap.check.digest-integrity/1","outcome":"PASS","required":true},{"checkId":"pap.check.source-quote/1","outcome":"PASS","required":true},{"checkId":"pap.check.relation-consistency/1","outcome":"PASS","required":true}]},"humanReview":{"status":"NOT_APPLICABLE"},"integrity":{"artifacts":"PASS","package":"PASS"},"legalEnforceability":"NOT_EVALUATED","semanticTruth":"NOT_EVALUATED","signature":{"validity":"NOT_APPLICABLE"},"sources":{"availability":"PASS","integrity":"PASS"},"trust":{"checkerRecognition":"NOT_EVALUATED","policyDecision":"NOT_EVALUATED","profileRecognition":"NOT_EVALUATED","signerIdentity":"NOT_APPLICABLE"}},"identities":{"artifacts":[{"computed":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","declared":"sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51","id":"artifact:acme-supplier"}],"checkerIdentity":"sha256:15a0b0149dc95f7b9711e7b28fc4189ed8539b03ffd2c96e967205316d75963f","extensionClosureDigest":null,"normalizedInputDigest":"sha256:fccf755793cf1a1b7982631c201282669924cdcf9d6b171bdff26513fc64d80b","packageIdentity":"sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020","sources":[{"computed":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","declared":"sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd","id":"SRC-ACME-POLICY"}],"verificationRecordIdentity":"sha256:0000000000000000000000000000000000000000000000000000000000000000"},"limitations":[],"package":{"identity":"sha256:77a8d1d0882428efdfa5bfc38faa1ff7ba772aff9373b9e6135a8bb744119020","papVersion":"0.1"},"policy":{"digest":null,"id":null,"state":"ABSENT"},"reportVersion":"0.1","verdict":"PASS","verifier":{"checkerIdentities":["sha256:15a0b0149dc95f7b9711e7b28fc4189ed8539b03ffd2c96e967205316d75963f"],"id":"pap.verifier.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"}}
```

The placeholder `identities.verificationRecordIdentity` is the fixed 64-zero digest specified in
§5.9; it is part of the identity form by definition (a record cannot contain its own hash without
a fixed point). Implementations MUST substitute it while computing the identity, then fill the
real value into the report.

This vector revises the Gate 1 draft, which excluded `checks[]` from the identity. That exclusion
would have let two reports with different check subjects, scopes or witnesses share an identity;
§5.9 now includes the records and excludes only presentation fields, and E.10 shows the resulting
sensitivity.

### E.5 Input normalization vector (LF rules)

| Value | Bytes / digest |
|---|---|
| raw bytes (hex) | `613a20310d0a623a20320d0a` (`a: 1\r\nb: 2\r\n`) |
| normalized bytes (hex) | `613a20310a623a20320a` (`a: 1\nb: 2\n`) |
| per-file digest for path `inputs/crlf.yml` | `sha256:2633064c5d3066746beae7416e97e87816fe9b031c6f57af4c9b02ca1c00453b` |
| set digest (single input) | `sha256:92e9ec329516a5672fc40fd0b4474f2a2fd7790d87817c37b772af3347df2021` |

### E.6 Domain separation and framing vectors

Domain separation: the same three bytes `hello` produce different digests in different domains:

| Domain | Digest |
|---|---|
| `pap.artifact.v1` | `sha256:49ade3eaed5c81a07ee5245b923abe3c629747f0eebe57a0052307d5965d5112` |
| `pap.source.raw.v1` | `sha256:8240a5313b027e89a99054c87e683a87d68f59dc566a40f16aa68edcbf1a81b7` |
| `pap.package.v1` | `sha256:4cb73e2896d009395089ea045b54b15eea2bc4c03e519bc08dc0f619da308308` |

Framing ambiguity: `frameRecord("x", ["ab", "c"])` and `frameRecord("x", ["a", "bc"])` must not
collide:

| Sequence | Digest under `pap.test.v1` |
|---|---|
| `("ab", "c")` | `sha256:a4ff1eac1c490e25d4a23ef485f9219a4a51b2c370ba86ed20ba0d8e5c7334e5` |
| `("a", "bc")` | `sha256:19777dd70824683c8483961510324f7656c03378f3a4b64192e8bee7ff0ecff2` |

The `pap.test.v1` domain exists only for this vector; it is not a format domain.

### E.7 DSSE pre-authentication encoding vector

The optional signature adapter of §11.2 signs the DSSE PAE of the canonical manifest from E.1.
With `payloadType` `application/vnd.pap.manifest.v0.1+json` (38 ASCII bytes) and the E.1 payload
(1 874 bytes), the PAE bytes have length 1 928 and begin with:

```text
DSSEv1 38 application/vnd.pap.manifest.v0.1+json 1874 {"artifacts":[{"bytes":80,
```

| Value | Expected |
|---|---|
| PAE bytes | `PAE(payloadType, E.1 canonical manifest)` per the §11.2 rule; length 1 928 |
| SHA-256 of the PAE bytes (plain SHA-256, not a PAP domain) | `sha256:4efbb78e8d9fa00d01f0f07b29cdf5a000e7748cc144ecbbc1eaf0dcdd2919d4` |
| Illustrative PAE for payload `{}` | `DSSEv1 38 application/vnd.pap.manifest.v0.1+json 2 {}` |
| SHA-256 of the illustrative PAE | `sha256:163a4832de57f229c9f653684640f74b07baafd9568ee683fa470a1352316bb2` |

An Ed25519 signature over the first PAE is what a v0.1 envelope carries; the vector fixes the
bytes being signed independently of the signing key.

### E.8 Reproduction note

A verifier's report is not required to equal the Appendix C example byte-for-byte: messages,
diagnostic order and optional witness fields may differ, and `evaluatedAt`/absolute paths are
excluded from the identity. What MUST match is every digest in E.1–E.9, the check outcomes,
dimension statuses and verdict for the Appendix F package under a policy that requires the three
checks and does not require a signature.

### E.9 JCS edge-case vectors

These vectors pin the parts of RFC 8785 that the ASCII-only E.1 manifest cannot exercise: UTF-16
code-unit key order (which differs from Unicode code-point order for astral keys), minimal string
escaping, and the integer-only number rule. They are canonical bytes and plain SHA-256 values, not
PAP domain digests; a canonicalizer that reproduces them is correct for these cases.

UTF-16 key order. The value `{"a":1,"😀":2,"\ufffd":3,"A":4,"b":5}` canonicalizes to exactly 36
UTF-8 bytes:

```json
{"A":4,"a":1,"b":5,"😀":2,"�":3}
```

The order is `A` (U+0041), `a` (U+0061), `b` (U+0062), `😀` (U+1F600, UTF-16 `D83D DE00`), `�`
(U+FFFD). A canonicalizer that sorts by Unicode code point would put U+FFFD before U+1F600 and is
non-conformant. Plain SHA-256 of the 36 bytes is
`sha256:9267454f732ed7ef9939b28dc1e451c88c2967ff4a6b1746bf638d313e72b508`.

String escaping. The value `{"s":"\u0001\t\n\"\\é😀"}` — one U+0001 control character, then tab,
LF, quote, backslash, `é`, `😀` — canonicalizes to exactly 28 UTF-8 bytes:

```json
{"s":"\u0001\t\n\"\\é😀"}
```

The escaping is `\u0001` (lowercase hex), `\t`, `\n`, `\"` and `\\`; the non-ASCII `é` and `😀` are
emitted as literal UTF-8 and never `\u`-escaped. Plain SHA-256 of the 28 bytes is
`sha256:9033f8f21bc1c3367ebcad55e2298bf113b63f9e5f21c20678de00e760c5ff5d`.

Numbers. `9007199254740991` and `-9007199254740991` are valid integer tokens; `9007199254740992`,
`1.0`, `1e3` and `-0` are invalid (§5.3.1). Invalid values have no canonical bytes: the
canonicalizer MUST reject them.

### E.10 Identity mutation vectors

These vectors demonstrate the evidence coverage of `verificationRecordIdentity` (§5.9). Each
mutation starts from the complete E.4 identity form, applies exactly the stated change, removes the
§5.9 presentation fields (`diagnostics[].message`, `checks[].diagnostics[].message` and
`checks[].witnesses[].quoteBase64`), and hashes the JCS bytes with `pap.report.v1`. They are
directly checkable by any implementation's identity function.

| Mutation of the E.4 identity form | `verificationRecordIdentity` |
|---|---|
| none (E.4 baseline) | `sha256:147aad0ab0f4b9274b7f66182de179ad69ae2924f311dcf723e67d39b07527ea` |
| `dimensions.checks.results[0].outcome` changed from `PASS` to `FAIL` | `sha256:f9f2c22f90baa970ebed16d3cceae08a2aac6544f617320dd06c95745d1b7e30` |
| `checks[1].witnesses[0].range.end` changed from `76` to `75` | `sha256:83d9147e35f2dc528f481f0f39335497b3c32ea7f45ed083cf8a448679f24c4c` |
| `checks[0].scope.artifacts` emptied | `sha256:652798f36a18daec12268ebe05eeb6022d5d1be704897d51a98a2d30adc044f8` |
| `checks[1].diagnostics[0]` added with `code: "pap.check.partial"`, `severity: "warning"` | `sha256:635dcc4a65d44e5e011f8193705e9eb6c62eae8e553fd8068b60bc2ca59fc9e3` |
| `checks[1].witnesses[0].quoteBase64` added (base64 of the same extracted span) | `sha256:147aad0ab0f4b9274b7f66182de179ad69ae2924f311dcf723e67d39b07527ea` (unchanged) |
| the same diagnostic added with message `"alpha"` instead of `"beta"` | `sha256:635dcc4a65d44e5e011f8193705e9eb6c62eae8e553fd8068b60bc2ca59fc9e3` (unchanged) |

The first four rows change a semantic result or recomputable evidence and must change the identity;
the last two change only presentation and must not. The mutations are identity-function vectors,
not necessarily conforming reports (for example the `FAIL` mutation keeps the original dimension
statuses); they test only the canonical-object construction of §5.9. This is the property that
lets §5.9 exclude messages and `quoteBase64` without letting two records with materially different
verification evidence or outcomes share an identity.

---


## Appendix F — Complete minimal example package

The package is valid at v0.1: one unsigned artifact, one input, one embedded source, three
claims and a producer report. All three checks are required. With no trust policy, the expected
result is: integrity `PASS`, sources `PASS`, checks `PASS`, signature `NOT_APPLICABLE`, trust
`NOT_EVALUATED`, human review `NOT_APPLICABLE`, semantic truth/legal enforceability
`NOT_EVALUATED`, verdict `PASS`, exit code 0 — a **mechanical** pass, not a statement of truth.

### F.1 Tree

```text
pap-example/
  assurance-package.json
  artifacts/ACME-SUPPLIER.draft.md
  inputs/project.yml
  sources/acme-policy.md
  claims/provenance.json
  claims/relations.json
  claims/producer-report.json
```

### F.2 `assurance-package.json`

```json
{
  "papVersion": "0.1",
  "package": {
    "id": "urn:pap:acme-supplier:2026-01",
    "title": "ACME supplier assurance package",
    "createdAt": "2026-11-02T00:00:00Z",
    "producer": {
      "name": "contract-builder",
      "version": "0.1.0"
    }
  },
  "subject": {
    "projectId": "acme-supplier",
    "revision": "1.0.0"
  },
  "build": {
    "engineVersion": "0.1.0",
    "manifestVersion": "0.1",
    "normalizedInputDigest": "sha256:fccf755793cf1a1b7982631c201282669924cdcf9d6b171bdff26513fc64d80b"
  },
  "artifacts": [
    {
      "id": "artifact:acme-supplier",
      "path": "artifacts/ACME-SUPPLIER.draft.md",
      "mediaType": "text/markdown; charset=utf-8",
      "bytes": 80,
      "digest": "sha256:5f521a6b5bedacdf8d3536f8fb509bef6e829bfb537b1ec818cb38a8e1a2dd51"
    }
  ],
  "inputs": [
    {
      "id": "input:project",
      "path": "inputs/project.yml",
      "mediaType": "application/yaml",
      "digest": "sha256:2da40818408dec8fe7d63c86cb8e67fbc624c743a7d81b02535f318b80cb08ff",
      "normalization": "lf"
    }
  ],
  "sources": [
    {
      "id": "SRC-ACME-POLICY",
      "path": "sources/acme-policy.md",
      "mediaType": "text/markdown; charset=utf-8",
      "digest": "sha256:d7a4ee24615f562232172021f3c992fa1a5aed7a2ae9c128446101ed8f46eecd",
      "acquiredAt": "2026-11-01T12:00:00Z",
      "acquisition": {
        "method": "git",
        "uri": "https://example.invalid/acme/policy.git",
        "revision": "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
      }
    }
  ],
  "claims": {
    "provenance": {
      "path": "claims/provenance.json",
      "digest": "sha256:8044adf1df927b30e67e743d6ca348a8f197f8af4e9e7cc668ebf525e6e7b95b"
    },
    "relations": {
      "path": "claims/relations.json",
      "digest": "sha256:992cd64e230f2480a88ab7128d802796abfbd44605809ba52cb16828559f83ab"
    },
    "producerReport": {
      "path": "claims/producer-report.json",
      "digest": "sha256:f45a69883bed0d0e62c69c7ff0105e902f86006e89c56d77cef1cc9630846e95"
    }
  },
  "profile": {
    "id": "acme-supplier",
    "version": "0.1.0"
  },
  "checkSpecs": [
    {
      "id": "pap.check.digest-integrity/1",
      "version": "1",
      "required": true
    },
    {
      "id": "pap.check.source-quote/1",
      "version": "1",
      "required": true
    },
    {
      "id": "pap.check.relation-consistency/1",
      "version": "1",
      "required": true
    }
  ]
}
```

The manifest is stored pretty-printed for readability; its identity is computed over the JCS form
in Appendix E.1, so the indentation does not matter.

### F.3 `artifacts/ACME-SUPPLIER.draft.md`

```markdown
# ACME supplier assurance

REQ-001: every delivery MUST include a packing list.
```

80 bytes, trailing LF, no CR.

### F.4 `inputs/project.yml`

```yaml
project:
  id: acme-supplier
  revision: "1.0.0"
```

### F.5 `sources/acme-policy.md`

```markdown
# ACME delivery policy

REQ-001: every delivery MUST include a packing list.

REQ-002: incomplete deliveries MUST be reported.
```

127 bytes. The provenance binding covers only the bytes `[24, 76)`, which are exactly the
`REQ-001` sentence without its trailing newline.

### F.6 `claims/provenance.json` (exact bytes; one line)

```json
{"bindings":[{"entityId":"REQ-001","id":"binding:REQ-001","locator":{"end":76,"kind":"byte-range","start":24},"quote":{"digest":"sha256:619cb81063fff535c31b93b66e274e6df0a1cef4582d17c7a6362c98fac48909","normalization":"none"},"sourceId":"SRC-ACME-POLICY"}],"papClaimsVersion":"0.1"}
```

### F.7 `claims/relations.json` (exact bytes; one line)

```json
{"edges":[{"from":"REQ-001","relation":"derivedFrom","to":"REQ-002"},{"from":"REQ-002","relation":"derives","to":"REQ-001"}],"entities":[{"id":"REQ-001","kind":"requirement"},{"id":"REQ-002","kind":"requirement"}],"papClaimsVersion":"0.1","relations":[{"from":"requirement","inverse":"derives","name":"derivedFrom","to":"requirement"},{"from":"requirement","inverse":"derivedFrom","name":"derives","to":"requirement"}]}
```

### F.8 `claims/producer-report.json` (exact bytes; one line)

```json
{"claims":[{"checkId":"pap.check.digest-integrity/1","checkVersion":"1","checkedAt":"2026-11-02T00:00:00Z","checker":{"id":"contract-builder.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"},"claimedOutcome":"PASS"},{"checkId":"pap.check.source-quote/1","checkVersion":"1","checkedAt":"2026-11-02T00:00:00Z","checker":{"id":"contract-builder.reference","implementationDigest":"sha256:73f738b733b177c04597b0e6ab9c4d267059ea1556e6f943d543c252c5ef15c0","version":"0.1.0"},"claimedOutcome":"PASS"}],"papClaimsVersion":"0.1","producer":{"name":"contract-builder","version":"0.1.0"}}
```

### F.9 Field-by-field walkthrough

| Field | Why it is there | What it does not establish |
|---|---|---|
| `papVersion` | pins the parsing rules and status vocabulary | that the verifier supports the exact minor |
| `package.id` | human/stable label for references | package identity; two packages may share a label |
| `package.createdAt` | acquisition/packaging record | when verification happened or that the package is fresh |
| `build.inputDigest` (absent here) | producer's build identity claim | that the package contains those inputs or that the build is reproducible |
| `build.normalizedInputDigest` | producer's claim about normalized inputs, independently recomputable here | that the producer used the same files |
| `artifacts[].digest`/`bytes` | exact artifact integrity | correctness or completeness of the artifact |
| `inputs[].digest` | per-file normalized input integrity | that the input was actually used by the build |
| `sources[].digest` | exact raw source bytes | that the source is authentic or from the claimed URI |
| `sources[].path` | enables offline source checks | availability at verification time if absent |
| `claims.provenance` | declared bindings, checkable against the snapshot | that the quote supports the entity |
| `claims.relations` | declared graph, checkable for internal consistency | semantic correctness of relations |
| `claims.producerReport` | producer's own outcomes, shown as claims | any verifier result |
| `profile` | identifies the producer configuration | trust in that configuration; no profile code is present |
| `checkSpecs` | the checks the package asks for | their outcomes |
| `requiredFeatures` (absent) | forward-compatible feature gates | anything else |

### F.10 Signed variant (informative)

An optional DSSE envelope for this package would be stored as
`signatures/acme.dsse.json`, signing the canonical manifest bytes from Appendix E.1 with
payloadType `application/vnd.pap.manifest.v0.1+json` and an Ed25519 key whose `keyId` appears in
the verifier's trust policy. Signing does not change any digest in this appendix; the envelope is
outside the manifest and therefore outside `packageIdentity` (§5.10). The signature is evaluated
as an optional adapter and produces the `signature` and `trust` dimensions of §6; it never
upgrades the semantic dimensions.

---


## Appendix G — Glossary

Terms are defined here for review convenience; the normative definitions are in the referenced
sections.

| Term | Meaning |
|---|---|
| **PAP** | Portable Assurance Package, the directory format specified by this RFC (§4). |
| **manifest** | The fixed file `assurance-package.json`; the package's declared content, subjects, identities and claims (§4.4, Appendix A). |
| **artifact** | An exported file whose exact bytes and digest the package declares; the verifier treats it as opaque bytes (§4.4.2, §5.4). |
| **input** | A declared build input snapshot, normalized for digesting under either `lf` or `none` (§4.5.1, §5.6). |
| **source** | A source document used as evidence; its raw-byte digest is declared and its snapshot is optional (§4.5.2, §5.5). |
| **referenced-only source** | A source declared with a digest but no embedded snapshot; source integrity is `UNAVAILABLE` and source-dependent checks cannot pass (§4.5.2, §7.3). |
| **claim** | Producer-supplied data in `claims/*.json`; never a verification result and never used for the verdict (§4.7, Appendix D). |
| **producer report** | The producer's own claimed check outcomes in `claims/producer-report.json`; shown as untrusted and optionally compared (§4.7.3, §7.6). |
| **verification report** | The verifier-generated result of `pap verify`, schema in Appendix C (§7.7). |
| **check** | One named, versioned, bounded mechanical procedure with an independently recomputable witness (§8). |
| **witness** | Recomputable evidence emitted by a check (digest record, source/quote span, relation violation list); never producer-supplied (§8.3). |
| **dimension** | One independent axis of the report: integrity, sources, signature, trust, checks, human review, semantic truth, legal enforceability (§7.3). |
| **status** | A dimension- or check-specific token such as `PASS`, `FAIL`, `UNSUPPORTED`, `NOT_EVALUATED`, `UNAVAILABLE`, `STALE`, `VALID`, `INVALID`, `UNTRUSTED` (§7.2–§7.3). |
| **verdict** | The aggregate conclusion derived from required dimensions and checks with a fixed precedence; there is no `verified` boolean (§7.4). |
| **coverage** | The counts and `full` flag that state exactly what the required set was and how much of it was evaluated (§7.5). |
| **identity** | A domain-separated SHA-256 value answering one specific question about package, artifact, source, inputs, extension closure, checker or verification record (§5). |
| **package identity** | `H("pap.package.v1", JCS(manifest))`; covers the manifest, not payload bytes (§5.3). |
| **JCS** | RFC 8785 JSON Canonicalization Scheme, restricted here to an I-JSON subset with integers only (§5.3.1). |
| **DSSE** | Dead Simple Signing Envelope; the optional v0.1 signature container, with its PAE pre-authentication encoding (§11.2). |
| **trust policy** | The operator-supplied local JSON file that supplies anchors, signer identities, required checks/dimensions and freshness (§6.3, Appendix B). |
| **trust snapshot** | One immutable trust-policy file plus its id, digest and validity window; rotation means a new snapshot (§6.4). |
| **relied-upon decision** | The operator's own acceptance decision made from the report's dimensions, coverage and limitations; it is not a verifier output (§6.8). |
| **normalization** | The declared conversion applied before hashing inputs: UTF-8 fatal decode then CRLF/CR to LF, with a binary fallback; sources are never normalized for their raw digest (§5.6, §5.5). |

---


## Appendix H — Issue #44 acceptance mapping

This appendix is the completeness checklist for issue #44. Section numbers are the assigned layout
for this document (§4–§16), and `D1`–`D12` are the decisions recorded in §16 (accepted by the
maintainer on 2026-11-02). A row is satisfied by the specification, not by producer assertion;
where the state of an item is genuinely deferred, the row says so. If the section layout changes
during integration, this appendix MUST be updated in the same change.

### H.1 Required RFC deliverables (1–10)

| # | Deliverable | Resolved in | Resolution in one line |
|---|---|---|---|
| 1 | Package format and layout | §4, Appendix A, Appendix F | Directory-only package with the fixed `assurance-package.json` manifest, ASCII POSIX package paths, required and optional files, artifact/input/source declarations, schema-version policy and an example package explained field by field. |
| 2 | Digest and identity model | §5, Appendix I | Seven identities with fixed domains and exact bytes; `packageIdentity` over the JCS manifest; raw, normalized, artifact, closure, checker and report identities distinct; no self-referencing digest; timestamps are records, not identity. |
| 3 | Trust model and verification semantics | §6, §7, Appendix B | Independent dimensions; explicit local offline trust policy; unsigned packages allowed; signature validity separated from signer trust and authority; semantic truth and legal enforceability never evaluated. |
| 4 | Status and coverage vocabulary | §7, Appendix C | Per-dimension statuses with explicit aggregation precedence, required-dimension gating, coverage counts and `limitations[]`; no `verified` boolean and no unqualified success. |
| 5 | Witness/check contract | §8, Appendix D | Check record carries check spec id/version, subject digests, checker identity, scope, outcome, witnesses and diagnostics; v0.1 has three checks, each with an independently recomputable witness and no producer-supplied PASS. |
| 6 | CLI contract | §9, Appendix C | `pap verify\|inspect\|explain`, explicit flags, exit codes 0/1/2/3/4/64/70/74, one JCS JSON document on stdout, human text mode, deterministic output, offline, no producer runtime. |
| 7 | Threat model and package parser safety | §10, §4 | Packages are hostile input; path/symlink/duplicate rules, declared size and count limits, no code execution, trust-policy substitution, stale/replay status and fake records covered; unsafe behaviours are out of scope explicitly. |
| 8 | Signature and transparency extension points | §11, §6 | DSSE and in-toto are specified as optional adapters; Sigstore/SCITT/OCI are evaluated and explicitly deferred (not implemented in v0.1); no bespoke signature format; signing optional; revocation and transparency consequences stated. |
| 9 | Conformance and acceptance tests | §12, Appendix E, Appendix F | Normative matrix of positive and negative fixtures with expected per-dimension result, verdict, exit code and diagnostics; vectors published for the supported subset. |
| 10 | Independent implementation strategy | §13, Appendix E | Published schemas, JCS and digest vectors, language-neutral rules, separate codebase and explicit independence criteria; cross-implementation equality required for package-derived identities and outcomes, not for `verificationRecordIdentity`. |

### H.2 Acceptance criteria (11 checkboxes)

| # | Acceptance criterion | Resolved in | Resolution in one line |
|---|---|---|---|
| 1 | RFC specifies package layout, schemas, versioning, canonicalization, and digest rules precisely enough for two independent implementations. | §4, §5, §12, §15.1, Appendix A, Appendix J | Exact schemas, JCS profile, hash domains and framing, compatibility rules (§15.1) and vectors are normative; any remaining underspecified area is listed as an implementation blocker in §13, not assumed away. |
| 2 | Raw, normalized, artifact, manifest, checker, and verification identities are not conflated. | §5, Appendix I | Seven identities with separate definitions, owners and comparison rules; engine identities are claims only and are never used as PAP identities. |
| 3 | Trust model distinguishes integrity, signature validity, signer identity, signer trust, authority, semantic truth, and human approval. | §6, §7 | Separate fields for each dimension; signature validity never implies trust or authority; human review is evidence shape, not reviewer authority; semantic truth is not evaluated. |
| 4 | Status vocabulary and aggregation rules cannot turn unsupported/incomplete checks into an unqualified success. | §7 | `PASS` requires all required checks evaluated and passing and all required dimensions passing; `INCOMPLETE`, `UNSUPPORTED`, `UNTRUSTED` and `FAIL` dominate; text output for a non-PASS verdict must read `NOT A PASS` (§9.6). |
| 5 | Producer-supplied claims are structurally and visually distinct from verifier-generated results. | §4, §7, §8, Appendix C, Appendix D | Claims live in digest-declared `claims/*` files and are labelled untrusted; verifier results exist only in the report; a claim is never a witness and its comparison never changes the verdict. |
| 6 | Threat model covers hostile package parsing and arbitrary code execution; safe defaults are explicit. | §10 | Hostile-input model, path and resource rules, no producer/profile code execution, no subprocess or network, and an explicit in/out-of-scope list with the residual risks named. |
| 7 | CLI contract defines command behavior, report schema, exit codes, offline operation, and no producer-runtime dependency. | §9 | Commands, flags, exit mapping, stdout/stderr split, report schema reference, determinism and offline/no-producer constraints are specified. |
| 8 | Positive and negative conformance fixtures have expected results. | §12, §12.2, §12.4 | Every runnable matrix row states expected dimensions, verdict, exit code and diagnostics; no-report CLI rows state exit code and stderr code. Expected results are normative in §12.2/§12.4; Appendix E fixes the digest/JCS values. |
| 9 | A second implementation can implement the supported subset without private Contract Builder dependencies. | §13 | Algorithms and schemas are language-neutral and published; the independent subset and its equality requirements are defined; no producer import is permitted. |
| 10 | Non-goals and deferred integrations (Sigstore/SCITT/OCI, production key management, temporal graph, mandates) are explicit. | §14, §11, §3.3 | Twelve non-goals and deferred integrations are listed with their reasons and consequences; none is silently included. |
| 11 | RFC is reviewed and accepted before Phase 2 implementation begins. | Document status, §2.4, §3.1 | The RFC is accepted (2026-11-02), Gate 0 is recorded COMPLETE on #43 (comment 6570952005), and the maintainer's #57 decision then authorized Phase 2. The Phase 2 implementation is merged into `main` via PR #64 and available under `pap/`; independent interoperability validation remains pending and Gate 3 remains OPEN. This row cites those records and does not independently re-audit Gate 0. |

### H.3 Required decisions / open questions (12 items)

| # | Question from #44 | Resolved in | Resolution |
|---|---|---|---|
| 1 | Directory-only v0.1 versus archive support; if archive is supported, safe extraction rules. | §16 D1, §4, §10.7, §14.1 | Directory-only in v0.1; archive transport, safe extraction and archive bombs are deferred, with the required extraction rules listed in §10.7 and referenced from §14.1. |
| 2 | Canonical JSON choice and exact canonicalization profile. | §16 D2, §5 | RFC 8785 JCS over an I-JSON subset: UTF-8 without BOM, JCS key order, arrays ordered, integers only, duplicate keys invalid, no Unicode normalization, lone surrogates invalid. |
| 3 | Digest algorithm and domain-separation scheme. | §16 D3, §5 | SHA-256 only; digest ids are `sha256:<hex>`; H(domain, octets) is SHA-256 over ASCII(domain), a 0x00 byte, then octets, with fixed domains for package, artifact, raw source, per-input file and input set, extension closure, checker identity, check record, claims, report, trust policy and quote. |
| 4 | Whether raw source snapshots are embedded, referenced, or both; behavior when unavailable. | §16 D4, §4, §7 | Snapshots are optional; both embedded and referenced-only sources are allowed; without a snapshot source integrity is `UNAVAILABLE`, source-dependent checks are `NOT_EVALUATED`, and a required source-dependent PASS is impossible. |
| 5 | Required versus optional manifest fields and unknown extension semantics. | §16 D5, §4, Appendix A | Strict core schema: unknown core fields are `INVALID`; extensions are namespaced reverse-DNS entries with `{version, critical}`; unknown critical extension or required feature is `UNSUPPORTED`; unknown non-critical extension is ignored with a warning and a limitation. |
| 6 | Producer claim format versus verifier report format. | §16 D6, §4, §7, Appendix C, Appendix D | Separate files, schemas and namespaces; claims are untrusted and the comparison (`AGREES`/`DISAGREES`/`UNVERIFIABLE`/`NOT_COMPARABLE`) never changes the verdict. |
| 7 | Per-check status model and aggregate status rules. | §16 D7, §7 | Fixed statuses per dimension and check; aggregate precedence `FAIL > UNTRUSTED > UNSUPPORTED > INCOMPLETE > PASS`, with `NOT_EVALUATED` for a degenerate report; `PASS` requires complete required coverage. |
| 8 | Trust policy format and offline trust snapshot semantics. | §16 D8, §6, Appendix B | Operator-supplied local `trust-policy.json` with version, id, validity, key material, signer roles/bindings, allowlists, required checks and dimensions, signature mode and freshness; it is not discovered from the package and offline revocation is out of scope. |
| 9 | Minimum v0.1 witness types. | §16 D9, §8, Appendix D | Digest record; source-quote extraction `{sourceId, sourceDigest, range, extractedDigest, quoteDigest}`; relation violation list; each independently checkable and none producer-supplied. |
| 10 | CLI command names, exit codes, output schema, and packaging. | §16 D10, §9 | `pap verify\|inspect\|explain`; exit 0/1/2/3/4/64/70/74; one JCS JSON document plus LF for `--format json`; text mode human-readable; packaging and release expectations in §9.1; deterministic except `evaluatedAt` and the other identity-excluded fields of §5.9; `--now` for reproducible tests. |
| 11 | Compatibility policy for future package versions. | §16 D11, §4, §15.1 | `papVersion` is `major.minor`; a verifier supports a documented major and minor range; the core schema is frozen within a major, minor releases add optional extension/feature data only, unknown required feature is `UNSUPPORTED`, and there is no silent downgrade. |
| 12 | What must be independently implemented for the first interoperability demonstration. | §16 D12, §13 | A separate codebase in a different language preferably, written from this RFC, schemas and published vectors only: parse/validate, JCS, domain-separated digests, the three checks, report and exit codes on unsigned packages; equality required for package identities and outcomes, not `verificationRecordIdentity`. |

### H.4 Issue #44 out-of-scope items

| # | Out-of-scope item | Where excluded |
|---|---|---|
| 1 | Implementing the package producer. | N1, §3.3; the RFC is a specification. |
| 2 | Implementing the verifier CLI. | N2, §3.3; §9 defines the contract, and implementation belongs to #43 Phase 2. |
| 3 | Adding Sigstore/SCITT integration. | N3, §3.3; §11 treats envelopes as optional adapters and defers integration. |
| 4 | Implementing a temporal dependency graph. | N4, §3.3; #43 Phase 4 is a separate component. |
| 5 | Implementing commitment mandates or an authorization service. | N5, §3.3; #43 Phase 5 is deliberately last. |
| 6 | Changing the current M1 plan without an explicit owner decision. | N8, §3.3; §2.5 states PAP is a separate product track and changes nothing in M1. |

---


## Appendix I — Relationship to existing engine identities and provenance work

The engine at `f1ddcf7` already produces a deterministic build identity and performs bounded
provenance binding. PAP reuses the *questions* the engine asks but none of its *values*: no PAP
identity is an engine identity, and no comparison between them is a verification result. This
appendix expands §2.6 and states what PAP does not claim.

### I.0 Summary: what PAP reuses from the engine and what it must not

| Engine capability | PAP reuse | Reason |
|---|---|---|
| Length-prefixed record framing (`u32 BE` lengths, typed tag, parts; `docs/architecture/build-identity.md:74–93`) | Reused formally, under PAP envelopes and domains | The framing is proven unambiguous and keeps the pre-hash byte stream deterministic; the domains are entirely PAP's. |
| LF normalization of text bytes (`spec/lib/identity.ts:124–134`) | Reused as a rule, with a PAP domain | The distinction between normalized text and raw source bytes must stay visible, so the two live in different identities. |
| Path containment and `external: true` as a safety principle (`spec/lib/manifest.ts:233+`) | Borrowed as a principle, not as a producer API | PAP path rules are stricter: ASCII-only segments, no `.`/`..`, no leading slash, declared length and depth limits. |
| Canonical JSON with sorted keys (`spec/lib/identity.ts:143–149`) | **Not reused** | PAP defines RFC 8785 JCS over an I-JSON subset, an external standard two implementations can target; the engine makes no JCS claim. |
| `inputDigest` value (`spec/lib/identity.ts:474`) | **Not reused** | The verifier cannot recompute it; it appears only as `build.inputDigest`, an untrusted producer claim. |
| Diagnostics and exit codes (`spec/lib/diagnostics.ts`, `spec/lib/build.ts:468–486`) | **Not reused** | PAP has its own dimensions, report schema and exit-code mapping (§7, §9); sharing them would import engine policy into the verifier. |
| Generic IR and producer types (`ProjectModel`, entities, relations; contract D5) | **Not reused** (C1) | The IR is explicitly experimental and producer-private; the package format must be implementable without it (§2.5, §13). |

### I.1 Expanded identity table

| Identity | Definition in PAP | Computed by | Engine counterpart at `f1ddcf7` | Comparison rule |
|---|---|---|---|---|
| `packageIdentity` | H(`pap.package.v1`, JCS(manifest)) where the manifest is `assurance-package.json` (§5). | Verifier, from packaged bytes. | None; the producer manifest is `contract-builder.json`, a different schema. | Recomputed by every implementation; cross-implementation equality required. |
| `build.inputDigest` | A copied engine `inputDigest` in the manifest's `build` block; a producer claim. | Producer only. | `BuildResult.identity.inputDigest` (`spec/lib/identity.ts:358–477`). | Claim only; never recomputed and never used by a required check. |
| `normalizedInputDigest` | H(`pap.input.set.v1`, framed input records `("input", path, LF-normalized bytes)` sorted by path) over packaged `inputs/`; each `inputs[].digest` uses `pap.input.file.v1` (§5.2, §5.6). | Verifier; optionally compared with a `build.normalizedInputDigest` claim. | No direct counterpart; inputs participate inside `inputDigest`. | Not comparable to `inputDigest`; recomputed from `inputs/` only, over the PAP-defined normalization. |
| `rawSourceDigest` | H(`pap.source.raw.v1`, raw source bytes) per source, CRLF included. | Verifier, when a snapshot is packaged. | None at baseline; `sources[].identity.sha256` is accepted but not implemented (§2.2). | Recomputed from the snapshot; not equal to the producer's plain SHA-256 and not comparable by string equality. |
| `artifactDigest` | H(`pap.artifact.v1`, raw packaged artifact bytes) per artifact. | Verifier. | `Artifact.sha256`, a plain SHA-256 of renderer-returned bytes (`spec/lib/render.ts:52–58`). | Recomputed over the packaged file; never equal to the engine value for the same bytes, and not comparable. |
| `extensionClosureDigest` | H(`pap.extension.closure.v1`, framed records: kind/id/version, sorted file records `(path, LF-normalized bytes)`, sorted dependency records `(name, version, integrity)`), for the `profile`, `extension` and `checker` jobs. | The party holding the declared files and dependencies; a verifier is not required to recompute a producer-side closure. | Profile/extension `closureDigest` (`spec/lib/identity.ts:166–189`; `profiles/core001/profile.json:119–151`). | Different domain and possibly different declared set; equality is a producer claim, not a verifiable PAP property. |
| `checkerIdentity` | H(`pap.checker.identity.v1`, JCS(`{id, version, implementationDigest}`)). | Verifier. | None; the engine has no checker identity. | Verifier-local; participates in `verificationRecordIdentity`, so cross-implementation equality is not required (D12). |
| `verificationRecordIdentity` | H(`pap.report.v1`, JCS(report identity form)), excluding `evaluatedAt`, `durationMs`, absolute package/policy paths, the `producerClaims` block, human diagnostic messages (report and per-check) and the optional `checks[].witnesses[].quoteBase64` (§5.9). | Verifier. | None. | Cross-implementation equality is not required because it includes the verifier's own checker identity. |

No self-referencing digest field exists in the manifest, and no manifest field is computed over the
report. Timestamps (`package.createdAt`, `sources[].acquiredAt`, `claims.checkedAt`,
`reviews.decidedAt`, `report.evaluatedAt`) are records, never build or package identity. The
`build` block is a producer claim, not a trusted identity (D6, §5, §7).

### I.2 The provenance RFC's source digest versus PAP `rawSourceDigest`

- The accepted provenance field is `sources[].identity.sha256` in the producer manifest: 64
  lowercase hex, plain SHA-256 over the raw bytes as read, with no normalization, BOM stripping or
  Unicode normalization (provenance RFC §4.4.2:418–433). It is a project-owned expectation
  checked by the core before provenance binding; a mismatch is an error, and absence with mapped
  provenance is a draft warning that blocks release and `--strict`
  (provenance RFC §4.4.3–4.4.5, and its Q5 decision — provenance RFC labels, not PAP D1–D12).
- PAP's `rawSourceDigest` is `sha256:<hex>` = H(`pap.source.raw.v1`, raw bytes), declared per source
  and recomputed by the verifier from a packaged snapshot when one exists (D4, §5). CRLF is part of
  the hashed bytes in both designs.
- Same underlying bytes, different hash constructions and owners: `sha256(bytes)` and H(domain,
  bytes) are different values by design. They MUST NOT be compared by string equality, and a PAP
  verifier MUST NOT treat the provenance field as a PAP identity.
- A verifier MAY cross-check a producer-supplied plain SHA-256 claim by recomputing
  `sha256(bytes)` from a snapshot and reporting `AGREES`, `DISAGREES`, `UNVERIFIABLE` or
  `NOT_COMPARABLE`. Per D6 the comparison never changes the verdict. Conversely, presence of the
  provenance field is not evidence that PAP's `rawSourceDigest` is correct, and its absence is not
  a PAP integrity failure.
- At baseline the engine cannot carry the field: `ManifestSource.identity` is
  `{document?, revision?}` and `validateSources` rebuilds the object, dropping unknown members
  (`spec/lib/manifest.ts:22–28`, `:383–399`). A producer that wants to embed the provenance
  claim before #45's implementation must record it in a PAP claims file, not in the engine
  manifest. This RFC does not depend on #45's implementation.

### I.3 Binding versus verification (#37)

- In the engine, a provenance binding is produced by `bindProvenance`, which copies the mapped
  selectors into the entity after checking completeness and source existence; it does not verify
  the quote against the source (`spec/lib/provenance.ts:1–71`). Quote location is checked
  separately by the profile hook through the adapter (`profiles/core001/checks/source.ts`;
  `spec/lib/adapters/markdown.ts`). The engine emits no verification record, method, source digest
  or verification status, which is why #37 is open.
- In PAP, a **binding** is an untrusted producer claim in `claims/provenance.json`: entity or
  assertion → source → declared locator/range → quoted bytes, declared by digest in the
  manifest. A **verification** is a verifier-generated check record plus witness: the source-quote
  check extracts the declared byte range from the packaged snapshot, computes the quote digest
  under `pap.quote.v1`, and records
  `{sourceId, sourceDigest, range, extractedDigest, quoteDigest}` (§8). Bindings without a
  snapshot leave source integrity `UNAVAILABLE` and source-dependent
  checks `NOT_EVALUATED`; they are never described as verified (§7).
- PAP therefore implements the #37 distinction for packages, but it does not close #37 for engine
  outputs. A producer assembling a package MUST NOT present a binding as a verification, and the
  RFC records the engine's remaining gap as a limitation (§2.3, §2.4).

### I.4 Profile trust (#35) versus PAP's no-code rule

- In the engine, profiles are executable code: `loadProfileModule` imports the profile's `view` and
  `validator` modules with a plain dynamic `import()` (`spec/lib/build.ts:342–366`), and the CLI
  statically imports the profile renderer (`spec/build.ts:3`), so profile code runs in-process with
  the builder's privileges. They are trusted, not sandboxed, and
  determinism is an author obligation (contract §8.1:828–831; contract D28:1212;
  `docs/architecture/build-identity.md:145–147`). #35 asks for an explicit declarative-versus-
  executable split and an opt-in trust decision; at the baseline the import is unconditional and no
  opt-in policy or rejection test was found, so #35 remained open at the baseline (§2.3).
- In PAP, the no-code rule is absolute: the package MUST NOT contain producer, profile or checker
  code that the verifier executes, and the verifier MUST NOT import the producer runtime.
  Profile and extension identities are values (id, version, `closureDigest`); the only code that
  runs is the verifier's own, identified by `checkerIdentity`. An unknown profile or checker leads
  to `UNSUPPORTED`, `UNTRUSTED` or `NOT_EVALUATED` according to the local trust policy, never to
  execution (§6, §7, §11).
- Consequence: PAP's verifier sits outside the engine's executable-extension trust boundary, but
  PAP does not make the producer's profile trusted or safe. At the baseline it did not close #35,
  and the minimum Gate 0 security gate was therefore open (§2.4); Gate 0 is now recorded COMPLETE
  on #43, and this document cites that record without independently re-auditing it. Recognition of
  a profile or checker identity is a policy decision, not an assurance that its checks are correct:
  `profileRecognition` and `checkerRecognition` are separate trust statuses, and no recognition
  result upgrades semantic truth (§6, §7).

### I.5 What PAP does not claim

- **Not a build reproduction proof.** `build.inputDigest` is a copied producer claim. A verifier
  that lacks the engine runtime, the producer's canonical manifest, its extension closures and its
  lockfile cannot recompute it (§5, Appendix I.1). Package integrity says the packaged bytes are
  internally consistent; it says nothing about whether a rebuild would reproduce them, about
  hermeticity, or about the correctness of the build.
- **Not a signature or an attestation.** DSSE/in-toto and Sigstore-compatible envelopes are optional
  extension points (§11). `signature.validity: VALID` establishes only that a key signed the
  canonical manifest bytes. It does not establish signer authority, package truth, correctness or
  signing time; signer trust is a separate local policy decision, and an unsigned package is still
  a valid PAP input (§6, D8).
- **Not semantic verification.** Schema validity means "structurally valid under the core schema".
  Relation consistency is a structural property of `claims/relations.json`. A source-quote check
  proves that an exact byte range hashes to a declared digest; it does not prove that the text is
  well chosen, correctly classified, or true. `semanticTruth` and `legalEnforceability` are always
  `NOT_EVALUATED` (§7).
- **Not human-review verification.** `claims/reviews.json` records producer claims about review.
  The human-review dimension statuses (`PASS|INCOMPLETE|UNKNOWN|NOT_APPLICABLE`) describe the shape
  of the evidence, not the quality, independence or authority of a reviewer; v0.1 has no
  cryptographic review attestation (§4, §7).
- **Not a "verified" package.** PAP has no boolean and never reports one. The report carries
  per-dimension statuses, check outcomes, coverage and limitations; the aggregate verdict is
  derived with the precedence `FAIL > UNTRUSTED > UNSUPPORTED > INCOMPLETE > PASS` (first match
  wins) and `NOT_EVALUATED` for a degenerate report, and any non-PASS report must display
  `NOT A PASS` (§7, D7).

The boundary in one sentence: PAP makes a package's claims inspectable and bounds what was
checked; it does not turn claims into truth, and it does not turn a producer's build identity into
a verifier's proof.

---


## Appendix J — Verifier diagnostic registry (normative)

Every diagnostic is `{code, severity, scope, message}`. The code is stable; the message is not
normative. `severity` is `error` (the verifier could not establish a positive result for the
affected requirement), `warning` (a limitation or a negative trust/recognition decision that the
verdict already accounts for) or `info` (observational, no effect). The verdict is computed from
dimensions and coverage (§7.4), not directly from this table; the "Effect" column states the
required consequence so an implementation cannot downgrade an error to a warning.

### J.1 Package, parser and paths

| Code | Severity | Effect / limitation |
|---|---|---|
| `pap.package.not-found` | error | The package path does not exist, or a symbolic link used as `PACKAGE` does not resolve; no report, exit 74. A path that exists or resolves to something that is not a directory (including an archive file) is a usage error (`pap.cli.usage`, exit 64). A symbolic link to a directory is resolved and is not this condition |
| `pap.package.io` | error | A declared file or the manifest cannot be read; integrity `FAIL` (an unreadable manifest also reports `package.identity: null`, verdict `FAIL`, exit 1; a missing package *directory* is `pap.package.not-found`, exit 74) |
| `pap.package.manifest-json` | error | Manifest is not valid UTF-8 JSON, has a BOM, trailing data or a non-I-JSON number; integrity `FAIL` |
| `pap.package.duplicate-key` | error | A JSON object repeats a member name; duplicate keys are invalid, not last-wins; integrity `FAIL` |
| `pap.package.schema` | error | Manifest violates Appendix A (type, required field, enum, pattern) or a cross-field invariant JSON Schema cannot express (duplicate id/path, `checkSpecs[].version` suffix mismatch); integrity `FAIL` |
| `pap.package.unknown-field` | error | Unknown field in a core object (additionalProperties violation); integrity `FAIL` |
| `pap.package.path-invalid` | error | Declared path violates §4.3.1 (non-ASCII, `.`/`..`, empty segment, too deep/long); integrity `FAIL` |
| `pap.package.path-duplicate` | error | Two declarations share a path, or differ only by case; integrity `FAIL` |
| `pap.package.path-escape` | error | A syntactically valid declared path resolves outside the package root (for example through a symlink or an unexpected mount); integrity `FAIL`. Traversal, absolute paths and `..` syntax are `pap.package.path-invalid` |
| `pap.package.symlink` | error | A declared path is a symbolic link, or a symlink is encountered where a payload is read; integrity `FAIL` |
| `pap.package.non-regular` | error | A declared path is not a regular file (directory, FIFO, socket, device); integrity `FAIL` |
| `pap.package.declared-file-missing` | error | A manifest-declared payload file is absent or unreadable; integrity `FAIL` |
| `pap.package.manifest-self-reference` | error | The manifest declares itself as a payload; integrity `FAIL` |
| `pap.package.undeclared-file` | warning | A regular file is present but not declared; it is not read and does not affect identities |
| `pap.package.undeclared-scan-incomplete` | warning | The verifier could not complete the undeclared-file scan: an I/O error while enumerating the package root or a directory under it, or a private implementation scan budget (entry count or traversal depth) stopped it. The absence of undeclared files was not established; the scan is `NOT_EVALUATED`, `coverage.full: false`, verdict at most `INCOMPLETE`, and a limitation with the same code. Declared payload integrity is unaffected; a declared payload failure remains `pap.package.io`/`declared-file-missing`/`FAIL` |
| `pap.package.limit-exceeded` | error | A §4.3.4 resource limit was exceeded; affected check(s) `NOT_EVALUATED`, verdict `INCOMPLETE` — except a limit that prevents reading/parsing the manifest, which yields `package.identity: null`, `integrity.package: FAIL`, verdict `FAIL` |
| `pap.package.duplicate-id` | error | Duplicate artifact/source/input/check/claim id, or duplicate check specification; integrity `FAIL` |
| `pap.package.empty-check-specs` | warning | No required check remains after the union with policy; the verifier evaluates the declared checks, then reports `INCOMPLETE` with `coverage.full: false` (§4.4.3, §7.4 rule 4); never a vacuous `PASS` |
| `pap.package.claim-invalid` | error | A claim file violates Appendix D; integrity `FAIL` and the dependent check is `NOT_EVALUATED` |

### J.2 Integrity

| Code | Severity | Effect / limitation |
|---|---|---|
| `pap.integrity.artifact-mismatch` | error | Declared artifact digest or byte count differs from recomputed; integrity `FAIL`, digest check `FAIL` |
| `pap.integrity.source-mismatch` | error | Declared raw source digest differs from recomputed; sources integrity `FAIL`, source checks `FAIL`/`NOT_EVALUATED` |
| `pap.integrity.input-mismatch` | error | Declared input digest or `build.normalizedInputDigest` differs from recomputed; integrity `FAIL` |
| `pap.integrity.claim-mismatch` | error | Declared claim-file digest differs from recomputed; integrity `FAIL` |
| `pap.integrity.identity-unavailable` | warning | A source/input identity could not be recomputed (referenced-only or absent); corresponding dimension `UNAVAILABLE`/`NOT_EVALUATED` |

### J.3 Sources and checks

| Code | Severity | Effect / limitation |
|---|---|---|
| `pap.source.unavailable` | warning | A source required by a check has no embedded snapshot; source integrity `UNAVAILABLE`, check `NOT_EVALUATED` |
| `pap.check.unsupported` | warning | The verifier does not implement a required check id/version; check `UNSUPPORTED`, verdict `UNSUPPORTED` |
| `pap.check.not-evaluated` | warning | A required check could not run (missing input, unavailable source, limit, unsupported newer `papVersion`); check `NOT_EVALUATED`; verdict `INCOMPLETE` unless a higher-precedence rule applies (for example `UNSUPPORTED` for a newer minor) |
| `pap.check.failed` | error | A required check completed with a failing assertion; check `FAIL`, verdict `FAIL` |
| `pap.check.partial` | warning | A check evaluated only part of its scope; never `PASS`; verdict `INCOMPLETE` with `coverage.full: false` (v0.1 has no policy switch that turns partial coverage into `FAIL` or `PASS`) |
| `pap.check.span-out-of-range` | error | A provenance byte range is outside the source snapshot or `start > end`; check `FAIL` |
| `pap.check.quote-mismatch` | error | Extracted span bytes do not hash to the declared quote digest; check `FAIL` |
| `pap.claim.binding-duplicate` | error | Duplicate/ambiguous provenance binding id or identical `(entityId, sourceId, range)` tuple; check `FAIL` |
| `pap.claim.duplicate-entity` | error | Duplicate entity id in relations claim; check `FAIL` |
| `pap.claim.relation-duplicate` | error | Duplicate relation name in relations claim; check `FAIL` (an edge naming it would be ambiguous) |
| `pap.claim.relation-unknown` | error | Edge names a relation that is not declared; check `FAIL` |
| `pap.claim.edge-unknown-entity` | error | Edge endpoint is not a declared entity; check `FAIL` |
| `pap.claim.relation-kind-mismatch` | error | Edge entity kinds do not match the relation declaration; check `FAIL` |
| `pap.claim.inverse-missing` | error | Declared inverse is not declared, or a reciprocal edge is missing; check `FAIL` |
| `pap.claim.inverse-not-reciprocal` | error | Inverse relation exists but its own `inverse` field is not the forward relation (or is absent); check `FAIL` |
| `pap.claim.inverse-kind-mismatch` | error | Inverse declaration's `from`/`to` are not the reverse of the forward declaration; check `FAIL` |
| `pap.claim.unsupported-version` | warning | A claim file declares an unknown `papClaimsVersion`; claim is not interpreted; dependent check `UNSUPPORTED`/`NOT_EVALUATED` |
| `pap.claims.producer-mismatch` | warning | A producer claim's `claimedOutcome` disagrees with the independent outcome; never changes the verdict by itself |

### J.4 Signatures, trust and review

| Code | Severity | Effect / limitation |
|---|---|---|
| `pap.signature.absent` | info in optional/absent-policy mode; warning in required mode | No envelope present; validity `NOT_APPLICABLE` unless policy mode is `required` (then `NOT_EVALUATED`, verdict `INCOMPLETE`) |
| `pap.signature.envelope-invalid` | error | Envelope structure is malformed (not JSON, invalid/missing base64 payload or signature, missing `signatures`); entry `INVALID` |
| `pap.signature.unsupported-format` | warning | Envelope format/payloadType/key type not supported in v0.1; envelope `NOT_EVALUATED` |
| `pap.signature.invalid` | error | Cryptographic signature verification failed; envelope `INVALID`; verdict `FAIL` when mode is `required` |
| `pap.signature.payload-mismatch` | error | Envelope payload does not canonicalize to the package manifest / expected package identity; envelope `INVALID` |
| `pap.signature.subject-mismatch` | error | in-toto subject or predicate does not match the package identity/predicate type; envelope `INVALID` |
| `pap.signature.predicate-unrecognized` | info | in-toto predicate type is not the PAP predicate; the signature is still verified, predicate is informational |
| `pap.signature.keyid-missing` | warning | Envelope has no usable key identifier; entry `NOT_EVALUATED`, signer identity `UNKNOWN`, policy decision `REJECTED` when a signature is required |
| `pap.signature.algorithm-unsupported` | warning | A signature entry or policy key names an algorithm outside v0.1 (Ed25519 only); entry `NOT_EVALUATED` |
| `pap.signature.duplicate-signer` | warning | The same `keyId` appears in more than one envelope signature; each entry is reported, but the signer is counted once for trust aggregation |
| `pap.trust.policy-absent` | info | No policy supplied; trust dimension `NOT_EVALUATED`; `PASS` only if signature/trust are not required |
| `pap.trust.policy-invalid` | error | Policy is unreadable, not JSON or violates Appendix B; fail closed: no report, exit 64 |
| `pap.trust.policy-stale` | warning | Policy `expiresAt` is before `--now`/clock; policy decision `STALE`, verdict `INCOMPLETE` |
| `pap.trust.policy-not-yet-valid` | warning | Policy `issuedAt` is in the future; policy decision `STALE`, verdict `INCOMPLETE` |
| `pap.trust.signer-unknown` | warning | Valid signature from a key/identity not present in the policy; signer identity `UNKNOWN`, policy decision `REJECTED`, verdict `UNTRUSTED` when the signature is required |
| `pap.trust.signer-untrusted` | warning | Key/identity known but not authorized for this package/role; signer identity `UNTRUSTED`, verdict `UNTRUSTED` |
| `pap.trust.policy-rejected` | warning | Policy explicitly rejects the package/signature set; policy decision `REJECTED`, verdict `UNTRUSTED` |
| `pap.trust.package-not-allowed` | warning | `package.id` is not in the signer's allowed package list; trust decision `UNTRUSTED` |
| `pap.trust.checker-unknown` | warning | Checker identity is not in the policy allowlist; recognition `UNSUPPORTED` |
| `pap.trust.checker-untrusted` | warning | Checker identity is known but not allowed; recognition `UNTRUSTED`, verdict `UNTRUSTED` |
| `pap.trust.profile-unknown` | warning | Profile identity is not in the policy allowlist; recognition `UNSUPPORTED` |
| `pap.trust.profile-untrusted` | warning | Profile identity is known but not allowed; recognition `UNTRUSTED`, verdict `UNTRUSTED` |
| `pap.trust.review-required` | warning | Policy requires human approval and evidence is not sufficient; human review `INCOMPLETE`, verdict `INCOMPLETE` |
| `pap.review.missing` | warning | Required approval evidence absent; human review `INCOMPLETE` |
| `pap.review.stale` | warning | Approval is older than the policy `maxAgeSeconds`; human review `INCOMPLETE` |
| `pap.review.unbound` | info | The approval is a producer claim without cryptographic binding (always in v0.1). MUST be emitted as a diagnostic **and** as a limitation whenever `humanReview.status` is `PASS`; records that the status is not an authenticated approval. No verdict effect |
| `pap.review.unknown-reviewer` | warning | Reviewer identity is not recognized by the policy; human review `UNKNOWN` |
| `pap.review.binding-invalid` | warning | Approval does not bind this package/artifact set (wrong or absent `packageIdentity`/scope); human review `INCOMPLETE` |

### J.5 Compatibility, features and CLI

| Code | Severity | Effect / limitation |
|---|---|---|
| `pap.feature.unsupported` | warning | A `requiredFeatures` entry is not supported; verdict `UNSUPPORTED` |
| `pap.extension.critical-unsupported` | warning | An unknown `critical: true` extension is present; verdict `UNSUPPORTED` |
| `pap.extension.ignored` | info | An unknown non-critical extension was ignored; listed in limitations, no verdict effect |
| `pap.compat.version-unsupported` | warning | `papVersion` major/minor cannot be safely parsed; verdict `UNSUPPORTED` |
| `pap.compat.minor-newer` | warning | Package minor is newer than the verifier's supported range; verdict `UNSUPPORTED` unless the verifier explicitly supports it |
| `pap.compat.deprecated` | warning | A deprecated field/status was accepted; listed in limitations, no verdict effect |
| `pap.limit.lowered` | info | Operator lowered a §4.3.4 limit; the effective values are reported in `effectiveLimits` and in `limitations[]` |
| `pap.claims.spoofed-result` | error | A producer claim contains verifier-only fields (`outcome`, `witnesses`) or otherwise mimics a verifier record; the claim file is invalid and integrity `FAIL` |
| `pap.cli.usage` | error | CLI usage error (unknown/missing option, extra positional, archive instead of a directory, invalid/undeclared `--check`); exit 64, no document |
| `pap.cli.unknown-check` | error | `explain --check` names a well-formed id that the package does not declare; exit 64, no document |
| `pap.io.error` | error | CLI could not write stdout/report or read its own assets; exit 74 |
| `pap.internal.error` | error | Verifier bug (unexpected exception); exit 70; no partial `PASS` may be reported |

Severity does not by itself determine the exit code: the exit code follows the verdict (§7.4,
§9.3): 0 `PASS`, 1 `FAIL`, 2 `INCOMPLETE`, 3 `UNTRUSTED`, 4 `UNSUPPORTED`, 64 usage, 70 internal,
74 I/O. A verifier that maps an `error` diagnostic to a warning status is non-conformant.
