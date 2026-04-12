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
from html import escape
from urllib.parse import quote
from datetime import datetime
from pathlib import Path


SITE_TEMPLATE_VARS = {
    "site_name": "cleberg.net",
    "site_owner": "Christian Cleberg <hello@cleberg.net>",
    "site_description": "Stillness amidst the chaos.",
}


def run_ruff():
    print("Running ruff...")
    for cmd in [["ruff", "check", "--fix"], ["ruff", "format"]]:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            print(f"ruff error ({' '.join(cmd)}):")
            print(result.stderr, file=sys.stderr)
            sys.exit(1)


def update_marked_section(
    html_snippet,
    template_path="./.build/index.html",
    begin_marker="<!-- BEGIN_POSTS -->",
    end_marker="<!-- END_POSTS -->",
):
    """
    Read the file at `template_path`, replace everything between `begin_marker`
    and `end_marker` with the provided html_snippet, and write the updated
    content back to the same file.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the indices of the markers
    begin_index = content.find(begin_marker)
    end_index = content.find(end_marker)

    if begin_index == -1 or end_index == -1:
        raise ValueError(f"Markers not found in {template_path}")

    # Compute insertion points: after the end of begin_marker line, before end_marker
    # Include the newline after BEGIN_POSTS
    insert_start = begin_index + len(begin_marker)
    # Ensure we capture the newline character if present
    if content[insert_start : insert_start + 1] == "\n":
        insert_start += 1

    # If there is a newline before END_POSTS, trim trailing whitespace from snippet block
    # We will preserve indentation of BEGIN_POSTS line
    indent = ""
    # Determine the indentation by looking at characters after the newline that follows begin_marker
    lines_after_begin = content[begin_index:].splitlines(True)
    if len(lines_after_begin) > 1:
        # The second line starts with the indentation to preserve
        second_line = lines_after_begin[1]
        indent = ""
        for ch in second_line:
            if ch.isspace():
                indent += ch
            else:
                break

    # Prepare the replacement block: indent each line of html_snippet
    snippet_lines = html_snippet.splitlines()
    indented_snippet = "\n".join(indent + line for line in snippet_lines) + "\n"

    # Compute the position just before end_marker (excluding any preceding whitespace/newline)
    end_line_start = content.rfind("\n", 0, end_index)
    if end_line_start == -1:
        end_line_start = end_index

    # Construct the new content
    new_content = content[:insert_start] + indented_snippet + content[end_line_start:]

    # Write back to index.html
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(new_content)


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
    rendered = rendered.replace(
        '{{ url_for("static", file="styles.min.css") }}',
        "/styles.min.css",
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


def get_recent_posts_html(content_dir="./content/blog", num_posts=3):
    """
    Return an HTML snippet for the `num_posts` most recent blog posts.
    """
    recent = get_blog_posts(content_dir)[:num_posts]

    lines = []
    for post in recent:
        lines.append('\t<li class="post-list-item">')
        lines.append(
            f'\t\t<time datetime="{post["date_str"]}">{post["date_full"]}</time>'
        )
        lines.append(f'\t\t<a href="/blog/{post["slug"]}.html">{post["title"]}</a>')
        lines.append("\t</li>")

    return "\n".join(lines)


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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print("Error during CSS minification:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def minify_html(src_html, dest_html):
    print(f"Minifying HTML: {src_html} → {dest_html}")
    result = subprocess.run(
        ["minify", "-o", str(dest_html), str(src_html)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print("Error during HTML minification:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def run_emacs_publish(dev_mode=True):
    mode = "development" if dev_mode else "production"
    print(f"Running Emacs publish script ({mode})...")

    result = subprocess.run(
        ["emacs", "--script", "publish.el"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode != 0:
        print("Error running publish.el output:")
        print(result.stdout)
        sys.exit(1)

    annoying_file = Path(".build/cleberg-net.html")
    if annoying_file.exists():
        os.remove(annoying_file)
    else:
        print(
            "Warning: .build/cleberg-net.html not found, but Emacs exited successfully."
        )


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


def generate_sitemap(build_dir=".build", base_url="https://cleberg.net"):
    """
    Generates a sitemap.xml based on contents of the .build directory.
    Only includes .html files (except 404.html).
    """
    sitemap_entries = []
    for root, dirs, files in os.walk(build_dir):
        for filename in files:
            if filename.endswith(".html") and filename != "404.html":
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, build_dir)
                url_path = "/" + quote(rel_path.replace(os.sep, "/"))
                # Remove index.html for cleaner URLs
                if url_path.endswith("/index.html"):
                    url_path = url_path[:-10] or "/"
                elif url_path == "/index.html":
                    url_path = "/"
                loc = f"{base_url}{url_path}"

                # Last modified time
                lastmod = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime(
                    "%Y-%m-%d"
                )

                sitemap_entries.append(f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
  </url>""")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{os.linesep.join(sitemap_entries)}
