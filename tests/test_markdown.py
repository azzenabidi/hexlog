"""Tests for the release-notes markdown renderer (no GUI required)."""

from hexlog.markdown import render_markdown


def test_headings_become_atx_html():
    html = render_markdown("## Combat\n### Initiative")
    assert "<h2>Combat</h2>" in html
    assert "<h3>Initiative</h3>" in html


def test_bullets_group_into_one_list():
    html = render_markdown("- one\n- two\n\n- three")
    assert "<ul>" in html
    assert html.count("<li>") == 3
    assert html.index("</ul>") < html.rindex("<ul>")


def test_numbered_list_uses_ordered_tags():
    html = render_markdown("1. first\n2. second")
    assert "<ol>" in html
    assert "<li>first</li>" in html
    assert "<li>second</li>" in html


def test_inline_emphasis_and_code():
    html = render_markdown("**bold** and *italic* and `code`")
    assert "<b>bold</b>" in html
    assert "<i>italic</i>" in html
    assert "<code>code</code>" in html


def test_links_become_anchors():
    html = render_markdown("See [the release](https://example.test).")
    assert '<a href="https://example.test">the release</a>' in html


def test_raw_html_is_escaped():
    html = render_markdown("Drop <script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_notes_render_empty():
    assert render_markdown("") == ""
