# JITIS Wiki release fork

This repository is the canonical source for the JITIS Wiki privacy changes. The
ERP platform consumes a reviewed release tag from the public `jitis-io/wiki`
fork; it must not carry or apply a second copy of the privacy patch.

## Production compatibility contract

- Frappe `v16.31.0` at `6a329d068416768ec47ccd3326b9cc95a8d7bf99`
- ERPNext `v16.32.3` at `11e0ba0a1c45f217e2e73e885f699102d06da325`
- Wiki `3.0.0+jitis.8` at `7f09528280ac6ce56db554bbbaa97b8d5e8779ac`
- Python 3.14, Node.js 24 and MariaDB 11.8

The Wiki fork pipeline creates clean Frappe v16 benches and runs the privacy,
permission, search-compatibility, and complete Wiki server suites. The exact
production combination above is additionally installed and tested by the
`jitis-platform-integration` clean-bench integration pipeline. The tests cover
private attachment migration, public-file cloning, rollback/idempotency,
role-controlled private files, anonymous access, and the SQLite search API.

## Downstream consumption

The ERP platform stores an exact semantic release tag in
`deploy/jitis/erpnext/app-lock.json`. Its `ci/pin-app-release.sh` helper verifies
that the remote tag resolves to one commit and that the app declares the same
version before updating the lock. The image builder fetches that exact tag, and
the resulting production image is promoted by immutable container digest.

Integration tests may pin the resolved 40-character commit directly and must
verify `HEAD` before installation. Consumers must not use a branch or duplicate
the privacy patch in a downstream repository as a fallback.
