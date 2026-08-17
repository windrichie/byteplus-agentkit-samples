# md2html

A pure-Python CLI tool that converts Markdown files to self-contained HTML files with polished, modern typography.

## Features

- **ATX headings** `#` through `######`
- **Bold** (`**text**`, `__text__`) and **italic** (`*text*`, `_text_`)
- **Inline code** `` `code` ``
- **Fenced code blocks** with optional language tag
- **Links** `[text](url)`
- **Unordered lists** (`-`, `*`, `+`) and **ordered lists** (`1.`)
- **Blockquotes** (`>`)
- HTML escaping — user input cannot inject HTML
- Standalone HTML output with embedded CSS

## Usage

```bash
# Convert input.md → input.html (default)
python -m md2html input.md

# Specify output path
python -m md2html input.md -o output.html

# Print to stdout
python -m md2html input.md -o -
```

## Requirements

- Python 3.10+
- No third-party packages required

## Development

```bash
python -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest
```
