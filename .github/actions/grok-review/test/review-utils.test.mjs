import assert from 'node:assert/strict';
import test from 'node:test';
import {
  REVIEW_SCHEMA, addedLines, selectReviewFiles,
  parseReview, validFindings, reviewBadge,
} from '../src/review-utils.mjs';

const settings = { maxFiles: 30, maxDiffChars: 60_000, maxPerFileChars: 12_000 };

test('unified diff tracks only added/new lines and keeps hunk offsets', () => {
  const patch = [
    '@@ -9,2 +10,3 @@',
    ' before',
    '-old',
    '+new',
    '++literal-plus-prefix',
    ' after',
    '@@ -30,1 +42,2 @@',
    '+changed',
    '+again',
    '\\ No newline at end of file',
  ].join('\n');
  assert.deepEqual([...addedLines(patch)], [11, 12, 42, 43]);
});

test('prioritize code and workflow over docs within a bounded budget', () => {
  const found = [
    { filename: 'README.md', patch: '@@ -0,0 +1 @@\n+hello' },
    { filename: '.github/workflows/build.yml', patch: '@@ -0,0 +1 @@\n+echo broken' },
    { filename: 'src/auth.ts', patch: '@@ -0,0 +1 @@\n+const auth = null' },
  ];
  const picked = selectReviewFiles(found, { ...settings, maxFiles: 2 });
  assert.deepEqual(picked.files.map((file) => file.path),
    ['src/auth.ts', '.github/workflows/build.yml']);
  assert.equal(picked.complete, false);
  assert.equal(picked.total, 3);
});

test('report partial scope for omitted patches or mid-hunk truncation', () => {
  const found = [
    { filename: 'src/a.ts', patch: '@@ -0,0 +1 @@\n+let a = 1' },
    { filename: 'assets/snapshot.png' },
  ];
  assert.equal(selectReviewFiles(found, settings).complete, false);
  const clipped = selectReviewFiles(found.slice(0, 1),
    { ...settings, maxPerFileChars: 10 });
  assert.equal(clipped.complete, false);
});

test('accept only findings anchored on actual changed lines', () => {
  const picked = selectReviewFiles([
    { filename: 'src/auth.ts', patch: '@@ -2,1 +2,1 @@\n-old\n+new' },
  ], settings);
  const found = validFindings({ findings: [
    { path: 'src/auth.ts', line: 2, title: 'Real', body: 'Explanation', severity: 'high' },
    { path: 'src/auth.ts', line: 8, title: 'Invented', body: 'No line', severity: 'high' },
    { path: 'src/other.ts', line: 2, title: 'Wrong file', body: 'No file', severity: 'high' },
  ] }, picked.files);
  assert.equal(found.length, 1);
  assert.equal(found[0].title, 'Real');
});

test('parse structured output only with a completed response', () => {
  const sample = { summary: 'No bugs.', findings: [] };
  const response = { status: 'completed', output: [{
    type: 'message', content: [{ type: 'output_text', text: JSON.stringify(sample) }],
  }] };
  assert.deepEqual(parseReview(response), sample);
  assert.throws(() => parseReview({ ...response, status: 'incomplete' }));
  assert.equal(REVIEW_SCHEMA.properties.findings.maxItems, 8);
});

test('reuses canonical Grok SVG and links to the originating Actions run', () => {
  const badge = reviewBadge('42250120359');
  assert.match(badge, /assets\/badges\/grok\.svg/);
  assert.match(badge, /actions\/runs\/42250120359/);
  assert.doesNotMatch(badge, /img\.shields\.io/);
});
