import { appendFile } from 'node:fs/promises';

const audience = 'https://automation.travny.workers.dev/grok-review/token';
const repository = process.env.TARGET_REPOSITORY || '';
if (!/^(?:trvny|travnie)\/[A-Za-z0-9_.-]+$/.test(repository)) {
  throw new Error('invalid_repository');
}
if (!process.env.ACTIONS_ID_TOKEN_REQUEST_URL ||
    !process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN ||
    !process.env.GITHUB_OUTPUT) {
  throw new Error('github_oidc_unavailable');
}

const url = new URL(process.env.ACTIONS_ID_TOKEN_REQUEST_URL);
url.searchParams.set('audience', audience);
const jwtResponse = await fetch(url, {
  headers: { Authorization: 'Bearer ' + process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN },
  signal: AbortSignal.timeout(10_000),
});
if (!jwtResponse.ok) throw new Error('github_oidc_request_failed:' + jwtResponse.status);
const jwt = (await jwtResponse.json()).value;
if (typeof jwt !== 'string' || !jwt) throw new Error('invalid_github_oidc_response');

const exchange = await fetch(audience, {
  method: 'POST',
  headers: {
    Authorization: 'Bearer ' + jwt,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ repository }),
  signal: AbortSignal.timeout(30_000),
});
if (!exchange.ok) throw new Error('review_bot_exchange_failed:' + exchange.status);
const data = await exchange.json();
if (typeof data.token !== 'string' || !data.token.startsWith('ghs_')) {
  throw new Error('invalid_review_bot_exchange_response');
}

console.log('::add-mask::' + data.token);
await appendFile(process.env.GITHUB_OUTPUT, 'token=' + data.token + '\n');
console.log('Short-lived repository-scoped GitHub App token obtained.');
