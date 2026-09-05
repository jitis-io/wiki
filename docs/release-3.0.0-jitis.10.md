# Wiki 3.0.0+jitis.10

This release candidate fixes GHSA-cp6q-959q-f8rh in the Wiki editor's Tiptap
dependency. The maintained upstream Wiki base and JITIS authorization code are
unchanged. Deployment requires the existing immutable platform release gates.

## Reviewed change

Pin the direct Tiptap dependencies to `3.30.4` and synchronize the
installed Tiptap family to `3.30.4`, including Core, ProseMirror wrappers,
StarterKit and extensions. Tiptap declares exact peer versions between these
packages. Updating the family avoids both a vulnerable nested Core copy and
mismatched editor peers. Non-Tiptap package versions are unchanged.

The original dependency PR #19 was reviewed at
`bcd173165692914413ff48740bbd3409cd47868e`. All ten checks passed, but its lockfile
still contained the vulnerable exact Core 3.30.0 dependency. This release closes
both dependency paths and adds security regression coverage.

## Security relevance and limits

Wiki custom image, link, callout, PDF, video, iframe and Mermaid extensions use
Tiptap's `mergeAttributes`. The upstream flaw can turn an own JSON `__proto__`
key into inherited attributes that ProseMirror's DOM serializer applies to an
element. Core 3.30.4 defines a normal own data property for that key instead of
invoking the prototype setter.

The repository's current image and link document schemas enumerate allowed
attributes. The vulnerable helper was reproduced in the installed 3.30.0
dependency, but this review does not claim an externally reachable Wiki exploit.
Updating the affected rendering dependency is a bounded security fix before
expanding customer use.

Regression tests exercise imported JSON through both the direct Core and the
Core resolved by StarterKit, then inspect attributes produced by the real
ProseMirror serializer. A normal Wiki link retains its URL, title, target and
`noopener noreferrer` attributes. Existing quality, clean-bench Frappe/ERPNext,
Wiki server and browser tests remain the release gates.

## Upstream follow-up

At the next reviewed stable upstream Wiki sync, preserve the security fix and
verify both direct and StarterKit dependency paths still resolve Core 3.30.4 or
later. This security exception does not authorize general runtime dependency
updates.

Sources:

- https://github.com/ueberdosis/tiptap/security/advisories/GHSA-cp6q-959q-f8rh
- https://github.com/ueberdosis/tiptap/commit/01d7af8c983ee5954c63734f4fa46cb23ae3246d
- https://github.com/ueberdosis/tiptap/releases/tag/v3.30.4
- https://github.com/jitis-io/wiki/pull/19
