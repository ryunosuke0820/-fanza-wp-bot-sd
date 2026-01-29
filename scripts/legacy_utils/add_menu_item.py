"""
WordPressメニュー項目追加スクリプト（改良版）
"""
import sys
import io
from wp_client import WPClient
from config import get_config

# Windows環境での文字化け対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def add_menu_item():
    config = get_config()
    wp = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    
    # ヘッダーメニューID
    menu_id = 12
    
    # 「即イキ動画」カテゴリID
    category_id = 29
    category_url = f"{config.wp_base_url}/category/instant-climax/"
    
    print("メニュー項目を追加中...")
    
    # 既存のメニュー項目を確認
    existing_items = wp._request('GET', 'menu-items', params={'menus': menu_id}).json()
    print(f"既存のメニュー項目: {len(existing_items)}件")
    for item in existing_items:
        print(f"  - {item.get('title', {}).get('rendered', 'N/A')}")
    
    # 「即イキ動画」が既にあるかチェック
    already_exists = any('即イキ動画' in str(item.get('title', {})) for item in existing_items)
    
    if already_exists:
        print("「即イキ動画」は既にメニューに存在します")
        return
    
    # メニュー項目を追加（カテゴリへのリンク）
    result = wp._request('POST', 'menu-items', json={
        'menus': menu_id,
        'type': 'taxonomy',
        'object': 'category',
        'object_id': category_id,
        'title': '即イキ動画',
        'status': 'publish',
        'menu_order': 2  # ホームの次
    }).json()
    
    print(f"メニュー項目追加成功: id={result.get('id')}")
    print(f"タイトル: {result.get('title', {}).get('rendered', 'N/A')}")

if __name__ == "__main__":
    add_menu_item()
