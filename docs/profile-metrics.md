# Profile metrics

[Workflow](../.github/workflows/profile-metrics.yml) refreshes daily (04:43 UTC), on relevant pushes, or on demand.

## Merged pull requests
All-time merged PRs across public repos owned by `trvny` and `travnie`. GitHub search totals from `is:pr is:merged user:trvny` and `is:pr is:merged org:travnie`. Not a count of PRs authored by one person.

## Repository size
Sum of GitHub REST repository `size` values (KiB) for public repos under both owners. Includes forks and archived repos; excludes private repos, LFS and full clone/working-tree sizes. Approximate GitHub metadata, not disk usage.

## Recent commits
[Native generator](../.github/scripts/profile-badges.cjs) lists the latest commits on default branches of public, non-archived, non-fork repositories owned by `trvny` and `travnie`. Shows repository, commit subject, author and date; skips routine profile-refresh commits. This measures repository activity including bots, not events attributed to an organization login. Only the latest four commits per repository are queried; the newest six overall appear on the card. It is a snapshot, not a complete commit count.

## RSS
[JBZD via Feedseek](https://trvny.github.io/feedseek/jbzd.xml) is rendered with [Lowlighter Metrics](https://github.com/lowlighter/metrics), using the existing Atom feed. No second feed generator, aggregation or cache.

Assets: [merged PRs](../assets/profile/metrics/merged-prs.svg), [repository size](../assets/profile/metrics/repo-size.svg), [latest commits](../assets/profile/metrics/activity.svg), [JBZD RSS](../assets/profile/metrics/rss.svg). Do not manually edit generated SVGs.

**Partial outages:** native cards retain their last good version if a GitHub API request fails (or display an explicit unavailable state on first run). RSS renders independently.

**Runners:** native cards and tests use `ubuntu-slim`. RSS rendering uses `ubuntu-latest` because Lowlighter's action requires Docker.
