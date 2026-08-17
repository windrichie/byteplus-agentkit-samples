"""Tests for the md2html converter and CLI."""

import sys
from pathlib import Path

import pytest

from md2html import markdown_to_html, markdown_file_to_html, main as cli_main


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level", range(1, 7))
def test_heading_levels(level):
    md = f"{'#' * level} Heading {level}"
    html = markdown_to_html(md)
    assert f"<h{level}>" in html
    assert f"</h{level}>" in html
    assert "Heading" in html and str(level) in html


def test_heading_content_escaped():
    """HTML inside heading text should be escaped."""
    md = "# Title <script>alert(1)</script>"
    html = markdown_to_html(md)
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


# ---------------------------------------------------------------------------
# Bold and italic
# ---------------------------------------------------------------------------

def test_bold_double_star():
    html = markdown_to_html("**bold text**")
    assert "<strong>bold text</strong>" in html


def test_bold_double_underscore():
    html = markdown_to_html("__bold text__")
    assert "<strong>bold text</strong>" in html


def test_italic_single_star():
    html = markdown_to_html("*italic text*")
    assert "<em>italic text</em>" in html


def test_italic_single_underscore():
    html = markdown_to_html("_italic text_")
    assert "<em>italic text</em>" in html


def test_underscore_inside_word_not_italic():
    """_ should not trigger emphasis inside words like some_var."""
    md = "some_var_here"
    html = markdown_to_html(md)
    assert "<em>" not in html


def test_bold_with_italic_inside():
    html = markdown_to_html("**bold and *italic* inside**")
    assert "<strong>bold and <em>italic</em> inside</strong>" in html


def test_mixed_bold_italic():
    html = markdown_to_html("***all bold italic***")
    assert "<strong>" in html and "<em>" in html


# ---------------------------------------------------------------------------
# Inline code
# ---------------------------------------------------------------------------

def test_inline_code():
    html = markdown_to_html("Use `code` here")
    assert "<code>" in html


def test_inline_code_escapes_html():
    """HTML inside inline code must be escaped."""
    html = markdown_to_html("`<script>alert(1)</script>`")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


def test_inline_code_no_markdown_inside():
    """Markdown inside inline code should be rendered literally."""
    html = markdown_to_html("`**not bold**`")
    assert "**not bold**" in html
    assert "<strong>" not in html


# ---------------------------------------------------------------------------
# Fenced code blocks
# ---------------------------------------------------------------------------

def test_fenced_code_block_no_lang():
    md = "```\ncode block\n```"
    html = markdown_to_html(md)
    assert "<pre><code>" in html
    assert "code block" in html


def test_fenced_code_block_with_lang():
    md = "```python\nprint('hello')\n```"
    html = markdown_to_html(md)
    assert '<pre><code class="language-python">' in html
    assert "print('hello')" in html


def test_fenced_code_block_inline_markdown_literal():
    """Inline Markdown inside code blocks must remain literal."""
    md = "```\n**not bold** *not italic*\n```"
    html = markdown_to_html(md)
    assert "**not bold** *not italic*" in html
    assert "<strong>" not in html
    assert "<em>" not in html


def test_fenced_code_block_escapes_html():
    """HTML in code blocks must be escaped."""
    md = "```\n<script>alert(1)</script>\n```"
    html = markdown_to_html(md)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def test_link_basic():
    html = markdown_to_html("[text](https://example.com)")
    assert '<a href="https://example.com">text</a>' in html


def test_link_url_escaping():
    """URLs with special characters like quotes must be escaped."""
    md = '[link](https://example.com?a="b")'
    html = markdown_to_html(md)
    assert 'href="https://example.com?a=&quot;b&quot;"' in html


# ---------------------------------------------------------------------------
# Paragraphs
# ---------------------------------------------------------------------------

def test_paragraphs_from_blank_lines():
    md = "First paragraph.\n\nSecond paragraph."
    html = markdown_to_html(md)
    assert "<p>First paragraph.</p>" in html
    assert "<p>Second paragraph.</p>" in html


def test_no_paragraph_for_heading():
    """A heading alone should not be wrapped in <p>."""
    html = markdown_to_html("# Only heading")
    assert "<h1>" in html
    assert "<p>" not in html


# ---------------------------------------------------------------------------
# Raw HTML escaping
# ---------------------------------------------------------------------------

def test_raw_html_escaped():
    md = "<script>alert(1)</script>"
    html = markdown_to_html(md)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


