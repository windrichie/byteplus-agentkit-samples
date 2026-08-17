"""Pure-Python Markdown-to-HTML converter (standard library only)."""

import re
import html
import os
from typing import List, Tuple


# ── Inline processing ────────────────────────────────────────────────────────

def _process_inline(text: str) -> str:
    """Apply inline formatting: escape -> code spans -> links -> bold -> italic.

    Inline code spans are protected with placeholders first so they are not
    re-processed by later regexes.
    """
    # 1. HTML-escape the text
    text = html.escape(text, quote=False)

    # 2. Protect inline code spans with placeholders.
    code_spans: List[str] = []

    def _capture_code(m: re.Match) -> str:
        code_spans.append(f'<code>{m.group(1)}</code>')
        return f'%%%CODEPLACEHOLDER{len(code_spans)-1}%%%'

    text = re.sub(r'`([^`]+)`', _capture_code, text)

    # 3. Links [text](url)
    def _link_repl(m: re.Match) -> str:
        link_text = m.group(1)
        url = m.group(2)
        url = url.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<a href="{url}">{link_text}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _link_repl, text)

    # 4. Bold: **text** or __text__ (non-greedy)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

    # 5. Italic: *text* or _text_ (non-greedy)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)

    # Restore code placeholders
    for i, replacement in enumerate(code_spans):
        text = text.replace(f'%%%CODEPLACEHOLDER{i}%%%', replacement)

    return text


# ── Block processing ─────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
_UL_RE = re.compile(r'^[-*+]\s+(.+)$')
_OL_RE = re.compile(r'^\d+\.\s+(.+)$')
_CODEBLOCK_PLACEHOLDER_RE = re.compile(r'^%%%CODEBLOCK\d+%%%$')


def _process_blocks(blocks: List[str]) -> List[str]:
    """Convert a list of text blocks (no fenced code blocks) to HTML."""
    results: List[str] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')

        # Code block placeholder — pass through as-is
        if _CODEBLOCK_PLACEHOLDER_RE.match(block):
            results.append(block)
            continue

        # ATX heading
        m = _HEADING_RE.match(block)
        if m:
            level = len(m.group(1))
            heading_text = _process_inline(m.group(2))
            results.append(f'<h{level}>{heading_text}</h{level}>')
            continue

        # Blockquote
        if all(line.startswith('>') for line in lines):
            inner_lines = []
            for line in lines:
                inner = line[1:]
                if inner.startswith(' '):
                    inner = inner[1:]
                inner_lines.append(inner)
            inner_text = '\n'.join(inner_lines)
            inner_html = _convert(inner_text).strip()
            results.append(f'<blockquote>\n{inner_html}\n</blockquote>')
            continue

        # Unordered list
        ul_items = [_UL_RE.match(l) for l in lines]
        if all(ul_items):
            items_html = []
            for match in ul_items:
                if match:
                    item_text = _process_inline(match.group(1))
                    items_html.append(f'  <li>{item_text}</li>')
            results.append('<ul>\n' + '\n'.join(items_html) + '\n</ul>')
            continue

        # Ordered list
        ol_items = [_OL_RE.match(l) for l in lines]
        if all(ol_items):
            items_html = []
            for match in ol_items:
                if match:
                    item_text = _process_inline(match.group(1))
                    items_html.append(f'  <li>{item_text}</li>')
            results.append('<ol>\n' + '\n'.join(items_html) + '\n</ol>')
            continue

        # Paragraph
        inline = _process_inline(block)
        results.append(f'<p>{inline}</p>')

    return results


# ── Top-level conversion ─────────────────────────────────────────────────────

def _convert(markdown_text: str) -> str:
    """Convert Markdown text to HTML (body content only, no wrapper)."""
    text = markdown_text.replace('\r\n', '\n').replace('\r', '\n')

    # --- Step 1: Extract fenced code blocks ---
    lines = text.split('\n')
    output_parts: List[str] = []
    code_blocks: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(```+)\s*(\w*)\s*$', line)
        if m:
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            lang = m.group(2)
            content_lines: List[str] = []
            i += 1
            while i < len(lines):
                cl = lines[i]
                if cl.startswith(fence_char * fence_len) and cl.strip() == fence_char * fence_len:
                    i += 1
                    break
                content_lines.append(cl)
                i += 1
            lang_attr = f' class="language-{html.escape(lang, quote=False)}"' if lang else ''
            escaped = html.escape('\n'.join(content_lines), quote=False)
            code_html = f'<pre><code{lang_attr}>{escaped}</code></pre>'
            code_blocks.append(code_html)
            output_parts.append(f'%%%CODEBLOCK{len(code_blocks)-1}%%%')
        else:
            output_parts.append(line)
            i += 1

    # --- Step 2: Process non-code-block text ---
    remaining_text = '\n'.join(output_parts)
    raw_blocks = re.split(r'\n{2,}', remaining_text.strip())
    html_blocks = _process_blocks(raw_blocks)

    result = '\n\n'.join(html_blocks)

    # --- Step 3: Restore code blocks ---
    for idx, code_html in enumerate(code_blocks):
        result = result.replace(f'%%%CODEBLOCK{idx}%%%', code_html)

    return result


# ── Full document helpers ────────────────────────────────────────────────────

from md2html.styles import STYLES as _STYLES


def _build_document(body_html: str, title: str = "Markdown") -> str:
    """Wrap body HTML in a complete standalone HTML document."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
{_STYLES}
  </style>
</head>
<body>
<main>
{body_html}
</main>
</body>
</html>
"""


def _extract_title(body_html: str) -> str:
    """Extract the first <h1> text to use as document title."""
    m = re.search(r'<h1>(.*?)</h1>', body_html)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1))
    return "Markdown"


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown text to a complete standalone HTML document."""
    body = _convert(markdown_text)
    title = _extract_title(body)
    return _build_document(body, title)


def markdown_file_to_html(input_path: str | os.PathLike,
                          output_path: str | os.PathLike | None = None) -> str:
    """Read a Markdown file, convert it, optionally write to output_path.

    Returns the full HTML string.
    """
    with open(input_path, encoding="utf-8") as f:
        md = f.read()
    html_doc = markdown_to_html(md)
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
    return html_doc
