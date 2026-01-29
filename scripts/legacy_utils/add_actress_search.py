"""
女優検索ウィジェット（控えめ版）
"""
import sys
import io
from wp_client import WPClient
from config import get_config

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def add_actress_search():
    config = get_config()
    wp = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    
    # 控えめだけどおしゃれなデザイン
    search_html = '''<div style="background: rgba(139, 92, 246, 0.08); padding: 12px 20px; border-radius: 8px; margin: 0 auto 15px; max-width: 500px; border: 1px solid rgba(139, 92, 246, 0.2);">
<form action="https://av-kantei.com/" method="get" style="display: flex; gap: 10px; align-items: center; justify-content: center;">
<span style="color: #8b5cf6; font-size: 14px; font-weight: bold;">🔍 女優検索</span>
<input type="text" name="s" placeholder="女優名..." style="padding: 10px 14px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; width: 200px;">
<button type="submit" style="background: #8b5cf6; color: #fff; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">検索</button>
</form>
</div>'''
    
    widgets = wp._request('GET', 'widgets').json()
    for w in widgets:
        if w.get('sidebar') == 'content-top' and 'custom_html' in w.get('id', ''):
            widget_id = w.get('id')
            print(f"ウィジェット {widget_id} を更新中...")
            result = wp._request('PUT', f"widgets/{widget_id}", json={
                'sidebar': 'content-top',
                'instance': {'raw': {'title': '', 'content': search_html}}
            })
            print(f"ステータス: {result.status_code}")
            return

if __name__ == "__main__":
    add_actress_search()
