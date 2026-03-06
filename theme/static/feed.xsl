<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" version="1.0" exclude-result-prefixes="atom dc">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>rss - <xsl:value-of select="/rss/channel/title"/></title>
        <style>
          :root {
            color-scheme: light dark;
            --bg:      #F6F4F0;
            --bg-soft: #EDEAE4;
            --fg:      #111111;
            --fg-soft: #555550;
            --accent:  #c0392b;
            --border:  #111111;
            --meta:    #555550;
            --code-bg: #E8E4DE;
            --max-width: 800px;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --bg:      #161412;
              --bg-soft: #1F1C1A;
              --fg:      #F0EDE8;
              --fg-soft: #888580;
              --accent:  #ee6f5c;
              --border:  #2C2825;
              --meta:    #888580;
              --code-bg: #0F0D0C;
            }
          }
          * { box-sizing: border-box; }
          body {
            background: var(--bg);
            color: var(--fg);
            font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
            line-height: 1.6;
            max-width: var(--max-width);
            margin: 0 auto;
            padding: 2rem 1rem;
          }
          nav ul { list-style: none; padding: 0; display: flex; gap: 1rem; border-bottom: 4px solid var(--fg); padding-bottom: 0.5rem; margin-bottom: 2rem; }
          nav a { text-transform: uppercase; font-weight: 900; text-decoration: none; color: var(--fg); }
          nav a:hover { background: var(--fg); color: var(--bg); }
          h1 { font-size: 2.2rem; font-weight: 900; text-transform: uppercase; line-height: 1.1; margin-bottom: 0.5rem; }
          h2 { border-left: 10px solid var(--accent); padding-left: 0.75rem; font-weight: 900; text-transform: uppercase; line-height: 1.1; margin-top: 0; margin-bottom: 0.25rem; font-size: 1rem; }
          h2 a { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
          h2 a:hover { background: var(--accent); color: var(--bg); text-decoration: none; }
          .description { color: var(--fg-soft); font-size: 0.85rem; margin-bottom: 2rem; }
          .notice {
            background: var(--bg-soft);
            border: 1px solid var(--border);
            padding: 0.75rem 1rem;
            font-size: 0.85rem;
            margin-bottom: 2rem;
          }
          .notice code {
            background: var(--code-bg);
            padding: 0.1rem 0.3rem;
            font-size: 0.85rem;
          }
          .post { border-bottom: 1px dashed var(--border); padding: 1rem 0; }
          .post:last-child { border-bottom: none; }
          time { font-size: 0.8rem; color: var(--meta); display: block; margin-bottom: 0.25rem; }
          footer { margin-top: 4rem; border-top: 1px solid var(--border); padding-top: 1rem; font-size: 0.8rem; text-transform: uppercase; color: var(--meta); }
        </style>
      </head>
      <body>
        <nav>
          <ul>
            <li>
              <a href="/">Home</a>
            </li>
            <li>
              <a href="/blog">Blog</a>
            </li>
            <li>
              <a href="/garden">Garden</a>
            </li>
          </ul>
        </nav>
        <h1>
          <xsl:value-of select="/rss/channel/title"/>
        </h1>
        <p class="description">
          <xsl:value-of select="/rss/channel/description"/>
        </p>
        <div class="notice">
          This is an RSS feed. Copy <code><xsl:value-of select="/rss/channel/atom:link/@href"/></code> into your feed reader to subscribe.
        </div>
        <xsl:for-each select="/rss/channel/item">
          <div class="post">
            <time>
              <xsl:value-of select="pubDate"/>
            </time>
            <h2>
              <a>
                <xsl:attribute name="href">
                  <xsl:value-of select="link"/>
                </xsl:attribute>
                <xsl:value-of select="title"/>
              </a>
            </h2>
          </div>
        </xsl:for-each>
        <footer><xsl:value-of select="/rss/channel/title"/> — RSS 2.0
        </footer>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
