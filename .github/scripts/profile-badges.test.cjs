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
      repos: { listForUser, listForOrg,
        listCommits: async ({owner, repo}) => ({data: owner === "travnie" && repo === "aistee" ? [
          {sha: "a".repeat(40), author: {login: "gptomek[bot]"},
            commit: {message: "fix: model routing & escaping",
              committer: {date: "2026-11-08T09:00:00Z"}}},
          {sha: "b".repeat(40), commit: {message: "chore(profile): refresh badges [skip ci]",
              committer: {date: "2026-11-08T10:00:00Z"}}},
        ] : [{sha: "c".repeat(40), author: {login: "trvny"},
          commit: {message: "feat: live updates", committer: {date: "2026-11-07T12:00:00Z"}}}]}),
      },
    },
    paginate: async (method) => method === listForUser
      ? [{ owner: { login: "trvny" }, name: "trvny", full_name: "trvny/trvny",
          visibility: "public", size: 1024 },
        { owner: { login: "trvny" }, name: "secret", full_name: "trvny/secret",
          visibility: "private", private: true, size: 9999 }]
      : [{ owner: { login: "travnie" }, name: "aistee", full_name: "travnie/aistee",
          visibility: "public", size: 2048 },
        { owner: { login: "travnie" }, name: "upstream", full_name: "travnie/upstream",
          visibility: "public", fork: true, size: 0 }],
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
    const prs = fs.readFileSync(path.join(dir, "merged-prs.svg"), "utf8");
    const size = fs.readFileSync(path.join(dir, "repo-size.svg"), "utf8");
    const activity = fs.readFileSync(path.join(dir, "activity.svg"), "utf8");
    assert.match(prs, /<svg xmlns="http:\/\/www.w3.org\/2000\/svg"/);
    assert.match(prs, /<circle cx="6"/);
    assert.ok(prs.includes(failSearch ? ">unavailable</text>" : ">1,801</text>"));
    assert.ok(size.includes(">3.0 MiB</text>"));
    assert.match(activity, /fix: model routing &amp; escaping/);
    assert.match(activity, /travnie\/aistee/);
    assert.match(activity, /gptomek\[bot\]/);
    assert.doesNotMatch(activity, /refresh badges/);
    assert.doesNotMatch(activity, /travnie\/upstream/);
    assert.equal(warnings.length, failSearch ? 1 : 0);
  } finally {
    fs.rmSync(dir, { force: true, recursive: true });
  }
}

test("counts merged PRs and only public repository size", () => runTest(false));
test("a failed request does not erase the other badge", () => runTest(true));
