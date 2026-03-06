# Brand Reference — cleberg.net

Design decisions, usage rules, and porting checklist for this site and any
future sites.

---

## Color

All tokens live in `theme/static/tokens.css`. Import it before any other
stylesheet.

### Palette

| Token          | Light       | Dark        | Role                                      |
|----------------|-------------|-------------|-------------------------------------------|
| `--bg`         | `#F6F4F0`   | `#161412`   | Page background                           |
| `--bg-soft`    | `#EDEAE4`   | `#1F1C1A`   | Subtle surfaces (code blocks, inputs)     |
| `--fg`         | `#111111`   | `#F0EDE8`   | Primary text, hard borders, table headers |
| `--fg-soft`    | `#555550`   | `#888580`   | Secondary text, metadata                  |
| `--accent`     | `#c0392b`   | `#ee6f5c`   | Interactive elements only (see below)     |
| `--salmon`     | `#ee6f5c`   | `#ee6f5c`   | Decorative only (see below)               |
| `--border`     | `#111111`   | `#2C2825`   | Hard borders (nav, tables)                |
| `--border-soft`| `#DDDAD4`   | `#2C2825`   | Dashed or subtle dividers                 |
| `--code-bg`    | `#E8E4DE`   | `#0F0D0C`   | Code blocks, blockquotes                  |
| `--meta`       | `#555550`   | `#888580`   | Timestamps, labels, footnote numbers      |

### Usage Rules

**`--accent` is for interactive elements only:** links, `h2` left border,
footnote numbers, focus indicators. It is text-safe (WCAG AA: 4.6:1 on `--bg` in
light mode; ~4.5:1 on `--bg` in dark mode).

**`--salmon` is decorative only.** Never use it for body text on a light
background — it fails WCAG AA there. In dark mode, `--accent` and `--salmon`
resolve to the same value (`#ee6f5c`), which is intentional.

---

## Typography

- **Font stack:** `--font-mono` (ui-monospace, Cascadia Code, Source Code Pro,
  Menlo, Consolas, monospace)
- **Headings:** weight 900, uppercase, `line-height: 1.1`
- **`h2` accent bar:** 10px left border in `--accent`
- **Body:** `1rem`, `line-height: 1.6`
- **Meta/labels:** `0.8–0.85rem`, uppercase, `--meta` color
- **Date format:** `YYYY-MM-DD` everywhere, no exceptions

---

## Logo

Files live in `~/Documents/brand/logo/`.

| Variant                 | Use case                                         |
|-------------------------|--------------------------------------------------|
| `koi_light.svg/png`     | Full logo on light backgrounds                   |
| `koi_dark.svg/png`      | Full logo on dark backgrounds                    |
| `koi_light_minimal.svg` | Favicon, nav, small UI contexts on light         |
| `koi_dark_minimal.svg`  | Favicon, nav, small UI contexts on dark          |

**Rule:** Use the minimal variant for anything under ~64px or in navigation
contexts. Use the full variant for headers, OG images, or anywhere it has room
to breathe.

---

## Signature Patterns

These are the things that make the site look like itself. Port all of them to
any new site.

1. **Grayscale images with color on hover** — `img { filter: grayscale(1) }
   img:hover { filter: grayscale(0) }`. Apply to all content images by default.
2. **Blockquote as raw org-mode markup** — `#+begin_quote` / `#+end_quote`
   pseudo-elements. Extend the "visible markup" aesthetic to other block
   elements where appropriate.
3. **Nav: uppercase, weight 900, invert on hover** — `background: var(--fg);
   color: var(--bg)` on hover. No underlines in nav.
4. **Links: underline offset** — `text-underline-offset: 3px`, invert on hover
   (same as nav pattern).
5. **Hard borders on tables** — `3px solid var(--fg)` outer border, `1px solid var(--fg)` internal. Table headers use `background: var(--fg); color: var(--bg)`.

---

## Porting Checklist (New Site)

- [ ] Import `tokens.css` (or copy variables and update `tokens.css` as the
      source)
- [ ] Apply monospace font stack
- [ ] Apply grayscale image treatment
- [ ] Use minimal koi as favicon
- [ ] Use `YYYY-MM-DD` date format
- [ ] Confirm `--accent` WCAG contrast on new background colors if palette is
      adjusted
- [ ] Build or adapt OG/social card template using koi + palette + monospace
      type
