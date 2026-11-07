"use strict";

const fs = require("node:fs");
const path = require("node:path");

const OWNERS = [
  { owner: "trvny", kind: "user", search: "is:pr is:merged user:trvny" },
  { owner: "travnie", kind: "org", search: "is:pr is:merged org:travnie" },
];

function logo(which) {
  const shape = which === "pr"
    ? '<circle cx="6" cy="3" r="2"/><path d="M6 5v12"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="6" r="2"/><path d="M18 8v4a6 6 0 0 1-6 6H8"/>'
    : '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3"/>';
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + shape + "</svg>";
}

function save(dir, file, label, message, color, which) {
  fs.writeFileSync(path.join(dir, file), JSON.stringify({
    schemaVersion: 1, label, message, color, logoSvg: logo(which), style: "flat-square",
  }, null, 2) + "\n");
}

async function mergedPullRequests(github) {
  let count = 0;
  for (const entry of OWNERS) {
    const { data } = await github.rest.search.issuesAndPullRequests({
      q: entry.search, per_page: 1,
    });
    if (!Number.isSafeInteger(data.total_count) || data.incomplete_results) {
      throw new Error("Incomplete PR search for " + entry.owner);
    }
    count += data.total_count;
  }
  return count;
}

async function repositorySizes(github) {
  let kib = 0;
  let count = 0;
  for (const { owner, kind } of OWNERS) {
    const repositories = kind === "org"
      ? await github.paginate(github.rest.repos.listForOrg, { org: owner, type: "all", per_page: 100 })
      : await github.paginate(github.rest.repos.listForUser, { username: owner, type: "owner", per_page: 100 });
    for (const repo of repositories) {
      if (repo.owner?.login?.toLowerCase() !== owner || repo.visibility !== "public") continue;
      if (!Number.isSafeInteger(repo.size) || repo.size < 0) {
        throw new Error("Invalid size for " + repo.full_name);
      }
      kib += repo.size;
      count++;
    }
  }
  return { kib, count };
}

module.exports = async function generateProfileBadges({
  github, core, outputDir = "assets/profile/metrics",
}) {
  fs.mkdirSync(outputDir, { recursive: true });
  async function update(file, label, color, which, calculate) {
    try {
      const message = await calculate();
      save(outputDir, file, label, message, color, which);
      core.info(label + ": " + message);
    } catch (error) {
      core.warning(label + " unavailable: " + error.message);
      if (!fs.existsSync(path.join(outputDir, file))) {
        save(outputDir, file, label, "unavailable", "9ca3af", which);
      }
    }
  }

  await update("merged-prs.json", "merged PRs", "8250df", "pr",
    async () => (await mergedPullRequests(github)).toLocaleString("en-US"));
  await update("repo-size.json", "repo size", "0969da", "size", async () => {
    const { kib, count } = await repositorySizes(github);
    core.info("Public repositories: " + count);
    return kib >= 1048576 ? (kib / 1048576).toFixed(2) + " GiB"
      : (kib / 1024).toFixed(1) + " MiB";
  });
};
