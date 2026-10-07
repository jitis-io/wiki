const assert = require('node:assert/strict');
const path = require('node:path');
const { createRequire } = require('node:module');
const { spawnSync } = require('node:child_process');

const from = createRequire(path.resolve(process.argv[2], 'package.json'));
const { SourceMapConsumer } = from('source-map-js');
const selector = from('postcss-selector-parser');
const postcss = from('postcss');
const tailwind = from('tailwindcss');
const typography = from('@tailwindcss/typography');

assert.equal(from('source-map-js/package.json').version, '1.2.2');
assert.equal(from('postcss-selector-parser/package.json').version, '7.1.6');
const plain = { version: 3, sources: ['source.css'], names: [], mappings: 'AAAA' };
const section = (line, map = plain) => ({ version: 3, sections: [{ offset: { line, column: 0 }, map }] });
const mappings = [];
new SourceMapConsumer(section(1)).eachMapping((mapping) => mappings.push(mapping));
assert.equal(mappings.length, 1);
assert.equal(mappings[0].generatedLine, 2);
assert.equal(mappings[0].originalLine, 1);
for (const offset of [-1, Infinity, 10000001]) {
  assert.throws(() => new SourceMapConsumer(section(offset)), /Section offset/);
}
assert.throws(() => new SourceMapConsumer(section(6000000, section(6000000))), /nested sections/);
const benign = 'article.prose :is(h1, h2) > a[href^="https://"]:not(.private), .md\\:block';
assert.equal(selector().processSync(benign), benign);

// The advisory's flat-class corpus exercises the old quadratic path. Keep it
// in a separate bounded process so a future regression cannot stall the suite.
const hostile = spawnSync(process.execPath, ['--max-old-space-size=256', '-e', `
  const assert = require('node:assert/strict');
  const parser = require(${JSON.stringify(from.resolve('postcss-selector-parser'))});
  const input = '.a'.repeat(100000);
  assert.equal(parser().processSync(input), input);
  process.stdout.write('bounded-flat-selector-ok');
`], { timeout: 5000, maxBuffer: 1024 });
assert.equal(hostile.error, undefined);
assert.equal(hostile.status, 0);
assert.equal(hostile.stdout.toString(), 'bounded-flat-selector-ok');

(async () => {
  const result = await postcss([tailwind({
    content: [{ raw: '<article class="prose md:block prose-a:text-blue-600"><a>Link</a></article>', extension: 'html' }],
    corePlugins: { preflight: false },
    plugins: [typography],
  })]).process('@tailwind components; @tailwind utilities;', { from: undefined });
  assert.match(result.css, /\.prose/);
  assert.match(result.css, /:where\(a\)/);
  assert.match(result.css, /\.md\\:block/);
  assert.match(result.css, /display: block/);
  const postcssFrom = createRequire(from.resolve('postcss/package.json'));
  const tailwindFrom = createRequire(from.resolve('tailwindcss/package.json'));
  assert.equal(postcssFrom('source-map-js/package.json').version, '1.2.2');
  assert.equal(tailwindFrom('postcss-selector-parser/package.json').version, '7.1.6');
  console.log(JSON.stringify({ sourceMap: '1.2.2', selectorParser: '7.1.6', normalIndexedMap: true,
    rejectedOversizedAndNestedOffsets: true, flatSelectorBytes: 200000,
    flatSelectorDeadlineSeconds: 5, tailwind3TypographyAndResponsiveUtilities: true }));
})().catch((error) => { console.error(error); process.exitCode = 1; });
