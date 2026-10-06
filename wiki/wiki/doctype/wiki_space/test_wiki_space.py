# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.core.doctype.file.file import has_permission as has_file_permission
from frappe.tests.utils import FrappeTestCase
from frappe.utils.nestedset import get_descendants_of
from pypdf import PdfWriter

from wiki import privacy
from wiki.tests.factory import WikiFixtureMixin
from wiki.wiki.doctype.wiki_space.patches.v3 import (
	migrate_orphan_pages_to_wiki_document,
	migrate_to_new_tree_document_structure,
)
from wiki.wiki.doctype.wiki_space.wiki_space import clone_wiki_space


class TestWikiSpaceClone(WikiFixtureMixin, FrappeTestCase):
	TEST_SITE = "wiki.localhost"

	def setUp(self):
		frappe.set_user("Administrator")
		self.space = self.wiki.track_space(
			frappe.get_doc(
				{
					"doctype": "Wiki Space",
					"space_name": f"Clone Source {frappe.generate_hash(length=6)}",
					"route": f"source-space-{frappe.generate_hash(length=6)}",
				}
			).insert()
		)
		self.group_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": "Group A",
				"is_group": 1,
				"parent_wiki_document": self.space.root_group,
			}
		).insert()  # inside the space, so its cascade takes this

		self.page_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": "Page A",
				"parent_wiki_document": self.group_doc.name,
				"content": "Hello from the source space.",
			}
		).insert()

	def test_clone_wiki_space_copies_tree_and_routes(self):
		new_route = f"clone-space-{frappe.generate_hash(length=6)}"
		new_space_name = clone_wiki_space(self.space.name, new_route)
		self.wiki.track_space(new_space_name)
		new_space = frappe.get_doc("Wiki Space", new_space_name)

		self.assertEqual(new_space.route, new_route)
		self.assertNotEqual(new_space.root_group, self.space.root_group)

		new_root = frappe.get_doc("Wiki Document", new_space.root_group)
		self.assertEqual(new_root.route, new_route)

		root_lft, root_rgt = frappe.get_value("Wiki Document", self.space.root_group, ["lft", "rgt"])
		new_root_lft, new_root_rgt = frappe.get_value("Wiki Document", new_space.root_group, ["lft", "rgt"])

		original_docs = frappe.get_all(
			"Wiki Document",
			filters={"lft": (">=", root_lft), "rgt": ("<=", root_rgt)},
			fields=["name"],
		)
		new_docs = frappe.get_all(
			"Wiki Document",
			filters={"lft": (">=", new_root_lft), "rgt": ("<=", new_root_rgt)},
			fields=["name"],
		)
		self.assertEqual(len(original_docs), len(new_docs))

		new_group = frappe.get_all(
			"Wiki Document",
			filters={
				"lft": (">=", new_root.lft),
				"rgt": ("<=", new_root.rgt),
				"title": self.group_doc.title,
				"is_group": 1,
			},
			fields=["name", "slug", "route"],
		)[0]
		new_page = frappe.get_all(
			"Wiki Document",
			filters={
				"lft": (">=", new_root.lft),
				"rgt": ("<=", new_root.rgt),
				"title": self.page_doc.title,
				"is_group": 0,
			},
			fields=["name", "slug", "route", "content", "parent_wiki_document"],
		)[0]

		expected_route = f"{new_route}/{new_group['slug']}/{new_page['slug']}"
		self.assertEqual(new_page["route"], expected_route)
		self.assertEqual(new_page["content"], self.page_doc.content)
		self.assertEqual(new_page["parent_wiki_document"], new_group["name"])

	def _attachment(self, owner, content: bytes, file_name: str, fieldname=None):
		return self.wiki.track(
			"File",
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": file_name,
					"content": content,
					"is_private": 1,
					"attached_to_doctype": owner.doctype,
					"attached_to_name": owner.name,
					"attached_to_field": fieldname,
				}
			).insert(ignore_permissions=True),
		)

	def _clone(self):
		name = clone_wiki_space(self.space.name, f"clone-assets-{frappe.generate_hash(length=8)}")
		self.wiki.track_space(name)
		space = frappe.get_doc("Wiki Space", name)
		page = frappe.get_doc(
			"Wiki Document",
			frappe.db.get_value(
				"Wiki Document",
				{
					"wiki_space": space.name,
					"title": self.page_doc.title,
				},
			),
		)
		return space, page

	def test_clone_private_files_rewrites_content_meta_image_and_space_logos(self):
		image = self._attachment(self.page_doc, b"<svg xmlns='http://www.w3.org/2000/svg'/>", "diagram.svg")
		stream = BytesIO()
		writer = PdfWriter()
		writer.add_blank_page(width=72, height=72)
		writer.write(stream)
		pdf = self._attachment(self.page_doc, stream.getvalue(), "manual.pdf")
		logo = self._attachment(self.space, b"<svg><title>Space logo</title></svg>", "logo.svg")
		self.page_doc.content = (
			f'<img src="{image.file_url}">[Manual]({pdf.file_url}?download=1)\n{image.file_url}'
		)
		self.page_doc.meta_image = image.file_url
		self.page_doc.save()
		for fieldname in ("light_mode_logo", "dark_mode_logo", "app_switcher_logo", "favicon"):
			self.space.set(fieldname, logo.file_url)
		self.space.save()

		space, page = self._clone()
		for source, owner in ((image, page), (pdf, page), (logo, space)):
			copies = frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": owner.doctype,
					"attached_to_name": owner.name,
					"content_hash": source.content_hash,
				},
				fields=["name", "file_url", "is_private"],
			)
			self.assertEqual(len(copies), 1)
			copy = frappe.get_doc("File", copies[0].name)
			self.assertEqual(copy.is_private, 1)
			self.assertNotEqual(copy.file_url, source.file_url)
			self.assertEqual(
				Path(copy.get_full_path()).read_bytes(), Path(source.get_full_path()).read_bytes()
			)
			self.assertEqual(frappe.db.count("File", {"file_url": copy.file_url}), 1)
			if owner.doctype == "Wiki Document":
				self.assertIn(copy.file_url, page.content)
				self.assertNotIn(source.file_url, page.content)
			else:
				self.assertEqual(space.light_mode_logo, copy.file_url)
				self.assertEqual(space.dark_mode_logo, copy.file_url)
				self.assertEqual(space.app_switcher_logo, copy.file_url)
				self.assertEqual(space.favicon, copy.file_url)
		self.assertNotEqual(page.meta_image, image.file_url)
		self.assertIn(page.meta_image, page.content)
		self.assertIn("?download=1", page.content)
		self.page_doc.reload()
		self.assertIn(image.file_url, self.page_doc.content)

	def test_clone_keeps_external_urls_and_copies_unreferenced_owned_files(self):
		source = self._attachment(self.page_doc, b"Owned attachment", "owned.txt")
		self.page_doc.content = f"External: https://docs.example.invalid{source.file_url}"
		self.page_doc.save()
		space, page = self._clone()
		self.assertEqual(page.content, self.page_doc.content)
		copy = frappe.get_doc(
			"File",
			frappe.db.get_value(
				"File",
				{
					"attached_to_doctype": "Wiki Document",
					"attached_to_name": page.name,
				},
			),
		)
		self.assertNotEqual(copy.file_url, source.file_url)
		self.assertEqual(Path(copy.get_full_path()).read_bytes(), b"Owned attachment")

	def _assert_clone_rejected_before_creation(self):
		route = f"rejected-clone-{frappe.generate_hash(length=8)}"
		files = set(frappe.get_all("File", pluck="name"))
		with self.assertRaises(frappe.ValidationError):
			clone_wiki_space(self.space.name, route)
		self.assertFalse(frappe.db.exists("Wiki Space", {"route": route}))
		self.assertEqual(set(frappe.get_all("File", pluck="name")), files)

	def test_clone_rejects_foreign_private_file_references(self):
		foreign = self.wiki.space(pages=[{"title": "Foreign private page"}])
		file = self._attachment(foreign, b"Foreign customer document", "foreign.txt")
		self.page_doc.content = f"[Foreign document]({file.file_url})"
		self.page_doc.save()
		self._assert_clone_rejected_before_creation()
		self.assertEqual(Path(file.get_full_path()).read_bytes(), b"Foreign customer document")

	def test_clone_rejects_foreign_space_logo(self):
		foreign = self.wiki.space()
		file = self._attachment(foreign, b"Foreign logo", "foreign-logo.txt")
		self.space.light_mode_logo = file.file_url
		self.space.save()
		self._assert_clone_rejected_before_creation()

	def test_clone_rejects_unknown_private_file_references(self):
		self.page_doc.content = "[Missing document](/private/files/no-owned-file.pdf)"
		self.page_doc.save()
		self._assert_clone_rejected_before_creation()

	def test_clone_rejects_missing_source_file(self):
		file = self._attachment(self.page_doc, b"Missing file", "missing.txt")
		path = Path(file.get_full_path())
		path.unlink()
		try:
			self._assert_clone_rejected_before_creation()
		finally:
			path.write_bytes(b"Missing file")

	def test_clone_rejects_source_content_hash_mismatch(self):
		file = self._attachment(self.page_doc, b"Original bytes", "changed.txt")
		path = Path(file.get_full_path())
		path.write_bytes(b"Different bytes")
		try:
			self._assert_clone_rejected_before_creation()
		finally:
			path.write_bytes(b"Original bytes")

	def test_clone_rejects_stale_foreign_space_stamp(self):
		foreign = self.wiki.space()
		frappe.db.set_value("Wiki Document", self.page_doc.name, "wiki_space", foreign.name)
		self._assert_clone_rejected_before_creation()

	def test_failed_clone_rollback_removes_new_file_bytes_and_keeps_source(self):
		one = self._attachment(self.page_doc, b"Source one", "source-one.txt")
		two = self._attachment(self.space, b"Source two", "source-two.txt")
		frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit
		root = Path(frappe.get_site_path("private", "files"))
		before = set(root.iterdir())
		copy = privacy._copy_to_private
		calls = 0

		def fail_later(source, target):
			nonlocal calls
			calls += 1
			if calls == 2:
				raise OSError("Synthetic later file-copy failure")
			copy(source, target)

		route = f"rollback-clone-{frappe.generate_hash(length=8)}"
		with patch("wiki.privacy._copy_to_private", side_effect=fail_later):
			with self.assertRaises(OSError):
				clone_wiki_space(self.space.name, route)
		frappe.db.rollback()
		self.assertFalse(frappe.db.exists("Wiki Space", {"route": route}))
		self.assertEqual(set(root.iterdir()), before)
		self.assertEqual(Path(one.get_full_path()).read_bytes(), b"Source one")
		self.assertEqual(Path(two.get_full_path()).read_bytes(), b"Source two")

		route = f"partial-write-clone-{frappe.generate_hash(length=8)}"
		with patch("wiki.privacy.os.fsync", side_effect=OSError("Synthetic file flush failure")):
			with self.assertRaises(OSError):
				clone_wiki_space(self.space.name, route)
		frappe.db.rollback()
		self.assertFalse(frappe.db.exists("Wiki Space", {"route": route}))
		self.assertEqual(set(root.iterdir()), before)
		self.assertEqual(Path(one.get_full_path()).read_bytes(), b"Source one")
		self.assertEqual(Path(two.get_full_path()).read_bytes(), b"Source two")

	def test_clone_rejects_ambiguous_private_file_owner(self):
		source = self._attachment(self.page_doc, b"Ambiguous source", "ambiguous.txt")
		foreign = self.wiki.space()
		alias = self._attachment(foreign, b"Other bytes", "alias.txt")
		frappe.db.set_value("File", alias.name, "file_url", source.file_url, update_modified=False)
		self._assert_clone_rejected_before_creation()

	def test_clone_private_files_keep_both_space_permission_boundaries(self):
		users = []
		roles = []
		for index in range(2):
			token = frappe.generate_hash(length=8)
			role = self.wiki.track(
				"Role", frappe.get_doc({"doctype": "Role", "role_name": f"Clone Reader {token}"}).insert()
			)
			user = self.wiki.track(
				"User",
				frappe.get_doc(
					{
						"doctype": "User",
						"email": f"clone-reader-{token}@example.invalid",
						"first_name": f"Clone Reader {index}",
						"send_welcome_email": 0,
					}
				).insert(),
			)
			user.add_roles(role.name)
			users.append(user.name)
			roles.append(role.name)
		self.space.append("roles", {"role": roles[0], "permission_level": "Read"})
		self.space.save()
		source = self._attachment(self.page_doc, b"Space-scoped bytes", "scope.txt")
		self.page_doc.content = source.file_url
		self.page_doc.save()
		space, page = self._clone()
		space.set("roles", [{"role": roles[1], "permission_level": "Read"}])
		space.save()
		copy = frappe.get_doc(
			"File",
			frappe.db.get_value(
				"File",
				{
					"attached_to_doctype": "Wiki Document",
					"attached_to_name": page.name,
				},
			),
		)
		self.assertTrue(has_file_permission(source, "read", user=users[0]))
		self.assertFalse(has_file_permission(source, "read", user=users[1]))
		self.assertTrue(has_file_permission(copy, "read", user=users[1]))
		self.assertFalse(has_file_permission(copy, "read", user=users[0]))
		self.assertFalse(has_file_permission(copy, "read", user="Guest"))

	def tearDown(self):
		frappe.db.rollback()


