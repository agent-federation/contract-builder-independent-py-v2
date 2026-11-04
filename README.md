# PAP Independent Implementation

A language-neutral starting point for independent implementations of the **Portable Assurance Package (PAP) v0.1** verifier.

This repository provides a frozen copy of the authorized normative inputs and a common implementation brief for independent implementations in different programming languages.

Its purpose is to support reproducible, evidence-based interoperability experiments without making one implementation the reference implementation for another.

## Purpose

The project explores whether independent implementations can interpret and implement the same normative contract consistently, using only explicitly authorized inputs.

The central principle is:

> Independent implementations must derive their behavior from the normative specification, not from another implementation.

Python and Rust implementations (and future implementations in other languages) are developed and evaluated independently.

## Repository contents

| Path | Purpose |
|---|---|
| `snapshot/` | Frozen normative input snapshot, manifest, checksums and provenance |
| `AGENT_BRIEF.md` | Implementation brief for the current experiment |
| `docs/` | Supporting documentation and decisions |

The snapshot is intended to preserve the exact authorized inputs used for an experiment.

It is not automatically updated when the upstream specification repository changes.

## Normative source and snapshot integrity

The snapshot records its upstream source repository and commit in its manifest and provenance documentation.

Before using the snapshot:

1. Verify the snapshot manifest and checksum inventory.
2. Confirm that the snapshot corresponds to the intended experiment.
3. Record the manifest SHA-256 in the experiment record.
4. Do not modify snapshot contents in place.

A successful checksum verification establishes consistency with the recorded checksums. It does not independently establish the authenticity, correctness or authority of the upstream source.

Any change to normative inputs must be treated as a new snapshot and recorded as a separate experiment input.

## Independent implementation rules

An implementation is considered independent only when it is developed without access to another implementation's source code, tests, internal helpers, generated outputs or implementation-specific audit findings.

In particular:

- Do not inspect or reuse another independent implementation.
- Do not copy implementation-specific tests or helper code.
- Do not use previous implementation audits, repair instructions or retrospective notes as hidden guidance.
- Derive behavior from the authorized normative sources and explicitly accepted decisions.
- Document assumptions, ambiguities, limitations and deferred requirements.
- Do not silently turn unknown or unsupported behavior into a passing result.

The implementation brief defines the authorized scope and additional experiment-specific restrictions.

Repository visibility alone does not establish experiment isolation. Experiment owners are responsible for controlling agent access to repositories, branches, files and external resources.

## Experiment records

Each independent implementation experiment should preserve enough metadata to make its conditions reproducible.

At minimum, record:

- Experiment identifier
- Implementation repository and starting commit
- Exact rendered prompt and its SHA-256
- Git blob SHA of the source brief, where applicable
- Normative snapshot manifest SHA-256
- Model and relevant runtime parameters
- Experiment start timestamp
- Initial implementation result and subsequent repair history

Prepared prompts and experiment records may contain implementation-specific or evaluation-sensitive information. They should be stored outside the blind implementation workspace.

## Scope and conformance

An implementation brief may define a limited implementation phase rather than full PAP conformance.

Passing a phase-specific test suite must not be represented as full specification conformance unless the complete applicable requirements have actually been evaluated.

Applicability decisions, deferred checks and unsupported requirements should be explicitly documented.

A test result is evidence about the tested behavior, not a general certification of the implementation.

## Upstream specification

The normative source project is:

[agent-federation/contract-builder](https://github.com/agent-federation/contract-builder)

This repository is an independent implementation support project. It does not replace the upstream specification or establish a competing normative authority.

When sources conflict, use the authority and precedence rules defined by the applicable PAP normative documents and accepted maintainer decisions.

## Contributions

Contributions to documentation, snapshot maintenance and experiment infrastructure are welcome.

Changes to normative inputs must include:

- The exact upstream source and revision
- A new snapshot manifest and checksum inventory
- A clear description of the changes
- An explanation of whether existing experiments remain comparable

Do not silently replace frozen inputs used by an existing experiment.

## License

See [LICENSE](LICENSE).

The repository license applies subject to any separate copyright, licensing or attribution terms accompanying upstream materials included in the snapshot.
