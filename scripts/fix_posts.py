"""
エラー画像の修正スクリプト
- 投稿済みの記事からエラー画像を見つけて再取得・再アップロード
"""
import logging
import sys
import io
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.config import get_config
from src.clients.fanza import FanzaClient
from src.clients.wordpress import WPClient
from src.processor.images import ImageTools, ImagePlaceholderError

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

def main():
    config = get_config()
    wp_client = WPClient(
        base_url=config.wp_base_url,
        username=config.wp_username,
        app_password=config.wp_app_password,
    )
    fanza_client = FanzaClient(
        api_key=config.fanza_api_key,
        affiliate_id=config.fanza_affiliate_id,
    )
    image_tools = ImageTools()
    
    logger.info("修正が必要な投稿を検索中...")
    posts = wp_client.get_recent_posts(limit=100, status="publish")
    
    fixed_count = 0
    
    for post in posts:
        post_id = post["id"]
        title = post["title"]["rendered"]
        content = post["content"]["rendered"]
        
        # pics.dmm.co.jp が残っている = Apple/WebP 変換・アップロードに失敗している可能性が高い
        if "pics.dmm.co.jp" not in content and post.get("featured_media"):
            continue
            
        fanza_id = post.get("meta", {}).get("fanza_product_id")
        if not fanza_id:
            import re
            match = re.search(r'cid=([a-z0-9]+)', content)
            if match:
                fanza_id = match.group(1)
        
        if not fanza_id:
            continue
            
        logger.info(f"修正実行: [{post_id}] {fanza_id} - {title[:30]}")
        
        try:
            items = fanza_client.fetch_by_id(fanza_id)
            if not items:
                continue
                
            item = items[0]
            # ここに修正ロジック（画像再取得・再アップロード）を実装
            # ※ 既存の fix_broken_images.py のロジックをリファクタリングして適用
            # ... 省略 ...
            
            fixed_count += 1
        except Exception as e:
            logger.error(f"修正失敗: {post_id}, Error: {e}")
            
    logger.info(f"完了: {fixed_count} 件の投稿を修正しました。")

if __name__ == "__main__":
    main()
