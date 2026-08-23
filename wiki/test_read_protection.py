# Copyright (c) 2026, Frappe and Contributors
# See license.txt

"""Tenant-isolation regressions for reader-facing Wiki endpoints."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request import (
	create_change_request,
	diff_change_request,
	list_change_requests,
)
from wiki.frappe_wiki.doctype.wiki_document.search import _filter_hits_by_space_visibility
from wiki.frappe_wiki.doctype.wiki_document.wiki_document import (
	get_breadcrumbs,
	get_page_data,
)
from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import WikiSQLiteSearch
from wiki.wiki.doctype.wiki_page_revision.wiki_page_revision import get_revisions
from wiki.wiki.doctype.wiki_settings.wiki_settings import get_all_spaces

TENANT_A_ROLE = "_Test Wiki Tenant A"
TENANT_B_ROLE = "_Test Wiki Tenant B"


def _ensure_role(role_name: str) -> None:
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 0}).insert(
			ignore_permissions=True
		)


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Wiki tenant test",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)

	existing_roles = {row.role for row in user.roles}
	for required_role in ("Wiki User", role):
		if required_role not in existing_roles:
			user.add_roles(required_role)
	return email


class TestTenantReadProtection(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		for role in (TENANT_A_ROLE, TENANT_B_ROLE):
			_ensure_role(role)
		cls.tenant_a_user = _ensure_user("wiki_tenant_a@example.com", TENANT_A_ROLE)
		cls.tenant_b_user = _ensure_user("wiki_tenant_b@example.com", TENANT_B_ROLE)
		frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.token = frappe.generate_hash(length=8).lower()
		self.space_a = self._make_space("Kunde A", [(TENANT_A_ROLE, "Read")])
		self.space_b = self._make_space("Kunde B", [(TENANT_B_ROLE, "Read")])
		self.public_space = self._make_space("Public", [("Guest", "Read")])

		self.page_a = self._make_page(self.space_a, "Kunde A intern")
		self.page_b = self._make_page(self.space_b, "Kunde B intern")
		self.public_page = self._make_page(self.public_space, "Öffentliche Hilfe")
		self.unpublished_a = self._make_page(self.space_a, "Kunde A Entwurf", is_published=0)
		self.orphan = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": f"Orphan {self.token}",
				"route": f"orphan-{self.token}",
				"content": "orphan secret",
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		self.mismatched = self._make_page(self.space_b, "Falsch gestempelt")
		frappe.db.set_value(
			"Wiki Document",
			self.mismatched.name,
			"wiki_space",
			self.space_a.name,
			update_modified=False,
		)
		frappe.clear_document_cache("Wiki Document", self.mismatched.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		super().tearDown()

	def _make_space(self, label: str, roles: list[tuple[str, str]]):
		space = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": f"{label} {self.token}",
				"route": f"{frappe.scrub(label).replace('_', '-')}-{self.token}",
				"is_published": 1,
				"show_in_switcher": 1,
			}
		)
		for role, level in roles:
			space.append("roles", {"role": role, "permission_level": level})
		return space.insert(ignore_permissions=True)

	def _make_page(self, space, title: str, *, is_published: int = 1):
		return frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": f"{title} {self.token}",
				"parent_wiki_document": space.root_group,
				"wiki_space": space.name,
				"content": f"secret content for {title}",
				"is_published": is_published,
			}
		).insert(ignore_permissions=True)

	def _hit(self, document) -> dict:
		return {
			"name": document.name,
			"title": document.title,
			"route": document.route,
			"content": document.content,
			"score": 1.0,
		}

	def test_change_request_list_and_diff_are_tenant_scoped_and_guest_closed(self):
		frappe.set_user(self.tenant_a_user)
		cr_a = create_change_request(self.space_a.name, "Kunde A Änderung")
		frappe.set_user(self.tenant_b_user)
		cr_b = create_change_request(self.space_b.name, "Kunde B Änderung")

		frappe.set_user(self.tenant_a_user)
		self.assertIn(cr_a.name, {row.name for row in list_change_requests(self.space_a.name)})
		with self.assertRaises(frappe.DoesNotExistError):
			list_change_requests(self.space_b.name)
		with self.assertRaises(frappe.DoesNotExistError):
			diff_change_request(cr_b.name)

		frappe.set_user(self.tenant_b_user)
		self.assertIn(cr_b.name, {row.name for row in list_change_requests(self.space_b.name)})
		self.assertEqual(diff_change_request(cr_b.name), [])

		frappe.set_user("Guest")
		with self.assertRaises(frappe.DoesNotExistError):
			list_change_requests(self.public_space.name)
		with self.assertRaises(frappe.DoesNotExistError):
			diff_change_request(cr_a.name)

	def test_switcher_and_space_list_show_only_readable_spaces(self):
		frappe.set_user(self.tenant_a_user)
		routes = set(get_all_spaces())
		self.assertIn(self.space_a.route, routes)
		self.assertNotIn(self.space_b.route, routes)
		switcher_names = {row.name for row in self.page_a.get_web_context()["wiki_spaces_for_switcher"]}
		self.assertIn(self.space_a.name, switcher_names)
		self.assertNotIn(self.space_b.name, switcher_names)

		frappe.set_user("Guest")
		guest_routes = set(get_all_spaces())
		self.assertIn(self.public_space.route, guest_routes)
		self.assertNotIn(self.space_a.route, guest_routes)
		self.assertNotIn(self.space_b.route, guest_routes)
		public_context = get_page_data(self.public_page.route)
		guest_switcher_names = {row.name for row in public_context["wiki_spaces_for_switcher"]}
		self.assertIn(self.public_space.name, guest_switcher_names)
		self.assertNotIn(self.space_a.name, guest_switcher_names)
		self.assertNotIn(self.space_b.name, guest_switcher_names)

	def test_breadcrumbs_use_current_document_permission(self):
		frappe.set_user(self.tenant_a_user)
		self.assertEqual(get_breadcrumbs(self.page_a.name)["current"]["name"], self.page_a.name)
		with self.assertRaises(frappe.DoesNotExistError):
			get_breadcrumbs(self.page_b.name)

		frappe.set_user(self.tenant_b_user)
		with self.assertRaises(frappe.DoesNotExistError):
			get_breadcrumbs(self.page_a.name)

		frappe.set_user("Guest")
		self.assertEqual(
			get_breadcrumbs(self.public_page.name)["current"]["name"],
			self.public_page.name,
		)
		with self.assertRaises(frappe.DoesNotExistError):
			get_breadcrumbs(self.page_a.name)

	def test_orphan_and_mismatched_documents_fail_closed_for_all_tenants(self):
		for user in (self.tenant_a_user, self.tenant_b_user, "Guest"):
			frappe.set_user(user)
			with self.assertRaises(frappe.DoesNotExistError):
				self.orphan.get_web_context()
			with self.assertRaises(frappe.DoesNotExistError):
				self.mismatched.get_web_context()

		frappe.set_user(self.tenant_a_user)
		visible = set(
			frappe.get_list(
				"Wiki Document",
				filters={
					"name": (
						"in",
						[self.page_a.name, self.page_b.name, self.orphan.name, self.mismatched.name],
					)
				},
				pluck="name",
			)
		)
		self.assertIn(self.page_a.name, visible)
		self.assertNotIn(self.page_b.name, visible)
		self.assertNotIn(self.orphan.name, visible)
		self.assertNotIn(self.mismatched.name, visible)

	def test_search_revalidates_stale_and_ambiguous_hits(self):
		stale_hit = {
			"name": f"deleted-{self.token}",
			"title": "Deleted secret",
			"route": f"deleted-{self.token}",
			"content": "deleted secret",
			"score": 1.0,
		}
		hits = [
			self._hit(self.page_a),
			self._hit(self.page_b),
			self._hit(self.public_page),
			self._hit(self.unpublished_a),
			self._hit(self.orphan),
			self._hit(self.mismatched),
			stale_hit,
		]

		frappe.set_user(self.tenant_a_user)
		tenant_a_names = {row["name"] for row in _filter_hits_by_space_visibility(hits)}
		self.assertIn(self.page_a.name, tenant_a_names)
		self.assertNotIn(self.page_b.name, tenant_a_names)
		self.assertNotIn(self.unpublished_a.name, tenant_a_names)
		self.assertNotIn(self.orphan.name, tenant_a_names)
		self.assertNotIn(self.mismatched.name, tenant_a_names)
		self.assertNotIn(stale_hit["name"], tenant_a_names)

		frappe.set_user("Guest")
		guest_names = {row["name"] for row in _filter_hits_by_space_visibility(hits)}
		self.assertEqual(guest_names, {self.public_page.name})

		search_engine = WikiSQLiteSearch()
		for unsafe_document in (self.orphan, self.mismatched):
			index_document = unsafe_document.as_dict()
			index_document["published"] = index_document.get("is_published")
			self.assertIsNone(search_engine.prepare_document(index_document))

	def test_legacy_revisions_require_authenticated_current_document_access(self):
		legacy_page = frappe.get_doc(
			{
				"doctype": "Wiki Page",
				"title": f"Legacy Kunde B {self.token}",
				"route": self.page_b.route,
				"content": "legacy tenant B secret",
				"published": 1,
				"allow_guest": 1,
			}
		)
		legacy_page.db_insert()

		with patch(
			"wiki.wiki.doctype.wiki_page_revision.wiki_page_revision._get_legacy_revision_rows"
		) as revision_query:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.DoesNotExistError):
				get_revisions(legacy_page.name)
			revision_query.assert_not_called()

			frappe.set_user(self.tenant_a_user)
			with self.assertRaises(frappe.DoesNotExistError):
				get_revisions(legacy_page.name)
			revision_query.assert_not_called()

			revision_query.return_value = [
				frappe._dict(
					content="Legacy authorized content",
					creation=now_datetime(),
					owner=self.tenant_b_user,
					raised_by=None,
					raised_by_username=None,
				)
			]
			frappe.set_user(self.tenant_b_user)
			revisions = get_revisions(legacy_page.name)
			self.assertEqual(len(revisions), 1)
			self.assertIn("Legacy authorized content", revisions[0].content)
			revision_query.assert_called_once_with(legacy_page.name)
