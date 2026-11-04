# Snapshot Notices

This directory contains a frozen snapshot of normative and supporting source materials used for independent implementations of the Portable Assurance Package (PAP) v0.1.

## Source and provenance

- **Source repository:** https://github.com/agent-federation/contract-builder
- **Source commit:** `c21907890ceb45c5d3c4d72a0a736102b984815a`
- **Snapshot inventory:** [`manifest.json`](manifest.json)
- **Checksum inventory:** [`SHA256SUMS`](SHA256SUMS)

The manifest records the files included in this snapshot and their source provenance. `SHA256SUMS` provides SHA-256 checksums for the snapshot files and the manifest itself.

Consumers should verify the snapshot against these inventories before using it in an implementation experiment.

## Copyright and licensing

The materials in this snapshot originate from the source repository identified above.

Unless a file or its accompanying notice states otherwise, no separate license grant is made by this notice. The license terms applicable to each file remain those provided by its original copyright holder or source repository.

The license of the surrounding independent-implementation repository does not automatically replace, extend, or override the license terms applicable to materials included in this snapshot.

If you redistribute this snapshot, preserve applicable copyright notices, license files, and attribution information.

## Scope of this notice

This notice documents provenance and licensing boundaries only.

It does not:

- certify the authenticity or authority of the source repository or commit;
- establish that every included document is normative;
- establish conformance of any implementation;
- grant rights beyond those granted by the applicable upstream licenses.

For questions about the intended normative status of individual documents, consult the relevant PAP specification and accepted maintainer decisions in the source materials.

## Snapshot integrity

Do not modify snapshot files in place during an independent implementation experiment.

If the snapshot needs to be updated, create a new, explicitly identified snapshot with a new manifest and checksum inventory. Record the source commit and snapshot digest in the corresponding experiment record.

A successful checksum verification establishes byte-level consistency with the supplied checksum inventory. It does not independently establish source authenticity, licensing authority, or normative correctness.
