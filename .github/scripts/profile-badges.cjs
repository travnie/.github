"use strict";

const fs = require("node:fs");
const path = require("node:path");

const OWNERS = [
  { owner: "trvny", kind: "user", search: "is:pr is:merged user:trvny" },
  { owner: "travnie", kind: "org", search: "is:pr is:merged org:travnie" },
];

function escapeXml(value){return String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&apos;");}

function badgeSvg(label,message,color,which){
 const leftWidth=Math.ceil(36+label.length*6.2);
 const rightWidth=Math.ceil(20+message.length*6.4);
 const width=leftWidth+rightWidth;
 const shape=which==="pr"
  ? '<circle cx="6" cy="3" r="2"/><path d="M6 5v12"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="6" r="2"/><path d="M18 8v4a6 6 0 0 1-6 6H8"/>'
  : '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3"/>';
 return '<svg xmlns="http://www.w3.org/2000/svg" width="'+width+'" height="20" viewBox="0 0 '+width+' 20" role="img" aria-label="'+escapeXml(label+": "+message)+'">'
  +'<title>'+escapeXml(label+": "+message)+'</title>'
  +'<rect width="'+leftWidth+'" height="20" fill="#30363d"/>'
  +'<rect x="'+leftWidth+'" width="'+rightWidth+'" height="20" fill="#'+color+'"/>'
  +'<g transform="translate(5 3) scale(0.58)" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'+shape+'</g>'
  +'<g font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" fill="#fff">'
  +'<text x="'+(leftWidth-9)+'" y="14" text-anchor="end">'+escapeXml(label)+'</text>'
  +'<text x="'+(leftWidth+rightWidth/2)+'" y="14" text-anchor="middle">'+escapeXml(message)+'</text>'
  +'</g></svg>\n';
}
function save(dir, file, label, message, color, which) {
  fs.writeFileSync(path.join(dir, file), badgeSvg(label, message, color, which));
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


function shorten(value, max) {
  const characters = [...String(value)];
  return characters.length > max ? characters.slice(0, max - 1).join("") + "…" : String(value);
}

async function recentCommits(github) {
  const repositories = [];
  for (const { owner, kind } of OWNERS) {
    const owned = kind === "org"
      ? await github.paginate(github.rest.repos.listForOrg, { org: owner, type: "public", per_page: 100 })
      : await github.paginate(github.rest.repos.listForUser, { username: owner, type: "owner", per_page: 100 });
    for (const repo of owned) {
      if (repo.owner?.login?.toLowerCase() !== owner ||
          repo.private || repo.disabled || repo.fork || repo.archived) continue;
      repositories.push(repo);
    }
  }

  const commits = [];
  for (const repo of repositories) {
    let data;
    try {
      ({ data } = await github.rest.repos.listCommits({
        owner: repo.owner.login, repo: repo.name, per_page: 4,
      }));
    } catch (error) {
      if ([404, 409].includes(error.status)) continue;
      throw error;
    }
    for (const item of data) {
      const subject = item.commit?.message?.split("\n")[0]?.trim();
      const date = item.commit?.committer?.date || item.commit?.author?.date;
      if (!subject || !date || !Number.isFinite(Date.parse(date))) continue;
      if (/^chore\((?:readme|profile)\): refresh .*\[skip ci\]/i.test(subject)) continue;
      commits.push({
        repo: repo.full_name,
        sha: item.sha,
        subject,
        author: item.author?.login || item.commit?.author?.name || "unknown",
        date,
      });
    }
  }
  return commits
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date) ||
      a.repo.localeCompare(b.repo) || a.sha.localeCompare(b.sha))
    .slice(0, 6);
}

function activitySvg(commits) {
  const rows = commits.length || 1;
  const height = 68 + rows * 44 + 12;
  const body = commits.length ? commits.map((item, index) => {
    const y = 77 + index * 44;
    const headline = escapeXml(shorten(item.subject, 78));
    const details = escapeXml(shorten(
      item.repo + "  ·  " + item.author + "  ·  " + item.date.slice(0, 10), 95,
    ));
    return '<text class="subject" x="22" y="' + y + '">' + headline + '</text>'
      + '<text class="details" x="22" y="' + (y + 17) + '">' + details + '</text>';
  }).join("") : '<text class="details" x="22" y="79">No commits found in public non-fork repositories.</text>';

  return '<svg xmlns="http://www.w3.org/2000/svg" width="650" height="' + height +
    '" viewBox="0 0 650 ' + height + '" role="img" aria-labelledby="activity-title activity-desc">' +
    '<title id="activity-title">Latest repository commits</title>' +
    '<desc id="activity-desc">Recent commits across public trvny and travnie repositories, excluding forks and routine profile refreshes.</desc>' +
    '<style>.bg{fill:#fff;stroke:#d0d7de}.heading{fill:#1f2328;font:700 19px system-ui,sans-serif}' +
    '.subtitle{fill:#57606a;font:12px system-ui,sans-serif}.subject{fill:#1f2328;font:600 13px system-ui,sans-serif}' +
    '.details{fill:#57606a;font:12px system-ui,sans-serif}' +
    '@media(prefers-color-scheme:dark){.bg{fill:#0d1117;stroke:#30363d}.heading,.subject{fill:#e6edf3}' +
    '.subtitle,.details{fill:#8b949e}}</style>' +
    '<rect class="bg" x="1" y="1" width="648" height="' + (height - 2) + '" rx="12"/>' +
    '<text class="heading" x="22" y="29">Latest repository commits</text>' +
    '<text class="subtitle" x="22" y="48">trvny + travnie · public repositories · no forks</text>' +
    body + '</svg>\n';
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

  await update("merged-prs.svg", "merged PRs", "8250df", "pr",
    async () => (await mergedPullRequests(github)).toLocaleString("en-US"));
  await update("repo-size.svg", "repo size", "0969da", "size", async () => {
    const { kib, count } = await repositorySizes(github);
    core.info("Public repositories: " + count);
    return kib >= 1048576 ? (kib / 1048576).toFixed(2) + " GiB"
      : (kib / 1024).toFixed(1) + " MiB";
  });
  try {
    const commits = await recentCommits(github);
    fs.writeFileSync(path.join(outputDir, "activity.svg"), activitySvg(commits));
    core.info("Latest repository commits: " + commits.length);
  } catch (error) {
    core.warning("Recent commits unavailable: " + error.message);
    if (!fs.existsSync(path.join(outputDir, "activity.svg"))) {
      fs.writeFileSync(path.join(outputDir, "activity.svg"), activitySvg([]));
    }
  }
};
