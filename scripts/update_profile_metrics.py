#!/usr/bin/env python3
"""Public GitHub statistics for the organization profile."""

import http.client
import json
import os
import sys
import urllib.parse
from pathlib import Path

OWNERS = (("user", "trvny"), ("org", "travnie"))
OUT = Path("assets/profile/metrics")
UA = "travnie-profile-metrics"


def api(path):
    if not path.startswith(("/search/issues?", "/users/trvny/repos?", "/orgs/travnie/repos?")):
        raise ValueError("unexpected GitHub API path")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": UA,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    connection = http.client.HTTPSConnection("api.github.com", timeout=20)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"GitHub API returned HTTP {response.status}")
        data = response.read(3_000_001)
        if len(data) > 3_000_000:
            raise ValueError("response too large")
        return json.loads(data)
    finally:
        connection.close()


def merged_pr_count():
    count = 0
    for kind, owner in OWNERS:
        q = urllib.parse.quote(f"is:pr is:merged {kind}:{owner}")
        result = api(f"/search/issues?q={q}&per_page=1")
        if result.get("incomplete_results") or not isinstance(result.get("total_count"), int):
            raise ValueError(f"incomplete PR search for {owner}")
        count += result["total_count"]
    return count


def repository_sizes():
    total, number = 0, 0
    for kind, owner in OWNERS:
        endpoint = f"/users/{owner}/repos?type=owner" if kind == "user" else f"/orgs/{owner}/repos?type=all"
        for page in range(1, 101):
            repos = api(f"{endpoint}&per_page=100&page={page}")
            if not isinstance(repos, list):
                raise ValueError("repository listing failed")
            for repo in repos:
                if repo.get("owner", {}).get("login", "").lower() != owner or repo.get("visibility") != "public":
                    continue
                kib = repo.get("size")
                if not isinstance(kib, int) or kib < 0:
                    raise ValueError("bad size: " + str(repo.get("full_name")))
                total += kib
                number += 1
            if len(repos) < 100:
                break
        else:
            raise ValueError(f"repository pagination exceeded for {owner}")
    return total, number


def icon(which):
    head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    if which == "pr":
        body = '<circle cx="6" cy="3" r="2"/><path d="M6 5v12"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="6" r="2"/><path d="M18 8v4a6 6 0 0 1-6 6H8"/>'
    else:
        body = '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3"/>'
    return head + body + "</svg>"


def badge(filename, label, message, color, logo):
    payload = {"schemaVersion": 1, "label": label, "message": message,
               "color": color, "logoSvg": icon(logo), "style": "flat-square"}
    (OUT / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        prs = merged_pr_count()
        badge("merged-prs.json", "merged PRs", f"{prs:,}", "8250df", "pr")
        print(f"merged PRs: {prs}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"::warning::merged PR count unavailable: {type(error).__name__}")
        if not (OUT / "merged-prs.json").exists():
            badge("merged-prs.json", "merged PRs", "unavailable", "9ca3af", "pr")
    try:
        kib, count = repository_sizes()
        size = f"{kib / 1048576:.2f} GiB" if kib >= 1048576 else f"{kib / 1024:.1f} MiB"
        badge("repo-size.json", "repo size", size, "0969da", "size")
        print(f"public repositories: {count}; reported size: {kib} KiB")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"::warning::repository size unavailable: {type(error).__name__}")
        if not (OUT / "repo-size.json").exists():
            badge("repo-size.json", "repo size", "unavailable", "9ca3af", "size")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"::error::{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
