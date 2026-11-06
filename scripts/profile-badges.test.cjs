"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const generate = require("./profile-badges.cjs");

function fakeGithub(failSearch = false) {
  const listForUser = () => {};
  const listForOrg = () => {};
  return {
    rest: {
      search: {
        issuesAndPullRequests: async ({ q }) => {
          if (failSearch) throw new Error("Unavailable");
          return { data: { total_count: q.includes("user:") ? 1234 : 567,
            incomplete_results: false } };
        },
      },
      repos: { listForUser, listForOrg },
    },
    paginate: async (method) => method === listForUser
      ? [{ owner: { login: "trvny" }, visibility: "public", size: 1024 },
        { owner: { login: "trvny" }, visibility: "private", size: 9999 }]
      : [{ owner: { login: "travnie" }, visibility: "public", size: 2048 }],
  };
}

async function runTest(failSearch) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "profile-badges-"));
  try {
    const warnings = [];
    await generate({
      github: fakeGithub(failSearch),
      core: { info() {}, warning(msg) { warnings.push(msg); } },
      outputDir: dir,
    });
    const prs = JSON.parse(fs.readFileSync(path.join(dir, "merged-prs.json")));
    const size = JSON.parse(fs.readFileSync(path.join(dir, "repo-size.json")));
    assert.equal(prs.schemaVersion, 1);
    assert.ok(prs.logoSvg.includes("<svg"));
    assert.equal(prs.message, failSearch ? "unavailable" : "1,801");
    assert.equal(size.message, "3.0 MiB");
    assert.equal(warnings.length, failSearch ? 1 : 0);
  } finally {
    fs.rmSync(dir, { force: true, recursive: true });
  }
}

test("counts merged PRs and only public repository size", () => runTest(false));
test("a failed request does not erase the other badge", () => runTest(true));
