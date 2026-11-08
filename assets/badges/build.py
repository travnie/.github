#!/usr/bin/env python3
"""Build brand badges (icon tile + label) and README snippets.

Icons: @lobehub/icons-static-svg (MIT). Usage:
  npm pack @lobehub/icons-static-svg && tar xzf lobehub-icons-static-svg-*.tgz
  python3 assets/badges/build.py package/icons
Needs Pillow + a bold font for label widths (DejaVu Sans/Verdana; BADGE_FONT to override).

Style mirrors docs7.svg (hand-made, not generated). Add a badge = add a BADGES row.

Ecosystem badges (twojstar, apps, bots, reviewers) are snapshots of the live
service at travny.pages.dev/badge (source: trvny/trvny pages/functions/_shared/eco.js);
add them there, then rerun to refresh. Live counters/status stay links, never snapshots.
--offline: skip the live service, reuse eco.json (last snapshot manifest).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import ImageFont

HERE = Path(__file__).resolve().parent
RAW = "https://raw.githubusercontent.com/travnie/.github/main/assets/badges"
CDN = "https://cdn.jsdelivr.net/gh/travnie/.github@main/assets/badges"
# Label width metrics only (render uses Verdana). Override: BADGE_FONT=/path/to/bold.ttf
FONTS = [
    os.environ.get("BADGE_FONT", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Debian/Ubuntu
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",  # Fedora
    "/Library/Fonts/Verdana Bold.ttf",  # macOS
    "C:/Windows/Fonts/verdanab.ttf",  # Windows
    "DejaVuSans-Bold.ttf",  # Pillow font search path
]
H, TILE, PAD = 28, 34, 12

# group, slug, label, lobe icon, link, gradient start, gradient end, extra
# extra: ink = colour for mono icons, tile = tile bg, text = label colour
BADGES = [
    ("Infra", "cloudflare", "Cloudflare", "cloudflare-color", "https://www.cloudflare.com", "#f6821f", "#c85a08", {}),
    ("Infra", "workers-ai", "Workers AI", "workersai-color", "https://developers.cloudflare.com/workers-ai/", "#f38020", "#a8420a", {}),
    ("Infra", "mcp", "MCP", "mcp", "https://modelcontextprotocol.io", "#33302c", "#0b0b0b", {"ink": "#111111"}),
    ("Infra", "github", "GitHub", "github", "https://github.com", "#2d333b", "#0d1117", {"ink": "#0d1117"}),
    ("Infra", "copilot", "Copilot", "githubcopilot", "https://github.com/features/copilot", "#8957e5", "#5a32a3", {"ink": "#6e40c9"}),
    ("Routers", "openrouter", "OpenRouter", "openrouter", "https://openrouter.ai", "#6467f2", "#3b3cb8", {"ink": "#4f50d6"}),
    ("Routers", "aihubmix", "AiHubMix", "aihubmix-color", "https://aihubmix.com", "#2f8bff", "#0057c8", {}),
    ("Routers", "groq", "Groq", "groq", "https://groq.com", "#f55036", "#c2321c", {"ink": "#f55036"}),
    ("Routers", "huggingface", "Hugging Face", "huggingface-color", "https://huggingface.co", "#ffd21e", "#ff9d00", {"text": "#2a1a00"}),
    ("Routers", "ollama", "Ollama", "ollama", "https://ollama.com", "#3a3a3a", "#111111", {"ink": "#111111"}),
    ("Models", "claude", "Claude", "claude-color", "https://claude.ai", "#d97757", "#ae5131", {}),
    ("Models", "claude-code", "Claude Code", "claudecode-color", "https://claude.com/product/claude-code", "#d97757", "#8f3f22", {}),
    ("Models", "anthropic", "Anthropic", "anthropic", "https://www.anthropic.com", "#3d3a33", "#141413", {"ink": "#141413", "tile": "#f0eee6"}),
    ("Models", "gpt", "GPT", "openai", "https://chatgpt.com", "#10a37f", "#0a7559", {"ink": "#0a7559"}),
    ("Models", "openai", "OpenAI", "openai", "https://openai.com", "#2e2e2e", "#0d0d0d", {"ink": "#0d0d0d"}),
    ("Models", "codex", "Codex", "codex-color", "https://openai.com/codex/", "#2e2e2e", "#0d0d0d", {}),
    ("Models", "gemini", "Gemini", "gemini-color", "https://gemini.google.com", "#4285f4", "#8e63d2", {}),
    ("Models", "google", "Google", "google-color", "https://ai.google.dev", "#4285f4", "#1a5fd0", {}),
    ("Models", "deepseek", "DeepSeek", "deepseek-color", "https://www.deepseek.com", "#4d6bfe", "#2b48d4", {}),
    ("Models", "qwen", "Qwen", "qwen-color", "https://qwen.ai", "#615ced", "#3d36c4", {}),
    ("Models", "kimi", "Kimi", "kimi-color", "https://www.kimi.com", "#1783ff", "#0a55c9", {}),
    ("Models", "glm", "GLM", "zai", "https://z.ai", "#3a3a3a", "#111111", {"ink": "#111111"}),
    ("Models", "grok", "Grok", "grok", "https://grok.com", "#3a3a3a", "#000000", {"ink": "#000000"}),
    ("Models", "mistral", "Mistral", "mistral-color", "https://mistral.ai", "#fa520f", "#c73e00", {}),
]
# hand-made badges kept as-is, listed in README only
EXTRA = [("Infra", "docs7", "Docs7", "https://travnie.docs7.io/")]

LIVE = "https://travny.pages.dev"
ECO_GROUPS = ["Brand", "Apps", "Workshop", "Bots", "Reviewers"]
ECO_LINKS = {
    "twojstar": "https://github.com/travnie",
    "papiesz": "https://travny.pages.dev/papagenerator/",
    "papagenerator": "https://travny.pages.dev/papagenerator/",
    "feedseek": "https://trvny.github.io/feedseek/",
    "kanarek": "https://github.com/travnie/kanarek",
    "autka": "https://github.com/travnie/Autka",
    "tvpi": "https://travny.pages.dev/tv/",
    "aistee": "https://github.com/travnie/aistee",
    "benches": "https://github.com/travnie/twojstar",
    "codebench": "https://codebench.travny.workers.dev/",
    "streambench": "https://streambench.travny.workers.dev/",
    "docbench": "https://docbench.travny.workers.dev/",
    "spacemolt": "https://github.com/travnie/twojstar",
}
# live-only routes -> link target; anything else in the catalogue's Live group links to /badges/
LIVE_LINKS = {
    "feedseek/feeds": "https://trvny.github.io/feedseek/",
    "tvpi/channels": "https://travny.pages.dev/tv/",
    "status/kanarek": "https://kanarek.travny.workers.dev/health",
    "status/tvpi": "https://travny.pages.dev/tv/",
    "status/feedseek": "https://trvny.github.io/feedseek/",
    "status/docbench": "https://docbench.travny.workers.dev/",
}
MARKS = ["twojstar", "papiesz", "kanarek", "autka", "tvpi"]  # bare logos, 128px
MANIFEST = HERE / "eco.json"  # last snapshot: eco rows + live rows; drives stale cleanup and --offline
SAFE_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
UNSAFE_SVG = re.compile(r"<script|<foreignObject|\son\w+\s*=|(?:href\s*=|url\()\s*(?:[\"'](?!#)|(?![\"'#]))", re.I)


def load_font():
    """First loadable bold font -> (font, width scale vs Verdana Bold)."""
    for path in filter(None, FONTS):
        try:
            return ImageFont.truetype(path, 11), 1.0 if "verdana" in path.lower() else 1.07
        except OSError:
            continue
    sys.exit("no bold font for label metrics; set BADGE_FONT=/path/to/DejaVuSans-Bold.ttf or Verdana Bold")


def icon_body(path: Path, slug: str, ink: str) -> tuple[str, str]:
    # icons dir comes from argv: keep reads inside it (CodeQL py/path-injection)
    root = os.path.realpath(path.parent)
    full = os.path.realpath(path)
    if not full.startswith(root + os.sep) or not full.endswith(".svg"):
        sys.exit(f"icon path escapes icons dir: {path}")
    with open(full, encoding="utf-8") as fh:
        src = fh.read()
    m = re.match(r"\s*<svg([^>]*)>(.*)</svg>\s*$", src, re.S)
    attrs, body = m.group(1), m.group(2)
    body = re.sub(r"<title>.*?</title>", "", body, flags=re.S)
    body = re.sub(r'id="([^"]+)"', rf'id="{slug}-\1"', body)
    body = re.sub(r"url\(#([^)]+)\)", rf"url(#{slug}-\1)", body)
    body = re.sub(r'href="#([^"]+)"', rf'href="#{slug}-\1"', body)
    body = body.replace("></path>", "/>").replace("currentColor", ink)
    keep = ""
    if 'fill="currentColor"' in attrs:
        keep += f' fill="{ink}"'
    if 'fill-rule="evenodd"' in attrs:
        keep += ' fill-rule="evenodd"'
    return keep, body


def badge(slug, label, icon, c1, c2, ex, icons: Path, font, scale) -> str:
    ink, tile, text = ex.get("ink", "#111111"), ex.get("tile", "#f8fafc"), ex.get("text", "#fff")
    tw = font.getlength(label) * scale  # Verdana runs ~7% wider than DejaVu
    lw = round(tw + 2 * PAD)
    w = TILE + lw
    keep, body = icon_body(icons / f"{icon}.svg", slug, ink)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" viewBox="0 0 {w} {H}" role="img" aria-label="{label}">
  <title>{label}</title>
  <defs>
    <linearGradient id="{slug}-g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="{slug}-shine" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity=".14"/>
      <stop offset=".55" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="{slug}-clip"><rect width="{w}" height="{H}" rx="6"/></clipPath>
  </defs>
  <g clip-path="url(#{slug}-clip)">
    <rect width="{TILE}" height="{H}" fill="{tile}"/>
    <rect x="{TILE}" width="{lw}" height="{H}" fill="url(#{slug}-g)"/>
    <rect x="{TILE}" width="{lw}" height="14" fill="url(#{slug}-shine)"/>
    <rect x="{TILE}" width="1" height="{H}" fill="{c2}" fill-opacity=".5"/>
  </g>
  <rect x=".5" y=".5" width="{w - 1}" height="{H - 1}" rx="5.5" fill="none" stroke="{c2}" stroke-opacity=".55"/>
  <!-- icon: lobehub/lobe-icons ({icon}), MIT -->
  <svg x="8" y="5" width="18" height="18" viewBox="0 0 24 24"{keep}>{body}</svg>
  <text x="{TILE + lw / 2:g}" y="18.5" text-anchor="middle" fill="{text}" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" font-weight="700" text-rendering="geometricPrecision">{label}</text>
</svg>
"""


