#!/usr/bin/env python3
"""Build a WordPress WXR import from the captured theapplepi.org HTML.

Reads capture/html, writes wordpress/import/washington-apple-pi.wxr and
capture/inventory.json. Wording is taken from the captured pages.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
HTML_ROOT = ROOT / "capture" / "html"
OUT = ROOT / "wordpress" / "import" / "washington-apple-pi.wxr"
INVENTORY = ROOT / "capture" / "inventory.json"
MEDIA_MAP = ROOT / "wordpress" / "import" / "media-map.json"
ASSET_ROOT = ROOT / "capture" / "assets"
SITE = "https://www.theapplepi.org"
TZ = ZoneInfo("America/New_York")

PAGE_FILES = [
    ("index.html", "home", "Home", True),
    ("general-meetings.html", "general-meetings", "General Meetings", True),
    ("clubhouse-saturday.html", "clubhouse-saturday", "Clubhouse Saturday", True),
    ("thursday-learners.html", "thursday-learners", "Thursday Learners", True),
    ("special-interest-groups.html", "special-interest-groups", "Special Interest Groups", True),
    ("rump-saturdays.html", "rump-saturdays", "RUMP Saturdays", True),
    ("using-join-it.html", "using-join-it", "Using Join It", True),
    ("using-groupsio.html", "using-groupsio", "Using groups.io", True),
    ("outreachpartners.html", "outreachpartners", "Outreach/Partners", True),
    ("resistreuserecycle.html", "resistreuserecycle", "Resist/Reuse/Recycle", True),
    ("join-the-pi.html", "join-the-pi", "Join the Pi", True),
    ("members-only.html", "members-only", "Members only!", True),
    ("contact-us.html", "contact-us", "Contact Us", True),
    ("the-pi-board.html", "the-pi-board", "The Pi Board", True),
    ("why-join-the-pi.html", "why-join-the-pi", "Why Join the Pi", False),
    ("why-join-groupsio.html", "why-join-groupsio", "Why Join groups.io", False),
    ("patience.html", "patience", "Patience!", False),
    ("using-archives.html", "using-archives", "Using Archives", False),
    ("volunteer.html", "volunteer", "Volunteer", False),
    ("to-do.html", "to-do", "To-Do", False),
]

# Top-level menu. Children are page slugs. Parents without a slug are labels.
MENU = [
    ("Home", "home", []),
    ("Meet With Us", None, [
        "general-meetings",
        "clubhouse-saturday",
        "thursday-learners",
        "special-interest-groups",
        "rump-saturdays",
    ]),
    ("For Members", None, [
        "using-join-it",
        "using-groupsio",
        "outreachpartners",
        "resistreuserecycle",
        "join-the-pi",
        "members-only",
    ]),
    ("Blog", "blog", []),
    ("Contact Us", "contact-us", []),
    ("The Pi Board", "the-pi-board", []),
]

BLOG_DIR = HTML_ROOT / "blog"
SKIP_BLOG_PARTS = {"archives", "category"}


def decode_cfemail(value: str) -> str:
    key = int(value[:2], 16)
    return "".join(chr(int(value[i : i + 2], 16) ^ key) for i in range(2, len(value), 2))


def cdata(text: str) -> str:
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def local_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def rfc822(dt: datetime) -> str:
    return format_datetime(local_dt(dt))


def wp_date(dt: datetime) -> tuple[str, str]:
    local = local_dt(dt)
    gmt = local.astimezone(ZoneInfo("UTC"))
    return local.strftime("%Y-%m-%d %H:%M:%S"), gmt.strftime("%Y-%m-%d %H:%M:%S")


class Builder:
    def __init__(self) -> None:
        self.media: dict[str, dict] = {}
        self.next_id = 100

    def alloc(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def register_media(self, url: str, title: str) -> str:
        url = normalize_media_url(url)
        if not url or "theapplepi.org" not in url:
            return url
        if url not in self.media:
            self.media[url] = {
                "id": self.alloc(),
                "url": url,
                "title": title or Path(urlparse(url).path).name,
            }
        return url


def normalize_media_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/"):
        url = SITE + url
    parsed = urlparse(url)
    if parsed.netloc not in ("www.theapplepi.org", "theapplepi.org"):
        return url
    path = parsed.path
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{SITE}{path}{query}"


def rewrite_href(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return href
    if "email-protection#" in href:
        token = href.split("email-protection#", 1)[1]
        token = token.split("&", 1)[0].split("?", 1)[0]
        try:
            return "mailto:" + decode_cfemail(token)
        except Exception:
            return href
    if href.startswith("#"):
        return href
    absolute = href
    if href.startswith("//"):
        absolute = "https:" + href
    elif href.startswith("/"):
        absolute = SITE + href
    parsed = urlparse(absolute)
    if parsed.netloc and parsed.netloc not in ("www.theapplepi.org", "theapplepi.org", ""):
        return absolute
    path = parsed.path or "/"
    if path in ("/", "/index.html"):
        return "/"
    # The live footer links to /contact.html, which returns 404.
    # Point that published label at the real Contact Us page.
    if path == "/contact.html":
        return "/contact-us/"
    if path.startswith("/blog/archives") or path.startswith("/blog/category"):
        return "/blog/"
    if path.startswith("/blog/"):
        slug = path.strip("/").split("/")[-1]
        if slug:
            return f"/{slug}/"
    if path.endswith(".html"):
        slug = path.strip("/").rsplit(".", 1)[0]
        return f"/{slug}/"
    if path.startswith("/uploads/"):
        return normalize_media_url(absolute)
    return absolute or href


def is_blank_html(fragment: str) -> bool:
    text = re.sub(r"<[^>]+>", "", fragment)
    text = text.replace("\xa0", "").replace("\u200b", "").replace("&nbsp;", "")
    return text.strip() == ""


PURPLE = "#5040ae"
SIZE_PX = {"7": "2.4rem", "6": "1.9rem", "5": "1.35rem"}


def font_style(tag: Tag) -> str:
    styles = []
    color = (tag.get("color") or "").strip().lower()
    style = tag.get("style") or ""
    if color in ("#5040ae", "5040ae") or "80, 64, 174" in style or "80,64,174" in style:
        styles.append(f"color:{PURPLE}")
    elif color and color not in ("#2a2a2a", "#151e24", "#222222"):
        if color.startswith("#"):
            styles.append(f"color:{color}")
    size = str(tag.get("size") or "")
    if size in SIZE_PX:
        styles.append(f"font-size:{SIZE_PX[size]}")
    # style="color:rgb(80, 64, 174)" on strong/span
    if "color:" in style and "color:" not in ";".join(styles):
        match = re.search(r"color:\s*([^;]+)", style)
        if match:
            raw = match.group(1).strip()
            if "80, 64, 174" in raw or "80,64,174" in raw:
                styles.append(f"color:{PURPLE}")
            elif raw.startswith("#") and raw.lower() not in ("#2a2a2a", "#151e24", "#222", "#222222"):
                styles.append(f"color:{raw}")
    # de-dupe
    seen = []
    for item in styles:
        if item not in seen:
            seen.append(item)
    return ";".join(seen)


class Converter:
    def __init__(self, builder: Builder) -> None:
        self.builder = builder

    def render_inline(self, node) -> str:
        if isinstance(node, NavigableString):
            return esc(str(node))
        if not isinstance(node, Tag):
            return ""
        if node.name in ("script", "style"):
            return ""
        if node.name == "br":
            return "<br>"
        if node.name in ("strong", "b"):
            inner = self.render_children(node)
            style = font_style(node)
            if style:
                return f'<strong><span style="{style}">{inner}</span></strong>'
            return f"<strong>{inner}</strong>"
        if node.name in ("em", "i"):
            return f"<em>{self.render_children(node)}</em>"
        if node.name == "a":
            href = rewrite_href(node.get("href") or "")
            if not href:
                return self.render_children(node)
            target = ""
            if node.get("target") == "_blank":
                target = ' target="_blank" rel="noopener noreferrer"'
            return f'<a href="{esc(href)}"{target}>{self.render_children(node)}</a>'
        if node.name in ("font", "span"):
            inner = self.render_children(node)
            style = font_style(node)
            if style and not is_blank_html(inner):
                return f'<span style="{style}">{inner}</span>'
            return inner
        if node.name in ("ul", "ol"):
            return ""
        return self.render_children(node)

    def render_children(self, tag: Tag) -> str:
        return "".join(self.render_inline(child) for child in tag.children)

    def paragraph_block(self, inner: str, align: str | None) -> str:
        inner = re.sub(r"(?:\s|&nbsp;|\u00a0|\u200b|<br>)+$", "", inner)
        inner = re.sub(r"^(?:\s|&nbsp;|\u00a0|\u200b|<br>)+", "", inner)
        if is_blank_html(inner):
            return ""
        attrs = ""
        cls = ""
        if align in ("center", "right", "left"):
            attrs = f' {{"align":"{align}"}}'
            if align != "left":
                cls = f' class="has-text-align-{align}"'
        return f"<!-- wp:paragraph{attrs} -->\n<p{cls}>{inner}</p>\n<!-- /wp:paragraph -->"

    def list_block(self, tag: Tag) -> str:
        items = []
        for li in tag.find_all("li", recursive=False):
            inline: list[str] = []
            nested: list[str] = []

            def flush() -> None:
                html_inline = "".join(inline).strip()
                inline.clear()
                if not is_blank_html(html_inline):
                    nested.append(html_inline)

            for child in li.children:
                if isinstance(child, Tag) and child.name in ("ul", "ol"):
                    flush()
                    block = self.list_block(child)
                    if block:
                        nested.append(block)
                else:
                    inline.append(self.render_inline(child))
            flush()
            inner = "".join(nested).strip()
            if inner:
                items.append(f"<li>{inner}</li>")
        if not items:
            return ""
        name = "ul" if tag.name == "ul" else "ol"
        ordered = "" if name == "ul" else ' {"ordered":true}'
        return (
            f"<!-- wp:list{ordered} -->\n"
            f'<{name} class="wp-block-list">{"".join(items)}</{name}>\n'
            f"<!-- /wp:list -->"
        )

    def blocks_from_paragraph(self, tag: Tag) -> list[str]:
        align = None
        style = tag.get("style") or ""
        match = re.search(r"text-align:\s*(left|center|right)", style)
        if match:
            align = match.group(1)
        blocks: list[str] = []
        inline: list[str] = []

        def flush() -> None:
            html_inline = "".join(inline).strip()
            inline.clear()
            block = self.paragraph_block(html_inline, align)
            if block:
                blocks.append(block)

        for child in tag.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                flush()
                block = self.list_block(child)
                if block:
                    blocks.append(block)
            else:
                inline.append(self.render_inline(child))
        flush()
        return blocks

    def heading_block(self, tag: Tag) -> str:
        align = None
        style = tag.get("style") or ""
        match = re.search(r"text-align:\s*(left|center|right)", style)
        if match:
            align = match.group(1)
        inner = self.render_children(tag).strip()
        if is_blank_html(inner):
            return ""
        # Promote a single purple span to heading color when the whole heading is purple.
        attrs = {"level": 2}
        if align in ("center", "right"):
            attrs["textAlign"] = align
        if PURPLE in inner and inner.count("<") <= 6:
            attrs["style"] = {"color": {"text": PURPLE}}
        attr_json = json.dumps(attrs, separators=(",", ":"))
        cls = "wp-block-heading"
        style_attr = ""
        if "style" in attrs:
            cls += " has-text-color"
            style_attr = f' style="color:{PURPLE}"'
        if align in ("center", "right"):
            cls += f" has-text-align-{align}"
        return (
            f"<!-- wp:heading {attr_json} -->\n"
            f"<h2 class=\"{cls}\"{style_attr}>{inner}</h2>\n"
            f"<!-- /wp:heading -->"
        )

    def image_block(self, tag: Tag) -> str:
        img = tag.find("img")
        if not img or not img.get("src"):
            return ""
        src = img.get("src")
        if "file_icons" in src or "weebly.com" in src:
            return ""
        url = self.builder.register_media(src, img.get("alt") or "Picture")
        alt = esc(img.get("alt") or "")
        link = None
        anchor = tag.find("a")
        if anchor and anchor.get("href"):
            link = rewrite_href(anchor.get("href"))
            if link == url or link.rstrip("/") == url.rstrip("/"):
                link = url
        align = "center"
        style = tag.get("style") or ""
        match = re.search(r"text-align:\s*(left|center|right)", style)
        if match:
            align = match.group(1)
        img_html = f'<img src="{esc(url)}" alt="{alt}"/>'
        if link and not link.startswith("javascript"):
            img_html = f'<a href="{esc(link)}">{img_html}</a>'
        return (
            "<!-- wp:image {\"sizeSlug\":\"large\",\"linkDestination\":\"custom\"} -->\n"
            f'<figure class="wp-block-image align{align} size-large">{img_html}</figure>\n'
            "<!-- /wp:image -->"
        )

    def button_block(self, tag: Tag) -> str:
        href = rewrite_href(tag.get("href") or "")
        if not href:
            return ""
        label = tag.get_text(" ", strip=True)
        if not label:
            return ""
        outline = "is-style-outline" if "wsite-button-normal" in (tag.get("class") or []) else ""
        cls = "wp-block-button" + (f" {outline}" if outline else "")
        return (
            '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->\n'
            f'<div class="wp-block-buttons">'
            f'<!-- wp:button -->\n<div class="{cls}">'
            f'<a class="wp-block-button__link wp-element-button" href="{esc(href)}">{esc(label)}</a>'
            f"</div>\n<!-- /wp:button --></div>\n<!-- /wp:buttons -->"
        )

    def video_block(self, tag: Tag) -> str:
        src = tag.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        match = re.search(r"youtube\.com/embed/([^?&]+)", src)
        if not match:
            return ""
        video_id = match.group(1)
        embed = f"https://www.youtube.com/embed/{video_id}"
        return (
            "<!-- wp:html -->\n"
            f'<div class="wap-video"><iframe src="{esc(embed)}" title="YouTube video" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            'allowfullscreen loading="lazy"></iframe></div>\n'
            "<!-- /wp:html -->"
        )

    def file_block(self, anchor: Tag) -> str:
        href = anchor.get("href") or ""
        url = self.builder.register_media(href, "Pi By-laws 2021-02-26.pdf")
        name = "Pi By-laws 2021-02-26.pdf"
        return (
            "<!-- wp:file -->\n"
            f'<div class="wp-block-file"><a href="{esc(url)}">{esc(name)}</a>'
            f'<a href="{esc(url)}" class="wp-block-file__button" download>Download</a></div>\n'
            "<!-- /wp:file -->"
        )

    def form_block(self, form: Tag) -> str:
        """Reproduce the contact form fields. The copy does not submit anywhere."""
        parts = ['<form class="wap-contact-form" action="#" method="post" onsubmit="return false;">']
        title = form.find(["h2", "h1"])
        if title:
            parts.append(f"<h2>{esc(title.get_text(' ', strip=True))}</h2>")
        note = form.find(class_="wsite-form-fields-required-label")
        if note:
            parts.append(f'<p class="wap-required-note">{esc(note.get_text(" ", strip=True))}</p>')
        for field in form.select(".wsite-form-field"):
            label_el = field.find("label", class_="wsite-form-label")
            label = label_el.get_text(" ", strip=True) if label_el else ""
            if label:
                parts.append(f"<label>{esc(label)}</label>")
            if field.select_one(".wsite-form-input-first-name"):
                parts.append('<div class="wap-name-row">')
                parts.append('<input type="text" name="first" placeholder="First" aria-label="First">')
                parts.append('<input type="text" name="last" placeholder="Last" aria-label="Last">')
                parts.append("</div>")
                continue
            for box in field.select("input[type=checkbox]"):
                text = ""
                lab = box.find_next("label")
                if lab:
                    text = lab.get_text(" ", strip=True)
                parts.append(
                    f'<label class="wap-choice"><input type="checkbox"> {esc(text)}</label>'
                )
            for radio in field.select("input[type=radio]"):
                text = ""
                lab = radio.find_next("label")
                if lab:
                    text = lab.get_text(" ", strip=True)
                parts.append(
                    f'<label class="wap-choice"><input type="radio" name="{esc(label)}"> {esc(text)}</label>'
                )
            area = field.find("textarea")
            if area is not None:
                parts.append(f'<textarea name="message" rows="5"></textarea>')
            text_input = field.find("input", attrs={"type": "text"})
            if text_input is not None and not field.select_one(".wsite-form-input-first-name"):
                parts.append('<input type="text" name="email">')
        parts.append('<button type="button">Submit</button>')
        parts.append("</form>")
        inner = "\n".join(parts)
        return f"<!-- wp:html -->\n{inner}\n<!-- /wp:html -->"

    def columns_block(self, tag: Tag) -> str:
        row = tag.find("tr")
        if not row:
            return ""
        cells = [td for td in row.find_all("td", recursive=False)]
        if len(cells) < 2:
            return ""
        columns = []
        for cell in cells:
            width = None
            style = cell.get("style") or ""
            match = re.search(r"width:\s*([0-9.]+)%", style)
            if match:
                width = match.group(1)
            inner_blocks = []
            for child in cell.children:
                if isinstance(child, Tag):
                    inner_blocks.extend(self.convert_node(child))
            inner = "\n\n".join(block for block in inner_blocks if block)
            if not inner.strip():
                continue
            if width:
                columns.append(
                    (
                        width,
                        f'<!-- wp:column {{"width":"{width}%"}} -->\n'
                        f'<div class="wp-block-column" style="flex-basis:{width}%">{inner}</div>\n'
                        f"<!-- /wp:column -->",
                    )
                )
            else:
                columns.append(
                    (
                        None,
                        "<!-- wp:column -->\n"
                        f'<div class="wp-block-column">{inner}</div>\n'
                        "<!-- /wp:column -->",
                    )
                )
        if not columns:
            return ""
        body = "\n\n".join(block for _, block in columns)
        return f"<!-- wp:columns -->\n<div class=\"wp-block-columns\">\n{body}\n</div>\n<!-- /wp:columns -->"

    def convert_node(self, el: Tag) -> list[str]:
        if not isinstance(el, Tag):
            return []
        if el.name in ("script", "style"):
            return []
        classes = set(el.get("class") or [])
        if "wsite-spacer" in classes:
            return []
        if el.name in ("h2", "h1") and (
            "wsite-content-title" in classes or el.name == "h2"
        ):
            # Avoid treating form titles twice; form handler covers those.
            if el.find_parent("form"):
                return []
            block = self.heading_block(el)
            return [block] if block else []
        if "paragraph" in classes:
            return self.blocks_from_paragraph(el)
        if el.name == "div" and "wsite-image" in classes:
            block = self.image_block(el)
            return [block] if block else []
        if el.name == "a" and "wsite-button" in classes:
            block = self.button_block(el)
            return [block] if block else []
        if el.name == "iframe":
            block = self.video_block(el)
            return [block] if block else []
        if el.name == "form":
            return [self.form_block(el)]
        if (
            el.name == "div"
            and "wsite-multicol" in classes
            and "wsite-multicol-table-wrap" not in classes
        ):
            block = self.columns_block(el)
            return [block] if block else []
        pdf_link = None
        for anchor in el.find_all("a", href=True):
            if ".pdf" in anchor["href"].lower():
                pdf_link = anchor
                break
        icon = el.find("img", src=lambda s: bool(s) and "file_icons" in s)
        # Only the small Weebly file widget, not a whole section that happens to contain it.
        if (
            pdf_link is not None
            and icon is not None
            and el.find(class_="paragraph") is None
            and el.find("h2") is None
        ):
            return [self.file_block(pdf_link)]
        blocks: list[str] = []
        for child in el.children:
            if isinstance(child, Tag):
                blocks.extend(self.convert_node(child))
        return blocks

    def banner_block(self, soup: BeautifulSoup) -> str:
        img = soup.select_one(".banner img")
        if not img or not img.get("src"):
            return ""
        url = self.builder.register_media(img.get("src"), img.get("alt") or "Picture")
        alt = esc(img.get("alt") or "")
        return (
            '<!-- wp:group {"align":"full","style":{"color":{"background":"#0873d0"}},"layout":{"type":"constrained"}} -->\n'
            '<div class="wp-block-group alignfull has-background" style="background-color:#0873d0">\n'
            '<!-- wp:image {"align":"center","sizeSlug":"large"} -->\n'
            f'<figure class="wp-block-image aligncenter size-large"><img src="{esc(url)}" alt="{alt}"/></figure>\n'
            "<!-- /wp:image -->\n"
            "</div>\n<!-- /wp:group -->"
        )

    def page_content(self, soup: BeautifulSoup, include_banner: bool) -> str:
        blocks: list[str] = []
        if include_banner:
            banner = self.banner_block(soup)
            if banner:
                blocks.append(banner)
        content = soup.select_one("#wsite-content") or soup.select_one(".blog-content")
        if content:
            blocks.extend(self.convert_node(content))
        return "\n\n".join(block for block in blocks if block)

    def post_content(self, soup: BeautifulSoup) -> str:
        content = soup.select_one(".blog-content")
        if not content:
            return ""
        blocks = self.convert_node(content)
        return "\n\n".join(block for block in blocks if block)


def load_comments(soup: BeautifulSoup) -> list[dict]:
    comments = []
    closed = soup.select_one(".blog-notice-comments-closed") is not None
    for wrap in soup.select(".blogCommentWrap"):
        author = wrap.select_one(".name")
        date_el = wrap.select_one(".blogCommentDate")
        text_el = wrap.select_one(".blogCommentText")
        if not (author and date_el and text_el):
            continue
        raw_date = date_el.get_text(" ", strip=True)
        try:
            dt = datetime.strptime(raw_date, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=TZ)
        except ValueError:
            dt = datetime(2024, 1, 1, tzinfo=TZ)
        comments.append(
            {
                "author": author.get_text(" ", strip=True),
                "date": dt,
                "content": text_el.get_text("\n", strip=True),
            }
        )
    return comments, closed


def parse_post_date(soup: BeautifulSoup) -> datetime:
    el = soup.select_one(".blog-date .date-text") or soup.select_one(".blog-date")
    raw = el.get_text(" ", strip=True) if el else ""
    try:
        return datetime.strptime(raw, "%m/%d/%Y").replace(hour=12, tzinfo=TZ)
    except ValueError:
        return datetime(2024, 1, 1, 12, tzinfo=TZ)


def post_title(soup: BeautifulSoup, fallback: str) -> str:
    el = soup.select_one("h2.blog-title")
    if el:
        return el.get_text(" ", strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.replace(" - THE PI", "").strip()
    return fallback


def visible_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "lxml")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def item_xml(
    *,
    title: str,
    link: str,
    creator: str,
    guid: str,
    content: str,
    post_id: int,
    date: datetime,
    slug: str,
    status: str,
    post_type: str,
    parent: int = 0,
    menu_order: int = 0,
    comment_status: str = "closed",
    extra: str = "",
    comments_xml: str = "",
) -> str:
    local, gmt = wp_date(date)
    return f"""<item>
