"""
av-kantei.com（メインサイト）の重複投稿を検出して削除（ゴミ箱へ移動）する。

- FANZA product_id は meta.fanza_product_id を優先し、無ければ slug 末尾から推定
- 重複グループは「公開優先 → 古い投稿日優先」で1件だけ残し、それ以外を削除
- 既定は dry-run（一覧とレポート作成のみ）。実際に削除するには --apply。
"""

import argparse
import io
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.config import get_config
from src.clients.wordpress import WPClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostRef:
    post_id: int
    status: str
    date_gmt: str
    link: str
    slug: str
    fanza_id: str


def setup_logging(level: str) -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="replace")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(errors="replace")

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _status_rank(status: str) -> int:
    # 小さいほど優先（残す候補）
    order = {
        "publish": 0,
        "pending": 1,
        "draft": 2,
        "private": 3,
        "future": 4,
        "any": 5,
        "trash": 9,
    }
    return order.get((status or "").lower(), 8)


def fetch_posts(wp: WPClient, per_page: int, max_pages: int, status: str) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params = {
            "per_page": per_page,
            "page": page,
            "status": status,
            "orderby": "date",
            "order": "desc",
            "context": "edit",
            "_fields": "id,status,date_gmt,date,link,slug,meta,content",
        }
        resp = wp._request("GET", "posts", params=params)
        if resp.status_code in (401, 403, 404):
            params.pop("context", None)
            resp = wp._request("GET", "posts", params=params)

        if resp.status_code == 400:
            break
        resp.raise_for_status()
        page_posts = resp.json()
        if not page_posts:
            break
        posts.extend(page_posts)
        if len(page_posts) < per_page:
            break
    return posts


def extract_fanza_id(wp: WPClient, post: dict[str, Any]) -> str | None:
    meta = post.get("meta", {})
    fanza_id = None
    if isinstance(meta, dict):
        fanza_id = meta.get("fanza_product_id")
    if fanza_id:
        return str(fanza_id).lower()

    slug = post.get("slug", "") or ""
    fanza_id = wp._extract_fanza_id_from_slug(slug)
    if fanza_id:
        return str(fanza_id).lower()

    # 最後の砦: 投稿本文内の affiliate URL から cid を拾う
    content = post.get("content", {})
    if isinstance(content, dict):
        rendered = content.get("rendered", "") or ""
    else:
        rendered = str(content or "")

    for pat in (r"(?i)cid=([A-Za-z0-9_\\-]+)", r"(?i)content_id=([A-Za-z0-9_\\-]+)"):
        m = __import__("re").search(pat, rendered)
        if m:
            return m.group(1).lower()

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="av-kantei.com 重複投稿の検出/削除（ゴミ箱移動）")
    parser.add_argument("--apply", action="store_true", help="実際に削除（ゴミ箱へ移動）する")
    parser.add_argument("--force", action="store_true", help="force delete（復元不可）で削除する")
    parser.add_argument("--status", type=str, default="any", help="対象ステータス（default: any）")
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = get_config()

    wp = WPClient(
        base_url=config.wp_base_url,
        username=config.wp_username,
        app_password=config.wp_app_password,
    )

    logger.info(f"Target site: {config.wp_base_url}")
    logger.info(f"Fetch posts: status={args.status}, per_page={args.per_page}, max_pages={args.max_pages}")

    raw_posts = fetch_posts(wp, per_page=args.per_page, max_pages=args.max_pages, status=args.status)
    logger.info(f"Fetched posts: {len(raw_posts)}")

    groups: dict[str, list[PostRef]] = {}
    skipped_no_id = 0

    for post in raw_posts:
        fanza_id = extract_fanza_id(wp, post)
        if not fanza_id:
            skipped_no_id += 1
            continue

        ref = PostRef(
            post_id=int(post["id"]),
            status=str(post.get("status", "")),
            date_gmt=str(post.get("date_gmt", post.get("date", ""))),
            link=str(post.get("link", "")),
            slug=str(post.get("slug", "")),
            fanza_id=fanza_id,
        )
        groups.setdefault(fanza_id, []).append(ref)

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    logger.info(f"Posts without fanza_id (skipped): {skipped_no_id}")
    logger.info(f"Duplicate groups: {len(dup_groups)}")

    report = {
        "base_url": config.wp_base_url,
        "fetched_posts": len(raw_posts),
        "skipped_no_id": skipped_no_id,
        "duplicate_groups": len(dup_groups),
        "apply": bool(args.apply),
        "force": bool(args.force),
        "groups": [],
        "deleted": [],
        "kept": [],
        "generated_at": datetime.now().isoformat(),
    }

    delete_count = 0
    for fanza_id, items in sorted(dup_groups.items(), key=lambda kv: kv[0]):
        # keep: status優先→古い日付優先→ID小さい方（安定化）
        items_sorted = sorted(
            items,
            key=lambda r: (_status_rank(r.status), r.date_gmt or "9999-99-99", r.post_id),
        )
        keep = items_sorted[0]
        to_delete = items_sorted[1:]

        report["groups"].append(
            {
                "fanza_id": fanza_id,
                "count": len(items_sorted),
                "keep": keep.__dict__,
                "delete": [r.__dict__ for r in to_delete],
            }
        )
        report["kept"].append(keep.__dict__)

        for r in to_delete:
            if args.apply:
                try:
                    wp.delete_post(r.post_id, force=bool(args.force))
                    delete_count += 1
                    report["deleted"].append({**r.__dict__, "deleted_at": datetime.now().isoformat()})
                except Exception as e:
                    logger.error(f"Delete failed: fanza_id={fanza_id} post_id={r.post_id} err={e}")
            else:
                report["deleted"].append({**r.__dict__, "dry_run": True})

    report_path = project_root / "data" / f"dedupe_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.apply:
        logger.info(f"Deleted (trash={not args.force}): {delete_count}")
    else:
        logger.info(f"Dry-run deletions: {len(report['deleted'])}")
    logger.info(f"Report: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
