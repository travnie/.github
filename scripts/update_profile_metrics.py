#!/usr/bin/env python3
"""Public profile totals and upkeep RSS bridge."""

import http.client
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

OWNERS = (("user", "trvny"), ("org", "travnie"))
UPKEEP = "https://raw.githubusercontent.com/trvny/.github/main/.github/workflows/upkeep.yml"
OUT = Path("assets/profile/metrics")
UA = "travnie-profile-metrics"


def fetch(url, auth=False):
    headers = {"User-Agent": UA}
    if auth:
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        data = response.read(3_000_001)
        if len(data) > 3_000_000:
            raise ValueError("response too large")
        return data


def api(path):
    return json.loads(fetch("https://api.github.com" + path, auth=True))


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


def upkeep_sources(text):
    lines = text.splitlines()
    index = next((i for i, line in enumerate(lines) if re.match(r"^\s+README_FEED_URLS:\s*[>|][-+]?\s*$", line)), None)
    if index is None:
        raise ValueError("upkeep RSS configuration not found")
    indent = len(lines[index]) - len(lines[index].lstrip())
    section = []
    for line in lines[index + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        if not line.lstrip().startswith("#"):
            section.append(line.strip().split(" #", 1)[0])
    urls = list(dict.fromkeys(re.findall(r"https?://[^\s,'}\"]+", "\n".join(section))))
    if not urls:
        raise ValueError("upkeep RSS sources missing")
    return urls


def child_text(node, key):
    for child in node:
        if child.tag.split("}")[-1] == key:
            return "".join(child.itertext()).strip()
    return ""


def parse_date(value):
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def entries(data, source):
    root = SafeET.fromstring(data)
    host = urllib.parse.urlsplit(source).hostname or "feed"
    kind = root.tag.split("}")[-1]
    if kind == "feed":
        title = child_text(root, "title") or host
        out = []
        for item in (x for x in root if x.tag.split("}")[-1] == "entry"):
            link = next((x.get("href", "") for x in item if x.tag.split("}")[-1] == "link" and x.get("rel", "alternate") == "alternate"), "")
            link = link or child_text(item, "id")
            name = child_text(item, "title")
            if name and link.startswith("http"):
                date = parse_date(child_text(item, "published") or child_text(item, "updated"))
                out.append((date, f"[{title}] {name}", link))
        return sorted(out, key=lambda item: item[0], reverse=True)[:3]
    channel = next((x for x in root if x.tag.split("}")[-1] == "channel"), None)
    if channel is None:
        raise ValueError("not RSS or Atom")
    title = child_text(channel, "title") or host
    parent = root if kind == "RDF" else channel
    out = []
    for item in (x for x in parent if x.tag.split("}")[-1] == "item"):
        name, link = child_text(item, "title"), child_text(item, "link")
        if name and link.startswith("http"):
            date = parse_date(child_text(item, "pubDate") or child_text(item, "date"))
            out.append((date, f"[{title}] {name}", link))
    return sorted(out, key=lambda item: item[0], reverse=True)[:3]


def refresh_rss():
    urls = upkeep_sources(fetch(UPKEEP).decode("utf-8"))
    items = []
    for url in urls:
        try:
            current = entries(fetch(url), url)
            items.extend(current)
            print(f"rss: {len(current)} items from {urllib.parse.urlsplit(url).hostname}")
        except (OSError, ValueError, ET.ParseError, DefusedXmlException, http.client.HTTPException) as error:
            print(f"::warning::rss source unavailable: {urllib.parse.urlsplit(url).hostname} ({type(error).__name__})")
    if not items:
        if not (OUT / "upkeep.xml").is_file():
            raise ValueError("no feed items and no existing cache")
        return
    unique, seen = [], set()
    for item in sorted(items, reverse=True):
        if item[2] not in seen:
            seen.add(item[2])
            unique.append(item)
        if len(unique) == 14:
            break
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for name, text in (("title", "Upkeep feed mix"), ("link", "https://github.com/trvny/.github/blob/main/.github/workflows/upkeep.yml"), ("description", "Feed sources from trvny/.github upkeep")):
        ET.SubElement(channel, name).text = text
    for date, title, link in unique:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title[:220]
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid", isPermaLink="true").text = link
        ET.SubElement(item, "pubDate").text = format_datetime(date)
    ET.indent(rss)
    (OUT / "upkeep.xml").write_bytes(ET.tostring(rss, encoding="utf-8", xml_declaration=True))
    print(f"rss: {len(unique)} distinct entries from {len(urls)} upstream sources")


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
    try:
        refresh_rss()
    except (OSError, ValueError, KeyError, DefusedXmlException, http.client.HTTPException) as error:
        print(f"::warning::RSS refresh unavailable: {type(error).__name__}")
        if not (OUT / "upkeep.xml").exists():
            root = ET.Element("rss", version="2.0")
            channel = ET.SubElement(root, "channel")
            ET.SubElement(channel, "title").text = "Upkeep feed mix"
            ET.SubElement(channel, "link").text = "https://github.com/trvny/.github"
            ET.SubElement(channel, "description").text = "Feeds temporarily unavailable"
            (OUT / "upkeep.xml").write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"::error::{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
