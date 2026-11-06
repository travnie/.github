import { readFile, appendFile } from 'node:fs/promises';
import {
  REVIEW_SCHEMA,
  selectReviewFiles,
  parseReview,
  validFindings,
  reviewBadge,
} from './review-utils.mjs';

const config = JSON.parse(await readFile(new URL('../config.json', import.meta.url), 'utf8'));
const policy = await readFile(new URL('../review-policy.md', import.meta.url), 'utf8');
const target = process.env.TARGET_REPOSITORY || '';
const number = Number(process.env.TARGET_NUMBER);
const expectedSha = process.env.EXPECTED_HEAD_SHA || '';
const githubToken = process.env.GROK_GH_TOKEN || '';
const xaiToken = process.env.XAI_API_KEY || '';
const repoPattern = /^(?:trvny|travnie)\/[A-Za-z0-9_.-]+$/;
const shaPattern = /^[0-9a-f]{40}$/i;
const markerPrefix = '<!-- grok-review:';

if (!repoPattern.test(target) || !Number.isSafeInteger(number) || number < 1 ||
  (expectedSha && !shaPattern.test(expectedSha))) {
  throw new Error('invalid_review_target');
}
if (!githubToken || !xaiToken) throw new Error('review_credentials_unavailable');
if (!['low', 'medium', 'high', 'xhigh'].includes(config.reasoningEffort) ||
  !/^grok-[\w.-]{1,40}$/.test(config.model) ||
  !Number.isInteger(config.maxFiles) || config.maxFiles < 1 || config.maxFiles > 80 ||
  !Number.isInteger(config.maxDiffChars) || config.maxDiffChars > 160_000 ||
  !Number.isInteger(config.maxPerFileChars) || config.maxPerFileChars > 30_000) {
  throw new Error('invalid_review_config');
}

const [owner, repo] = target.split('/');
const apiBase = '/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo);
const headers = {
  Accept: 'application/vnd.github+json',
  Authorization: 'Bearer ' + githubToken,
  'X-GitHub-Api-Version': '2022-11-28',
  'User-Agent': 'travnie-central-grok-review',
};

async function github(path, method = 'GET', body) {
  const response = await fetch('https://api.github.com' + path, {
    method,
    headers: { ...headers, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(config.githubTimeoutMs),
  });
  if (response.status === 404 && method === 'GET' && path.includes('/contents/')) return null;
  if (!response.ok) throw new Error('github_request_failed:' + method + ':' + response.status);
  return response.status === 204 ? null : response.json();
}

async function pullRequest() {
  return github(apiBase + '/pulls/' + number);
}

function reviewable(pr) {
  const labels = Array.isArray(pr.labels) ? pr.labels : [];
  return pr.state === 'open' &&
    !pr.draft && pr.head?.repo?.full_name === target &&
    shaPattern.test(pr.head?.sha || '') &&
    (!expectedSha || pr.head.sha.toLowerCase() === expectedSha.toLowerCase()) &&
    pr.user?.type !== 'Bot' && !/\[bot\]$/i.test(pr.user?.login || '') &&
    !labels.some((item) => item.name?.toLowerCase() === 'no-goblin');
}

async function changedFiles() {
  const found = [];
  for (let page = 1; page <= 3 && found.length < 300; page++) {
    const batch = await github(apiBase + '/pulls/' + number + '/files?per_page=100&page=' + page);
    found.push(...batch);
    if (batch.length < 100) break;
  }
  return selectReviewFiles(found, config);
}

async function repositoryContext(baseSha) {
  if (!shaPattern.test(baseSha || '')) return [];
  const paths = ['AGENTS.md', 'CLAUDE.md', 'package.json'];
  let remaining = config.maxContextChars;
  const context = [];
  for (const path of paths) {
    if (remaining <= 0) break;
    const result = await github(apiBase + '/contents/' + path +
      '?ref=' + encodeURIComponent(baseSha));
    if (!result || result.encoding !== 'base64' || typeof result.content !== 'string') continue;
    const decoded = Buffer.from(result.content.replace(/\s/g, ''), 'base64').toString('utf8');
    const excerpt = decoded.slice(0, remaining);
    if (!excerpt) continue;
    context.push({ path, content: excerpt });
    remaining -= excerpt.length;
  }
  return context;
}

async function previousReview(sha) {
  for (let page = 1; page <= 5; page++) {
    const reviews = await github(apiBase + '/pulls/' + number +
      '/reviews?per_page=100&page=' + page);
    if (reviews.some((r) => typeof r.body === 'string' &&
      r.body.startsWith(markerPrefix + sha + ' -->'))) return true;
    if (reviews.length < 100) break;
  }
  return false;
}

function safeXaiError(response, payload) {
  const error = payload?.error && typeof payload.error === 'object' ? payload.error : {};
  const safeCode = (value) => typeof value === 'string' && /^[a-zA-Z0-9_.-]{1,64}$/.test(value)
    ? value : null;
  const message = typeof error.message === 'string' ? error.message :
    typeof payload?.message === 'string' ? payload.message : '';
  const category = /credit|balance|billing|payment|insufficient|quota/i.test(message)
    ? 'account_quota_or_billing'
    : /rate.limit|too.many|throttl|capacity/i.test(message) ? 'rate_limit_or_capacity'
      : 'unspecified';
  return { xai: 'http_error', status: response.status,
    code: safeCode(error.code ?? payload?.code),
    type: safeCode(error.type ?? payload?.type),
    category, retryAfter: safeCode(response.headers.get('retry-after')) };
}

function formatFindings(items, sha) {
  return items.map((finding) => {
    const path = finding.path.replace(/[\r\n\]<>]/g, '');
    const url = 'https://github.com/' + target + '/blob/' + sha + '/' +
      finding.path.split('/').map(encodeURIComponent).join('/') + '#L' + finding.line;
    const title = finding.title.replace(/[\[\]<>]/g, '');
    const body = finding.body.replace(/<\/?script\b[^>]*>/gi, '');
    return '**' + finding.severity.toUpperCase() + '** [' + path + ':' + finding.line +
      '](' + url + ') · **' + title + '**\n\n' + body;
  });
}

