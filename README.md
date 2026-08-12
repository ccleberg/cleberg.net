# cleberg.net

This repository holds the files for [cleberg.net](https://cleberg.net),
a static-site with blog posts, personal links, and more.

This site uses [orgo](https://github.com/krazywarez/orgo) to build the
static site.

## Site Structure

I write content pages (e.g., blog posts) in org-mode and templates in
HTML. orgo builds these files into a static site, and then I deploy
them to a web server.

The main site components are:

- Org source files in `content/`, containing blog posts and pages.
  That directory is the site's URL root: `content/blog/post.org`
  publishes at `/blog/post.html`.
- A configuration file (`content/orgo.toml`) that specifies the base
  URL, navigation, templates, and the generated pages (home, blog and
  garden indexes, tags, and the RSS feed).
- HTML templates in `content/templates/`.
- Assets such as images and style sheets, located in designated
  subdirectories. `theme/static/` is published at `/`.
- Utility scripts (e.g., `build.py`) to facilitate building and
  deployment.

## Dependencies

The publishing system depends on:

- [orgo](https://github.com/krazywarez/orgo), the static site
  generator, installed with `cargo install --git
  https://github.com/krazywarez/orgo`.
- `rsync` for deployment.
- [uv](https://github.com/astral-sh/uv) to run `build.py`.

## Configuration

You can customize site settings within the `content/orgo.toml` file.
This file establishes key variables such as:

- The base URL for links.
- Which pages appear in the navigation, and in what order.
- Per-directory template rules.
- The collections that generate the indexes, tag pages, and feed.

Users intending to modify site parameters should review and edit this
file accordingly. The orgo documentation contains extensive details on
configuration options and expected formats.

## Setup Instructions

To obtain a working copy of this repository, execute the following
commands within a shell environment or Emacs shell interface:

``` shell
git clone https://git.sr.ht/~ccleberg/cleberg.net
cd cleberg.net
emacs -nw
```

For users employing Doom Emacs, open any repository Org file using
`SPC f f` to access the content.

## Building and Publishing the Site

The `build.py` script wraps the build: it runs orgo, and then either
deploys the result or serves it locally.

Two environment variables control what it does, and both default to
off:

- `BUILD=true` performs the build.
- `DEPLOY=true` deploys in production, or starts a development server
  on port 8000 otherwise.

A third, `ENV`, selects the mode. Setting `ENV=prod` rewrites image
URLs to be root-relative (see Deployment below) and skips the `ruff`
pass; anything else builds for development.

``` shell
# Production build:
ENV=prod BUILD=true uv run build.py

# Development build:
BUILD=true uv run build.py

# Development build, then serve it on localhost:8000:
BUILD=true DEPLOY=true uv run build.py
```

Generated site files reside in `.build/` for production and
`.build-dev/` for development, ready for deployment. You can deploy the
resulting static site files via standard file transfer protocols such as
`scp` or SFTP.

Builds are incremental: orgo keeps an `.orgo-cache.json` inside the
output directory and re-renders only what changed, so the directory is
left in place between runs. Delete it for a clean build. The two
environments use separate directories because production rewrites image
URLs in the output and development does not.

orgo can also build and preview on its own, without `build.py`:

``` shell
orgo serve content -o /tmp/preview
```

## Deployment

Production builds rewrite image URLs to root-relative ones
(`/img/blog/...`) instead of absolute `https://img.cleberg.net/` ones so
the site renders standalone on the onion service without fetching assets
off-onion. The stylesheet is already same-origin.

This means the web server must serve the image store at `/img/` on the
`cleberg.net` vhost. The images live at `/var/www/img/` (their own host,
`img.cleberg.net`); expose them under `cleberg.net/img/` with a symlink:

``` shell
ln -s /var/www/img /var/www/cleberg.net/img
```

Without this, images 404 in production. Development builds keep the
absolute `img.cleberg.net` URLs, so local previews load images from the
live host and need no symlink.

Once assets are same-origin, the vhost CSP can tighten `img-src`,
`style-src`, and `font-src` back to `'self'`, and drop `bubbles.town`
from `script-src`/`connect-src` (the vote widget was removed; only a
plain link to Bubbles remains). After deploying, purge the Cloudflare
cache (responses carry a 31-day `max-age`).

## Creating New Blog Posts

To add new blog content, follow this procedure within Emacs:

1.  Open a new Org file (via `C-x C-f` or Doom\'s `SPC f f`).
2.  Insert the contents of the post template with `C-x i`, sourcing from
    `utils/template.org`.
3.  Modify the new file as needed to add post content and metadata.

This method streamlines content creation by reusing a preformatted
template.
