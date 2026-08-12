#!/usr/bin/env python3
"""
This script automates the process of building, testing, and deploying the website.
It handles tasks such as:

- Removing and recreating the build directory.
- Minifying CSS assets.
- Running the Emacs publishing script to generate site content.
- Updating the index.html file with the latest blog posts.
- Optionally deploying the built site to a remote server.
- Starting a local development server for previewing changes.

Usage:
    Set the environment variable ENV to 'prod' for production builds.
    Run the script to perform the build process accordingly.

Dependencies:
    - Python 3
    - Emacs with the publish.el script
    - minify tool for CSS minification
    - rsync for deployment

Author:
    Christian Cleberg <hello@cleberg.net>
"""

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from html import escape
from pathlib import Path

SITE_TEMPLATE_VARS = {
    "site_name": "cleberg.net",
    "site_owner": "Christian Cleberg <hello@cleberg.net>",
    "site_description": "Stillness amidst the chaos.",
}


def run_ruff():
    print("Running ruff...")
    for cmd in [["ruff", "check", "--fix"], ["ruff", "format"]]:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"ruff error ({' '.join(cmd)}):")
            print(result.stderr, file=sys.stderr)
            sys.exit(1)


def render_base_template(main_html, subtitle="", title=None):
    """
    Render a small subset of the site's shared templates for Python-generated
    pages that still need to follow the common chrome.
    """
    base_template = Path("theme/templates/base.html").read_text(encoding="utf-8")

    if title is None:
        title = SITE_TEMPLATE_VARS["site_name"]

    rendered = base_template
    rendered = rendered.replace(
        "{% block subtitle %}{% endblock %}",
        escape(subtitle),
    )
    rendered = rendered.replace(
        '{% block title %}{{ site_name | default("cleberg.net") }}{% endblock %}',
        escape(title),
    )
    rendered = rendered.replace(
        '{% if site_owner is defined %}<meta name="author" content="{{ site_owner }}">{% endif %}',
        f'<meta name="author" content="{escape(SITE_TEMPLATE_VARS["site_owner"])}">',
    )
    rendered = rendered.replace(
        '{% if site_description is defined %}<meta name="description" content="{{ site_description }}">{% endif %}',
        f'<meta name="description" content="{escape(SITE_TEMPLATE_VARS["site_description"])}">',
    )
    rendered = rendered.replace(
        '{% if site_keywords is defined %}<meta name="keywords" content="{{ site_keywords }}">{% endif %}',
        "",
    )
    rendered = rendered.replace("{% block meta %}{% endblock %}", "")
    rendered = rendered.replace("{% block head %}", "")
    rendered = rendered.replace("{% endblock %}", "", 1)
    rendered = rendered.replace("{% block main %}{% endblock %}", main_html)

    return rendered


def render_tags_page_html(tags_html):
    """
    Render the tags page by using the shared tags/base templates instead of a
    hand-authored standalone HTML document.
    """
    tags_template = Path("theme/templates/tags.html").read_text(encoding="utf-8")

    main_html = tags_template
    main_html = main_html.replace('{% extends "base.html" %}', "")
    main_html = main_html.replace(
        "{% block subtitle %}tags - {% endblock %}",
        "",
    )
    main_html = main_html.replace("{% block main %}", "")
    main_html = main_html.replace("{% endblock %}", "")
    main_html = main_html.replace("<!-- BEGIN_TAGS -->\n<!-- END_TAGS -->", tags_html)

    return render_base_template(main_html.strip(), subtitle="tags - ")


