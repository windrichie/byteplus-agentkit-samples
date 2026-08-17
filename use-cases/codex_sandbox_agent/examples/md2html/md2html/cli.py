"""Command-line interface for md2html."""

import argparse
import sys
import os

from md2html.converter import markdown_to_html

__version__ = "1.0.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="md2html",
        description="Convert a Markdown file to a self-contained HTML file.",
    )
    parser.add_argument(
        "input",
        metavar="INPUT.md",
        help="Path to the input Markdown file.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        default=None,
        help="Output path. Use '-' for stdout (default).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    input_path = args.input

    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, encoding="utf-8") as f:
            markdown_text = f.read()
    except OSError as exc:
        print(f"Error: cannot read {input_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    html_doc = markdown_to_html(markdown_text)

    output_path = args.output

    if output_path is None or output_path == "-":
        sys.stdout.write(html_doc)
    else:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_doc)
        except OSError as exc:
            print(f"Error: cannot write {output_path}: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
