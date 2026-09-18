# Wiki 3.2.1+jitis.1

This candidate synchronizes the maintained JITIS fork with the released upstream
Wiki v3.2.1. It keeps Wiki as the home for durable customer documentation and
runbooks. Tickets hold the conversation, tasks hold planned work, and Wiki holds
the resulting knowledge; it does not become another task or billing database.

## Sources and scope

- JITIS starting commit: `55cf5ce5` (3.0.0+jitis.10).
- Prior stable upstream base: `0a6025159289bcdaae26d727ada34764370ac765` (v3.0.0).
- New stable upstream base: `0c0adb06b9deb84d11d1f95e85df891c2a29f8da` (v3.2.1).
- Reviewed release notes: [3.1.0](https://github.com/frappe/wiki/releases/tag/v3.1.0),
  [3.2.0](https://github.com/frappe/wiki/releases/tag/v3.2.0), and
  [3.2.1](https://github.com/frappe/wiki/releases/tag/v3.2.1).

This is a stable v3 sync, not a switch to develop or a new major version. It
imports the space-oriented navigation, command palette, editor outline, upload
collision fixes, longer page titles, route-cache fixes, Frappe v16 search
re-indexing and revision batching. The changed navigation needs a real operator
smoke test before production acceptance.

Upstream removes horizontal tabs from the interface. The old tab fields remain
hidden for historical revisions and change requests; existing content is not
deleted. The new standard migration adds space identity and last-edited fields,
backfills last-edited from page modification dates, widens titles, and removes a
stale generated `/wiki` entry left by the previous move to `/wiki-app`.

## Retained and retired fork changes

Retained: portal-only spaces, canonical document-tree ownership, fail-closed
guest/publication checks, tenant-filtered navigation/search/revisions, private
attachments and migration, private Git imports, space-owned editor uploads,
desktop visibility and immutable CI/runtime pins. JPI remains the portal
authorization boundary; no second customer-grant store or endpoint is added.

The new command-palette search uses the existing document query permission hook.
Directory statistics use permission-filtered spaces. Added regression tests
cover Customer A/B, malformed document scope, portal-only spaces and guest API
denial. Portal-only spaces retain their restricted indicator even for managers.

The WebP merge combines upstream's unique filenames with JITIS's private path,
content-hash and file-size handling. An additional regression checks two
same-named private images, no public output, unchanged first-image bytes and
consistent saved metadata.

Retired: the separate JITIS callout serializer is replaced by upstream's richer
container implementation and fixed-point tests. The former local `index_doc`
compatibility workaround is now upstream behavior; the JITIS security filters
and immediate stale-index removal remain.

Upstream's Tiptap resolutions pin 3.29.2, which would regress the earlier
GHSA-cp6q-959q-f8rh fix. A second current advisory,
[GHSA-j95f-988m-3j2f](https://github.com/ueberdosis/tiptap/security/advisories/GHSA-j95f-988m-3j2f),
also affects the previous 3.30.4 fork version. All Tiptap direct dependencies and
resolutions are therefore aligned on the fixed 3.30.5, including the packages
used by frappe-ui beta.55. Both real serializer regression paths (direct Core
and StarterKit) are retained. Additional tests cover malformed Markdown
attribute parsing and a bounded child-process check for the quadratic parser.
No unrelated dependency-bot branch is merged.

## Validation and release boundary

Target CI stack: Frappe v16.34.0
(`c1f1e8ec3708750d7254f7f99d869ffb9886f19f`) and ERPNext v16.35.0
(`12cd563fb9a79731f75ae2a45b1446a0a2dd9e74`), Python 3.14, Node 24, MariaDB 11.8.
The clean-bench gate covers ERPNext plus the security suites, and the complete
Wiki suite on a separate clean site. Browser CI now pins the same Frappe release
instead of the moving default branch. The integration test category is explicit.

All 124 local frontend tests passed, covering callout, prototype-attribute
and Markdown-attribute regressions. Local Python lint and the CI/secret contracts were checked. The
prescribed local Docker quality, integration and cleanup commands were attempted,
but Docker Desktop's Linux-engine pipe was unavailable; this is not a local
integration pass. The PR must supply successful quality, clean-bench, security
and browser CI at the final head. The release coordinator owns merge, tag,
downstream lock, backup, migration and deployment.

The optional native Windows frontend build was stopped after the upstream
frappe-ui bench-discovery loop failed to terminate at a Windows drive root.
The target Linux build is checked by clean-bench and browser CI; no local
Windows dependency hotpatch is part of this release.

Neither these local checks nor CI constitute production acceptance. After the
immutable platform deployment, verify a permitted customer page and private
asset, denied Guest and Customer-A/B access, editor upload/save and search,
and the updated navigation through the actual portal path.
