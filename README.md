# cleberg.net

This repository holds the files for [cleberg.net](https://cleberg.net),
a static-site with blog posts, personal links, and more.

This site uses [orgo](https://gitbay.org/krz/orgo) to build the
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

- [orgo](https://gitbay.org/krz/orgo), the static site
  generator, installed with `cargo install --git
  https://gitbay.org/krz/orgo`.
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
git clone https://gitbay.org/cmc/cleberg.net
cd cleberg.net
emacs -nw
```

For users employing Doom Emacs, open any repository Org file using
`SPC f f` to access the content.

## Building and Publishing the Site

The `build.py` script wraps the build: it runs orgo, rewrites the footer's
orgo version to match the orgo that ran, and then either deploys the result
or serves it locally.

Environment variables control what it does, and all default to off:

- `BUILD=true` performs the build.
- `DEPLOY=true` deploys in production, or starts a development server
  on port 8000 otherwise.
- `ENV=prod` selects production: image URLs are rewritten to be
  root-relative (see Deployment below) and the `ruff` pass is skipped.
  Anything else builds for development.
- `DRY_RUN=true` turns a production deploy into a report. Production
  only; ignored everywhere else.

Exactly one combination writes to the server:

| `ENV`  | `BUILD` | `DEPLOY` | `DRY_RUN` | What happens                          | Output       | Server            |
|--------|---------|----------|-----------|---------------------------------------|--------------|-------------------|
| unset  | `true`  | —        | —         | Development build, `ruff` first       | `.build-dev/`| Untouched         |
| unset  | `true`  | `true`   | —         | Development build, then serve on :8000| `.build-dev/`| Untouched         |
| `prod` | `true`  | —        | —         | Production build and image rewrite    | `.build/`    | Untouched         |
| `prod` | —       | `true`   | `true`    | Reports what a deploy would change    | —            | Read only         |
| `prod` | `true`  | `true`   | —         | Production build, then deploy         | `.build/`    | **Overwritten**   |

``` shell
# Development build:
BUILD=true uv run build.py

# Development build, then serve it on localhost:8000:
BUILD=true DEPLOY=true uv run build.py

# Production build, no deploy:
ENV=prod BUILD=true uv run build.py

# What would a deploy change? Connects, compares, transfers nothing:
ENV=prod DEPLOY=true DRY_RUN=true uv run build.py

# Production build and deploy. This is the one that writes to the server:
ENV=prod BUILD=true DEPLOY=true uv run build.py
```

Generated site files reside in `.build/` for production and
`.build-dev/` for development.

The deploy is `rsync --delete-before`, so files the build no longer
produces are removed from the server. That is what makes the dry run
worth having: a build that silently produced fewer pages would quietly
delete the rest. Lines beginning `*deleting` in the dry-run output are
what the real deploy would remove.

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