</urlset>
"""
    # Write to .build/sitemap.xml
    sitemap_path = os.path.join(build_dir, "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    print(f"Sitemap generated at {sitemap_path} with {len(sitemap_entries)} entries.")


def inject_blog_year_separators(blog_index_path="./.build/blog/index.html"):
    """
    Post-processes the rendered blog index to inject year separator <li> elements
    between groups of posts. Weblorg/templatel doesn't support mutable loop state,
    so this runs after the HTML is generated.

    Finds each <li class="post-list-item"> that contains a <time datetime="YYYY-MM-DD">,
    and inserts <li class="post-list-year">YYYY</li> before the first post of each year.
    """
    path = Path(blog_index_path)
    if not path.exists():
        print(f"Warning: {blog_index_path} not found, skipping year separators.")
        return

    content = path.read_text(encoding="utf-8")

    # Match each post list item, capturing the date and the full element
    item_pattern = re.compile(
        r'(<li class="post-list-item">.*?</li>)',
        re.DOTALL,
    )
    date_pattern = re.compile(r"datetime=['\"]?(\d{4})-\d{2}-\d{2}['\"]?")

    current_year = None

    def replace_item(m):
        nonlocal current_year
        item_html = m.group(1)
        date_match = date_pattern.search(item_html)
        if not date_match:
            return item_html
        year = date_match.group(1)
        if year != current_year:
            current_year = year
            separator = f'<li class="post-list-year">{year}</li>'
            return f"{separator}\n{item_html}"
        return item_html

    new_content = item_pattern.sub(replace_item, content)
    path.write_text(new_content, encoding="utf-8")
    print(f"Blog year separators injected into {blog_index_path}")


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
    ordered_tags.extend(sorted(tag for tag in tag_map if tag not in preferred_tag_order))

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


def generate_tags_page(content_dir="./content/blog", build_dir="./.build"):
    """
    Render the tags page using the shared template structure.
    """
    tags_html = get_tags_html(content_dir)
    out_path = Path(build_dir) / "tags" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_tags_page_html(tags_html), encoding="utf-8")
    print(f"Tags page written to {out_path}")


def deploy_to_server(build_dir, server):
    remote_path = f"{server}:/var/www/cleberg.net/"
    print(f"Deploying .build/ → {remote_path}")
    result = subprocess.run(
        ["rsync", "-r", "--delete-before", f"{build_dir}/", remote_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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
    html_snippet = get_recent_posts_html("./content/blog", num_posts=3)

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
            run_emacs_publish(dev_mode=False)
            copy_org_sources()
            update_marked_section(html_snippet)
            inject_blog_year_separators()
            generate_tags_page()
            # minify_html("./.build/index.html", "./.build/index.html")
            generate_sitemap()
        if deploy:
            print("Deploying to production...")
            deploy_to_server(build_dir, "homelab")
            return
    else:
        print("Environment: Development")
        if build:
            remove_build_directory(build_dir)
            minify_css(css_src, css_min)
            run_emacs_publish(dev_mode=True)
            copy_org_sources()
            update_marked_section(html_snippet)
            inject_blog_year_separators()
            generate_tags_page()
            minify_html("./.build/index.html", "./.build/index.html")
            generate_sitemap()
        if deploy:
            start_dev_server(build_dir)


if __name__ == "__main__":
    main()
