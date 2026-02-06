from __future__ import annotations

import logging
import re
import time
from pathlib import Path
import sys

import requests

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts import configure_sites as cs


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://av-kantei.com"
REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_STATUSES = {429, 500, 502, 503, 504}

NOTICE_CLASS = "avk-legal-notice"
STYLE_MARKER = "avk-toc-hide"

PREFIX_BLOCK = """<!-- wp:html -->
<style id="avk-toc-hide">
.toc,
#toc,
.toc-container,
.toc-title,
.ez-toc-container,
.ez-toc-title,
.cocoon-toc,
.entry-content .toc,
.entry-content #toc {
  display: none !important;
}
</style>
<div class="avk-legal-notice" style="margin:14px 0 16px;padding:12px 14px;border:1px solid rgba(0,0,0,.08);border-radius:10px;background:rgba(0,0,0,.02);font-size:13px;line-height:1.7;">
  <div style="color:#d00;font-weight:700;">※本ページは成人向け内容を含みます。18歳未満の方は閲覧できません。</div>
  <div style="color:#444;">※当サイトはアフィリエイト広告を利用しています。</div>
</div>
<!-- /wp:html -->
"""

TOC_PATTERNS = [
    re.compile(r"\[toc\]", re.I),
    re.compile(r"\[table of contents\]", re.I),
    re.compile(r"<!--\s*wp:ez-toc\/block.*?-->(.*?)<!--\s*\/wp:ez-toc\/block\s*-->", re.S | re.I),
    re.compile(r"<div[^>]+(?:id=[\"']toc[\"']|class=[\"'][^\"']*toc[^\"']*[\"'])[^>]*>.*?</div>", re.S | re.I),
]


def _request_with_retry(method: str, url: str, session: requests.Session, **kwargs) -> requests.Response:
    last_res = None
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            if res.status_code in RETRY_STATUSES:
                last_res = res
                logger.warning(f"{method} {url} -> {res.status_code} (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(1.5 * attempt)
                continue
            return res
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"{method} {url} failed (attempt {attempt}/{MAX_RETRIES}): {exc}")
            time.sleep(1.5 * attempt)
    if last_res is not None:
        return last_res
    raise last_exc if last_exc else RuntimeError("request failed")


def _iter_posts(session: requests.Session):
    page = 1
    while True:
        res = _request_with_retry(
            "GET",
            f"{BASE_URL}/wp-json/wp/v2/posts",
            session,
            params={"per_page": 100, "page": page, "context": "edit", "status": "publish"},
        )
        if res.status_code == 400 and "rest_post_invalid_page_number" in res.text:
            break
        res.raise_for_status()
        posts = res.json()
        if not posts:
            break
        for post in posts:
            yield post
        total_pages = int(res.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1


def _strip_toc(content: str) -> tuple[str, bool]:
    new_content = content
    changed = False
    for pattern in TOC_PATTERNS:
        next_content, n = pattern.subn("", new_content)
        if n:
            changed = True
            new_content = next_content
    return new_content, changed


def _ensure_prefix(content: str) -> tuple[str, bool]:
    has_notice = NOTICE_CLASS in content
    has_style = STYLE_MARKER in content
    if has_notice and has_style:
        return content, False
    return f"{PREFIX_BLOCK}\n\n{content}", True


def main() -> None:
    session = requests.Session()
    session.auth = (cs.WP_USERNAME, cs.WP_APP_PASSWORD)

    scanned = 0
    updated = 0
    toc_cleaned = 0
    notices_added = 0

    for post in _iter_posts(session):
        scanned += 1
        post_id = post.get("id")
        content_obj = post.get("content", {}) or {}
        content = content_obj.get("raw") or content_obj.get("rendered") or ""

        new_content, toc_changed = _strip_toc(content)
        newer_content, notice_changed = _ensure_prefix(new_content)

        if not toc_changed and not notice_changed:
            continue

        res = _request_with_retry(
            "POST",
            f"{BASE_URL}/wp-json/wp/v2/posts/{post_id}",
            session,
            json={"content": newer_content},
        )
        res.raise_for_status()

        updated += 1
        if toc_changed:
            toc_cleaned += 1
        if notice_changed:
            notices_added += 1

        if updated % 20 == 0:
            logger.info(
                f"progress: scanned={scanned}, updated={updated}, toc_cleaned={toc_cleaned}, notices_added={notices_added}"
            )

    logger.info(
        f"done: scanned={scanned}, updated={updated}, toc_cleaned={toc_cleaned}, notices_added={notices_added}"
    )


if __name__ == "__main__":
    main()
