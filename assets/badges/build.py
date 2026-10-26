#!/usr/bin/env python3
"""Build brand badges (icon tile + label) and README snippets.

Icons: @lobehub/icons-static-svg (MIT). Usage:
  npm pack @lobehub/icons-static-svg && tar xzf lobehub-icons-static-svg-*.tgz
  python3 assets/badges/build.py package/icons
Needs Pillow + a bold font for label widths (DejaVu Sans/Verdana; BADGE_FONT to override).

Style mirrors docs7.svg (hand-made, not generated). Add a badge = add a BADGES row.
"""
import os
import re
import sys
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


def load_font():
    """First loadable bold font -> (font, width scale vs Verdana Bold)."""
    for path in filter(None, FONTS):
        try:
            return ImageFont.truetype(path, 11), 1.0 if "verdana" in path.lower() else 1.07
        except OSError:
            continue
    sys.exit("no bold font for label metrics; set BADGE_FONT=/path/to/DejaVuSans-Bold.ttf or Verdana Bold")


def icon_body(path: Path, slug: str, ink: str) -> tuple[str, str]:
    src = path.read_text()
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


def readme(rows) -> str:
    out = [
        "# Badges",
        "",
        "Brand badges for READMEs, comments and sites. 28 px tall, same style as `docs7.svg`.",
        "Generated by `build.py` (icons: [lobe-icons](https://github.com/lobehub/lobe-icons), MIT) - edit `BADGES` there, rerun, commit.",
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
        md = f"[![{label}]({RAW}/{slug}.svg)]({href})"
        html = f'<a href="{href}"><img src="{CDN}/{slug}.svg" alt="{label}" height="28"></a>'
        out.append(f"| {md} | `{md}` | `{html}` |")
        if rows.index((g, slug, label, href)) + 1 == len(rows) or rows[rows.index((g, slug, label, href)) + 1][0] != g:
            out.append("")
    return "\n".join(out)


def main():
    icons = Path(sys.argv[1] if len(sys.argv) > 1 else "package/icons")
    font, scale = load_font()
    for _, slug, label, icon, _, c1, c2, ex in BADGES:
        (HERE / f"{slug}.svg").write_text(badge(slug, label, icon, c1, c2, ex, icons, font, scale))
    rows = [(g, s, l, h) for g, s, l, _, h, *_ in BADGES] + EXTRA
    order = {"Infra": 0, "Routers": 1, "Models": 2}
    rows.sort(key=lambda r: order[r[0]])
    (HERE / "README.md").write_text(readme(rows))
    print(f"{len(BADGES)} badges -> {HERE}")


if __name__ == "__main__":
    main()
