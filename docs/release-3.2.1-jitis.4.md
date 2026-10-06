# Wiki 3.2.1+jitis.4

Cloning a Wiki Space now copies its owned attachments into new isolated private
File rows attached to the cloned documents or space. Document content, meta
images and space logos use the new URLs; original files and references remain
unchanged. Native revisions are created after the copied files have their new
owners, so the new history does not retain the source's private URLs.

Cloning rejects missing or changed file bytes, ambiguous ownership, invalid
trees and local references to foreign or unknown attachments before creating
the target space. A failed transaction removes newly copied file bytes. Role
checks stay native and source/target file access remains separately scoped.

Customer mappings and grants are not cloned. The companion JPI validation hook
protects an enabled customer mapping from accidental removal of `Portal Only`;
this tenant policy belongs in JPI rather than the Wiki fork.

The existing transitive DOMPurify selector is locked to the upstream security
release 3.4.16 for [GHSA-p98j-92pf-mc4p](https://github.com/cure53/DOMPurify/security/advisories/GHSA-p98j-92pf-mc4p).
The affected in-place sanitization and node-removing after-hook combination
was not found in Wiki's own frontend. This targeted dependency fix is carried
until the next stable upstream sync incorporates or retains it; package ranges
and other dependencies are unchanged.

Compatibility targets remain Frappe 16.35.0 and ERPNext 16.36.0, retaining
upstream Wiki v3.2.1 and the [preceding privacy and presentation changes](release-3.2.1-jitis.3.md).
Release requires both disposable repository gates and default-branch CI,
including the existing browser suite. Only an immutable tested tag consumed
through the ERP platform app lock establishes the deployed version.
