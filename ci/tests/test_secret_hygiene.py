import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IGNORED_PARTS = {".git", ".ruff_cache", "__pycache__", "node_modules"}
TEXT_SUFFIXES = {"", ".json", ".md", ".py", ".sh", ".toml", ".yaml", ".yml"}
KNOWN_SECRET_FIXTURES = {Path("wiki/api/test_github.py")}


def _repository_text_files():
	for path in sorted(ROOT.rglob("*")):
		if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
			continue
		if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile"}:
			yield path


class SecretHygieneTests(unittest.TestCase):
	def test_no_secret_or_private_key_files_are_present(self):
		for path in ROOT.rglob("*"):
			if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
				continue
			name = path.name.lower()
			with self.subTest(path=path.relative_to(ROOT)):
				self.assertFalse(name == ".env" or name.startswith(".env."))
				self.assertNotIn(name, {"id_rsa", "id_ed25519", "credentials.json", "service-account.json"})
				self.assertNotIn(path.suffix.lower(), {".key", ".p12", ".pfx"})

	def test_no_known_token_fingerprints_or_private_keys_are_embedded(self):
		markers = (
			"gl" + "pat-",
			"cf" + "at_",
			"gh" + "p_",
			"gh" + "o_",
			"-----BEGIN " + "PRIVATE KEY-----",
			"-----BEGIN " + "OPENSSH PRIVATE KEY-----",
		)
		for path in _repository_text_files():
			if path.relative_to(ROOT) in KNOWN_SECRET_FIXTURES:
				continue
			text = path.read_text(encoding="utf-8", errors="replace")
			with self.subTest(path=path.relative_to(ROOT)):
				for marker in markers:
					self.assertNotIn(marker, text)
				self.assertIsNone(re.search(r"\bAKIA[0-9A-Z]{16}\b", text))
				self.assertIsNone(re.search(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.", text))

	def test_no_credentials_are_embedded_in_urls(self):
		credential_url = re.compile(r"https?://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE)
		for path in _repository_text_files():
			text = path.read_text(encoding="utf-8", errors="replace")
			with self.subTest(path=path.relative_to(ROOT)):
				self.assertIsNone(credential_url.search(text))


if __name__ == "__main__":
	unittest.main()
