"""Modern embedded CSS for md2html output."""

STYLES = """\
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-text-size-adjust: 100%;
}

body {
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.75;
  color: #1f2937;
  background: #f3f4f6;
  padding: 2rem 1rem;
}

main {
  max-width: 820px;
  margin: 0 auto;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 4px 16px rgba(0, 0, 0, 0.04);
  padding: 2.5rem 2rem;
}

@media (max-width: 640px) {
  main {
    padding: 1.5rem 1rem;
    border-radius: 8px;
  }
}

/* ── Headings ────────────────────────────────────────────────────────────── */

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  line-height: 1.3;
  color: #3730a3;
  margin-top: 1.75em;
  margin-bottom: 0.5em;
}

h1 { font-size: 2.25rem; margin-top: 0; }
h2 { font-size: 1.75rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.25em; }
h3 { font-size: 1.4rem; }
h4 { font-size: 1.15rem; }
h5 { font-size: 1rem; }
h6 { font-size: 0.875rem; color: #6b7280; }

/* ── Paragraphs ──────────────────────────────────────────────────────────── */

p {
  margin-bottom: 1.25em;
}

/* ── Links ───────────────────────────────────────────────────────────────── */

a {
  color: #4f46e5;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.15s ease;
}

a:hover {
  color: #3730a3;
  text-decoration: underline;
}

/* ── Inline code ─────────────────────────────────────────────────────────── */

code {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', 'Monaco', 'Andale Mono', monospace;
  font-size: 0.875em;
  background: #eef2ff;
  color: #4338ca;
  padding: 0.2em 0.45em;
  border-radius: 6px;
  word-break: break-word;
}

/* ── Fenced code blocks ──────────────────────────────────────────────────── */

pre {
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  overflow-x: auto;
  margin-bottom: 1.25em;
  font-size: 0.9rem;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
  word-break: normal;
}

pre code::before,
pre code::after {
  content: none;
}

/* ── Blockquotes ─────────────────────────────────────────────────────────── */

blockquote {
  border-left: 4px solid #6366f1;
  background: #eef2ff;
  margin: 1.25em 0;
  padding: 0.75rem 1.25rem;
  border-radius: 0 8px 8px 0;
  color: #374151;
}

blockquote p:last-child {
  margin-bottom: 0;
}

/* ── Lists ───────────────────────────────────────────────────────────────── */

ul, ol {
  margin: 0.5em 0 1.25em 1.5em;
}

li {
  margin-bottom: 0.35em;
}

li > ul,
li > ol {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

/* ── Horizontal rule ─────────────────────────────────────────────────────── */

hr {
  border: none;
  border-top: 2px solid #e5e7eb;
  margin: 2em 0;
}

/* ── Misc ────────────────────────────────────────────────────────────────── */

strong {
  font-weight: 700;
}

em {
  font-style: italic;
}
"""
