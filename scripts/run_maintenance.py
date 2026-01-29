"""
サイトメンテナンス実行スクリプト
- 重複投稿の削除
- 問題のある投稿（アイキャッチなし等）の削除
"""
import logging
import sys
import io
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.config import get_config
from src.clients.wordpress import WPClient
from src.services.maintenance import MaintenanceService

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
    
    service = MaintenanceService(wp_client)
    
    print("=" * 60)
    print("メンテナンス処理を開始します...")
    print("=" * 60)
    
    # 1. 重複投稿のチェックと削除
    logger.info("重複投稿をチェック中...")
    duplicates = service.find_duplicate_posts(limit=500)
    if duplicates:
        print(f"重複投稿を {len(duplicates)} 件検出しました。削除を開始します。")
        service.delete_posts(duplicates)
    else:
        print("重複投稿はありませんでした。")
        
    # 2. 問題投稿のチェックと削除
    logger.info("問題のある投稿（アイキャッチなし等）をチェック中...")
    bad_posts = service.find_bad_posts(limit=100)
    if bad_posts:
        print(f"問題投稿を {len(bad_posts)} 件検出しました。削除を開始します。")
        service.delete_posts(bad_posts)
    else:
        print("問題のある投稿はありませんでした。")
        
    print("\n" + "=" * 60)
    print("メンテナンス処理が完了しました。")
    print("=" * 60)

if __name__ == "__main__":
    main()
