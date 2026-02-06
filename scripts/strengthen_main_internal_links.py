from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
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

BLOCK_START = "<!-- avk-internal-links:start -->"
BLOCK_END = "<!-- avk-internal-links:end -->"


@dataclass(frozen=True)
class PostRef:
    post_id: int
    link: str
    title: str
    categories: tuple[int, ...]


@dataclass(frozen=True)
class CategoryRef:
    cat_id: int
    name: str
    link: str


def _request_with_retry(method: str, url: str, session: requests.Session, **kwargs) -> requests.Response:
    last_res = None
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            if res.status_code in RETRY_STATUSES:
                last_res = res
                logger.warning(f"{method} {url} -> {res.status_code} (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(1.2 * attempt)
                continue
            return res
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"{method} {url} failed (attempt {attempt}/{MAX_RETRIES}): {exc}")
            time.sleep(1.2 * attempt)
    if last_res is not None:
        return last_res
    raise last_exc if last_exc else RuntimeError("request failed")


def fetch_posts(session: requests.Session) -> list[dict]:
    posts = []
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
        data = res.json()
        if not data:
            break
        posts.extend(data)
        total_pages = int(res.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1
    return posts


def fetch_categories(session: requests.Session) -> dict[int, CategoryRef]:
    categories: dict[int, CategoryRef] = {}
    page = 1
    while True:
        res = _request_with_retry(
            "GET",
            f"{BASE_URL}/wp-json/wp/v2/categories",
            session,
            params={"per_page": 100, "page": page, "context": "view", "hide_empty": True},
        )
        if res.status_code == 400 and "rest_term_invalid_page_number" in res.text:
            break
        res.raise_for_status()
        data = res.json()
        if not data:
            break
        for c in data:
            categories[int(c["id"])] = CategoryRef(cat_id=int(c["id"]), name=str(c.get("name", "")), link=str(c.get("link", "")))
        total_pages = int(res.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1
    return categories


def normalize_title(title_obj: dict | str | None) -> str:
    if isinstance(title_obj, dict):
        return str(title_obj.get("rendered", "")).strip()
    return str(title_obj or "").strip()


def strip_existing_block(content: str) -> str:
    if BLOCK_START not in content or BLOCK_END not in content:
        return content
    start = content.find(BLOCK_START)
    end = content.find(BLOCK_END, start)
    if start == -1 or end == -1:
        return content
    return (content[:start] + content[end + len(BLOCK_END):]).strip()


def build_block(current: PostRef, all_posts: list[PostRef], cat_map: dict[int, CategoryRef]) -> str:
    others = [p for p in all_posts if p.post_id != current.post_id]
    same_cat = [p for p in others if set(current.categories) & set(p.categories)]
    latest = others[:]
    random.seed(current.post_id)
    random.shuffle(same_cat)

    pick_same = same_cat[:3]
    picked_ids = {p.post_id for p in pick_same}
    pick_latest = [p for p in latest if p.post_id not in picked_ids][:3]

    cat_links = []
    for cat_id in current.categories[:3]:
        c = cat_map.get(cat_id)
        if c and c.link:
            cat_links.append(c)

    related_links_html = "\n".join([f'    <li><a href="{p.link}">{p.title}</a></li>' for p in (pick_same + pick_latest)[:6]])
    cat_links_html = "\n".join([f'    <li><a href="{c.link}">{c.name}の一覧を見る</a></li>' for c in cat_links])

    return f"""{BLOCK_START}
<!-- wp:html -->
<section class="avk-internal-links" style="margin:28px 0 10px;padding:16px;border:1px solid rgba(0,0,0,.08);border-radius:10px;background:rgba(0,0,0,.02);">
  <h3 style="margin:0 0 10px;font-size:16px;">関連リンク</h3>
  <ul style="margin:0 0 12px 18px;padding:0;line-height:1.8;">
{related_links_html}
  </ul>
  <h4 style="margin:0 0 6px;font-size:14px;">探し方</h4>
  <ul style="margin:0 0 8px 18px;padding:0;line-height:1.8;">
    <li><a href="{BASE_URL}/">トップページへ戻る</a></li>
{cat_links_html}
  </ul>
</section>
<!-- /wp:html -->
{BLOCK_END}"""


def ensure_block(content: str, block: str) -> str:
    cleaned = strip_existing_block(content)
    return f"{cleaned}\n\n{block}\n"


def main() -> None:
    session = requests.Session()
    session.auth = (cs.WP_USERNAME, cs.WP_APP_PASSWORD)

    raw_posts = fetch_posts(session)
    cat_map = fetch_categories(session)
    refs = [
        PostRef(
            post_id=int(p["id"]),
            link=str(p.get("link", "")),
            title=normalize_title(p.get("title")),
            categories=tuple(int(c) for c in (p.get("categories") or [])),
        )
        for p in raw_posts
    ]

    refs_sorted = sorted(refs, key=lambda p: p.post_id, reverse=True)
    ref_by_id = {r.post_id: r for r in refs_sorted}

    scanned = 0
    updated = 0
    for post in raw_posts:
        scanned += 1
        post_id = int(post["id"])
        current = ref_by_id[post_id]
        content_obj = post.get("content", {}) or {}
        content = content_obj.get("raw") or content_obj.get("rendered") or ""

        new_block = build_block(current, refs_sorted, cat_map)
        new_content = ensure_block(content, new_block)
        if new_content == content:
            continue

        res = _request_with_retry(
            "POST",
            f"{BASE_URL}/wp-json/wp/v2/posts/{post_id}",
            session,
            json={"content": new_content},
        )
        res.raise_for_status()
        updated += 1
        if updated % 20 == 0:
            logger.info(f"progress: scanned={scanned}, updated={updated}")

    logger.info(f"done: scanned={scanned}, updated={updated}")


if __name__ == "__main__":
    main()

