export const REVIEW_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'findings'],
  properties: {
    summary: { type: 'string', maxLength: 800 },
    findings: {
      type: 'array',
      maxItems: 8,
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['severity', 'path', 'line', 'title', 'body'],
        properties: {
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          path: { type: 'string', maxLength: 400 },
          line: { type: 'integer', minimum: 1 },
          title: { type: 'string', maxLength: 120 },
          body: { type: 'string', maxLength: 800 },
        },
      },
    },
  },
};

export function addedLines(patch) {
  const lines = new Set();
  let cursor = 0;
  for (const row of patch.split('\n')) {
    const hunk = row.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) cursor = Number(hunk[1]);
    else if (row.startsWith('\\')) continue;
    else if (row.startsWith('+')) lines.add(cursor++);
    else if (row.startsWith(' ')) cursor++;
  }
  return lines;
}

function priority(path) {
  if (/(^|\/)(auth|security|payment|migration|deploy|core)(\/|[.-])/i.test(path)) return 9;
  if (/^\.github\/(workflows|actions)\//.test(path)) return 8;
  if (/\.(ts|tsx|js|mjs|cjs|py|go|rs|kt|java|sh|sql|yml|yaml)$/.test(path)) return 6;
  if (/^(package\.json|Dockerfile|wrangler\.jsonc?)$/.test(path)) return 5;
  if (/\.(md|txt|lock|sum|svg|png|jpg|webp)$/.test(path)) return 1;
  return 3;
}

export function selectReviewFiles(found, config) {
  const ranked = found
    .filter((item) => typeof item.filename === 'string')
    .map((item, index) => ({ ...item, index }))
    .sort((a, b) => priority(b.filename) - priority(a.filename) || a.index - b.index);
  let remaining = config.maxDiffChars;
  let truncated = found.length >= 300;
  const files = [];
  for (const item of ranked) {
    if (files.length >= config.maxFiles || remaining <= 0) {
      truncated = true;
      break;
    }
    if (typeof item.patch !== 'string' || !item.patch) {
      truncated = true;
      continue;
    }
    const patch = item.patch.slice(0, Math.min(remaining, config.maxPerFileChars));
    if (patch.length !== item.patch.length) truncated = true;
    files.push({ path: item.filename, patch, lines: addedLines(patch) });
    remaining -= patch.length;
  }
  return {
    files,
    total: found.length,
    complete: !truncated && files.length === found.length,
  };
}

export function responseText(response) {
  return (Array.isArray(response.output) ? response.output : [])
    .flatMap((entry) => Array.isArray(entry.content) ? entry.content : [])
    .filter((part) => part.type === 'output_text' && typeof part.text === 'string')
    .map((part) => part.text).join('\n').trim();
}

export function parseReview(response) {
  if (response.status !== 'completed') throw new Error('xai_response_incomplete');
  const text = responseText(response);
  const value = JSON.parse(text);
  if (!value || typeof value.summary !== 'string' || !Array.isArray(value.findings)) {
    throw new Error('invalid_review_contract');
  }
  return value;
}

export function validFindings(generated, files, maxFindings = 8) {
  const changed = new Map(files.map((file) => [file.path, file.lines]));
  const findings = [];
  const seen = new Set();
  for (const raw of generated.findings.slice(0, maxFindings * 2)) {
    if (!raw || typeof raw.path !== 'string' || !changed.has(raw.path) ||
      !Number.isInteger(raw.line) || !changed.get(raw.path).has(raw.line) ||
      typeof raw.title !== 'string' || typeof raw.body !== 'string') continue;
    const title = raw.title.trim().slice(0, 120).replace(/[\r\n]/g, ' ');
    const body = raw.body.trim().slice(0, 800);
    const key = raw.path + ':' + raw.line;
    if (!title || !body || seen.has(key)) continue;
    seen.add(key);
    findings.push({ path: raw.path, line: raw.line, title, body,
      severity: ['high', 'medium', 'low'].includes(raw.severity) ? raw.severity : 'medium' });
    if (findings.length >= maxFindings) break;
  }
  return findings;
}

export function reviewBadge(runId) {
  const workflowUrl = 'https://github.com/travnie/.github/actions/workflows/grok-review.yml';
  const url = /^\d+$/.test(runId || '')
    ? 'https://github.com/travnie/.github/actions/runs/' + runId
    : workflowUrl;
  return '[![Grok](https://raw.githubusercontent.com/travnie/.github/main/assets/badges/grok.svg)](' + url + ')';
}
