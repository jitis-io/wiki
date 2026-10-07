# Wiki 3.3.0+jitis.1

Merge upstream [v3.3.0](https://github.com/frappe/wiki/releases/tag/v3.3.0)
(`04c3cacb7dc2d5a3eae517df19653a4fcd83d723`) into the reviewed JITIS fork.
This introduces upstream analytics, indexing controls, internal page links,
space deletion and editor improvements. All JITIS Portal Only, private upload,
clone ownership, publication, search and fail-closed document-scope boundaries
remain in force.

Internal page-link targets and document analytics resolve the same authoritative tree and stamp ownership as
reader APIs before reading its derived cache or disclosing a target route. Negative tests cover foreign and
Portal Only spaces, deletion capabilities and orphan/mismatched document scopes.
The POST-only metadata command reloads the persisted record before authorizing
its current document owner and applying only explicit metadata arguments. Forged space
stamps and pending content/tree fields cannot bypass its write permission;
positive git-synced metadata behavior remains covered by the native suite.
Atomic WebP output retains the original private/public location and file metadata.

Frontend dependencies use stable frappe-ui 1.0.0, Tiptap 3.31.4, Vue 3.5.43,
VueUse 15, Pinia 4, fuzzysort 4 and Vite 8. The explicit search threshold preserves
lenient title matching after fuzzysort 4's new default threshold. Tailwind 3 and
Vue Router 4 remain required by the published frappe-ui/framework peers.
The existing Biome 1 configuration is retained; a formatter-major migration is a
separate tooling task. PDFjs 6 is shared with vue-pdf-embed 2.1.6.

The disposable native gate pins Frappe 16.51.0 at
`6b450a166e076dd842e4db7ea0843f62881e62ac` and ERPNext 16.50.0 at
`7474d9e786277383de1242ab882f16856d17a9c9`. The shared framework UI package is
provided by that Frappe tree. Quality/frontend tests, a native asset build and the
full Wiki suite must pass on the final source. Runtime telemetry follows the
upstream optional Pulse configuration; this release does not enable it.

An immutable app tag and central App-Lock update are separately coordinated.
No application-source update implies productive migration, customer enablement
or acceptance of a new real External-ID signup/MFA/recovery flow.
