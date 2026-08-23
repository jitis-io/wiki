import frappe


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def search(query: str, space: str | None = None) -> dict:
	"""
	Search wiki documents with space-scoped filtering.

	Args:
	    query: Search query string
	    space: Wiki space (root group) name to scope search

	Returns:
	    Search results with title, content snippets, and scores
	"""
	from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import WikiSQLiteSearch

	if not query or not query.strip():
		return {"results": [], "total": 0}

	search_engine = WikiSQLiteSearch()
	filters = {"space": space} if space else {}

	result = search_engine.search(query, filters=filters)

	hits = _filter_hits_by_space_visibility(result["results"])

	return {
		"results": [
			{
				"name": r["name"],
				"title": r["title"],
				"route": r.get("route", ""),
				"content": r["content"],
				"score": r["score"],
			}
			for r in hits
		],
		"total": len(hits),
	}


def _filter_hits_by_space_visibility(hits: list[dict]) -> list[dict]:
	"""Drop search hits the current user couldn't open as a page.

	The SQLite index is built without user context, so titles/snippets from
	restricted spaces can surface here. Every hit is revalidated against the
	current database row and the central document/space permission helper.
	Deleted, unpublished, grouped, external, orphaned or inconsistently scoped
	rows are dropped, even when their old index entry still exists.
	"""
	from wiki.permissions import can_read_document

	names = [hit.get("name") for hit in hits if hit.get("name")]
	if not names:
		return []

	documents = {
		row.name: row
		for row in frappe.get_all(
			"Wiki Document",
			filters={"name": ("in", names)},
			fields=["name", "wiki_space", "is_published", "is_group", "is_external_link"],
		)
	}

	allowed = []
	for hit in hits:
		document = documents.get(hit.get("name"))
		if not document:
			continue
		if not document.is_published or document.is_group or document.is_external_link:
			continue
		if can_read_document(document, require_published=True):
			allowed.append(hit)
	return allowed
