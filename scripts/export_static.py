#!/usr/bin/env python3
"""Export the local WordPress preview to docs/ for GitHub Pages.

Internal links and files are rewritten to /Apple-Pi-Wordpress/ so the
export works at https://kerschberg-lgtm.github.io/Apple-Pi-Wordpress/.
"""

from __future__ import annotations

import re
import shutil
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
ORIGIN = "http://localhost:8080"
PREFIX = "/Apple-Pi-Wordpress"
SKIP_PREFIXES = (
    "/wp-admin",
    "/wp-login.php",
    "/xmlrpc.php",
    "/wp-json",
    "/feed",
    "/comments/feed",
)

HTML_TYPES = ("text/html", "application/xhtml")
TEXT_SUFFIXES = {".html", ".css", ".js", ".svg"}
ASSET_SUFFIXES = {
    ".css", ".js", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".ico", ".map",
}


def same_origin(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in ("localhost:8080", "127.0.0.1:8080")


def clean_path(url: str) -> str | None:
    """Return the site path for a same-origin URL, without a query or fragment."""
    url, _frag = urldefrag(url)
    if url.startswith("//"):
        return None
    if url.startswith("/"):
        path = url
    else:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        if not same_origin(url):
            return None
        path = parsed.path or "/"
    path = path.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    for prefix in SKIP_PREFIXES:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            return None
    if "replytocom=" in url or path.rstrip("/").endswith("/feed"):
        return None
    return path


def dest_for(path: str) -> Path:
    suffix = Path(path).suffix.lower()
    relative = path.lstrip("/")
    if path.endswith("/") or suffix == "":
        if relative == "":
            return OUT / "index.html"
        return OUT / relative.strip("/") / "index.html"
    return OUT / relative


def looks_like_asset(path: str) -> bool:
    return Path(path).suffix.lower() in ASSET_SUFFIXES


def extract_links(html: str, page_url: str) -> set[str]:
    found: set[str] = set()
    for match in re.findall(r"""(?i)\b(?:href|src|poster|data-src)=['"]([^'"]+)['"]""", html):
        found.add(urljoin(page_url, match))
    for match in re.findall(r"""(?i)\bsrcset=['"]([^'"]+)['"]""", html):
        for part in match.split(","):
            bit = part.strip().split(" ")[0]
            if bit:
                found.add(urljoin(page_url, bit))
    for match in re.findall(r"""url\(\s*['"]?([^)'"]+)""", html):
        found.add(urljoin(page_url, match))
    return found


def rewrite(text: str) -> str:
    text = text.replace("http://localhost:8080", PREFIX)
    text = text.replace("http://127.0.0.1:8080", PREFIX)
    text = text.replace("http:\\/\\/localhost:8080", "\\/Apple-Pi-Wordpress")
    text = text.replace("http:\\/\\/127.0.0.1:8080", "\\/Apple-Pi-Wordpress")

    def repl_attr(match: re.Match) -> str:
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith("//") or url.startswith(PREFIX + "/") or url == PREFIX:
            return match.group(0)
        if url.startswith("/"):
            return f"{attr}={quote}{PREFIX}{url}{quote}"
        return match.group(0)

    text = re.sub(r"(?i)\b(href|src|action|poster|data-src)=([\'\"])([^\'\"]*)\2", repl_attr, text)

    def repl_srcset(match: re.Match) -> str:
        quote, value = match.group(1), match.group(2)
        parts = []
        for piece in value.split(","):
            piece = piece.strip()
            if not piece:
                continue
            bits = piece.split()
            url = bits[0]
            if url.startswith("/") and not url.startswith("//") and not url.startswith(PREFIX + "/"):
                bits[0] = PREFIX + url
            parts.append(" ".join(bits))
        return f"srcset={quote}{', '.join(parts)}{quote}"

    text = re.sub(r"(?i)\bsrcset=([\'\"])([^\'\"]*)\1", repl_srcset, text)

    def repl_css(match: re.Match) -> str:
        quote = match.group(1) or ""
        url = match.group(2)
        if url.startswith("//") or url.startswith(PREFIX + "/") or url == PREFIX:
            return match.group(0)
        if url.startswith("/"):
            return f"url({quote}{PREFIX}{url}{quote})"
        return match.group(0)

    text = re.sub(r"url\(\s*([\'\"]?)(/[^)\'\"]+)\1\s*\)", repl_css, text)
    text = re.sub(r"<link[^>]+rel=[\'\"]https://api\.w\.org/[\'\"][^>]*>", "", text)
    text = re.sub(r"<link[^>]+type=[\'\"]application/rss\+xml[\'\"][^>]*>", "", text, flags=re.I)
    text = re.sub(r"<link[^>]+rel=[\'\"]pingback[\'\"][^>]*>", "", text, flags=re.I)
    # Discovery endpoints do not exist on the static site, and oEmbed query
    # strings still contain a percent-encoded localhost origin.
    text = re.sub(
        r"<link[^>]+(?:wp-json|xmlrpc\.php|oembed|localhost|127\.0\.0\.1)[^>]*>",
        "",
        text,
        flags=re.I,
    )
    text = text.replace("http%3A%2F%2Flocalhost%3A8080", "")
    text = text.replace("http%3A%2F%2F127.0.0.1%3A8080", "")
    text = text.replace("http%3A//localhost%3A8080", "")
    text = text.replace("localhost:8080", "")
    text = text.replace("127.0.0.1:8080", "")
    return text


def crawl() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    session = requests.Session()
    session.headers["User-Agent"] = "WashingtonApplePi-static-export/1.0"
    queue: deque[str] = deque([ORIGIN + "/"])
    seen: set[str] = set()
    saved: list[Path] = []

    while queue:
        url = queue.popleft()
        path = clean_path(url)
        if not path or path in seen:
            continue
        seen.add(path)
        try:
            response = session.get(urljoin(ORIGIN, path), timeout=60, allow_redirects=True)
        except requests.RequestException as exc:
            print(f"skip {path}: {exc}")
            continue
        if response.status_code != 200:
            print(f"skip {path}: HTTP {response.status_code}")
            continue
        final_path = clean_path(response.url) or path
        if final_path in seen and final_path != path:
            continue
        seen.add(final_path)
        content_type = response.headers.get("content-type", "")
        is_html = any(kind in content_type for kind in HTML_TYPES) and not looks_like_asset(final_path)
        dest = dest_for(final_path if not is_html else (final_path if final_path.endswith("/") or Path(final_path).suffix == "" else final_path))
        if is_html:
            # Directory-style pages become index.html even if the path has no slash.
            if Path(final_path).suffix.lower() not in ASSET_SUFFIXES:
                dest = dest_for(final_path if final_path.endswith("/") else final_path + "/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if is_html:
            html = response.text
            dest.write_text(html, encoding="utf-8")
            for link in extract_links(html, response.url):
                linked = clean_path(link)
                if linked and linked not in seen:
                    queue.append(urljoin(ORIGIN, linked))
            print(f"page {final_path}")
        else:
            dest.write_bytes(response.content)
            if dest.suffix.lower() == ".css":
                css = response.content.decode("utf-8", errors="replace")
                for match in re.findall(r"url\(\s*['\"]?([^)'\"]+)", css):
                    linked = clean_path(urljoin(response.url, match))
                    if linked and linked not in seen:
                        queue.append(urljoin(ORIGIN, linked))
            print(f"file {final_path}")
        saved.append(dest)

    rewritten = 0
    for path in saved:
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "index.html":
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        updated = rewrite(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            rewritten += 1
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    pages = list(OUT.rglob("index.html"))
    print(f"saved {len(saved)} files, rewrote {rewritten}, pages {len(pages)}")


if __name__ == "__main__":
    crawl()
