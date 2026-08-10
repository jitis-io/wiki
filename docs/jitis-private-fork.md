# JITIS Wiki release fork

This repository is the canonical source for the JITIS Wiki privacy changes. A
consumer must pin one full commit ID from the public `jitis-io/wiki` fork; it must
not carry or apply a second copy of the privacy patch.

## Compatibility contract

- Frappe `v16.29.0` at `06613fc60b44d5736007ae3107cdab029b2ae045`
- ERPNext `v16.30.0` at `8378b6e203841c056925420cc44e6d631c915cf1`
- Python 3.14, Node.js 24 and MariaDB 11.8

The GitHub Actions pipeline creates a clean Bench and builds the exact Wiki tree. It
runs the privacy, permission, and SQLite search compatibility gates on a site
with ERPNext 16.30 installed, then runs the complete Wiki server suite on a
second clean Frappe 16.29 site. The two-site split avoids Frappe's legacy test
record loader traversing optional ERPNext applications that are not part of
this pinned stack. The tests cover private attachment migration, public-file
cloning, rollback/idempotency, role-controlled private files, anonymous access,
and the Frappe 16.29 SQLite search API.

## Downstream consumption

Consumers should clone `https://github.com/jitis-io/wiki.git` without
credentials, check out an exact 40-character commit ID, and verify `HEAD`.
Do not duplicate the privacy patch in a downstream repository as a fallback.

Local integration tests may clone a trusted local checkout, but must verify the
same full commit before installing it.
