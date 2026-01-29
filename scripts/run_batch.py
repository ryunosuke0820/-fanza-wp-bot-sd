"""
実行バッチ
"""
import argparse
import logging
import sys
import time
import io
import random
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from pathlib import Path

# srcルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import get_config
from src.clients.fanza import FanzaClient
from src.clients.wordpress import WPClient
from src.clients.openai import OpenAIClient
from src.processor.renderer import Renderer
from src.processor.images import ImageTools
from src.database.dedupe import DedupeStore
from src.services.poster import PosterService
from scripts.configure_sites import get_site_config

def setup_logging(level: str) -> None:
    # WindowsのコンソールでUnicodeEncodeErrorが発生するのを防ぐ
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="replace")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(errors="replace")

    # ハンドラーの作成
    stream_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            stream_handler,
            logging.FileHandler("fanza_bot.log", encoding="utf-8"),
        ],
    )

def main():
    parser = argparse.ArgumentParser(description="FANZA → WordPress 自動記事投稿")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")
    parser.add_argument("--sort", type=str, default="date")
    parser.add_argument("--since", type=str)
    parser.add_argument("--subdomain", type=str, help="対象のサブドメイン (例: sd01-chichi)")
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    config = get_config()

    # サブドメイン指定がある場合、設定を上書き
    site_keywords = None
    resolved_subdomain = args.subdomain
    if args.subdomain:
        subdomain_alias = {
            "sd1": "sd01-chichi",
        }
        resolved_subdomain = subdomain_alias.get(args.subdomain, args.subdomain)
        site_info = get_site_config(resolved_subdomain)
        if site_info:
            logger.info(f"サイト設定適用: {site_info.title} ({resolved_subdomain})")
            config.wp_base_url = f"https://{resolved_subdomain}.av-kantei.com"
            site_keywords = " ".join(site_info.keywords)
            logger.info(f"検索キーワード: {site_keywords}")
        else:
            logger.error(f"サブドメイン {resolved_subdomain} の設定が見つかりません。")
            sys.exit(1)
    
    fanza_client = FanzaClient(config.fanza_api_key, config.fanza_affiliate_id)
    llm_client = OpenAIClient(config.openai_api_key, config.openai_model, config.prompts_dir, config.base_dir / "viewpoints.json")
    wp_client = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    renderer = Renderer(config.base_dir / "templates")
    dedupe_key = resolved_subdomain or "default"
    dedupe_store = DedupeStore(config.data_dir / f"posted_{dedupe_key}.sqlite3")
    image_tools = ImageTools()
    
    poster_service = PosterService(config, fanza_client, wp_client, llm_client, renderer, dedupe_store, image_tools)
    
    logger.info("=" * 60)
    logger.info(f"開始: limit={args.limit}, dry_run={args.dry_run}, site={dedupe_key}")
    
    # 候補取得
    posted_ids = {pid.lower() for pid in wp_client.get_posted_fanza_ids()}
    target_count = args.limit
    candidate_pool_size = max(target_count * 2, 40)
    all_items = []
    
    seen_pids = set(posted_ids)
    
    for page in range(2):
        # 修正: 取得件数を減らして高速化
        batch = fanza_client.fetch(limit=100, since=args.since, sort=args.sort, keyword=site_keywords, offset=page * 100)
        if not batch: break
        for item in batch:
            pid = item['product_id']
            pid_norm = str(pid).lower()
            if pid_norm in seen_pids:
                continue
            
            if not dedupe_store.is_posted(pid_norm):
                all_items.append(item)
                seen_pids.add(pid_norm)
            
            if len(all_items) >= candidate_pool_size: break
        if len(all_items) >= candidate_pool_size: break
    
    random.shuffle(all_items)
    items = all_items[:target_count]
    logger.info(f"処理対象: {len(items)}件 (候補プール: {len(all_items)}件からランダム選定)")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    with tqdm(total=len(items), desc="全体進捗", unit="件") as pbar:
        for idx, item in enumerate(items, 1):
            pbar.set_postfix_str(f"処理中: {item['product_id']}")
            try:
                res = poster_service.process_item(idx, len(items), item, dry_run=args.dry_run, site_info=site_info if args.subdomain else None)
                if res == "success":
                    success_count += 1
                elif res == "skip":
                    skip_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"予期せぬエラー: {item['product_id']} - {e}")
                fail_count += 1
            pbar.update(1)
            
    logger.info(f"結果: 成功={success_count}, 失敗={fail_count}, スキップ={skip_count}")

if __name__ == "__main__":
    main()
