"""Private-by-default storage and migration for Wiki attachments.

Frappe's standard public/private transition updates every ``File`` row with the
same content hash. Wiki must not use that transition because identical bytes
can also belong to an unrelated ERP document. This module copies Wiki files to
isolated private paths and updates only the owning Wiki row.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import frappe
from frappe.core.doctype.file.utils import get_content_hash
from frappe.utils import cint

WIKI_ATTACHMENT_DOCTYPES = ("Wiki Document", "Wiki Space")
WIKI_REFERENCE_FIELDS = {
	"Wiki Document": ("content", "meta_image"),
	"Wiki Space": ("light_mode_logo", "dark_mode_logo", "app_switcher_logo", "favicon"),
}
PUBLIC_FILE_PREFIX = "/files/"
PRIVATE_FILE_PREFIX = "/private/files/"
LOCAL_PUBLIC_REFERENCE = re.compile(r"(?<![\w:/])/files/")


@dataclass(frozen=True)
class VerifiedSource:
	file_url: str
	path: Path
	file_name: str
	content_hash: str
	file_size: int


@dataclass(frozen=True)
class WikiReference:
	doctype: str
	name: str
	wiki_space: str
	values: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class FileMove:
	name: str
	attached_to_doctype: str
	attached_to_name: str
	old_url: str
	new_url: str
	target: Path
	source: VerifiedSource


@dataclass(frozen=True)
class FileClone:
	attached_to_doctype: str
	attached_to_name: str
	attached_to_field: str | None
	old_url: str
	new_url: str
	target: Path
	source: VerifiedSource


@dataclass(frozen=True)
class MigrationPlan:
	moves: tuple[FileMove, ...]
	clones: tuple[FileClone, ...]
	updates: tuple[tuple[str, str, str, str, str], ...]


def enforce_private_wiki_attachment(doc, method=None):
	"""Force Wiki attachments private and give every row an isolated URL."""
	if cint(getattr(doc, "is_folder", 0)):
		return
	if getattr(doc, "attached_to_doctype", None) not in WIKI_ATTACHMENT_DOCTYPES:
		return

	doc.is_private = 1
	if method != "before_insert" and doc.is_new():
		return

	file_url = str(getattr(doc, "file_url", "") or "")
	if not file_url:
		frappe.throw("Wiki attachment has no local file URL", frappe.ValidationError)
	if not file_url.startswith((PUBLIC_FILE_PREFIX, PRIVATE_FILE_PREFIX)):
		frappe.throw("Remote Wiki attachments are not permitted", frappe.ValidationError)

	shared_filters = {"file_url": file_url, "is_folder": 0}
	if method != "before_insert":
		shared_filters["name"] = ("!=", doc.name)
	shared_url = bool(frappe.db.exists("File", shared_filters))
	if file_url.startswith(PRIVATE_FILE_PREFIX) and not shared_url:
		return

	rows = frappe.get_all(
		"File",
		filters={"file_url": file_url, "is_folder": 0},
		fields=["name", "file_name", "file_url", "file_size", "content_hash"],
		limit_page_length=0,
	)
	if not any(row.name == getattr(doc, "name", None) for row in rows):
		rows.append(doc)
	source = _verify_source(file_url, rows)
	target = _reserve_private_target(
		source.file_name,
		f"file:{getattr(doc, 'name', '') or frappe.generate_hash(length=10)}",
		set(),
	)
	_copy_to_private(source, target)
	doc.file_url = _private_url(target)
	doc.content_hash = source.content_hash
	doc.file_size = source.file_size
	_schedule_source_cleanup(file_url, source.path)


def validate_private_wiki_references(doc, method=None):
	"""Reject local public URLs introduced after the migration."""
	for fieldname in WIKI_REFERENCE_FIELDS.get(doc.doctype, ()):  # pragma: no branch - fixed map
		value = str(doc.get(fieldname) or "")
		if LOCAL_PUBLIC_REFERENCE.search(value):
			frappe.throw(
				f"{doc.doctype}.{fieldname} must not reference a public local file",
				frappe.ValidationError,
			)


def ensure_wiki_attachments_private() -> dict[str, int]:
	"""Migrate and audit Wiki files without changing content-hash siblings."""
	if not _required_tables_exist():
		return {"moved": 0, "cloned": 0, "updated": 0}

	plan = _build_migration_plan()
	for move in plan.moves:
		_copy_to_private(move.source, move.target)
		frappe.db.set_value(
			"File",
			move.name,
			{
				"file_url": move.new_url,
				"is_private": 1,
				"content_hash": move.source.content_hash,
				"file_size": move.source.file_size,
			},
			update_modified=False,
		)
		_schedule_source_cleanup(move.old_url, move.source.path)

	for clone in plan.clones:
		_copy_to_private(clone.source, clone.target)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": clone.source.file_name,
				"file_url": clone.new_url,
				"is_private": 1,
				"content_hash": clone.source.content_hash,
				"file_size": clone.source.file_size,
				"attached_to_doctype": clone.attached_to_doctype,
				"attached_to_name": clone.attached_to_name,
				"attached_to_field": clone.attached_to_field,
			}
		)
		file_doc.flags.copy_from_existing_file = True
		file_doc.insert(ignore_permissions=True)

	for doctype, name, fieldname, old_url, new_url in plan.updates:
		value = str(frappe.db.get_value(doctype, name, fieldname) or "")
		updated = _replace_local_url(value, old_url, new_url)
		if updated != value:
			frappe.db.set_value(doctype, name, fieldname, updated, update_modified=False)

	if plan.moves or plan.clones or plan.updates:
		from wiki.frappe_wiki.doctype.wiki_document.wiki_document import clear_wiki_content_cache

		clear_wiki_content_cache()

	return {
		"moved": len(plan.moves),
		"cloned": len(plan.clones),
		"updated": len(plan.updates),
	}


def _required_tables_exist() -> bool:
	return all(frappe.db.table_exists(doctype) for doctype in ("File", *WIKI_ATTACHMENT_DOCTYPES))


def _build_migration_plan() -> MigrationPlan:
	file_rows = frappe.get_all(
		"File",
		filters={"is_folder": 0},
		fields=[
			"name",
			"file_name",
			"file_url",
			"file_size",
			"content_hash",
			"is_private",
			"attached_to_doctype",
			"attached_to_name",
			"attached_to_field",
		],
		order_by="name",
		limit_page_length=0,
	)
	references = _load_wiki_references()
	rows_by_url = defaultdict(list)
	for row in file_rows:
		if row.file_url:
			rows_by_url[str(row.file_url)].append(row)

	public_urls = sorted(
		(url for url in rows_by_url if url.startswith(PUBLIC_FILE_PREFIX)),
		key=len,
		reverse=True,
	)
	public_references = _reference_urls(references, public_urls, reject_unknown=True)

	url_counts = Counter(str(row.file_url or "") for row in file_rows if row.file_url)
	wiki_rows = [
		row
		for row in file_rows
		if row.attached_to_doctype in WIKI_ATTACHMENT_DOCTYPES
		and (
			not cint(row.is_private)
			or str(row.file_url or "").startswith(PUBLIC_FILE_PREFIX)
			or (row.file_url and url_counts[str(row.file_url)] > 1)
		)
	]
	for row in wiki_rows:
		if not row.file_url or not str(row.file_url).startswith((PUBLIC_FILE_PREFIX, PRIVATE_FILE_PREFIX)):
			frappe.throw(
				f"Wiki File {row.name} is not a verifiable local attachment",
				frappe.ValidationError,
			)

	source_cache: dict[str, VerifiedSource] = {}

	def source_for(file_url: str) -> VerifiedSource:
		if file_url not in source_cache:
			source_cache[file_url] = _verify_source(file_url, rows_by_url[file_url])
		return source_cache[file_url]

	for row in wiki_rows:
		source_for(str(row.file_url))
	for urls in public_references.values():
		for file_url in urls:
			source_for(file_url)

	reserved: set[Path] = set()
	moves = []
	owner_targets: dict[tuple[str, str, str], str] = {}
	for row in wiki_rows:
		old_url = str(row.file_url)
		source = source_for(old_url)
		target = _reserve_private_target(
			str(row.file_name or source.file_name),
			f"file:{row.name}",
			reserved,
		)
		move = FileMove(
			name=row.name,
			attached_to_doctype=str(row.attached_to_doctype or ""),
			attached_to_name=str(row.attached_to_name or ""),
			old_url=old_url,
			new_url=_private_url(target),
			target=target,
			source=source,
		)
		moves.append(move)
		owner_targets.setdefault(
			(move.attached_to_doctype, move.attached_to_name, old_url),
			move.new_url,
		)

	interesting_urls = sorted(set(public_urls).union(move.old_url for move in moves), key=len, reverse=True)
	urls_per_reference = _reference_urls(references, interesting_urls)
	clones = []
	clone_targets: dict[tuple[str, str, str], str] = {}
	updates = set()
	for reference in references:
		for old_url in urls_per_reference.get((reference.doctype, reference.name), set()):
			new_url = _owned_target(reference, old_url, owner_targets)
			if not new_url:
				clone_key = (reference.doctype, reference.name, old_url)
				new_url = clone_targets.get(clone_key)
				if not new_url:
					source = source_for(old_url)
					target = _reserve_private_target(
						source.file_name,
						f"reference:{reference.doctype}:{reference.name}:{old_url}",
						reserved,
					)
					new_url = _private_url(target)
					clone_targets[clone_key] = new_url
					clones.append(
						FileClone(
							attached_to_doctype=reference.doctype,
							attached_to_name=reference.name,
							attached_to_field=_attachment_field(reference, old_url),
							old_url=old_url,
							new_url=new_url,
							target=target,
							source=source,
						)
					)
			for fieldname, value in reference.values:
				if old_url in value:
					updates.add((reference.doctype, reference.name, fieldname, old_url, new_url))

	return MigrationPlan(
		moves=tuple(moves),
		clones=tuple(clones),
		updates=tuple(sorted(updates)),
	)


def _load_wiki_references() -> tuple[WikiReference, ...]:
	references = []
	for doctype, fieldnames in WIKI_REFERENCE_FIELDS.items():
		fields = ["name", *fieldnames]
		if doctype == "Wiki Document":
			fields.append("wiki_space")
		for row in frappe.get_all(
			doctype,
			fields=fields,
			order_by="name",
			limit_page_length=0,
		):
			references.append(
				WikiReference(
					doctype=doctype,
					name=str(row.name),
					wiki_space=str(row.get("wiki_space") or (row.name if doctype == "Wiki Space" else "")),
					values=tuple((fieldname, str(row.get(fieldname) or "")) for fieldname in fieldnames),
				)
			)
	return tuple(references)


def _reference_urls(
	references: tuple[WikiReference, ...],
	known_urls: list[str],
	*,
	reject_unknown: bool = False,
) -> dict[tuple[str, str], set[str]]:
	result = defaultdict(set)
	blockers = []
	for reference in references:
		for fieldname, value in reference.values:
			masked = value
			for file_url in known_urls:
				updated = _replace_local_url(masked, file_url, "")
				if updated != masked:
					result[(reference.doctype, reference.name)].add(file_url)
					masked = updated
			if reject_unknown and LOCAL_PUBLIC_REFERENCE.search(masked):
				blockers.append(f"{reference.doctype}:{reference.name}:{fieldname}")
	if blockers:
		frappe.throw(
			"Unverifiable public local references block the Wiki migration: " + ", ".join(blockers[:25]),
			frappe.ValidationError,
		)
	return result


def _replace_local_url(value: str, old_url: str, new_url: str) -> str:
	pattern = re.compile(rf"(?<![\w:/?&=%.-]){re.escape(old_url)}(?![\w/%.-])")
	return pattern.sub(lambda _match: new_url, value)


def _owned_target(
	reference: WikiReference,
	old_url: str,
	owner_targets: dict[tuple[str, str, str], str],
) -> str | None:
	direct = owner_targets.get((reference.doctype, reference.name, old_url))
	if direct:
		return direct
	if reference.doctype == "Wiki Document" and reference.wiki_space:
		return owner_targets.get(("Wiki Space", reference.wiki_space, old_url))
	return None


def _attachment_field(reference: WikiReference, old_url: str) -> str | None:
	for fieldname, value in reference.values:
		if fieldname != "content" and old_url in value:
			return fieldname
	return None


def _verify_source(file_url: str, rows) -> VerifiedSource:
	path = _safe_local_path(file_url)
	if not path.is_file():
		frappe.throw(f"Local File source is missing: {file_url}", frappe.ValidationError)
	content = path.read_bytes()
	content_hash = get_content_hash(content)
	file_size = len(content)
	for row in rows:
		row_hash = str(getattr(row, "content_hash", "") or "")
		row_size = cint(getattr(row, "file_size", 0))
		if row_hash and row_hash != content_hash:
			frappe.throw(f"File content hash mismatch: {row.name}", frappe.ValidationError)
		if row_size and row_size != file_size:
			frappe.throw(f"File size mismatch: {row.name}", frappe.ValidationError)
	file_name = next((str(getattr(row, "file_name", "") or "") for row in rows if row), "")
	return VerifiedSource(
		file_url=file_url,
		path=path,
		file_name=os.path.basename(file_name) or path.name,
		content_hash=content_hash,
		file_size=file_size,
	)


def _safe_local_path(file_url: str) -> Path:
	if file_url.startswith(PRIVATE_FILE_PREFIX):
		root = Path(frappe.get_site_path("private", "files")).resolve()
		relative = file_url.removeprefix(PRIVATE_FILE_PREFIX)
	elif file_url.startswith(PUBLIC_FILE_PREFIX):
		root = Path(frappe.get_site_path("public", "files")).resolve()
		relative = file_url.removeprefix(PUBLIC_FILE_PREFIX)
	else:
		frappe.throw(f"File URL is not local: {file_url}", frappe.ValidationError)

	parts = PurePosixPath(relative).parts
	if not relative or any(part in {"", ".", ".."} for part in parts):
		frappe.throw(f"File URL is not safe: {file_url}", frappe.ValidationError)
	path = root.joinpath(*parts).resolve()
	if not path.is_relative_to(root):
		frappe.throw(f"File URL leaves the site files directory: {file_url}", frappe.ValidationError)
	return path


def _reserve_private_target(file_name: str, identity: str, reserved: set[Path]) -> Path:
	root = Path(frappe.get_site_path("private", "files")).resolve()
	safe_name = re.sub(r"[/\\%?#]", "_", os.path.basename(file_name or "wiki-file"))
	stem, extension = os.path.splitext(safe_name)
	digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
	for index in range(1_000):
		suffix = digest if index == 0 else f"{digest}-{index}"
		candidate = root / f"{stem}-{suffix}{extension}"
		if candidate not in reserved and not candidate.exists():
			reserved.add(candidate)
			return candidate
	frappe.throw("Could not reserve an isolated private Wiki file path", frappe.ValidationError)


def _copy_to_private(source: VerifiedSource, target: Path) -> None:
	content = source.path.read_bytes()
	if len(content) != source.file_size or get_content_hash(content) != source.content_hash:
		frappe.throw(f"File changed after migration preflight: {source.file_url}", frappe.ValidationError)
	target.parent.mkdir(parents=True, exist_ok=True)
	if target.exists():
		frappe.throw(f"Private migration target already exists: {target.name}", frappe.ValidationError)
	with target.open("xb") as handle:
		handle.write(content)
		handle.flush()
		os.fsync(handle.fileno())
	frappe.db.after_rollback.add(lambda path=target: path.unlink(missing_ok=True))


def _private_url(path: Path) -> str:
	return f"{PRIVATE_FILE_PREFIX}{path.name}"


def _schedule_source_cleanup(file_url: str, source: Path) -> None:
	def remove_if_unreferenced():
		if not frappe.db.exists("File", {"file_url": file_url}):
			source.unlink(missing_ok=True)

	frappe.db.after_commit.add(remove_if_unreferenced)