const pr = await pullRequest();
if (!reviewable(pr)) {
  console.log('Skipped: closed, stale, draft, bot, fork or no-goblin.');
  process.exit(0);
}
const headSha = pr.head.sha.toLowerCase();
if (await previousReview(headSha)) {
  console.log('Skipped: Grok already reviewed this head.');
  process.exit(0);
}

const { files, total, complete } = await changedFiles();
if (!files.length) {
  console.log('Skipped: no reviewable textual patch.');
  process.exit(0);
}
const context = await repositoryContext(pr.base?.sha);
const input = {
  repository: target,
  pull_request: {
    number,
    title: String(pr.title || '').slice(0, 300),
    body: String(pr.body || '').slice(0, 2000),
  },
  base_branch_context: context,
  changed_files: files.map(({ path, patch }) => ({ path, patch })),
  scope: { totalFilesReturned: total, complete },
};

const response = await fetch('https://api.x.ai/v1/responses', {
  method: 'POST',
  headers: { Authorization: 'Bearer ' + xaiToken, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: config.model,
    store: false,
    reasoning: { effort: config.reasoningEffort },
    max_output_tokens: config.maxOutputTokens,
    prompt_cache_key: 'travnie-central-pr-review-v2',
    input: [
      { role: 'system', content: policy },
      { role: 'user', content: JSON.stringify(input) },
    ],
    text: {
      format: {
        type: 'json_schema', name: 'code_review', schema: REVIEW_SCHEMA, strict: true,
      },
    },
  }),
  signal: AbortSignal.timeout(config.xaiTimeoutMs),
});
if (!response.ok) {
  console.error(JSON.stringify(safeXaiError(response,
    await response.json().catch(() => null))));
  throw new Error('xai_request_failed:' + response.status);
}
const raw = await response.json();
const generated = parseReview(raw);
const findings = validFindings(generated, files, config.maxFindings);

const latest = await pullRequest();
if (!reviewable(latest) || latest.head.sha.toLowerCase() !== headSha) {
  console.log('Skipped: PR changed before publication.');
  process.exit(0);
}
if (await previousReview(headSha)) {
  console.log('Skipped: another Grok review already published.');
  process.exit(0);
}

const summary = generated.summary.trim().slice(0, 800);
const reviewLines = formatFindings(findings, headSha);
const disclaimer = complete ? '' : '\n\n_Partial review: the diff exceeded the bounded input window or contains unrendered files._';
const body = markerPrefix + headSha + ' -->\n' +
  reviewBadge(process.env.GITHUB_RUN_ID) + '\n\n' +
  '### Grok 4.7 · independent code review\n\n' +
  (reviewLines.length ? reviewLines.join('\n\n') : (summary || 'No high-confidence defects found in reviewed changes.')) +
  disclaimer;
await github(apiBase + '/pulls/' + number + '/reviews', 'POST',
  { commit_id: headSha, event: 'COMMENT', body });
const ticks = Number(raw.usage?.cost_in_usd_ticks);
const cost = Number.isFinite(ticks) && ticks >= 0 ? ticks / 1e10 : null;
const cachedTokens = Number(raw.usage?.input_tokens_details?.cached_tokens);
console.log(JSON.stringify({ review: 'submitted', repository: target, number,
  head: headSha, findings: findings.length, model: config.model,
  scopeComplete: complete, costUSD: cost,
  cachedInputTokens: Number.isFinite(cachedTokens) ? cachedTokens : null }));
if (process.env.GITHUB_STEP_SUMMARY) {
  await appendFile(process.env.GITHUB_STEP_SUMMARY,
    'Grok review: ' + target + '#' + number + ', ' + findings.length +
    ' findings, scope ' + (complete ? 'full' : 'partial') + ', cost ' +
    (cost === null ? 'unknown' : '$' + cost.toFixed(6)) + '\n');
}
