# Wiki 3.2.1+jitis.2

Security follow-up on the released upstream Wiki 3.2.1 base. This is a release
candidate until the reviewed commit is tagged and the platform pins and deploys
that tag; merging the fork does not deploy it.

## Scope

- Restrict direct Desk/REST access to internal revision records, revision items,
  content blobs and merge conflicts to Wiki Managers and System Managers.
- Preserve ordinary contributors' existing space-authorized change-request APIs.
- Reject generic saves that replace a stored portal-only boundary, adopt another
  space's document root or attach foreign revision history. Source and destination
  trees must both be authorized for a move.
- Include the translated revision-permission message and native regressions for
  history disclosure, ownership changes and cross-space writes.
- Preserve the customer documentation workflow and reusable templates under
  [customer-documentation](customer-documentation/README.md).

JPI remains responsible for Entra identity, Customer relationships and explicit
portal grants. This release adds no alternative identity or customer-grant store,
does not publish customer content, and does not alter the chosen upstream base.

## Compatibility and release checks

The disposable compatibility gate pins Frappe 16.35.0 at
`012667b9c4e7f66d5e1ff5858d2e922331d4300a` and ERPNext 16.36.0 at
`b30aa5334bcea94dba74f5b866af13c43a861948`, with Python 3.14, Node 24 and MariaDB
11.8. It installs and migrates the complete local source, builds assets, runs
the ERPNext-compatible privacy/security suites, then the full Wiki suite on a
separate clean Frappe site. Quality and frontend checks are also required.

After review, publish the immutable `3.2.1+jitis.2` tag and pin its exact commit
in JPI integration and the platform app lock. Run the combined downstream
checks before the ERP image release. No live document/data migration has been
performed by preparing this release.

Production acceptance must use the real portal path: an allowed customer page
and private attachment, denied Guest and Customer-A/B access, editor upload/save,
search and navigation. Passing repository tests alone is not production acceptance.
