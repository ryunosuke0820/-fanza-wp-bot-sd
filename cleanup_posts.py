"""
重複投稿・画像エラー投稿の確認・削除スクリプト
"""
import sys
import io
from collections import defaultdict
from wp_client import WPClient
from config import get_config

# Windows環境での文字化け対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_duplicate_and_small_image_posts():
    """重複投稿と小さい画像の投稿を検出"""
    config = get_config()
    wp = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    
    # 全投稿を取得（ページング対応）
    all_posts = []
    page = 1
    while True:
        posts = wp._request('GET', 'posts', params={
            'status': 'publish',
            'per_page': 100,
            'page': page
        }).json()
        if not posts:
            break
        all_posts.extend(posts)
        page += 1
        if len(posts) < 100:
            break
    
    print(f"Total posts: {len(all_posts)}")
    
    # FANZA IDごとにグループ化
    fanza_id_posts = defaultdict(list)
    for p in all_posts:
        # メタフィールドからFANZA IDを取得
        fanza_id = p.get('meta', {}).get('fanza_product_id', '')
        if fanza_id:
            fanza_id_posts[fanza_id].append(p)
    
    # 重複を検出
    duplicates = []
    for fanza_id, posts in fanza_id_posts.items():
        if len(posts) > 1:
            # 古い方を削除対象に
            posts_sorted = sorted(posts, key=lambda x: x['id'])
            for p in posts_sorted[:-1]:  # 最新以外を削除対象
                duplicates.append(p)
                print(f"[DUPLICATE] ID: {p['id']}, FANZA: {fanza_id}, Title: {p['title']['rendered'][:40]}...")
    
    # 小さい画像（アイキャッチ）の投稿を検出
    small_image_posts = []
    for p in all_posts:
        featured_media = p.get('featured_media', 0)
        if featured_media:
            # メディア情報を取得
            try:
                media = wp._request('GET', f'media/{featured_media}').json()
                # ファイルサイズをチェック（メタデータにない場合もある）
                if media.get('media_details', {}).get('filesize', 999999) < 10000:
                    small_image_posts.append(p)
                    print(f"[SMALL IMAGE] ID: {p['id']}, Title: {p['title']['rendered'][:40]}...")
            except:
                pass
    
    return duplicates, small_image_posts

def delete_posts(posts, wp):
    """投稿を削除"""
    for p in posts:
        try:
            wp._request('DELETE', f"posts/{p['id']}", params={'force': True})
            print(f"Deleted: ID={p['id']}, Title={p['title']['rendered'][:30]}...")
        except Exception as e:
            print(f"Failed to delete ID={p['id']}: {e}")

def main():
    config = get_config()
    wp = WPClient(config.wp_base_url, config.wp_username, config.wp_app_password)
    
    print("=" * 60)
    print("問題のある投稿を検出中...")
    print("=" * 60)
    
    duplicates, small_image_posts = find_duplicate_and_small_image_posts()
    
    print("\n" + "=" * 60)
    print(f"検出結果: 重複={len(duplicates)}件, 小さい画像={len(small_image_posts)}件")
    print("=" * 60)
    
    to_delete = duplicates + small_image_posts
    # 重複を除去
    to_delete_unique = {p['id']: p for p in to_delete}.values()
    
    if not to_delete_unique:
        print("削除対象の投稿はありません。")
        return
    
    print(f"\n削除対象: {len(list(to_delete_unique))}件")
    print("削除を実行します...")
    
    delete_posts(list(to_delete_unique), wp)
    
    print("\n削除完了!")

if __name__ == "__main__":
    main()
