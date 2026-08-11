export function renderCalloutFence({
	type = 'note',
	title = '',
	content = '',
}) {
	const openingFence = title ? `:::${type}[${title}]` : `:::${type}`;

	// TipTap's Markdown serializer owns the separator between block nodes.
	// Returning another blank-line separator here makes every parse/serialize
	// cycle grow two trailing newlines and leaves pages permanently dirty.
	return `${openingFence}\n${content}\n:::`;
}
