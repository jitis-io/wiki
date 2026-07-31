# Private Wiki Attachments

## Problem

Customer Wiki content must not create or retain public local files. Frappe's
normal public-to-private transition moves the physical file and updates every
`File` row with the same `content_hash`. That transition is unsafe when Wiki
content and an unrelated ERP document contain identical bytes: privatizing the
Wiki attachment must not change or break the ERP file.

Wiki Markdown can also reference a local public file that is not attached to
the Wiki document. Such references must not remain public after the customer
Wiki cutover.

## Invariants

- New files attached to `Wiki Document` or `Wiki Space` are private, even when
  the caller requests a public upload.
- A migration changes only Wiki-owned `File` rows and Wiki URL fields.
- A public non-Wiki `File` row and its URL remain unchanged when its bytes are
  also used by a Wiki attachment.
- Every migrated Wiki attachment receives its own private URL so tenant-aware
  asset delivery can resolve exactly one owning `File` row.
- A local public URL referenced by Wiki content but owned elsewhere is copied
  to a new private Wiki attachment; its source remains public and unchanged.
- Missing, remote, malformed, or unverifiable local sources block the
  migration before any database or filesystem mutation.
- Re-running the migration is a no-op.

## Migration

1. Inventory public local `File` rows and all local public URLs referenced by
   Wiki Document content, meta images, and Wiki Space image fields.
2. Preflight every planned source and reject the entire migration if a source
   cannot be read and verified.
3. Copy each Wiki-owned source to a unique private path and update only that
   Wiki `File` row. Never call Frappe's content-hash-wide privacy transition.
4. For an otherwise-owned public URL referenced by a Wiki record, create a
   distinct private `File` row attached to that Wiki record and rewrite only
   the Wiki reference.
5. Remove obsolete Wiki-owned public `File` rows and public blobs only when no
   remaining public `File` row uses the URL.
6. Clear Wiki content caches after changes.

The migration runs as an explicit patch for upgrades and as an idempotent
`after_migrate` audit so future regressions fail closed.

## Verification

- Integration test: a Wiki attachment and an ERP-style attachment share the
  same `content_hash`; only the Wiki row and Wiki URL become private.
- Integration test: an unowned public file referenced in Wiki Markdown is
  cloned privately while its original stays public.
- Integration test: a missing source fails in preflight without partial
  changes.
- Integration test: the migration is idempotent.
- Unit/quality checks and the complete Wiki server test suite pass in a clean
  Frappe container.