def get_blog_posts(content_dir="./content/blog"):
    """
    Scan blog posts and return normalized metadata for non-draft entries.
    """
    posts = []

    header_patterns = {
        "title": re.compile(r"^#\+title:\s*(.+)$", re.IGNORECASE),
        "date": re.compile(r"^#\+date:\s*[\[<](\d{4}-\d{2}-\d{2})"),
        "slug": re.compile(r"^#\+slug:\s*(.+)$", re.IGNORECASE),
        "tags": re.compile(r"^#\+filetags:\s*(.+)$", re.IGNORECASE),
        "draft": re.compile(r"^#\+draft:\s*(.+)$", re.IGNORECASE),
    }

    for org_path in Path(content_dir).glob("*.org"):
        title = None
        date_str = None
        slug = None
        tags = []
        is_draft = False

        with org_path.open("r", encoding="utf-8") as f:
            for line in f:
                if title is None:
                    m = header_patterns["title"].match(line)
                    if m:
                        title = m.group(1).strip()
                        continue

                if date_str is None:
                    m = header_patterns["date"].match(line)
                    if m:
                        # date_str is just YYYY-MM-DD
                        date_str = m.group(1)
                        continue

                if slug is None:
                    m = header_patterns["slug"].match(line)
                    if m:
                        slug = m.group(1).strip()
                        continue

                if not tags:
                    m = header_patterns["tags"].match(line)
                    if m:
                        raw = m.group(1).strip().strip(":")
                        tags = [t.strip() for t in raw.split(":") if t.strip()]
                        continue

                m = header_patterns["draft"].match(line)
                if m:
                    draft_value = m.group(1).strip().lower()
                    if draft_value != "nil":
                        is_draft = True
                        break
                    continue

                # Stop scanning once we have all required fields
                if title and date_str and slug:
                    break

        if is_draft:
            continue

        if title and date_str and slug:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_full = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # Skip files with invalid date format
                continue

            posts.append(
                {
                    "title": title,
                    "date_str": date_str,
                    "date_obj": date_obj,
                    "date_full": date_full,
                    "slug": slug,
                    "tags": tags,
                }
            )

    posts.sort(key=lambda x: x["date_obj"], reverse=True)
    return posts


def prompt(prompt_text):
    try:
        return input(prompt_text).strip()
    except EOFError:
        return ""


def remove_build_directory(build_dir):
    if build_dir.exists():
        print(f"Removing previous build directory: {build_dir}/")
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)


