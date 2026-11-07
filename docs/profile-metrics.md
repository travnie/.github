# Profile metrics

Source: [Lowlighter Metrics](https://github.com/lowlighter/metrics). [Workflow](../.github/workflows/profile-metrics.yml) refreshes daily (04:43 UTC) or on demand, using public GitHub data.

## Merged pull requests
All-time merged PRs across public repos owned by `trvny` and `travnie`. GitHub search totals from `is:pr is:merged user:trvny` and `is:pr is:merged org:travnie`. Not a count of PRs authored by one person.

## Repository size
Sum of GitHub REST repository `size` values (KiB) for public repos under both owners. Includes forks and archived repos; excludes private repos, LFS and full clone/working-tree sizes. Approximate GitHub metadata, not disk usage.

## Feeds and cards

RSS displays only [JBZD](https://trvny.github.io/feedseek/jbzd.xml) using the existing [Feedseek](https://github.com/trvny/feedseek) Atom feed. No second feed generator, aggregation or cache.

Cards: JBZD RSS; public activity + random public code + mildly interesting habits. Generated assets: [merged PRs](../assets/profile/metrics/merged-prs.svg), [repository size](../assets/profile/metrics/repo-size.svg), and Metrics SVG cards. Badges are generated directly, without Shields. Do not manually edit.

For activity, code and habits, add a repository/org secret `METRICS_TOKEN` with read access to the public organization metadata (`read:org`) and public repository data. Existing `GH_PAT` may be used instead. Without either secret, RSS and badges still refresh; the GitHub-backed cards are skipped (first run: setup placeholder SVG, later runs: last generated card retained). The built-in `GITHUB_TOKEN` is not a substitute for organization-wide Metrics API access.

**Partial outages:** badge generation uses cached values or explicit unavailable badges and emits warnings when GitHub API data fails. RSS is rendered independently from Feedseek.

**Runners:** badge generation and tests use `ubuntu-slim`. Metrics rendering stays on `ubuntu-latest` because its containerized action requires Docker.
