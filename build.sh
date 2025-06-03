#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Function: generate_recent_posts
#     After publishing to .build/, finds the 3 newest HTML files under .build/blog
#     (excluding blog index.html), extracts each post’s date/title/tags by:
#         - <time datetime="...">
#         - <h1>…</h1>
#         - <span class="tag">…</span> lines
#     Replaces everything between <!-- RECENT-POSTS-START --> and
#     <!-- RECENT-POSTS-END --> in .build/index.html.
#     Tested on macOS.
# -----------------------------------------------------------------------------
generate_recent_posts() {
    BUILD_DIR="${SCRIPT_DIR}/.build"
    INDEXFILE="$BUILD_DIR/index.html"
    BLOGDIR="$BUILD_DIR/blog"
    TMPFILE="$(mktemp)"
    MARKER_START="<!-- RECENT-POSTS-START -->"
    MARKER_END="<!-- RECENT-POSTS-END -->"

    # 1) Verify generated index.html exists
    if [[ ! -f "$INDEXFILE" ]]; then
        echo "Error: Generated index.html not found at $INDEXFILE" >&2
        exit 1
    fi

    # 2) Verify .build/blog exists
    if [[ ! -d "$BLOGDIR" ]]; then
        echo "Error: Generated blog directory not found at $BLOGDIR" >&2
        exit 1
    fi

    # 3) Collect the three newest post HTML files, excluding /index.html
    POSTS=()
    for FILEPATH in $(ls -1t "$BLOGDIR"/*.html 2>/dev/null | grep -v "/index.html\$" | head -n 3); do
        [[ -f "$FILEPATH" ]] && POSTS+=("$FILEPATH")
    done

    # 4) Build the HTML snippet into TMPFILE
    {
        for POST in "${POSTS[@]}"; do
            BASENAME="$(basename "$POST")"
            URL="/blog/${BASENAME}"

            # 4a) DATE: extract from first <time datetime="...">
            POST_DATE_FULL="$(sed -n 's/.*<time datetime="\([^"]*\)".*/\1/p' "$POST" | head -n1)"
            if [[ -n "$POST_DATE_FULL" ]]; then
                POST_DATE="${POST_DATE_FULL%% *}"
            else
                POST_DATE="$(stat -f "%Sm" -t "%Y-%m-%d" "$POST")"
            fi

            # 4b) TITLE: extract from first <h1>…</h1>
            TITLE="$(sed -n 's/.*<h1[^>]*>\(.*\)<\/h1>.*/\1/p' "$POST" | head -n1)"
            if [[ -z "$TITLE" ]]; then
                TITLE="${BASENAME%.html}"
            fi

            # 4c) TAGS: extract each <span class="tag">…</span> line, re-indent by 6 spaces
            TAGSPAN="$(grep -o '^[[:space:]]*<span class="tag">[^<]*</span>' "$POST" \
                | sed 's/^[[:space:]]*/            /' || true)"

            # 4d) Emit one <div class="post">…</div> block
            cat <<EOF
    <div class="post">
        <time datetime="${POST_DATE}">${POST_DATE}</time>
        <div class="post-content">
            <a href="${URL}">${TITLE}</a>
            <div class="post-tags">
                $(printf "%s\n" "$TAGSPAN")
            </div>
        </div>
    </div>
EOF
        done
    } > "$TMPFILE"

    # 5) Replace everything between the markers in .build/index.html (keeping markers)
    sed -i '' -e "/${MARKER_START}/,/${MARKER_END}/{ 
        /${MARKER_START}/{p; r $TMPFILE
            }; 
        /${MARKER_END}/p; 
        d
    }" "$INDEXFILE"

    rm "$TMPFILE"
    echo "→ Injected up to 3 newest posts into $INDEXFILE"
}


# -------------------- Main build.sh logic --------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Clean previous build
rm -rf "${SCRIPT_DIR}/.build"/*

# Step 2: Minify CSS
minify -o "${SCRIPT_DIR}/theme/static/styles.min.css" "${SCRIPT_DIR}/theme/static/styles.css"

# Step 3: Run Emacs publish.el (outputs into .build/)
emacs --script "${SCRIPT_DIR}/publish.el" &>/dev/null

# Step 4: Inject the “Recent Blog Posts” section into the generated index.html
generate_recent_posts

if [[ "$ENV" == "prod" ]]; then
    echo "Environment: Production"
    printf "Publishing on remote or LAN? [r|l] "
    read -r method
    if [[ "$method" =~ ^[Rr]$ ]]; then
        ubuntu_server="ubuntu-remote"
    elif [[ "$method" =~ ^[Ll]$ ]]; then
        ubuntu_server="ubuntu"
    else
        echo "Invalid input. Assuming LAN (ubuntu)"
        ubuntu_server="ubuntu"
    fi

    # Step 5: Deploy via rsync
    rsync -r --delete-before "${SCRIPT_DIR}/.build/" "$ubuntu_server":/var/www/cleberg.net/
else
    echo "Environment: Development"
    # Step 5: Launch local HTTP server from .build/
    cd "${SCRIPT_DIR}/.build/" || exit
    python3 -m http.server
fi