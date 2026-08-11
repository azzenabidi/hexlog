"""Tiny markdown-to-HTML renderer for GitHub release notes.

Covers the constructs the project's release notes actually use (ATX
headings, bullet and numbered lists, links, ``code``, **bold**, *italic*)
without pulling in a full markdown parser. Input is escaped before inline
styling, so note text can never smuggle raw HTML into the UI.
"""

import html
import re

_INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_ORDERED = re.compile(r"^(\d+)\.\s+(.*)$")


def _inline(text):
    """Escape a line, then apply inline link/code/emphasis rules."""
    text = html.escape(text, quote=False)
    text = _INLINE_LINK.sub(r'<a href="\2">\1</a>', text)
    text = _CODE.sub(r"<code>\1</code>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    return text


def render_markdown(text):
    """Convert `text` into an HTML fragment suitable for QTextEdit.setHtml."""
    out = []
    list_tag = None  # "ul", "ol", or None while grouping consecutive items

    def close_list():
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        match = _HEADING.match(line)
        if match:
            close_list()
            level = len(match.group(1))
            out.append(f"<h{level}>{_inline(match.group(2))}</h{level}>")
            continue
        if stripped.startswith("- "):
            if list_tag != "ul":
                close_list()
                out.append("<ul>")
                list_tag = "ul"
            out.append(f"<li>{_inline(stripped[2:])}</li>")
            continue
        match = _ORDERED.match(stripped)
        if match:
            if list_tag != "ol":
                close_list()
                out.append("<ol>")
                list_tag = "ol"
            out.append(f"<li>{_inline(match.group(2))}</li>")
            continue
        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")
    close_list()
    return "\n".join(out)