def fetch(path: str) -> str:
    req = urllib.request.Request(LIVE + path, headers={"user-agent": "travnie-badges-build"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.read().decode()
    except (urllib.error.URLError, TimeoutError) as e:
        raise SystemExit(f"{path}: {e}; rerun later or use --offline") from e


def checked_svg(name: str, svg: str, icon: bool) -> str:
    """Reject non-SVG, unsafe or icon-less responses before anything is written."""
    if not re.match(r"\s*<svg\b", svg) or UNSAFE_SVG.search(svg):
        raise SystemExit(f"{name}: not a clean SVG")
    if icon and svg.count("<svg") < 2:  # badge = root svg + nested icon svg
        raise SystemExit(f"{name}: snapshot without icon, retry later")
    return svg


def snapshot_eco() -> tuple[list, list]:
    """Download ecosystem badges + marks, write only when all succeeded; return (eco rows, live rows)."""
    catalogue = json.loads(fetch("/badge/index.json"))
    rows, live, files = [], [], {}
    for row in catalogue["badges"]:
        if row["group"] == "Live":
            live.append((row["slug"], LIVE_LINKS.get(row["slug"], LIVE + "/badges/")))
            continue
        if row["group"] not in ECO_GROUPS:
            continue
        slug = row["slug"]
        if not SAFE_SLUG.fullmatch(slug):
            raise SystemExit(f"unsafe slug in catalogue: {slug!r}")
        files[f"{slug}.svg"] = checked_svg(slug, fetch(row["path"]), icon=True)
        rows.append([row["group"], slug, row["label"], ECO_LINKS.get(slug, LIVE + "/badges/")])
    for slug in MARKS:
        files[f"mark-{slug}.svg"] = checked_svg(f"mark-{slug}", fetch(f"/badge/mark/{slug}.svg?size=128"), icon=False)
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"eco": []}
    for _, slug, *_ in old["eco"]:
        if SAFE_SLUG.fullmatch(slug) and f"{slug}.svg" not in files:
            (HERE / f"{slug}.svg").unlink(missing_ok=True)  # dropped upstream
    for name, svg in files.items():
        (HERE / name).write_text(svg)
    MANIFEST.write_text(manifest(rows, live))
    return rows, live


def manifest(rows, live) -> str:
    """One row per line: readable diffs."""
    lines = lambda xs: ",\n".join(" " + json.dumps(list(x)) for x in xs)  # noqa: E731
    return f'{{"eco": [\n{lines(rows)}\n], "live": [\n{lines(live)}\n]}}\n'


def md_text(s: str) -> str:
    return re.sub(r"([\[\]|\\])", r"\\\1", s)


def attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def readme(rows, live) -> str:
    out = [
        "# Badges",
        "",
        "Brand badges for READMEs, comments and sites. 28 px tall, same style as `docs7.svg`.",
        "Generated by `build.py` (icons: [lobe-icons](https://github.com/lobehub/lobe-icons), MIT) - edit `BADGES` there, rerun, commit.",
        "Ecosystem groups (Brand, Apps, Workshop, Bots, Reviewers) and marks are snapshots of the live service:"
        " change them in trvny/trvny `pages/functions/_shared/eco.js`, deploy, then rerun `build.py` (not `BADGES`).",
        "",
        "- Markdown: `raw.githubusercontent.com` (fine on GitHub).",
        "- HTML / Pages / external sites: jsDelivr (proper `image/svg+xml`, cached; purge `https://purge.jsdelivr.net/gh/travnie/.github@main/assets/badges/<name>.svg` after changes).",
        "- Row of badges: separate with a space; in HTML add `style=\"vertical-align:middle\"` if mixed with text.",
        "",
    ]
    group = None
    for g, slug, label, href in rows:
        if g != group:
            group = g
            out += [f"## {g}", "", "| Badge | Markdown | HTML |", "|---|---|---|"]
        md = f"[![{md_text(label)}]({RAW}/{slug}.svg)]({href})"
        html = f'<a href="{attr(href)}"><img src="{CDN}/{slug}.svg" alt="{attr(label)}" height="28"></a>'
        cell = lambda s: s.replace("|", "\\|")  # noqa: E731 - pipes inside table code spans
        out.append(f"| {md} | `{cell(md)}` | `{cell(html)}` |")
        i = rows.index((g, slug, label, href))
        if i + 1 == len(rows) or rows[i + 1][0] != g:
            out.append("")
    marks = " ".join(f'<img src="{CDN}/mark-{m}.svg" alt="{m}" height="48">' for m in MARKS)
    out += [
        "## Marks",
        "",
        "Bare logos (128 px, scale freely): " + ", ".join(f"`mark-{m}.svg`" for m in MARKS) + ".",
        "",
        marks,
        "",
        "## Live (not snapshotted)",
        "",
        f"Rendered on request by [{LIVE}/badges/]({LIVE}/badges/) - counters refresh hourly, status every 2 min.",
        "Any badge there also takes `?label=`, `?color=` and (except counters/status, which show the probe result) `?value=`;"
        " any Primer Octicon via `/badge/o/<name>.svg`.",
        "",
        "| Badge | Markdown |",
        "|---|---|",
    ]
    for path, href in [*live, ("o/git-pull-request-agent.svg?label=agent%20PR&color=purple", None)]:
        src = f"{LIVE}/badge/{path}" + ("" if ".svg" in path else ".svg")
        md = f"[![{path}]({src})]({href})" if href else f"![{path}]({src})"
        out.append(f"| {md} | `{md}` |")
    out.append("")
    return "\n".join(out)


def main():
    args = [a for a in sys.argv[1:] if a != "--offline"]
    icons = Path(args[0] if args else "package/icons")
    font, scale = load_font()
    for _, slug, label, icon, _, c1, c2, ex in BADGES:
        (HERE / f"{slug}.svg").write_text(badge(slug, label, icon, c1, c2, ex, icons, font, scale))
    if "--offline" in sys.argv:
        if not MANIFEST.exists():
            sys.exit("--offline needs eco.json from an earlier online run")
        snap = json.loads(MANIFEST.read_text())
        eco, live = snap["eco"], snap["live"]
    else:
        eco, live = snapshot_eco()
    rows = [(g, s, l, h) for g, s, l, _, h, *_ in BADGES] + EXTRA + [tuple(r) for r in eco]
    order = {g: i for i, g in enumerate(ECO_GROUPS + ["Infra", "Routers", "Models"])}
    rows.sort(key=lambda r: order[r[0]])
    (HERE / "README.md").write_text(readme(rows, [tuple(r) for r in live]))
    print(f"{len(BADGES)} brand + {len(eco)} eco badges, {len(MARKS)} marks -> {HERE}")


if __name__ == "__main__":
    main()
