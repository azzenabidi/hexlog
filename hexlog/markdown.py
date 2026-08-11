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


def _close_list(out, list_tag):
    """Emit the closing tag for an open list, returning the cleared state."""
    if list_tag:
        out.append(f"</{list_tag}>")
    return None


def _heading_html(line):
    """HTML for an ATX heading line, or None if it is not a heading."""
    match = _HEADING.match(line)
    if match is None:
        return None
    level = len(match.group(1))
    return f"<h{level}>{_inline(match.group(2))}</h{level}>"


def _append_list_item(out, list_tag, tag, text):
    """Emit an <li>, opening the `tag` list wrapper when it changes."""
    if list_tag != tag:
        if list_tag:
            out.append(f"</{list_tag}>")
        out.append(f"<{tag}>")
    out.append(f"<li>{_inline(text)}</li>")
    return tag


def render_markdown(text):
    """Convert `text` into an HTML fragment suitable for QTextEdit.setHtml."""
    out = []
    list_tag = None  # "ul", "ol", or None while grouping consecutive items

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            list_tag = _close_list(out, list_tag)
            continue
        heading = _heading_html(line)
        if heading is not None:
            list_tag = _close_list(out, list_tag)
            out.append(heading)
            continue
        if stripped.startswith("- "):
            list_tag = _append_list_item(out, list_tag, "ul", stripped[2:])
            continue
        match = _ORDERED.match(stripped)
        if match:
            list_tag = _append_list_item(out, list_tag, "ol", match.group(2))
            continue
        list_tag = _close_list(out, list_tag)
        out.append(f"<p>{_inline(stripped)}</p>")
    _close_list(out, list_tag)
    return "\n".join(out)
