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
from urllib.parse import quote
from datetime import datetime
from pathlib import Path


def update_index_html(html_snippet, template_path="./.build/index.html"):
    """
    Read the index.html file at `template_path`, replace everything between
    <!-- BEGIN_POSTS --> and <!-- END_POSTS --> with the provided html_snippet,
    and write the updated content back to the same file.
    """
    # Read the current contents of index.html
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    begin_marker = "<!-- BEGIN_POSTS -->"
    end_marker = "<!-- END_POSTS -->"

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
    new_content = (
        content[:insert_start] + indented_snippet + content[end_line_start:]
    )

    # Write back to index.html
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_recent_posts_html(content_dir="./content/blog", num_posts=3):
    """
    Scan the `content_dir` for .org blog post files, extract their headers,
    and return an HTML snippet for the `num_posts` most recent posts.

    Expects each .org file to contain headers of the form:
      #+title:    Post Title
      #+date:     <YYYY-MM-DD Day HH:MM:SS>
      #+slug:     post-slug

    Returns a string containing the section with the three most recent posts,
    formatted like the snippet in the prompt.
    """
    posts = []

    header_patterns = {
        "title": re.compile(r"^#\+title:\s*(.+)$", re.IGNORECASE),
        "date": re.compile(r"^#\+date:\s*<(\d{4}-\d{2}-\d{2})"),
        "slug": re.compile(r"^#\+slug:\s*(.+)$", re.IGNORECASE),
        "draft": re.compile(r"^#\+draft:\s*(.+)$", re.IGNORECASE),
    }

    for org_path in Path(content_dir).glob("*.org"):
        title = None
        date_str = None
        slug = None
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
                }
            )

    # Sort posts by date (newest first)
    posts.sort(key=lambda x: x["date_obj"], reverse=True)

    # Take the top `num_posts`
    recent = posts[:num_posts]

    # Build HTML lines
    lines = []
    for post in recent:
        lines.append('\t<div class="post">')
        lines.append(
            f'\t\t<time datetime="{post["date_str"]}">{post["date_full"]}</time>'
        )
        lines.append(
            f'\t\t\t<a href="/blog/{post["slug"]}.html">{post["title"]}</a>'
        )
        lines.append("\t</div>")

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
    if dev_mode:
        print("Running Emacs publish script (development)...")
        result = subprocess.run(
            ["emacs", "--script", "publish.el"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    else:
        print("Running Emacs publish script (production)...")
        result = subprocess.run(
            ["emacs", "--script", "publish.el"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    if result.returncode != 0:
        print("Error running publish.el:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    annoying_file = Path(".build/cleberg-net.html")
    if annoying_file.exists():
        os.remove(annoying_file)
    else:
        print("Warning: .build/cleberg-net.html not found, but Emacs exited successfully.")


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
                lastmod = datetime.fromtimestamp(
                    os.path.getmtime(full_path)
                ).strftime("%Y-%m-%d")

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
    print(
        f"Sitemap generated at {sitemap_path} with {len(sitemap_entries)} entries."
    )


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
        subprocess.run(
            [sys.executable, "-m", "http.server", "8000"], check=True
        )
    except KeyboardInterrupt:
        print("\nDevelopment server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting development server: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    html_snippet = get_recent_posts_html("./content/blog", num_posts=3)

    build_dir = Path(".build")
    theme_dir = Path("theme/static")
    css_src = theme_dir / "styles.css"
    css_min = theme_dir / "styles.min.css"

    env = os.environ.get("ENV", "").casefold()
    deploy = os.environ.get("DEPLOY", "").casefold() == "true"

    if deploy:
        print("Deploying to production...")
        deploy_to_server(build_dir, "homelab-remote")
        return
    else:
        if env == "prod":
            print("Environment: Production")

            # Remove previous build
            remove_build_directory(build_dir)

            # Minify CSS
            minify_css(css_src, css_min)

            # Run publishing script (silenced output)
            run_emacs_publish(dev_mode=False)

            # Update index page with latest posts
            update_index_html(html_snippet)

            # Minify index page
            minify_html("./.build/index.html", "./.build/index.html")

            # Generate sitemap
            generate_sitemap()

        else:
            print("Environment: Development")

            # Remove previous build
            remove_build_directory(build_dir)

            # Minify CSS
            minify_css(css_src, css_min)

            # Run publishing script (with console output)
            run_emacs_publish(dev_mode=True)

            # Update index page with latest posts
            update_index_html(html_snippet)

            # Minify index page
            minify_html("./.build/index.html", "./.build/index.html")

            # Generate sitemap
            generate_sitemap()

            # Launch development web server
            start_dev_server(build_dir)


if __name__ == "__main__":
    main()
