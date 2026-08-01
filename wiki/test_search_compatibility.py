# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import (
	WikiSQLiteSearch,
	enqueue_reindex,
)


class TestFrappe1629SearchCompatibility(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		token = frappe.generate_hash(length=8).lower()
		self.space = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": f"Search compatibility {token}",
				"route": f"search-compatibility-{token}",
			}
		).insert(ignore_permissions=True)
		self.document = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": f"Search compatibility {token}",
				"parent_wiki_document": self.space.root_group,
				"wiki_space": self.space.name,
				"content": "staletermv1zzz",
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		self.search = WikiSQLiteSearch()

	def tearDown(self):
		self.search.drop_index()
		frappe.db.rollback()
		super().tearDown()

	def test_index_doc_updates_existing_entry_on_frappe_16_29(self):
		self.search.drop_index()
		self.search.build_index()
		self.assertIn(
			self.document.name,
			{row["name"] for row in self.search.search("staletermv1zzz")["results"]},
		)

		frappe.db.set_value("Wiki Document", self.document.name, "content", "freshtermv2zzz")
		enqueue_reindex([self.document.name])

		self.assertNotIn(
			self.document.name,
			{row["name"] for row in self.search.search("staletermv1zzz")["results"]},
		)
		self.assertIn(
			self.document.name,
			{row["name"] for row in self.search.search("freshtermv2zzz")["results"]},
		)
