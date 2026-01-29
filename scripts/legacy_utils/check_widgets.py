"""
WordPressウィジェット・サイドバー確認スクリプト
"""
import sys
import io
from wp_client import WPClient
from config import get_config

# Windows環境での文字化け対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_widgets():
    config = get_config()
    wp = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    
    # サイドバー/ウィジェットエリアを確認
    print("=== サイドバー/ウィジェットエリア確認 ===")
    try:
        sidebars = wp._request('GET', 'sidebars').json()
        for sb in sidebars:
            print(f"\n【{sb.get('name', 'N/A')}】")
            print(f"  ID: {sb.get('id')}")
            print(f"  説明: {sb.get('description', 'なし')}")
            widgets = sb.get('widgets', [])
            print(f"  ウィジェット数: {len(widgets)}")
    except Exception as e:
        print(f"サイドバーAPI未対応: {e}")
    
    # 既存のウィジェットを確認
    print("\n=== 全ウィジェット一覧 ===")
    try:
        widgets = wp._request('GET', 'widgets').json()
        for w in widgets:
            print(f"  - {w.get('id')}: {w.get('id_base')} in {w.get('sidebar')}")
    except Exception as e:
        print(f"ウィジェットAPI未対応: {e}")

if __name__ == "__main__":
    check_widgets()
