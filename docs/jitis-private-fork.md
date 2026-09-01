# JITIS Wiki release fork

This repository is the canonical source for the JITIS Wiki privacy changes. The
ERP platform consumes a reviewed release tag from the public `jitis-io/wiki`
fork; it must not carry or apply a second copy of the privacy patch.

## Production compatibility contract

- ERP platform `v4.2.14`
- Frappe `v16.32.0` at `5cba016e86b54b57f34a3864282b92300ef20fb0`
- ERPNext `v16.33.0` at `b24c9eba551905e256e336ff170a91a92d197a2f`
- Wiki `3.0.0+jitis.9` at `af910c9af9044f70163522c90376da45eb5b1aa5`
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

## Stable upstream sync runbook

This repository is an upstream fork, not an independently updated JavaScript,
Python, or container product. Keep the JITIS difference small and reviewable.

- `origin` is `jitis-io/wiki`.
- `jitis-v3` is the maintained JITIS branch.
- `upstream` is `frappe/wiki`.
- Normal sync follows a released upstream v3 stable tag and
  `upstream/version-3`, never a blind merge from `upstream/develop`.
- Check monthly for stable releases and immediately when a relevant security
  advisory appears.
- Dependency bots may maintain GitHub Actions patch/minor references, but must
  not independently update npm, pip, Docker, Frappe, ERPNext or Wiki runtime
  dependencies in this fork.

For a normal stable sync:

1. Fetch both remotes and all tags. Confirm that the working tree is clean and
   record the current `jitis-v3` commit and latest JITIS release tag.
2. Inspect the published upstream release notes and resolved stable-tag commit.
   Do not treat a moving branch name as release evidence.
3. Create `sync/upstream-vX.Y.Z` from current `jitis-v3` and merge or rebase the
   published stable tag with an explicit, reviewable history.
4. Preserve and review the complete JITIS security boundary: `portal_only`
   spaces; deny-by-default guest/publication rules; document-tree space
   ownership; fail-closed search, navigation and revisions; private attachment
   migration; asset permissions; and the narrow JPI/portal contract.
5. Run repository quality checks, clean-bench Frappe/ERPNext compatibility,
   the complete Wiki server suite, Playwright where required, and negative
   guest plus cross-customer tests. A public-page success is not enough.
6. Set the app version and create an annotated immutable JITIS tag. Use
   `X.Y.Z+jitis.1` for a new upstream base and increment `jitis.N` for a local
   follow-up.
7. Pin that exact tag and resolved commit in the ERP platform app lock. Run the
   complete JPI and platform gates and release only through the immutable
   platform workflow.
8. After deployment, verify an allowed page and private asset plus denied guest
   and Customer-A/B access in the real portal path.

If a security fix is needed before a stable upstream release, cherry-pick only
the smallest reviewed upstream fix, rerun every JITIS boundary test, publish a
new JITIS tag, and record whether the fix is included or must be carried at the
next stable sync. Never copy the same privacy patch into the ERP platform.
