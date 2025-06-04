#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

def prompt(prompt_text):
    try:
        return input(prompt_text).strip()
    except EOFError:
        return ''

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
            [sys.executable, "-m", "http.server", "8000"],
            check=True
        )
    except KeyboardInterrupt:
        print("\nDevelopment server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting development server: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    build_dir = Path(".build")
    theme_dir = Path("theme/static")
    css_src = theme_dir / "styles.css"
    css_min = theme_dir / "styles.min.css"

    answer = prompt("Did you update the 'Recent Blog Posts' section? [yn] ")
    if not answer.lower().startswith("y"):
        print("Please update the 'Recent Blog Posts' section before publishing!")
        sys.exit(0)

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

        # Launch development web server
        start_dev_server(build_dir)

if __name__ == "__main__":
    main()