<title>{esc(title)}</title>
<link>{esc(link)}</link>
<pubDate>{rfc822(date)}</pubDate>
<dc:creator>{cdata(creator)}</dc:creator>
<guid isPermaLink="false">{esc(guid)}</guid>
<description></description>
<content:encoded>{cdata(content)}</content:encoded>
<excerpt:encoded>{cdata("")}</excerpt:encoded>
<wp:post_id>{post_id}</wp:post_id>
<wp:post_date>{local}</wp:post_date>
<wp:post_date_gmt>{gmt}</wp:post_date_gmt>
<wp:post_modified>{local}</wp:post_modified>
<wp:post_modified_gmt>{gmt}</wp:post_modified_gmt>
<wp:comment_status>{comment_status}</wp:comment_status>
<wp:ping_status>closed</wp:ping_status>
<wp:post_name>{esc(slug)}</wp:post_name>
<wp:status>{status}</wp:status>
<wp:post_parent>{parent}</wp:post_parent>
<wp:menu_order>{menu_order}</wp:menu_order>
<wp:post_type>{post_type}</wp:post_type>
<wp:post_password></wp:post_password>
<wp:is_sticky>0</wp:is_sticky>
{extra}{comments_xml}</item>
"""


def meta(key: str, value: str) -> str:
    return (
        "<wp:postmeta>\n"
        f"<wp:meta_key>{esc(key)}</wp:meta_key>\n"
        f"<wp:meta_value>{cdata(value)}</wp:meta_value>\n"
        "</wp:postmeta>\n"
    )


def local_asset(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc not in ("www.theapplepi.org", "theapplepi.org"):
        return None
    rel = parsed.path.lstrip("/")
    if not rel:
        return None
    candidate = ASSET_ROOT / rel
    if parsed.query:
        hashed = candidate.with_name(candidate.name + "_" + hashlib.md5(parsed.query.encode()).hexdigest()[:8])
        if hashed.is_file():
            return str(hashed.relative_to(ROOT / "capture"))
    if candidate.is_file():
        return str(candidate.relative_to(ROOT / "capture"))
    return None


def main() -> None:
    builder = Builder()
    converter = Converter(builder)
    pages = []
    posts = []
    now = datetime(2026, 9, 22, 12, 0, tzinfo=TZ)

    for filename, slug, menu_label, _in_menu in PAGE_FILES:
        path = HTML_ROOT / filename
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
        title = menu_label
        content = converter.page_content(soup, include_banner=(slug == "home"))
        original = ""
        node = soup.select_one("#wsite-content")
        if node:
            original = node.get_text(" ", strip=True)
        pages.append(
            {
                "id": builder.alloc(),
                "slug": slug,
                "title": title,
                "menu_label": menu_label,
                "content": content,
                "source": filename,
                "original_chars": len(original),
                "converted_chars": len(visible_text(content)),
            }
        )

    blog_id = builder.alloc()
    pages.append(
        {
            "id": blog_id,
            "slug": "blog",
            "title": "Blog",
            "menu_label": "Blog",
            "content": "",
            "source": "blog.html",
            "original_chars": 0,
            "converted_chars": 0,
        }
    )

    for path in sorted(BLOG_DIR.glob("*.html")):
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
        slug = path.stem
        title = post_title(soup, slug)
        content = converter.post_content(soup)
        comments, closed = load_comments(soup)
        posts.append(
            {
                "id": builder.alloc(),
                "slug": slug,
                "title": title,
                "content": content,
                "date": parse_post_date(soup),
                "comments": comments,
                "comment_status": "closed" if closed else "open",
                "source": f"blog/{path.name}",
            }
        )
    posts.sort(key=lambda post: post["date"], reverse=True)

    page_ids = {page["slug"]: page["id"] for page in pages}
    items: list[str] = []

    for page in pages:
        items.append(
            item_xml(
                title=page["title"],
                link=f"{SITE}/{page['slug']}/",
                creator="pi-editor",
                guid=f"{SITE}/{page['source']}",
                content=page["content"],
                post_id=page["id"],
                date=now,
                slug=page["slug"],
                status="publish",
                post_type="page",
            )
        )

    comment_id = 8000
    for post in posts:
        comments_xml = []
        for comment in post["comments"]:
            local, gmt = wp_date(comment["date"])
            comments_xml.append(
                "<wp:comment>\n"
                f"<wp:comment_id>{comment_id}</wp:comment_id>\n"
                f"<wp:comment_author>{cdata(comment['author'])}</wp:comment_author>\n"
                "<wp:comment_author_email></wp:comment_author_email>\n"
                "<wp:comment_author_url></wp:comment_author_url>\n"
                "<wp:comment_author_IP></wp:comment_author_IP>\n"
                f"<wp:comment_date>{local}</wp:comment_date>\n"
                f"<wp:comment_date_gmt>{gmt}</wp:comment_date_gmt>\n"
                f"<wp:comment_content>{cdata(comment['content'])}</wp:comment_content>\n"
                "<wp:comment_approved>1</wp:comment_approved>\n"
                "<wp:comment_type></wp:comment_type>\n"
                "<wp:comment_parent>0</wp:comment_parent>\n"
                "<wp:comment_user_id>0</wp:comment_user_id>\n"
                "</wp:comment>\n"
            )
            comment_id += 1
        items.append(
            item_xml(
                title=post["title"],
                link=f"{SITE}/blog/{post['slug']}",
                creator="pi-editor",
                guid=f"{SITE}/blog/{post['slug']}",
                content=post["content"],
                post_id=post["id"],
                date=post["date"],
                slug=post["slug"],
                status="publish",
                post_type="post",
                comment_status=post["comment_status"],
                comments_xml="".join(comments_xml),
            )
        )

    for url, media in builder.media.items():
        filename = Path(urlparse(url).path).name
        items.append(
            item_xml(
                title=media["title"] or filename,
                link=url,
                creator="pi-editor",
                guid=url,
                content="",
                post_id=media["id"],
                date=now,
                slug=re.sub(r"[^a-z0-9-]+", "-", filename.lower()).strip("-")[:180],
                status="inherit",
                post_type="attachment",
                extra=(
                    f"<wp:attachment_url>{cdata(url)}</wp:attachment_url>\n"
                    + meta("_wap_source_url", url)
                ),
            )
        )

    # Navigation menu items. Parents are custom links; children point at pages.
    menu_order = 1
    menu_items_xml = []

    def add_menu_item(title: str, parent: int, object_id: int | None, url: str) -> int:
        nonlocal menu_order
        item_id = builder.alloc()
        if object_id:
            extra = (
                meta("_menu_item_type", "post_type")
                + meta("_menu_item_object", "page")
                + meta("_menu_item_object_id", str(object_id))
                + meta("_menu_item_menu_item_parent", str(parent))
                + meta("_menu_item_target", "")
                + meta("_menu_item_url", "")
            )
        else:
            extra = (
                meta("_menu_item_type", "custom")
                + meta("_menu_item_object", "custom")
                + meta("_menu_item_object_id", "0")
                + meta("_menu_item_menu_item_parent", str(parent))
                + meta("_menu_item_target", "")
                + meta("_menu_item_url", url)
            )
        menu_items_xml.append(
            item_xml(
                title=title,
                link="",
                creator="pi-editor",
                guid=f"{SITE}/?menu-item={item_id}",
                content="",
                post_id=item_id,
                date=now,
                slug=f"menu-{item_id}",
                status="publish",
                post_type="nav_menu_item",
                menu_order=menu_order,
                extra=(
                    '<category domain="nav_menu" nicename="primary"><![CDATA[Primary]]></category>\n'
                    + extra
                ),
            )
        )
        menu_order += 1
        return item_id

    labels = {page["slug"]: page["menu_label"] for page in pages}
    for title, slug, children in MENU:
        if slug:
            parent_id = add_menu_item(title, 0, page_ids[slug], "")
        else:
            parent_id = add_menu_item(title, 0, None, "#")
        for child_slug in children:
            add_menu_item(labels[child_slug], parent_id, page_ids[child_slug], "")

    channel = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"
 xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
 xmlns:content="http://purl.org/rss/1.0/modules/content/"
 xmlns:wfw="http://wellformedweb.org/CommentAPI/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:wp="http://wordpress.org/export/1.2/">
<channel>
<title>THE PI</title>
<link>{SITE}</link>
<description>Washington Apple Pi</description>
<pubDate>{rfc822(now)}</pubDate>
<language>en-US</language>
<wp:wxr_version>1.2</wp:wxr_version>
<wp:base_site_url>{SITE}</wp:base_site_url>
<wp:base_blog_url>{SITE}</wp:base_blog_url>
<wp:author>
<wp:author_id>2</wp:author_id>
<wp:author_login>pi-editor</wp:author_login>
<wp:author_email>office@wap.org</wp:author_email>
<wp:author_display_name>{cdata("Washington Apple Pi")}</wp:author_display_name>
<wp:author_first_name>{cdata("Washington Apple")}</wp:author_first_name>
<wp:author_last_name>{cdata("Pi")}</wp:author_last_name>
</wp:author>
<wp:term>
<wp:term_id>2</wp:term_id>
<wp:term_taxonomy>nav_menu</wp:term_taxonomy>
<wp:term_slug>primary</wp:term_slug>
<wp:term_name>{cdata("Primary")}</wp:term_name>
</wp:term>
{''.join(items)}
{''.join(menu_items_xml)}
</channel>
</rss>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(channel, encoding="utf-8")

    inventory = {
        "source": SITE,
        "crawled": "2026-10-05",
        "pages": [
            {
                "slug": page["slug"],
                "title": page["title"],
                "menu_label": page["menu_label"],
                "source": page["source"],
                "in_primary_menu": page["slug"] in {slug for _, slug, _ in [(a, b, c) for a, b, c in MENU] if False} or any(
                    page["slug"] == slug or page["slug"] in children for _, slug, children in MENU
                ),
                "original_text_chars": page["original_chars"],
                "converted_text_chars": page["converted_chars"],
            }
            for page in pages
        ],
        "posts": [
            {
                "slug": post["slug"],
                "title": post["title"],
                "date": post["date"].date().isoformat(),
                "comment_status": post["comment_status"],
                "comments": len(post["comments"]),
                "source": post["source"],
            }
            for post in posts
        ],
        "media_count": len(builder.media),
        "media": [item["url"] for item in builder.media.values()],
    }
    INVENTORY.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    media_map = {}
    missing = []
    for url in builder.media:
        rel = local_asset(url)
        if rel:
            media_map[url] = rel
        else:
            missing.append(url)
    MEDIA_MAP.write_text(json.dumps(media_map, indent=2), encoding="utf-8")
    print(f"media map {len(media_map)} missing {len(missing)}")
    for url in missing:
        print("  missing", url)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"pages {len(pages)} posts {len(posts)} media {len(builder.media)}")
    for page in pages:
        if page["slug"] == "blog":
            continue
        ratio = 0
        if page["original_chars"]:
            ratio = page["converted_chars"] / page["original_chars"]
        flag = "" if 0.55 <= ratio <= 1.35 else "  CHECK"
        print(f"  {page['slug']}: orig {page['original_chars']} conv {page['converted_chars']} ratio {ratio:.2f}{flag}")


if __name__ == "__main__":
    main()
