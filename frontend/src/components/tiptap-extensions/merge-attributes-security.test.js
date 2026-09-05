import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

import { mergeAttributes } from '@tiptap/core';
import { DOMSerializer } from '@tiptap/pm/model';

import { WikiLink } from './link-extension.js';

const starterKitRequire = createRequire(
	import.meta.resolve('@tiptap/starter-kit'),
);
const starterKitCore = starterKitRequire('@tiptap/core');

// The serializer's actual attribute enumeration is the security boundary. A
// minimal document records attributes without executing any event handler.
const document = {
	createElement(name) {
		return {
			nodeType: 1,
			nodeName: name,
			attributes: Object.create(null),
			setAttribute(key, value) {
				this.attributes[key] = String(value);
			},
		};
	},
};

for (const [consumer, merge] of [
	['Wiki extensions', mergeAttributes],
	['StarterKit dependency', starterKitCore.mergeAttributes],
]) {
	test(`${consumer} cannot inherit executable attributes from imported JSON`, () => {
		const imported = JSON.parse(
			'{"__proto__":{"onerror":"security-canary","src":"invalid://canary"}}',
		);
		const attributes = merge({ alt: 'Wiki attachment' }, imported);
		const { dom } = DOMSerializer.renderSpec(document, ['img', attributes]);

		assert.equal(Object.getPrototypeOf(attributes), Object.prototype);
		assert.equal(attributes.onerror, undefined);
		assert.equal(attributes.src, undefined);
		assert.equal(dom.attributes.onerror, undefined);
		assert.equal(dom.attributes.src, undefined);
		assert.equal(dom.attributes.alt, 'Wiki attachment');
		assert.equal(Object.prototype.onerror, undefined);
	});
}

test('Wiki links preserve configured attributes after the security update', () => {
	const spec = WikiLink.config.renderHTML.call(
		{
			options: {
				HTMLAttributes: { target: '_blank', rel: 'noopener noreferrer' },
			},
		},
		{
			HTMLAttributes: { href: '/wiki-app/document/example', title: 'Runbook' },
		},
	);
	const { dom } = DOMSerializer.renderSpec(document, spec);

	assert.equal(dom.attributes.href, '/wiki-app/document/example');
	assert.equal(dom.attributes.title, 'Runbook');
	assert.equal(dom.attributes.target, '_blank');
	assert.equal(dom.attributes.rel, 'noopener noreferrer');
});