def minify_css(src_css, dest_css):
    print(f"Minifying CSS: {src_css} → {dest_css}")
    result = subprocess.run(
        ["minify", "-o", str(dest_css), str(src_css)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("Error during CSS minification:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def rewrite_img_urls(build_dir=".build"):
    """
    Rewrite absolute img.cleberg.net URLs to root-relative /img/ paths so the
    onion serves images from its own origin instead of fetching them off-onion.
    Production only: dev builds keep the absolute URLs so local previews still
    load images from the live image host.

    Requires the server to serve /var/www/img/ at /img/ on the cleberg.net vhost
    (e.g. `ln -s /var/www/img /var/www/cleberg.net/img`).

    The pattern tolerates a stray number of slashes after the scheme
    (https:/img, https:///img, ...) so a typo in the org source can't silently
    slip through un-rewritten and ship a broken cross-origin URL.
    """
    pattern = re.compile(r"https:/+img\.cleberg\.net/")
    count = 0
    for html in Path(build_dir).rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        new_text, n = pattern.subn("/img/", text)
        if n:
            count += n
            html.write_text(new_text, encoding="utf-8")
    print(f"Rewrote {count} img.cleberg.net references to /img/")


def run_orgo_build(dev_mode=True):
    """
    Build the site with orgo.

    Replaces the weblorg/Emacs publish. orgo reads content/orgo.toml, so the routes,
    templates and collections that used to live in publish.el live there now. Four of the
    steps this script used to perform afterwards are gone with it: the blog index groups
    itself by year, the tags page is a collection, the recent-posts list is generated from
    the blog collection, and the sitemap is written by orgo once base_url is set.

    What is left around it is what orgo does not do: minifying CSS, copying the org
    sources for readers who want them, and rewriting image URLs for the onion.
    """
    print("Building with orgo...")
    result = subprocess.run(
        ["orgo", "build", "content", "-o", ".build", "--strict"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print("orgo build failed", file=sys.stderr)
        sys.exit(1)


def copy_org_sources(content_dir="./content", build_dir="./.build/org"):
    print(f"Copying org sources: {content_dir} → {build_dir}")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    slug_pattern = re.compile(r"^#\+slug:\s*(.+)$", re.IGNORECASE)

    for src_path in Path(content_dir).rglob("*.org"):
        rel_dir = src_path.parent.relative_to(content_dir)
        dest_dir = Path(build_dir) / rel_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Try to extract slug from file headers
        slug = None
        with src_path.open("r", encoding="utf-8") as f:
            for line in f:
                m = slug_pattern.match(line)
                if m:
                    slug = m.group(1).strip()
                    break

        dest_name = f"{slug}.org" if slug else src_path.name
        shutil.copy2(src_path, dest_dir / dest_name)
        if slug:
            print(f"  {src_path.name} → {dest_name}")


def get_tags_html(content_dir="./content/blog"):
    """
    Build the tag index HTML snippet for the rendered tags template.
    """
    preferred_tag_order = [
        "audit",
        "emacs",
        "development",
        "ios",
        "linux",
        "personal",
        "privacy",
        "security",
        "self-hosting",
        "web",
    ]

    tag_map = {}

    for post in get_blog_posts(content_dir):
        for tag in post["tags"]:
            tag_map.setdefault(tag, []).append(
                {
                    "title": post["title"],
                    "slug": post["slug"],
                    "date_obj": post["date_obj"],
                    "date_str": post["date_str"],
                }
            )

    ordered_tags = [tag for tag in preferred_tag_order if tag in tag_map]
    ordered_tags.extend(
        sorted(tag for tag in tag_map if tag not in preferred_tag_order)
    )

    for tag in ordered_tags:
        tag_map[tag].sort(key=lambda x: x["date_obj"], reverse=True)

    toc_items = "".join(
        f'<li><a href="#{tag}">{tag}</a> <span class="tag-count">({len(tag_map[tag])})</span></li>'
        for tag in ordered_tags
    )

    sections = []
    for tag in ordered_tags:
        posts = tag_map[tag]
        items = "\n".join(
            f'<li class="post-list-item">'
            f'<time datetime="{p["date_str"]}">{p["date_str"]}</time>'
            f'<a href="/blog/{p["slug"]}.html">{p["title"]}</a>'
            f"</li>"
            for p in posts
        )
        sections.append(
            f'<h2 id="{tag}">{tag}</h2>\n<ul class="post-list">\n{items}\n</ul>'
        )

    return f'<ul class="tag-toc">{toc_items}</ul>\n' + "".join(
        f"<section>{section}</section>" for section in sections
    )


def deploy_to_server(build_dir, server):
    remote_path = f"{server}:/var/www/cleberg.net/"
    print(f"Deploying .build/ → {remote_path}")
    result = subprocess.run(
        # The build cache lives in the output directory because it describes it, but it
        # is not part of the site. Excluding it also stops --delete removing it locally.
        [
            "rsync",
            "-r",
            "--delete-before",
            "--exclude",
            ".orgo-cache.json",
            f"{build_dir}/",
            remote_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("Error during rsync deployment:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def start_dev_server(build_dir):
    print(f"Starting development HTTP server from {build_dir}/ on port 8000")
    os.chdir(build_dir)
    # This will run until interrupted (Ctrl+C)
    try:
        subprocess.run([sys.executable, "-m", "http.server", "8000"], check=True)
    except KeyboardInterrupt:
        print("\nDevelopment server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting development server: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    env = os.environ.get("ENV", "").casefold()
    if env != "prod":
        run_ruff()

    build_dir = Path(".build")
    theme_dir = Path("theme/static")
    css_src = theme_dir / "styles.css"
    css_min = theme_dir / "styles.min.css"

    build = os.environ.get("BUILD", "").casefold() == "true"
    deploy = os.environ.get("DEPLOY", "").casefold() == "true"

    if env == "prod":
        print("Environment: Production")
        if build:
            remove_build_directory(build_dir)
            minify_css(css_src, css_min)
            run_orgo_build(dev_mode=False)
            copy_org_sources()
            rewrite_img_urls(build_dir)
        if deploy:
            print("Deploying to production...")
            deploy_to_server(build_dir, "homelab")
            return
    else:
        print("Environment: Development")
        if build:
            remove_build_directory(build_dir)
            minify_css(css_src, css_min)
            run_orgo_build(dev_mode=True)
            copy_org_sources()
        if deploy:
            start_dev_server(build_dir)


if __name__ == "__main__":
    main()
