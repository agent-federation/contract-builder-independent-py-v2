# Snapshot Provenance

## Source

Repository: agent-federation/contract-builder

Commit:
c21907890ceb45c5d3c4d72a0a736102b984815a

PAP version: 0.1

## Purpose

This repository contains a frozen specification and conformance
material snapshot for an independent PAP verifier implementation.

It is intended to support Gate 3 interoperability validation.

## Inventory model

`manifest.json.files` lists the files copied from the source commit: the PAP
fixtures, schemas, RFC and maintainer decision. `manifest.json.bundle_local` lists
repository-authored metadata that is not part of the source copy; the only such
entry is this provenance document. `SHA256SUMS` covers both inventories and the
manifest itself.

## Included materials

See `manifest.json` for the exact file inventory and checksums.

## Excluded materials

The snapshot intentionally excludes:

- The first verifier implementation source.
- The first verifier implementation tests.
- Implementation reports.
- Runtime and package-manager configuration.
- First implementation PR discussions and review comments.

These exclusions preserve implementation independence.

## Authority

The RFC is the normative specification.
Other documents and fixtures provide supporting decisions,
clarifications and conformance examples.

## Integrity

File-level SHA-256 checksums are provided in `SHA256SUMS`.
