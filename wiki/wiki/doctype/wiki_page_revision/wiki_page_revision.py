# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import md_to_html, pretty_date


class WikiPageRevision(Document):
	pass


def _get_legacy_revision_rows(wiki_page_name):
	return frappe.db.get_all(
		"Wiki Page Revision",
		{"wiki_page": wiki_page_name},
		["content", "creation", "owner", "raised_by", "raised_by_username"],
	)


@frappe.whitelist()
def get_revisions(wiki_page_name):
	# This is a legacy table without tenant scope. Anonymous access is disabled,
	# and authenticated reads are authorized through the one current Wiki
	# Document with the same route. Missing or ambiguous migrations fail closed.
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Page not found"), frappe.DoesNotExistError)

	legacy_route = frappe.db.get_value("Wiki Page", wiki_page_name, "route")
	current_documents = (
		frappe.get_all(
			"Wiki Document",
			filters={
				"route": legacy_route,
				"is_group": 0,
				"is_external_link": 0,
			},
			pluck="name",
			limit=2,
		)
		if legacy_route
		else []
	)
	if len(current_documents) != 1:
		frappe.throw(frappe._("Page not found"), frappe.DoesNotExistError)

	from wiki.permissions import assert_can_read_document

	assert_can_read_document(current_documents[0])
	revisions = _get_legacy_revision_rows(wiki_page_name)

	for revision in revisions:
		revision.revision_time = pretty_date(revision.creation)
		revision.author = revision.raised_by_username or revision.raised_by or revision.owner
		revision.content = md_to_html(revision.content)
		del revision.raised_by_username
		del revision.raised_by
		del revision.creation
		del revision.owner

	return revisions
