import frappe

VISIBLE_ROLES = ("Wiki Manager", "Wiki User", "System Manager")


def ensure_wiki_desktop_visibility() -> None:
	"""Keep the Wiki app visible to every Desk user who has a Wiki role."""
	if frappe.db.exists("Desktop Icon", "Wiki"):
		icon = frappe.get_doc("Desktop Icon", "Wiki")
		icon.hidden = 0
		icon.set("roles", [{"role": role} for role in VISIBLE_ROLES])
		icon.save(ignore_permissions=True)

	if frappe.db.exists("Workspace", "Wiki"):
		frappe.db.set_value(
			"Workspace",
			"Wiki",
			{"public": 1, "is_hidden": 0, "module": "Wiki"},
			update_modified=False,
		)

	frappe.clear_cache()
