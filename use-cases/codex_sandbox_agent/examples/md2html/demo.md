# md2html Demo

Welcome to the **md2html** converter demo. This file exercises *every* supported feature.

## Text Formatting

You can write **bold** text and __also with underscores__. For *italic* use asterisks or _underscores_. Combine them for **_bold italic_** or __*italic bold*__.

Inline `code` is rendered as a `<code>` element. If you have `**bold inside code**` it should not be formatted.

## Links

Visit [OpenAI](https://openai.com) or the [Python documentation](https://docs.python.org/3/). Links are styled with an accent colour.

## Fenced Code Blocks

Here is a Python code block with a language tag:

```python
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

print(greet("World"))
```

And a plain code block (no language tag):

```
Raw text block.
No formatting applied.
```

## Blockquotes

> This is a blockquote.
>
> It can span multiple paragraphs.
>
> > Nested blockquotes work too.

## Lists

Unordered list:

- First item
- Second item with **bold**
- Third item with `inline code`

Ordered list:

1. Step one
2. Step two
3. Step three

## Combined Example

Here is a paragraph with **bold**, *italic*, `code`, and a [link](https://example.com) all in one line.

### Level 3 Heading

#### Level 4 Heading

##### Level 5 Heading

###### Level 6 Heading

That's all, folks!