class TestWikiSpaceMigration(WikiFixtureMixin, FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def create_legacy_wiki_page(self, route: str, title: str, content: str, published=1, allow_guest=1):
		page = frappe.get_doc(
			{
				"doctype": "Wiki Page",
				"title": title,
				"route": route,
				"content": content,
				"published": published,
				"allow_guest": allow_guest,
			}
		)
		page.db_insert()
		self.wiki.track("Wiki Page", page)
		return page

	def create_legacy_space(self, route: str, sidebar_rows: list[dict]):
		space = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": f"Legacy Space {frappe.generate_hash(length=6)}",
				"route": route,
			}
		)
		for row in sidebar_rows:
			space.append("wiki_sidebars", row)
		return self.wiki.track_space(space.insert())

	def test_migrate_to_v3_is_idempotent_and_resumable(self):
		page_one = self.create_legacy_wiki_page(
			route=f"legacy-page-{frappe.generate_hash(length=6)}",
			title="Legacy Page One",
			content="Page one content",
		)
		page_two = self.create_legacy_wiki_page(
			route=f"legacy-page-{frappe.generate_hash(length=6)}",
			title="Legacy Page Two",
			content="Page two content",
			allow_guest=0,
		)
		space = self.create_legacy_space(
			route=f"space-{frappe.generate_hash(length=6)}",
			sidebar_rows=[
				{"wiki_page": page_one.name, "parent_label": "Getting Started"},
				{"wiki_page": page_two.name, "parent_label": "Getting Started"},
			],
		)

		self.assertEqual(get_descendants_of("Wiki Document", space.root_group, ignore_permissions=True), [])

		space.migrate_to_v3()
		space.reload()

		first_descendants = get_descendants_of("Wiki Document", space.root_group, ignore_permissions=True)
		self.assertEqual(len(first_descendants), 3)

		group_name = frappe.db.get_value(
			"Wiki Document",
			{
				"parent_wiki_document": space.root_group,
				"is_group": 1,
				"route": f"{space.route}/getting-started",
			},
			"name",
		)
		self.assertTrue(group_name)

		page_one_doc = frappe.get_doc(
			"Wiki Document",
			frappe.db.get_value("Wiki Document", {"route": page_one.route, "is_group": 0}, "name"),
		)
		page_two_doc = frappe.get_doc(
			"Wiki Document",
			frappe.db.get_value("Wiki Document", {"route": page_two.route, "is_group": 0}, "name"),
		)
		self.assertEqual(page_one_doc.parent_wiki_document, group_name)
		self.assertEqual(page_one_doc.sort_order, 0)
		self.assertEqual(page_two_doc.parent_wiki_document, group_name)
		self.assertEqual(page_two_doc.sort_order, 1)

		space.migrate_to_v3()
		second_descendants = get_descendants_of("Wiki Document", space.root_group, ignore_permissions=True)

		self.assertEqual(first_descendants, second_descendants)
		self.assertEqual(
			frappe.db.count("Wiki Document", {"route": page_one.route, "is_group": 0}),
			1,
		)
		self.assertEqual(
			frappe.db.count("Wiki Document", {"route": f"{space.route}/getting-started", "is_group": 1}),
			1,
		)

	def test_migrate_to_v3_repairs_partial_migration(self):
		page_one = self.create_legacy_wiki_page(
			route=f"partial-page-{frappe.generate_hash(length=6)}",
			title="Partial Page One",
			content="Fresh content",
		)
		page_two = self.create_legacy_wiki_page(
			route=f"partial-page-{frappe.generate_hash(length=6)}",
			title="Partial Page Two",
			content="Second content",
		)
		space = self.create_legacy_space(
			route=f"partial-space-{frappe.generate_hash(length=6)}",
			sidebar_rows=[
				{"wiki_page": page_one.name, "parent_label": "Docs"},
				{"wiki_page": page_two.name, "parent_label": "Docs"},
			],
		)

		group_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": "Docs",
				"route": f"{space.route}/docs",
				"is_group": 1,
				"is_published": 1,
				"parent_wiki_document": space.root_group,
				"sort_order": 0,
			}
		).insert()
		stale_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": "Stale Title",
				"route": page_one.route,
				"is_group": 0,
				"is_published": 0,
				"content": "stale",
				"parent_wiki_document": group_doc.name,
				"sort_order": 99,
			}
		).insert()

		space.migrate_to_v3()

		stale_doc.reload()
		self.assertEqual(stale_doc.title, page_one.title)
		self.assertEqual(stale_doc.content, page_one.content)
		self.assertEqual(stale_doc.is_published, page_one.published)
		self.assertEqual(stale_doc.sort_order, 0)

		page_two_name = frappe.db.get_value("Wiki Document", {"route": page_two.route, "is_group": 0}, "name")
		self.assertTrue(page_two_name)
		self.assertEqual(frappe.db.count("Wiki Document", {"parent_wiki_document": group_doc.name}), 2)

	def test_v3_patch_migrates_spaces_even_when_root_group_exists(self):
		page = self.create_legacy_wiki_page(
			route=f"patch-page-{frappe.generate_hash(length=6)}",
			title="Patch Page",
			content="Patch content",
		)
		space = self.create_legacy_space(
			route=f"patch-space-{frappe.generate_hash(length=6)}",
			sidebar_rows=[{"wiki_page": page.name, "parent_label": "Guides"}],
		)

		self.assertTrue(space.root_group)
		self.assertEqual(get_descendants_of("Wiki Document", space.root_group, ignore_permissions=True), [])

		before = self.wiki.snapshot_documents()
		migrate_to_new_tree_document_structure.execute()
		self.wiki.track_new(before)

		self.assertEqual(
			frappe.db.count("Wiki Document", {"route": page.route, "is_group": 0}),
			1,
		)
		self.assertEqual(
			frappe.db.count("Wiki Document", {"route": f"{space.route}/guides", "is_group": 1}),
			1,
		)

	def test_orphan_patch_upserts_existing_documents(self):
		page = self.create_legacy_wiki_page(
			route=f"orphan-page-{frappe.generate_hash(length=6)}",
			title="Orphan Page",
			content="Canonical content",
			allow_guest=0,
		)
		existing_doc = self.wiki.track_document(
			frappe.get_doc(
				{
					"doctype": "Wiki Document",
					"title": "Old Title",
					"route": page.route,
					"is_group": 0,
					"is_published": 0,
					"content": "old content",
				}
			).insert()
		)

		before = self.wiki.snapshot_documents()
		migrate_orphan_pages_to_wiki_document.execute()
		self.wiki.track_new(before)

		existing_doc.reload()
		self.assertEqual(existing_doc.title, page.title)
		self.assertEqual(existing_doc.content, page.content)
		self.assertEqual(existing_doc.is_published, page.published)
		self.assertEqual(frappe.db.count("Wiki Document", {"route": page.route, "is_group": 0}), 1)

	def tearDown(self):
		frappe.db.rollback()
