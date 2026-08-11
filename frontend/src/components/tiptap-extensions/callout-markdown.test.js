import assert from 'node:assert/strict';
import test from 'node:test';

import { renderCalloutFence } from './callout-markdown.js';

test('renders titled callouts without a duplicate block separator', () => {
	assert.equal(
		renderCalloutFence({
			type: 'note',
			title: 'Test',
			content: 'This has **bold** text',
		}),
		':::note[Test]\nThis has **bold** text\n:::',
	);
});

test('renders untitled callouts with safe defaults', () => {
	assert.equal(renderCalloutFence({ content: 'Body' }), ':::note\nBody\n:::');
});
