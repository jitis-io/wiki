import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_COMMITS = {
	"FRAPPE_COMMIT": "06613fc60b44d5736007ae3107cdab029b2ae045",
	"ERPNEXT_COMMIT": "8378b6e203841c056925420cc44e6d631c915cf1",
}

EXPECTED_ACTION_PINS = {
	"actions/cache": ("0057852bfaa89a56745cba8c7296529d2fc39830", "v4.3.0"),
	"actions/checkout": ("11d5960a326750d5838078e36cf38b85af677262", "v4.4.0"),
	"actions/download-artifact": ("d3f86a106a0bac45b974a628896c90dbdf5c8093", "v4.3.0"),
	"actions/setup-node": ("49933ea5288caeca8642d1e84afbd3f7d6820020", "v4.4.0"),
	"actions/setup-python": ("a26af69be951a213d495a4c3e4e4022e16d87065", "v5.6.0"),
	"actions/upload-artifact": ("ea165f8d65b6e75b540449e92b4886f43607fa02", "v4.6.2"),
	"pre-commit/action": ("2c7b3805fd2a0fd8c1884dcaebf91fc102a13ecd", "v3.0.1"),
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
		pipeline = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn("FROM node:24-bookworm-slim AS node", dockerfile)
		self.assertIn("FROM python:3.14-slim-bookworm AS runtime", dockerfile)
		self.assertIn("frappe-bench==5.31.0 ruff==0.8.1", dockerfile)
		self.assertIn("image: mariadb:11.8", compose)
		self.assertNotIn(":latest", "\n".join((dockerfile, compose, pipeline)))
		self.assertIn("COMPOSE_PROJECT_NAME: wiki_${{ github.run_id }}_quality", pipeline)
		self.assertIn("COMPOSE_PROJECT_NAME: wiki_${{ github.run_id }}_integration", pipeline)
		self.assertEqual(pipeline.count("down --volumes --remove-orphans"), 2)

	def test_upstream_workflow_actions_are_immutable_release_pins(self):
		workflow_paths = (
			ROOT / ".github" / "workflows" / "ui-tests.yml",
			ROOT / ".github" / "workflows" / "linters.yml",
		)
		pinned_action = re.compile(
			r"^\s*-?\s*uses:\s+(actions/[\w-]+|pre-commit/action)@([0-9a-f]{40})"
			r"\s+#\s+(v\d+\.\d+\.\d+)\s*$"
		)
		uses_lines = [
			line
			for path in workflow_paths
			for line in path.read_text(encoding="utf-8").splitlines()
			if "uses:" in line
		]

		self.assertTrue(uses_lines)
		self.assertEqual([line for line in uses_lines if not pinned_action.match(line)], [])
		resolved_pins = {
			match.group(1): (match.group(2), match.group(3))
			for line in uses_lines
			if (match := pinned_action.match(line))
		}
		self.assertEqual(resolved_pins, EXPECTED_ACTION_PINS)


if __name__ == "__main__":
	unittest.main()
