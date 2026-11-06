# Profile metrics

Source: [Lowlighter Metrics](https://github.com/lowlighter/metrics). [Workflow](../.github/workflows/profile-metrics.yml) refreshes daily (04:43 UTC) or on demand, using public GitHub data.

## Merged pull requests
All-time merged PRs across public repos owned by `trvny` and `travnie`. GitHub search totals from `is:pr is:merged user:trvny` and `is:pr is:merged org:travnie`. Not a count of PRs authored by one person.

## Repository size
Sum of GitHub REST repository `size` values (KiB) for public repos under both owners. Includes forks and archived repos; excludes private repos, LFS and full clone/working-tree sizes. Approximate GitHub metadata, not disk usage.

## Feeds and cards
RSS source list extracted from the default `README_FEED_URLS` entries in [upkeep.yml](https://github.com/trvny/.github/blob/main/.github/workflows/upkeep.yml). Up to three newest items per source, deduplicated and mixed (14 entries maximum); an organization-specific repository variable override in the other repo cannot be read here. The Metrics RSS plugin accepts one feed, so it reads the generated `upkeep.xml`.

Cards: RSS; public activity + random public code + mildly interesting habits; lines in terminal template. Badge values: [merged PRs](../assets/profile/metrics/merged-prs.json), [repository size](../assets/profile/metrics/repo-size.json). Generated SVGs and JSON belong to this workflow. No manual edits.

For activity, code, habits, and lines, add a repository/org secret `METRICS_TOKEN` with read access to the public organization metadata (`read:org`) and public repository data. Existing `GH_PAT` may be used instead. Without either secret, RSS and badges still refresh; the GitHub-backed cards are skipped (first run: setup placeholder SVG, later runs: last generated card retained). The built-in `GITHUB_TOKEN` is not a substitute for organization-wide Metrics API access.

**Partial outages:** the generator deliberately publishes cached values or explicit unavailable badges and logs `::warning::` on per-source failures. The workflow may stay green while one upstream source is unavailable; the other sources and cards continue refreshing. GitHub Actions logs are the diagnostic record.
