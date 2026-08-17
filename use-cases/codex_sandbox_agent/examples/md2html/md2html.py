#!/usr/bin/env python3
"""md2html — A Markdown-to-HTML converter using only the Python standard library."""

import argparse
import html
import re
import sys

__version__ = "1.0.0"


def escape_html(text: str) -> str:
    """HTML-escape a string (&, <, >, and double-quotes)."""
    return html.escape(text, quote=True)


# ---------------------------------------------------------------------------
# Inline formatting helpers
# ---------------------------------------------------------------------------

def _process_inline_basic(text: str) -> str:
    """Process bold, italic, and inline code in *already-HTML-escaped* text.

    This is used for link text where links themselves must not be nested.
    """
    # 1) Inline code → placeholder (content already escaped)
    code_spans: list[str] = []

    def _save_code(m: re.Match) -> str:
        code_spans.append(f"<code>{m.group(1)}</code>")
        return f"\x00CODE{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # 2) Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)

    # 3) Italic  (*text*)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    #    Italic (_text_) – but not inside words
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)

    # 4) Restore code placeholders
    for i, code in enumerate(code_spans):
        text = text.replace(f"\x00CODE{i}\x00", code)

    return text


def process_inline(text: str) -> str:
    """Apply all inline formatting to *raw* markdown text.

    Order: HTML-escape → inline-code → links → bold → italic.
    """
    # 1) HTML-escape first
    text = escape_html(text)

    # 2) Inline code → placeholder
    code_spans: list[str] = []

    def _save_code(m: re.Match) -> str:
        code_spans.append(f"<code>{m.group(1)}</code>")
        return f"\x00CODE{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # 3) Links  [text](url) — text may contain bold/italic/code
    def _process_link(m: re.Match) -> str:
        link_text = m.group(1)
        url = m.group(2)
        processed = _process_inline_basic(link_text)
        return f'<a href="{escape_html(url)}">{processed}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _process_link, text)

    # 4) Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)

    # 5) Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)

    # 6) Restore code placeholders
    for i, code in enumerate(code_spans):
        text = text.replace(f"\x00CODE{i}\x00", code)

    return text


# ---------------------------------------------------------------------------
# Block-level parsing
# ---------------------------------------------------------------------------

def _parse_lines(md_text: str) -> str:
    """Line-by-line markdown parser."""
    md_text = md_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = md_text.split("\n")

    html_parts: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # --- Blank line ---
        if line.strip() == "":
            i += 1
            continue

        # --- Fenced code block ---
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            # Skip closing fence
            if i < n:
                i += 1  # skip the ``` line

            code_content = "\n".join(code_lines)
            # Code content should have trailing newline stripped
            code_content = code_content.strip("\n")
            escaped = escape_html(code_content)
            if lang:
                html_parts.append(
                    f'<pre><code class="language-{escape_html(lang)}">{escaped}</code></pre>'
                )
            else:
                html_parts.append(f"<pre><code>{escaped}</code></pre>")
            continue

        # --- ATX Heading ---
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            processed = process_inline(text)
            html_parts.append(f"<h{level}>{processed}</h{level}>")
            i += 1
            continue

        # --- Paragraph (collect consecutive non-blank, non-special lines) ---
        para_lines: list[str] = []
        while i < n:
            cline = lines[i]
            # A blank line ends the paragraph
            if cline.strip() == "":
                i += 1
                break
            # A fenced code block or heading starts a new block
            if cline.startswith("```") or re.match(r"^#{1,6}\s+", cline):
                break
            para_lines.append(cline)
            i += 1

        if para_lines:
            para_text = " ".join(process_inline(l) for l in para_lines)
            # Collapse multiple spaces
            para_text = re.sub(r" +", " ", para_text)
            html_parts.append(f"<p>{para_text}</p>")

    body = "\n".join(html_parts)
    return _wrap_document(body)


def _wrap_document(body: str) -> str:
    """Wrap the body HTML in a complete, styled HTML5 document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Converted Markdown</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 1.5rem;
    line-height: 1.7;
    color: #1a1a1a;
    background: #fafafa;
  }}
  h1, h2, h3, h4, h5, h6 {{
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
    line-height: 1.3;
  }}
  h1 {{ font-size: 2em; border-bottom: 2px solid #e0e0e0; padding-bottom: 0.3em; }}
  h2 {{ font-size: 1.5em; border-bottom: 1px solid #e8e8e8; padding-bottom: 0.25em; }}
  h3 {{ font-size: 1.25em; }}
  h4 {{ font-size: 1.1em; }}
  h5, h6 {{ font-size: 1em; }}
  p {{ margin: 0 0 1em 0; }}
  strong {{ font-weight: 600; }}
  em {{ font-style: italic; }}
  a {{
    color: #0366d6;
    text-decoration: none;
  }}
  a:hover {{ text-decoration: underline; }}
  code {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    background: #f0f0f0;
    padding: 0.15em 0.4em;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  pre {{
    background: #2d2d2d;
    color: #f8f8f2;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    margin: 0 0 1em 0;
  }}
  pre code {{
    background: transparent;
    padding: 0;
    border-radius: 0;
    font-size: 0.9em;
    color: inherit;
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to a styled HTML5 document."
    )
    parser.add_argument("input", metavar="INPUT.md", nargs="?",
                        help="Markdown input file")
    parser.add_argument(
        "-o", "--output", metavar="OUTPUT.html",
        help="Write output to file instead of stdout"
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Print version and exit"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.version:
        print(f"md2html {__version__}")
        return 0

    if args.input is None:
        print("Error: input file is required", file=sys.stderr)
        return 1

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            md_text = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: cannot read {args.input}: {e}", file=sys.stderr)
        return 1

    html_output = markdown_to_html(md_text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"Wrote {args.output}")
    else:
        print(html_output, end="")

    return 0


def markdown_to_html(md_text: str) -> str:
    """Convert markdown text to a complete HTML5 document.

    This is the main public API — import and call this function in tests.
    """
    return _parse_lines(md_text)


if __name__ == "__main__":
    sys.exit(main())
