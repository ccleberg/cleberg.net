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
      #+filetags: :tag1:tag2:tag3:

    Returns a string containing the section with the three most recent posts,
    formatted like the snippet in the prompt.
    """
    posts = []

    header_patterns = {
        "title": re.compile(r"^#\+title:\s*(.+)$", re.IGNORECASE),
        "date": re.compile(r"^#\+date:\s*<(\d{4}-\d{2}-\d{2})"),
        "slug": re.compile(r"^#\+slug:\s*(.+)$", re.IGNORECASE),
        "filetags": re.compile(r"^#\+filetags:\s*(.+)$", re.IGNORECASE),
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
                    m = header_patterns["filetags"].match(line)
                    if m:
                        # filetags are in the form ":tag1:tag2:tag3:"
                        raw = m.group(1).strip()
                        # split on ":" and filter out empty strings
                        tags = [t for t in raw.split(":") if t]
                        continue

                m = header_patterns["draft"].match(line)
                if m:
                    draft_value = m.group(1).strip().lower()
                    if draft_value != "nil":
                        is_draft = True
                        break
                    continue

                # Stop scanning once we have all required fields
                if title and date_str and slug and tags:
                    break

        if is_draft:
            continue

        if title and date_str and slug:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # Skip files with invalid date format
                continue
            
            posts.append(
                {
                    "title": title,
                    "date_str": date_str,
                    "date_obj": date_obj,
                    "slug": slug,
                    "tags": tags,
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
            f'\t\t<time datetime="{post["date_str"]}">{post["date_str"]}</time>'
        )
        lines.append('\t\t<div class="post-content">')
        lines.append(
            f'\t\t\t<a href="/blog/{post["slug"]}.html">{post["title"]}</a>'
        )
        if post["tags"]:
            lines.append('\t\t\t<div class="post-tags">')
            for tag in post["tags"]:
                lines.append(f'\t\t\t\t<span class="tag">{tag}</span>')
            lines.append("\t\t\t</div>")
        lines.append("\t\t</div>")
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    if result.returncode != 0:
        print("Error running publish.el:")
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


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

    env = os.environ.get("ENV", "").lower()
    if env == "prod":
        print("Environment: Production")
        method = prompt("Publishing on remote or LAN? [r|l] ").lower()
        if method == "r":
            homelab_server = "homelab-remote"
        elif method == "l":
            homelab_server = "homelab"
        else:
            print("Invalid input. Assuming LAN (homelab)")
            homelab_server = "homelab"

        # Remove previous build
        remove_build_directory(build_dir)

        # Minify CSS
        minify_css(css_src, css_min)

        # Run publishing script (silenced output)
        run_emacs_publish(dev_mode=False)

        # Update index page with latest posts
        update_index_html(html_snippet)

        # Deploy changes
        deploy_to_server(build_dir, homelab_server)

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

        # Launch development web server
        start_dev_server(build_dir)


if __name__ == "__main__":
    main()
