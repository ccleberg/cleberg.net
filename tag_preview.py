#!/usr/bin/env python3
"""
Preview tag assignments for all blog posts.
Run with --write to actually add #+filetags to org files.
"""
import re
import sys
from pathlib import Path

CONTENT_DIR = Path("./content/blog")

# Explicit overrides take priority over rules
OVERRIDES = {
    "2018-11-28-cpp-compiler":                          ["linux"],
    "2019-12-16-password-security":                     ["security"],
    "2020-07-26-business-analysis":                     ["audit"],
    "2020-08-22-redirect-github-pages":                 ["web"],
    "2020-09-22-internal-audit":                        ["audit"],
    "2020-12-28-neon-drive":                            ["personal"],
    "2020-12-29-zork":                                  ["personal"],
    "2021-08-25-audit-sampling":                        ["audit"],
    "2021-12-04-cisa":                                  ["audit"],
    "2023-05-22-burnout":                               ["personal"],
    "2023-06-20-audit-review-template":                 ["audit"],
    "2023-08-18-agile-auditing":                        ["audit"],
    "2025-05-30-it-audit-career":                       ["audit"],
    "2025-11-13-wcag":                                  ["audit", "web"],
    "2025-11-23-it-audit-ai":                           ["audit"],
    "2026-02-21-auditing-aws-iam":                      ["audit"],
    "2026-02-21-auditing-aws-passwords":                ["audit"],
    "2026-03-03-auditing-aws-s3":                       ["audit"],
    "2020-09-01-visual-recognition":                    ["linux"],
    "2024-01-26-audit-dashboard":                       ["audit"],
    "2023-09-19-audit-sql-scripts":                     ["audit"],
    "2021-04-28-photography":                           ["personal"],
    "2022-06-22-daily-poetry":                          ["personal"],
    "2020-09-25-happiness-map":                         ["personal"],
    "2022-03-03-financial-database":                    ["self-hosting"],
    "2023-01-03-recent-website-changes":                ["personal", "web"],
    "2025-09-25-minimalist-website-redesign":           ["web"],
    "2026-02-07-indieweb-carnival-2026-02-intersecting-interests": ["personal", "web"],
}

TAG_RULES = {
    "audit": [
        "audit", "cisa", "ansoff",
    ],
    "emacs": [
        "emacs", "org-mode", "org-blog", "mu4e", "doom-emacs",
        "emacs-carnival", "gnu-stow",
    ],
    "linux": [
        "linux", "ubuntu", "debian", "fedora", "alpine",
        "customizing-ubuntu", "linux-software", "linux-display",
        "mtp-linux", "serenity-os", "fedora-i3", "fedora-login",
        "flatpak", "zfs", "ubuntu-emergency", "ubuntu-on-macos",
        "steam-on-ntfs", "bash-it", "byobu", "scli",
        "terminal-lifestyle", "curseradio", "st", "flac-to-opus",
        "pinetime", "server-build", "macos", "macos-customization",
        "deprecated-trusted-gpg", "exiftool", "graphene",
        "asahi", "aerc", "rocket-league",
    ],
    "self-hosting": [
        "self-hosting", "homelab", "vps-web-server", "git-server",
        "plex", "nextcloud", "wireguard", "backblaze", "syncthing",
        "docker", "n8n", "prometheus-grafana", "transmission",
        "goaccess", "unifi", "git-mirror", "automating-weblorg",
    ],
    "security": [
        "aes-encryption", "cryptography", "gnupg", "password",
        "server-hardening", "ssh-mfa", "ufw", "hardening",
        "authelia", "wireguard", "njalla-dns", "cloudflare-dns",
        "ditching-cloudflare", "obscura-vpn",
    ],
    "privacy": [
        "privacy", "graphene-os", "session-messenger", "fediverse",
        "digital-minimalism", "privacy-com", "local-llm",
        "email-migration", "dont-say-hello",
    ],
    "web": [
        "nginx", "apache", "php", "css", "redirect", "website-redesign",
        "gemini", "indieweb", "weblorg", "html", "digital-garden",
        "tableau",
    ],
    "personal": [
        "mediocrity", "burnout", "tuesday", "leaving-the-office",
        "vaporwave", "video-game-sales", "reliable-notes",
        "mass-unlike-tumblr", "changing-git-authors", "delete-gitlab",
        "clone-github", "this-year-i-will", "completion",
        "seum", "neon-drive", "zork",
    ],
}

def assign_tags(slug: str, title: str) -> list[str]:
    if slug in OVERRIDES:
        return OVERRIDES[slug]
    slug_lower = slug.lower()
    title_lower = title.lower()
    tags = []
    for tag, patterns in TAG_RULES.items():
        for pattern in patterns:
            if pattern in slug_lower or pattern in title_lower:
                if tag not in tags:
                    tags.append(tag)
                break
    return sorted(tags)

def get_title(path: Path) -> str:
    title_pat = re.compile(r"^#\+title:\s*(.+)$", re.IGNORECASE)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            m = title_pat.match(line)
            if m:
                return m.group(1).strip()
    return path.stem

def has_filetags(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if re.match(r"^#\+filetags:", line, re.IGNORECASE):
                return True
    return False

def write_filetags(path: Path, tags: list[str]):
    tag_str = ":" + ":".join(tags) + ":"
    content = path.read_text(encoding="utf-8")
    slug_pat = re.compile(r"(#\+slug:\s*.+\n)", re.IGNORECASE)
    m = slug_pat.search(content)
    if m:
        insert_at = m.end()
        new_content = content[:insert_at] + f"#+filetags: {tag_str}\n" + content[insert_at:]
        path.write_text(new_content, encoding="utf-8")
        return True
    return False

write_mode = "--write" in sys.argv

untagged = []
rows = []
for org_path in sorted(CONTENT_DIR.glob("*.org")):
    slug = org_path.stem
    title = get_title(org_path)
    tags = assign_tags(slug, title)
    if not tags:
        untagged.append((slug, title))
    rows.append((slug, title, tags))

print(f"{'SLUG':<50} {'TAGS'}")
print("-" * 85)
for slug, title, tags in rows:
    tag_str = ", ".join(tags) if tags else "-- UNTAGGED --"
    print(f"{slug:<50} {tag_str}")

print(f"\nTotal: {len(rows)} posts | Untagged: {len(untagged)}")
if untagged:
    print("\nUntagged posts:")
    for slug, title in untagged:
        print(f"  {slug}")

if write_mode:
    written = 0
    skipped = 0
    for org_path in sorted(CONTENT_DIR.glob("*.org")):
        slug = org_path.stem
        title = get_title(org_path)
        tags = assign_tags(slug, title)
        if not tags:
            skipped += 1
            continue
        if has_filetags(org_path):
            skipped += 1
            continue
        if write_filetags(org_path, tags):
            written += 1
    print(f"\nWrote filetags to {written} files, skipped {skipped}.")
else:
    print("\nRun with --write to apply filetags to org files.")
