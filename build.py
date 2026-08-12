#!/usr/bin/env python3
"""
This script automates the process of building and deploying the website.
It handles tasks such as:

- Running orgo to generate site content.
- Rewriting image URLs for the onion service (production only).
- Optionally deploying the built site to a remote server.
- Starting a local development server for previewing changes.

Usage:
    Set BUILD=true to build, DEPLOY=true to deploy or serve.
    Set ENV=prod for production builds; anything else builds for development.

    Builds are incremental. Production writes .build/ and development .build-dev/;
    delete either one for a clean build.

Dependencies:
    - Python 3
    - orgo, the static site generator (reads content/orgo.toml)
    - rsync for deployment

Author:
    Christian Cleberg <hello@cleberg.net>
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def run(cmd, error):
    """Run cmd quietly, exiting with its stderr if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(error, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def run_ruff():
    print("Running ruff...")
    for cmd in [["ruff", "check", "--fix"], ["ruff", "format"]]:
        run(cmd, f"ruff error ({' '.join(cmd)}):")


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


def run_orgo_build(build_dir):
    """
    Build the site with orgo.

    orgo reads content/orgo.toml, which holds the routes, templates and collections: the
    blog index groups itself by year, the tags page is a collection, the recent-posts
    list comes from the blog collection, and the sitemap is written once base_url is set.

    The output directory is left in place between builds rather than wiped, because the
    .orgo-cache.json inside it is what makes a build incremental: orgo re-renders only
    the pages whose content, config or templates changed, re-emits any page whose output
    is missing, and deletes the outputs of pages that have since been removed. Wiping the
    directory would throw that away and force a full render every time. For a clean build
    from scratch, delete the output directory by hand.

    What is left around it is what orgo does not do: rewriting image URLs for the onion.
    """
    print("Building with orgo...")
    result = subprocess.run(
        ["orgo", "build", "content", "-o", str(build_dir), "--strict"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print("orgo build failed", file=sys.stderr)
        sys.exit(1)


def deploy_to_server(build_dir, server):
    remote_path = f"{server}:/var/www/cleberg.net/"
    print(f"Deploying {build_dir}/ → {remote_path}")
    run(
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
        "Error during rsync deployment:",
    )


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
    prod = os.environ.get("ENV", "").casefold() == "prod"
    if not prod:
        run_ruff()

    # One output directory per environment, because the two differ after orgo has run:
    # production rewrites image URLs in place and development does not. Sharing a
    # directory would let an incremental build reuse a page rendered for the other one —
    # a dev preview showing /img/ paths that only resolve on the server. Production keeps
    # .build/ because that is the directory the deploy and the CI manifest name.
    build_dir = Path(".build" if prod else ".build-dev")

    print(f"Environment: {'Production' if prod else 'Development'}")

    if os.environ.get("BUILD", "").casefold() == "true":
        run_orgo_build(build_dir)
        # The onion needs same-origin images; dev previews keep the absolute URLs.
        # Runs over every page, not just the re-rendered ones, so a page carried over
        # from an earlier build is rewritten too.
        if prod:
            rewrite_img_urls(build_dir)

    if os.environ.get("DEPLOY", "").casefold() == "true":
        if prod:
            print("Deploying to production...")
            deploy_to_server(build_dir, "homelab")
        else:
            start_dev_server(build_dir)


if __name__ == "__main__":
    main()
