import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_COMMITS = {
	"FRAPPE_COMMIT": "06613fc60b44d5736007ae3107cdab029b2ae045",
	"ERPNEXT_COMMIT": "8378b6e203841c056925420cc44e6d631c915cf1",
}


class CiContractTests(unittest.TestCase):
	def setUp(self):
		self.integration = (ROOT / "ci" / "run-integration.sh").read_text(encoding="utf-8")

	def test_framework_dependencies_are_exact_sha1_pins(self):
		found = dict(
			re.findall(r'^readonly ([A-Z]+_COMMIT)="([0-9a-f]{40})"$', self.integration, re.MULTILINE)
		)
		self.assertEqual(found, EXPECTED_COMMITS)

	def test_release_tags_and_resolved_commits_are_verified(self):
		self.assertIn("--frappe-branch v16.29.0", self.integration)
		self.assertIn('test "$(git -C apps/frappe rev-parse HEAD)" = "$FRAPPE_COMMIT"', self.integration)
		self.assertIn("bench get-app --branch v16.30.0 --skip-assets erpnext", self.integration)
		self.assertIn('test "$(git -C apps/erpnext rev-parse HEAD)" = "$ERPNEXT_COMMIT"', self.integration)

	def test_exact_private_tree_is_installed_and_fully_tested(self):
		commands = [
			'bench get-app --skip-assets wiki "$APP_DIR"',
			"--install-app erpnext",
			"install-app wiki",
			"migrate",
			"build --app wiki",
			"run-tests --app wiki --module wiki.test_privacy",
			"run-tests --app wiki --module wiki.test_permissions",
			"run-tests --app wiki --module wiki.test_search_compatibility",
			'"$WIKI_ONLY_SITE_NAME"',
			"run-tests --app wiki\n",
		]
		positions = [self.integration.index(command) for command in commands]
		self.assertEqual(positions, sorted(positions))
		self.assertEqual(self.integration.count("run-tests --app wiki\n"), 1)

	def test_private_attachment_hooks_and_patch_are_in_the_release_tree(self):
		hooks = (ROOT / "wiki" / "hooks.py").read_text(encoding="utf-8")
		patches = (ROOT / "wiki" / "patches.txt").read_text(encoding="utf-8")
		doctype = json.loads(
			(ROOT / "wiki" / "frappe_wiki" / "doctype" / "wiki_document" / "wiki_document.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertIn('"wiki.privacy.ensure_wiki_attachments_private"', hooks)
		self.assertIn('"wiki.desktop.ensure_wiki_desktop_visibility"', hooks)
		self.assertIn('"File": {', hooks)
		self.assertIn("wiki.patches.v3.ensure_private_attachments", patches)
		self.assertEqual(doctype["make_attachments_public"], 0)

	def test_editor_uploads_are_private_and_owned_by_the_wiki_space(self):
		editor = (ROOT / "frontend" / "src" / "components" / "WikiEditor.vue").read_text(encoding="utf-8")
		published_panel = (ROOT / "frontend" / "src" / "components" / "WikiDocumentPanel.vue").read_text(
			encoding="utf-8"
		)
		draft_panel = (ROOT / "frontend" / "src" / "components" / "DraftContributionPanel.vue").read_text(
			encoding="utf-8"
		)

		self.assertIn("private: true", editor)
		self.assertIn("doctype: 'Wiki Space'", editor)
		self.assertIn("docname: props.spaceId", editor)
		self.assertIn(':space-id="props.spaceId"', published_panel)
		self.assertIn(':space-id="props.spaceId"', draft_panel)

	def test_container_versions_and_job_isolation_are_fixed(self):
		dockerfile = (ROOT / "ci" / "Dockerfile").read_text(encoding="utf-8")
		compose = (ROOT / "ci" / "compose.yaml").read_text(encoding="utf-8")
		pipeline = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
		self.assertIn("FROM node:24-bookworm-slim AS node", dockerfile)
		self.assertIn("FROM python:3.14-slim-bookworm AS runtime", dockerfile)
		self.assertIn("frappe-bench==5.31.0 ruff==0.8.1", dockerfile)
		self.assertIn("image: mariadb:11.8", compose)
		self.assertNotIn(":latest", "\n".join((dockerfile, compose, pipeline)))
		self.assertIn('COMPOSE_PROJECT_NAME: "wiki_${CI_PIPELINE_ID}_${CI_JOB_ID}"', pipeline)
		self.assertEqual(pipeline.count("down --volumes --remove-orphans"), 2)


if __name__ == "__main__":
	unittest.main()
