import os
import sys
import logging
import io
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.clients.wordpress import WPClient
from scripts.configure_sites import SITES, SiteConfig
from src.core.config import get_config

# Windows環境での文字化け対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 共通ログイン情報
WP_USERNAME = "moco"
WP_APP_PASSWORD = "LS3q H0qN 6PNB dTHN W07W iHh3"

def check_posts(base_url: str, label: str):
    wp_client = WPClient(
        base_url=base_url,
        username=WP_USERNAME,
        app_password=WP_APP_PASSWORD,
    )
    try:
        posts = wp_client.get_recent_posts(limit=1, status="any")
        count = len(posts)
        if count == 0:
            logger.info(f"[{label}] {base_url}: 0 posts (Clean)")
        else:
            # 実際には全件数ではないが、残っているかどうかの確認
            logger.info(f"[{label}] {base_url}: Found posts! Still has content.")
    except Exception as e:
        logger.error(f"[{label}] Error checking {base_url}: {e}")

def main():
    config = get_config()
    logger.info("Verifying post counts...")
    
    # メインサイトの確認
    check_posts(config.wp_base_url, "MAIN SITE")
    
    # 各サブドメインの確認
    for site in SITES:
        base_url = f"https://{site.subdomain}.av-kantei.com"
        check_posts(base_url, f"SUBDOMAIN: {site.subdomain}")
    
    logger.info("Verification completed.")

if __name__ == "__main__":
    main()
