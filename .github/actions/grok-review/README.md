# Grok PR Review

Central, read-only-first **composite GitHub Action** for `trvny/*` and
`travnie/*`. The calling workflow is
[`grok-review.yml`](../../workflows/grok-review.yml). Other repositories
do not need their own workflow.

## Flow

1. Kanarek's verified GitHub webhook dispatches a bounded PR target.
2. The central workflow requests GitHub OIDC. The Cloudflare Worker verifies
   the signed identity and issues a repository-scoped Kanarek App token.
3. The Action reads the current PR, base-branch `AGENTS.md` /
   `CLAUDE.md` / `package.json` (when available), and ranked unified diffs.
4. xAI **Responses API** runs `grok-4.7` with a versioned
   [review policy](review-policy.md) and strict JSON Schema.
5. The Action validates each finding against an actual changed line,
   checks the PR head again, and submits one native review per head SHA.
6. The native review uses the existing
   [Grok SVG](../../../assets/badges/grok.svg), linked to its Actions run.

## Configuration

Edit [`config.json`](config.json) to choose the model, reasoning effort,
context and diff budgets, response size, and timeouts. Review quality rules
live only in [`review-policy.md`](review-policy.md); the response contract
and diff validation live in [`src/review-utils.mjs`](src/review-utils.mjs).
No extra npm dependencies or installation step.

The model is called directly by API, **not Grok Build CLI**. Build supports
headless runs and plugins, but would require checking out untrusted PR
code, installing a mutable CLI, and allowing extra tools. For automatic
code review we intentionally keep tools disabled. Available read-only
context and strict structured output provide a smaller attack surface
and more predictable costs.

## Controls

- Untrusted PR branches are **never checked out** in the review job.
- Only `trvny/*` and `travnie/*`, same-repo, non-draft, non-bot PRs.
- `no-goblin` opts out.
- PR content is untrusted data; model responses are validated and anchored
  to actual added lines.
- No automatic retries after uncertain GitHub writes or xAI API failures.
- Partial scope is disclosed when file/diff budgets truncate input.
- Provider error logs include bounded codes/categories, not response bodies.
- Model spending is metered; see private Actions summaries for cost.
- Disable dispatch independently with `GROK_REVIEW_DISPATCH_ENABLED=false`
  in the shared Worker configuration.

Run the tests with:

```bash
node --test .github/actions/grok-review/test/*.test.mjs
```

The `syntax` job runs tests without API secrets. A successful CI check
does not substitute for a live, separately monitored inference run.