# ---------------------------------------------------------------------------
# Full document structure
# ---------------------------------------------------------------------------

def test_doctype_present():
    html = markdown_to_html("# Hello")
    assert html.startswith("<!DOCTYPE html>")


def test_viewport_meta():
    html = markdown_to_html("# Hello")
    assert 'name="viewport"' in html
    assert "content=" in html


def test_embedded_css():
    html = markdown_to_html("# Hello")
    assert "<style>" in html
    assert "font-family" in html


def test_title_from_h1():
    html = markdown_to_html("# My Title\n\nContent")
    assert "<title>My Title</title>" in html


def test_title_default_when_no_h1():
    html = markdown_to_html("Just text.")
    assert "<title>Markdown</title>" in html


# ---------------------------------------------------------------------------
# Unordered lists
# ---------------------------------------------------------------------------

def test_unordered_list_dash():
    md = "- item one\n- item two"
    html = markdown_to_html(md)
    assert "<ul>" in html
    assert "<li>item one</li>" in html
    assert "<li>item two</li>" in html


def test_unordered_list_star():
    md = "* item one\n* item two"
    html = markdown_to_html(md)
    assert "<ul>" in html


def test_unordered_list_plus():
    md = "+ item one\n+ item two"
    html = markdown_to_html(md)
    assert "<ul>" in html


# ---------------------------------------------------------------------------
# Ordered lists
# ---------------------------------------------------------------------------

def test_ordered_list():
    md = "1. first\n2. second\n3. third"
    html = markdown_to_html(md)
    assert "<ol>" in html
    assert "<li>first</li>" in html
    assert "<li>second</li>" in html
    assert "<li>third</li>" in html


# ---------------------------------------------------------------------------
# Blockquotes
# ---------------------------------------------------------------------------

def test_blockquote():
    md = "> This is a quote."
    html = markdown_to_html(md)
    assert "<blockquote>" in html
    assert "This is a quote" in html


# ---------------------------------------------------------------------------
# markdown_file_to_html
# ---------------------------------------------------------------------------

def test_markdown_file_to_html(tmp_path):
    input_file = tmp_path / "test.md"
    input_file.write_text("# File Test\n\nHello world.", encoding="utf-8")
    output_file = tmp_path / "out.html"

    result = markdown_file_to_html(input_file, output_file)
    assert "<h1>File Test</h1>" in result
    assert "<p>Hello world.</p>" in result
    assert output_file.exists()
    assert "File Test" in output_file.read_text(encoding="utf-8")


def test_markdown_file_to_html_no_output(tmp_path):
    input_file = tmp_path / "test.md"
    input_file.write_text("# No Output File\n\nJust testing.", encoding="utf-8")
    result = markdown_file_to_html(input_file)
    assert "<h1>No Output File</h1>" in result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_with_output(tmp_path, monkeypatch):
    """Test CLI with -o flag using monkeypatch on sys.argv."""
    input_file = tmp_path / "test.md"
    input_file.write_text("# CLI Test\n\nCLI content.", encoding="utf-8")
    output_file = tmp_path / "out.html"

    monkeypatch.setattr(sys, "argv", ["md2html", str(input_file), "-o", str(output_file)])
    cli_main()

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "<h1>CLI Test</h1>" in content
    assert "<p>CLI content.</p>" in content


def test_cli_stdout(tmp_path, capsys):
    """Without -o, output goes to stdout."""
    input_file = tmp_path / "test_stdout.md"
    input_file.write_text("# STDOUT\n\nprinted.", encoding="utf-8")

    cli_main([str(input_file)])
    captured = capsys.readouterr()
    assert "<h1>STDOUT</h1>" in captured.out
    assert "<p>printed.</p>" in captured.out


def test_cli_version(capsys):
    """--version prints version and exits."""
    with pytest.raises(SystemExit) as exc:
        cli_main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "md2html" in captured.out
    assert "1.0.0" in captured.out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_input():
    html = markdown_to_html("")
    assert "<!DOCTYPE html>" in html
    assert "<title>Markdown</title>" in html


def test_only_blank_lines():
    html = markdown_to_html("\n\n\n")
    assert "<!DOCTYPE html>" in html


def test_code_block_no_closing_fence():
    """An unclosed code block should still produce output."""
    md = "```python\nprint('hello')"
    html = markdown_to_html(md)
    assert "<pre><code" in html
    assert "print('hello')" in html
