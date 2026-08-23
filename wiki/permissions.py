# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Access control for Wiki Spaces.

Read access  -> view a space + its pages and raise Change Requests.
Write access -> additionally merge Change Requests. Write implies Read.

A space with no role rows is open to all logged-in users (backward compatible).
A space whose Read list contains the built-in ``Guest`` role is publicly readable
(``frappe.get_roles()`` returns ``Guest`` for anonymous requests). ``System Manager``
and ``Wiki Manager`` always have full access. A ``portal_only`` space denies every
other native Wiki/REST caller; a trusted integration must enforce tenant access
before reading it through its own narrowly scoped API.
"""

import frappe
from frappe import _

MANAGER_ROLES = {"System Manager", "Wiki Manager"}
WRITE_PTYPES = {"write", "create", "delete", "submit", "cancel", "amend"}


def is_git_synced_space(space) -> bool:
	"""True if the space mirrors a GitHub repo (content is read-only in the wiki)."""
	name = _resolve_space_name(space)
	if not name:
		return False
	return bool(frappe.get_cached_value("Wiki Space", name, "git_synced"))


def assert_space_writable(space) -> None:
	"""Block content mutations on a git-synced space (the repo is the source of truth).

	The sync engine itself bypasses this by running under
	``frappe.flags.in_apply_merge_revision``.
	"""
	if frappe.flags.in_apply_merge_revision:
		return
	if is_git_synced_space(space):
		frappe.throw(
			_("This wiki space is synced from GitHub and is read-only."),
			frappe.PermissionError,
		)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _is_manager(user=None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(MANAGER_ROLES & set(frappe.get_roles(user)))


def _resolve_space_name(space):
	if not space:
		return None
	if isinstance(space, str):
		return space
	return space.name


def _raise_not_found() -> None:
	"""Hide whether a denied or ambiguously scoped object exists."""
	frappe.throw(_("Page not found"), frappe.DoesNotExistError)


def assert_can_read_space(space, user=None, *, require_authenticated: bool = False) -> str:
	"""Return the existing, readable space name or fail without leaking it."""
	user = user or frappe.session.user
	name = _resolve_space_name(space)
	if (require_authenticated and user == "Guest") or not can_read_space(name, user):
		_raise_not_found()
	return name


def resolve_document_space(document) -> str | None:
	"""Resolve one authoritative space for a persisted Wiki Document.

	The nested tree is authoritative. The denormalized ``wiki_space`` value may
	be empty for older, otherwise valid trees, but when present it must agree
	with the tree. Missing roots, duplicate roots, loops and stale/mismatched
	space stamps all fail closed.
	"""
	name = document if isinstance(document, str) else document.get("name")
	if not name:
		return None

	state = frappe.db.get_value(
		"Wiki Document",
		name,
		["wiki_space", "parent_wiki_document"],
		as_dict=True,
	)
	if not state:
		return None

	current = name
	visited = set()
	tree_space = None
	while current and current not in visited:
		visited.add(current)
		owners = frappe.get_all(
			"Wiki Space",
			filters={"root_group": current},
			pluck="name",
			limit=2,
		)
		if owners:
			if len(owners) != 1:
				return None
			tree_space = owners[0]
			break
		current = frappe.db.get_value("Wiki Document", current, "parent_wiki_document")

	if not tree_space:
		return None
	if state.wiki_space and state.wiki_space != tree_space:
		return None
	return tree_space


def can_read_document(document, user=None, *, require_published: bool = False) -> bool:
	"""Whether a current, unambiguously scoped document may be read."""
	user = user or frappe.session.user
	name = document if isinstance(document, str) else document.get("name")
	space = resolve_document_space(document)
	if not name or not space:
		return False

	if require_published or user == "Guest":
		if not frappe.db.get_value("Wiki Document", name, "is_published"):
			return False
	return can_read_space(space, user)


def assert_can_read_document(
	document,
	user=None,
	*,
	require_published: bool = False,
) -> str:
	"""Return the owning space or raise a non-disclosing 404."""
	if not can_read_document(document, user, require_published=require_published):
		_raise_not_found()
	return resolve_document_space(document)


def is_portal_only_space(space) -> bool:
	"""Whether native Wiki access is blocked for a portal-managed space."""
	name = _resolve_space_name(space)
	if not name:
		return False
	if not isinstance(space, str) and hasattr(space, "portal_only"):
		return bool(space.portal_only)
	return bool(frappe.get_cached_value("Wiki Space", name, "portal_only"))


def _space_role_levels(space) -> dict:
	"""Return ``{role: permission_level}`` for a space. Empty dict means open access.

	When a role appears with both levels, ``Write`` wins (it implies Read).
	"""
	name = _resolve_space_name(space)
	if not name:
		return {}

	rows = frappe.get_all(
		"Wiki Space Role",
		filters={"parent": name, "parenttype": "Wiki Space"},
		fields=["role", "permission_level"],
	)

	levels = {}
	for row in rows:
		if levels.get(row.role) == "Write":
			continue
		levels[row.role] = row.permission_level
	return levels


def can_read_space(space, user=None) -> bool:
	user = user or frappe.session.user
	name = _resolve_space_name(space)
	if not name or not frappe.db.exists("Wiki Space", name):
		return False
	if _is_manager(user):
		return True
	if is_portal_only_space(space):
		return False
	if user == "Guest" and not frappe.get_cached_value("Wiki Space", name, "is_published"):
		return False

	levels = _space_role_levels(space)
	if not levels:
		# Open space: every logged-in user, but not anonymous Guests.
		return user != "Guest"

	# Any role row (Read or Write) grants read. Guest/All rows behave naturally
	# because frappe.get_roles() returns them in the appropriate contexts.
	return bool(set(frappe.get_roles(user)) & set(levels))


def can_write_space(space, user=None) -> bool:
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	if is_portal_only_space(space):
		return False

	levels = _space_role_levels(space)
	if not levels:
		# Open space: writers are the global Wiki Approvers.
		return "Wiki Approver" in frappe.get_roles(user)

	user_roles = set(frappe.get_roles(user))
	return any(role in user_roles for role, level in levels.items() if level == "Write")


def _space_accepts_contributions(space) -> bool:
	"""Whether a space lets Read-tier users propose changes (raise CRs).

	Missing/NULL is treated as enabled so spaces created before this toggle (and
	rows not yet backfilled) keep accepting contributions.
	"""
	name = _resolve_space_name(space)
	if not name:
		return True
	value = frappe.get_cached_value("Wiki Space", name, "allow_contributions")
	return value is None or bool(value)


def can_contribute_to_space(space, user=None) -> bool:
	"""Whether the user may propose changes (raise/edit Change Requests).

	Write-tier users (and managers) can always contribute. Read-tier users can
	contribute only while the space accepts contributions.
	"""
	user = user or frappe.session.user
	if not can_read_space(space, user):
		return False
	if can_write_space(space, user):
		return True
	return _space_accepts_contributions(space)


def can_manage_tabs(space, user=None) -> bool:
	"""Whether the user may create or promote/demote tabs in a space.

	Deliberately stricter than `can_contribute_to_space`: a tab restructures the
	top-level navigation for every reader of the space, which is an editor
	decision rather than a contribution.
	"""
	return can_write_space(space, user)


def assert_can_manage_tabs(space, user=None) -> None:
	if not can_manage_tabs(space, user):
		frappe.throw(
			_("Only space editors can create or change tabs."),
			frappe.PermissionError,
		)


def _accessible_space_names(user=None) -> set:
	"""Spaces a user may read: open spaces (no role rows) plus restricted spaces
	with a role row whose role the user holds. Guests get only the latter."""
	user = user or frappe.session.user
	if _is_manager(user):
		return set(frappe.get_all("Wiki Space", pluck="name"))
	user_roles = set(frappe.get_roles(user))
	portal_only_spaces = set(frappe.get_all("Wiki Space", filters={"portal_only": 1}, pluck="name"))

	rows = frappe.get_all(
		"Wiki Space Role",
		filters={"parenttype": "Wiki Space"},
		fields=["parent", "role"],
	)
	restricted_spaces = {row.parent for row in rows}
	accessible_restricted = {
		row.parent for row in rows if row.role in user_roles and row.parent not in portal_only_spaces
	}

	if user == "Guest":
		published = (
			set(
				frappe.get_all(
					"Wiki Space",
					filters={"name": ("in", tuple(accessible_restricted)), "is_published": 1},
					pluck="name",
				)
			)
			if accessible_restricted
			else set()
		)
		return accessible_restricted & published

	all_spaces = set(frappe.get_all("Wiki Space", filters={"portal_only": 0}, pluck="name"))
	open_spaces = all_spaces - restricted_spaces
	return open_spaces | accessible_restricted


def get_readable_spaces(
	*,
	user=None,
	fields: list[str] | None = None,
	pluck: str | None = None,
	filters: dict | None = None,
	or_filters: dict | list | None = None,
	order_by: str | None = None,
) -> list:
	"""Fetch only spaces present in the central read-access set."""
	names = _accessible_space_names(user)
	if not names:
		return []

	query_filters = dict(filters or {})
	query_filters["name"] = ("in", tuple(names))
	kwargs = {"filters": query_filters, "limit": 0}
	if fields:
		kwargs["fields"] = fields
	if pluck:
		kwargs["pluck"] = pluck
	if or_filters:
		kwargs["or_filters"] = or_filters
	if order_by:
		kwargs["order_by"] = order_by
	return frappe.get_all("Wiki Space", **kwargs)


def _space_in_clause(table: str, user: str, allow_null: bool) -> str:
	"""Build a WHERE fragment restricting ``table`` to spaces the user can read."""
	names = _accessible_space_names(user)
	parts = []
	if allow_null:
		parts.append(f"`{table}`.`wiki_space` is null")
	if names:
		escaped = ", ".join(frappe.db.escape(name) for name in names)
		parts.append(f"`{table}`.`wiki_space` in ({escaped})")

	if not parts:
		return "1=0"
	if len(parts) == 1:
		return parts[0]
	return "(" + " or ".join(parts) + ")"


def _document_space_integrity_clause(table: str) -> str:
	"""Require the denormalized space to match the current nested-set tree."""
	return f"""
		exists (
			select 1
			from `tabWiki Space` `_wiki_scope`
			inner join `tabWiki Document` `_wiki_root`
				on `_wiki_root`.`name` = `_wiki_scope`.`root_group`
			where `_wiki_scope`.`name` = `{table}`.`wiki_space`
				and (
					`{table}`.`name` = `_wiki_scope`.`root_group`
					or (
						`{table}`.`lft` > `_wiki_root`.`lft`
						and `{table}`.`rgt` < `_wiki_root`.`rgt`
					)
				)
		)
	""".strip()


# ---------------------------------------------------------------------------
# Hook entry points
# ---------------------------------------------------------------------------


def wiki_space_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return ""

	names = _accessible_space_names(user)
	if not names:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(name) for name in names)
	return f"`tabWiki Space`.`name` in ({escaped})"


def wiki_space_has_permission(doc, ptype, user=None):
	user = user or frappe.session.user
	if ptype in WRITE_PTYPES:
		return can_write_space(doc, user)
	return can_read_space(doc, user)


def wiki_document_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return ""
	space_clause = _space_in_clause("tabWiki Document", user, allow_null=False)
	integrity_clause = _document_space_integrity_clause("tabWiki Document")
	if user == "Guest":
		return f"({space_clause}) and ({integrity_clause}) and `tabWiki Document`.`is_published` = 1"
	return f"({space_clause}) and ({integrity_clause})"


def wiki_document_has_permission(doc, ptype, user=None):
	user = user or frappe.session.user
	name = doc.get("name")
	is_new = not (name and frappe.db.exists("Wiki Document", name))
	if is_new:
		space = doc.wiki_space
	else:
		space = resolve_document_space(doc)
	if not space:
		# Managers retain Desk access so they can repair orphaned/mismatched rows;
		# public and API rendering still goes through assert_can_read_document.
		return _is_manager(user)

	if ptype in WRITE_PTYPES:
		# A git-synced space is read-only; only the sync engine (running under
		# in_apply_merge_revision) may write its documents.
		if not frappe.flags.in_apply_merge_revision and is_git_synced_space(space):
			return False
		return can_write_space(space, user)
	if is_new:
		if user == "Guest" and not doc.is_published:
			return False
		return can_read_space(space, user)
	return can_read_document(doc, user)


def wiki_cr_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return ""
	return _space_in_clause("tabWiki Change Request", user, allow_null=False)


def wiki_cr_has_permission(doc, ptype, user=None):
	user = user or frappe.session.user
	space = doc.wiki_space
	if not space:
		return _is_manager(user)

	# Reading a CR requires space Read. Editing/saving it (proposing changes)
	# additionally requires the space to accept contributions (Write-tier users
	# bypass that). Merging is gated separately by can_write_space in the CR
	# controller.
	if ptype in WRITE_PTYPES:
		return can_contribute_to_space(space, user)
	return can_read_space(space, user)
