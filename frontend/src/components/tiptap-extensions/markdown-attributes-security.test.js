import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import test from 'node:test';

import * as directCore from '@tiptap/core';

const starterRequire = createRequire(
	import.meta.resolve('@tiptap/starter-kit'),
);

for (const [consumer, core] of [
	['Wiki extensions', directCore],
	['StarterKit dependency', starterRequire('@tiptap/core')],
]) {
	test(`${consumer} rejects forged Markdown attribute placeholders`, () => {
		assert.deepEqual(
			core.parseAttributes('title=__QUOTED_0__ "forged" disabled'),
			{ disabled: true },
		);
		assert.deepEqual(core.parseAttributes('title="Customer runbook"'), {
			title: 'Customer runbook',
		});
	});

	test(`${consumer} only accepts shortcode attributes at token boundaries`, () => {
		const tokenizer = core.createInlineMarkdownSpec({
			nodeName: 'probe',
			selfClosing: true,
		}).markdownTokenizer;
		const token = tokenizer.tokenize(
			'[probe prefix:id="ignored" label="kept"]',
			[],
			{},
		);
		assert.deepEqual(token.attributes, { label: 'kept' });
	});

	test(`${consumer} bounds malformed block and inline Markdown parsing`, () => {
		// A separate process makes a synchronous regex stall interruptible. The
		// fixed scanner completes these inputs in milliseconds; the old quadratic
		// parser exceeds this generous five-second budget on the same input.
		const source = `
			import { createRequire } from 'node:module';
			import * as direct from '@tiptap/core';
			const require = createRequire(import.meta.resolve('@tiptap/starter-kit'));
			const core = ${consumer === 'Wiki extensions' ? 'direct' : "require('@tiptap/core')"};
			const block = '__QUOTED_0'.repeat(16384) + '__QUOTED_0__';
			const inline = '0'.repeat(131072);
			const lexer = { blockTokens: () => [], inlineTokens: () => [] };
			core.createAtomBlockMarkdownSpec({ nodeName: 'probe' }).markdownTokenizer
				.tokenize(':::probe {' + block + '} :::\\n', [], lexer);
			core.createBlockMarkdownSpec({ nodeName: 'probe' }).markdownTokenizer
				.tokenize(':::probe {' + block + '}\\ncontent\\n:::', [], lexer);
			core.createInlineMarkdownSpec({ nodeName: 'probe', selfClosing: true }).markdownTokenizer
				.tokenize('[probe ' + inline + ']', [], lexer);
		`;
		const result = spawnSync(
			process.execPath,
			['--input-type=module', '-e', source],
			{
				cwd: new URL('../../../', import.meta.url),
				timeout: 5000,
				encoding: 'utf8',
			},
		);
		assert.equal(result.error, undefined, result.error?.message);
		assert.equal(result.status, 0, result.stderr);
	});
}
