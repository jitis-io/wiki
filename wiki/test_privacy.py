# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from pathlib import Path

import frappe
from frappe.core.doctype.file.file import has_permission as has_file_permission
from frappe.tests import IntegrationTestCase

from wiki.privacy import ensure_wiki_attachments_private


class TestWikiAttachmentPrivacy(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		token = frappe.generate_hash(length=8).lower()
		self.space = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": f"Private files {token}",
				"route": f"private-files-{token}",
			}
		).insert(ignore_permissions=True)
		self.document = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": f"Private file page {token}",
				"parent_wiki_document": self.space.root_group,
				"wiki_space": self.space.name,
				"content": "Private file test.",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def _file(self, content: bytes, file_name: str, *, is_private: int = 0):
		return frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_name,
				"content": content,
				"is_private": is_private,
				"attached_to_doctype": "User",
				"attached_to_name": "Administrator",
			}
		).insert(ignore_permissions=True)

	def _legacy_wiki_file(self, content: bytes, file_name: str):
		file_doc = self._file(content, file_name)
		frappe.db.set_value(
			"File",
			file_doc.name,
			{
				"attached_to_doctype": "Wiki Document",
				"attached_to_name": self.document.name,
				"attached_to_field": None,
			},
			update_modified=False,
		)
		file_doc.reload()
		return file_doc

	def test_shared_public_hash_does_not_change_unrelated_file(self):
		content = b"same bytes in ERP and Wiki"
		erp_file = self._file(content, "erp-public.txt")
		wiki_file = self._legacy_wiki_file(content, "wiki-public.txt")
		self.assertEqual(wiki_file.file_url, erp_file.file_url)
		self.assertEqual(wiki_file.content_hash, erp_file.content_hash)
		frappe.db.set_value(
			"Wiki Document",
			self.document.name,
			"content",
			f"Customer attachment: {wiki_file.file_url}",
			update_modified=False,
		)

		result = ensure_wiki_attachments_private()

		wiki_file.reload()
		erp_file.reload()
		self.document.reload()
		self.assertEqual(result, {"moved": 1, "cloned": 0, "updated": 1})
		self.assertEqual(erp_file.is_private, 0)
		self.assertTrue(erp_file.file_url.startswith("/files/"))
		self.assertEqual(Path(erp_file.get_full_path()).read_bytes(), content)
		self.assertEqual(wiki_file.is_private, 1)
		self.assertTrue(wiki_file.file_url.startswith("/private/files/"))
		self.assertNotEqual(wiki_file.file_url, erp_file.file_url)
		self.assertEqual(Path(wiki_file.get_full_path()).read_bytes(), content)
		self.assertEqual(self.document.content, f"Customer attachment: {wiki_file.file_url}")
		self.assertEqual(frappe.db.count("File", {"file_url": wiki_file.file_url}), 1)
		self.assertEqual(
			ensure_wiki_attachments_private(),
			{"moved": 0, "cloned": 0, "updated": 0},
		)

	def test_public_reference_owned_elsewhere_is_cloned(self):
		content = b"public source retained for its original owner"
		source = self._file(content, "shared-source.txt")
		frappe.db.set_value(
			"Wiki Document",
			self.document.name,
			"content",
			f"![customer diagram]({source.file_url})\nExternal: https://docs.example.invalid{source.file_url}",
			update_modified=False,
		)

		result = ensure_wiki_attachments_private()

		source.reload()
		self.document.reload()
		clones = frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Wiki Document",
				"attached_to_name": self.document.name,
				"is_private": 1,
			},
			fields=["name", "file_url"],
		)
		self.assertEqual(result, {"moved": 0, "cloned": 1, "updated": 1})
		self.assertEqual(len(clones), 1)
		self.assertEqual(source.is_private, 0)
		self.assertTrue(source.file_url.startswith("/files/"))
		self.assertIn(clones[0].file_url, self.document.content)
		self.assertNotIn(f"]({source.file_url})", self.document.content)
		self.assertIn(f"https://docs.example.invalid{source.file_url}", self.document.content)
		clone = frappe.get_doc("File", clones[0].name)
		self.assertEqual(Path(clone.get_full_path()).read_bytes(), content)

	def test_missing_source_blocks_before_valid_file_changes(self):
		valid = self._legacy_wiki_file(b"valid legacy Wiki file", "valid-wiki.txt")
		missing_content = b"missing public source"
		missing = self._file(missing_content, "missing-source.txt")
		frappe.db.set_value(
			"Wiki Document",
			self.document.name,
			"content",
			f"{valid.file_url}\n{missing.file_url}",
			update_modified=False,
		)
		missing_path = Path(missing.get_full_path())
		missing_path.unlink()

		try:
			with self.assertRaises(frappe.ValidationError):
				ensure_wiki_attachments_private()
		finally:
			missing_path.write_bytes(missing_content)

		valid.reload()
		self.document.reload()
		self.assertEqual(valid.is_private, 0)
		self.assertTrue(valid.file_url.startswith("/files/"))
		self.assertEqual(self.document.content, f"{valid.file_url}\n{missing.file_url}")

	def test_new_wiki_upload_is_private_and_url_is_unique(self):
		content = b"same private bytes, separate owners"
		unrelated = self._file(content, "unrelated-private.txt", is_private=1)
		wiki_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "wiki-private.txt",
				"content": content,
				"is_private": 0,
				"attached_to_doctype": "Wiki Document",
				"attached_to_name": self.document.name,
			}
		).insert(ignore_permissions=True)

		unrelated.reload()
		self.assertEqual(wiki_file.is_private, 1)
		self.assertTrue(wiki_file.file_url.startswith("/private/files/"))
		self.assertNotEqual(wiki_file.file_url, unrelated.file_url)
		self.assertEqual(frappe.db.count("File", {"file_url": wiki_file.file_url}), 1)
		self.assertEqual(Path(wiki_file.get_full_path()).read_bytes(), content)
		self.assertEqual(Path(unrelated.get_full_path()).read_bytes(), content)

	def test_existing_public_file_reattached_to_wiki_is_isolated(self):
		content = b"same public bytes, existing File is reattached"
		unrelated = self._file(content, "unrelated-public.txt")
		wiki_file = self._file(content, "reattached-public.txt")
		self.assertEqual(wiki_file.file_url, unrelated.file_url)

		wiki_file.attached_to_doctype = "Wiki Document"
		wiki_file.attached_to_name = self.document.name
		wiki_file.save(ignore_permissions=True)

		unrelated.reload()
		wiki_file.reload()
		self.assertEqual(unrelated.is_private, 0)
		self.assertTrue(unrelated.file_url.startswith("/files/"))
		self.assertEqual(Path(unrelated.get_full_path()).read_bytes(), content)
		self.assertEqual(wiki_file.is_private, 1)
		self.assertTrue(wiki_file.file_url.startswith("/private/files/"))
		self.assertNotEqual(wiki_file.file_url, unrelated.file_url)
		self.assertEqual(Path(wiki_file.get_full_path()).read_bytes(), content)

	def test_private_file_access_follows_restricted_space_role(self):
		token = frappe.generate_hash(length=8).lower()
		role_name = f"_Test Wiki File Reader {token}"
		frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 0}).insert(
			ignore_permissions=True
		)
		reader = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"wiki-file-reader-{token}@example.com",
				"first_name": "Wiki file reader",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		reader.add_roles(role_name)
		self.space.reload()
		self.space.append("roles", {"role": role_name, "permission_level": "Read"})
		self.space.save(ignore_permissions=True)

		wiki_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "role-protected.txt",
				"content": b"role protected Wiki attachment",
				"is_private": 1,
				"attached_to_doctype": "Wiki Document",
				"attached_to_name": self.document.name,
			}
		).insert(ignore_permissions=True)

		self.assertTrue(has_file_permission(wiki_file, "read", user=reader.name))
		self.assertFalse(has_file_permission(wiki_file, "read", user="Guest"))

	def test_guest_private_file_access_requires_published_document_and_public_space(self):
		self.space.reload()
		self.space.is_published = 1
		self.space.append("roles", {"role": "Guest", "permission_level": "Read"})
		self.space.save(ignore_permissions=True)
		wiki_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "public-page-private-asset.txt",
				"content": b"private storage with explicit public read",
				"is_private": 1,
				"attached_to_doctype": "Wiki Document",
				"attached_to_name": self.document.name,
			}
		).insert(ignore_permissions=True)

		self.assertFalse(has_file_permission(wiki_file, "read", user="Guest"))
		frappe.db.set_value("Wiki Document", self.document.name, "is_published", 1)
		self.assertTrue(has_file_permission(wiki_file, "read", user="Guest"))
		frappe.db.set_value("Wiki Space", self.space.name, "is_published", 0)
		frappe.clear_document_cache("Wiki Space", self.space.name)
		self.assertFalse(has_file_permission(wiki_file, "read", user="Guest"))

	def test_guest_private_space_asset_requires_public_space(self):
		self.space.reload()
		self.space.is_published = 1
		self.space.append("roles", {"role": "Guest", "permission_level": "Read"})
		self.space.save(ignore_permissions=True)
		wiki_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "public-space-private-asset.txt",
				"content": b"private storage attached to a public Wiki Space",
				"is_private": 1,
				"attached_to_doctype": "Wiki Space",
				"attached_to_name": self.space.name,
			}
		).insert(ignore_permissions=True)

		self.assertTrue(has_file_permission(wiki_file, "read", user="Guest"))
		frappe.db.set_value("Wiki Space", self.space.name, "is_published", 0)
		frappe.clear_document_cache("Wiki Space", self.space.name)
		self.assertFalse(has_file_permission(wiki_file, "read", user="Guest"))
