# Wiki 3.2.1+jitis.3

Keeps upstream Wiki v3.2.1 and the existing customer privacy boundary. Portal-only
spaces now explain publication and customer access correctly in their native
settings instead of implying that publication makes them public.
The new-space dialog selects the existing `Portal Only` protection by default
and omits the Guest role for those spaces. Explicitly choosing an ordinary space
retains the upstream public-space behavior. No customer mapping or grant is
created automatically, and existing spaces are not reclassified by a migration.

The [customer guide](customer-documentation/README.md) describes one space per
customer, a freely editable company title, a stable customer-number route and
three starter pages. It also explains the separate portal URL, safe onboarding,
supported content and the deliberately simple draw.io source/PNG workflow.
The [fork guide](jitis-private-fork.md#architecture-and-fork-boundary) maps the
editor, native document model, JPI boundary and portal renderer.

The companion Portal change handles parsed HTML resource validation, internal
links and native PDF download cards. Customer mapping validation belongs in
JPI. Neither change is duplicated in the Wiki fork.

Compatibility targets remain Frappe 16.35.0 and ERPNext 16.36.0. Release requires
both disposable repository gates and default-branch CI, including the existing
browser suite. Publish an immutable tag on that tested commit and consume it
through the ERP platform app lock; merging this app alone does not deploy it.
