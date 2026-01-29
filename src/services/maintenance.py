"""
メンテナンスサービス - 投稿のクリーンアップや重複チェックなど
"""
import logging
import re
from collections import defaultdict
from typing import List, Tuple, Dict, Any

from ..clients.wordpress import WPClient

logger = logging.getLogger(__name__)

class MaintenanceService:
    """WordPressの投稿管理・クリーンアップを担当"""
    
    def __init__(self, wp_client: WPClient):
        self.wp = wp_client

    def find_duplicate_posts(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """重複投稿を検出（FANZA IDが同じもの）"""
        logger.info("重複投稿のチェックを開始...")
        
        all_posts = self._fetch_all_posts(limit)
        fanza_id_posts = defaultdict(list)
        
        for p in all_posts:
            fanza_id = p.get('meta', {}).get('fanza_product_id', '')
            if not fanza_id:
                # コンテンツから抽出試行
                content = p.get('content', {}).get('rendered', '')
                match = re.search(r'cid=([a-z0-9]+)', content)
                if match:
                    fanza_id = match.group(1)
            
            if fanza_id:
                fanza_id_posts[fanza_id].append(p)
        
        duplicates = []
        for fanza_id, posts in fanza_id_posts.items():
            if len(posts) > 1:
                # 投稿IDが小さい（古い）ものを削除対象に
                posts_sorted = sorted(posts, key=lambda x: x['id'])
                for p in posts_sorted[:-1]:
                    duplicates.append(p)
                    logger.info(f"重複検出: ID={p['id']}, FANZA={fanza_id}, Title={p['title']['rendered'][:30]}...")
        
        return duplicates

    def find_bad_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """アイキャッチなし、またはFANZA IDなしの問題投稿を検出"""
        logger.info("問題のある投稿のチェックを開始...")
        posts = self.wp.get_recent_posts(limit=limit, status="publish")
        
        bad_posts = []
        for post in posts:
            featured_media = post.get("featured_media", 0)
            fanza_id = post.get("meta", {}).get("fanza_product_id")
            
            if not fanza_id:
                content = post.get('content', {}).get('rendered', '')
                match = re.search(r'cid=([a-z0-9]+)', content)
                if match:
                    fanza_id = match.group(1)
            
            # アイキャッチなし、またはIDなし
            if not featured_media or featured_media == 0 or not fanza_id:
                bad_posts.append(post)
                logger.info(f"問題投稿検出: ID={post['id']}, Title={post['title']['rendered'][:30]}...")
        
        return bad_posts

    def delete_posts(self, posts: List[Dict[str, Any]], force: bool = True) -> int:
        """指定された投稿を削除"""
        deleted_count = 0
        for p in posts:
            try:
                self.wp._request('DELETE', f"posts/{p['id']}", params={'force': force})
                logger.info(f"削除成功: ID={p['id']}, Title={p['title']['rendered'][:30]}...")
                deleted_count += 1
            except Exception as e:
                logger.error(f"削除失敗: ID={p['id']}, Error={e}")
        return deleted_count

    def _fetch_all_posts(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """ページングして投稿を取得"""
        all_posts = []
        page = 1
        per_page = 100
        
        while len(all_posts) < limit:
            try:
                response = self.wp._request('GET', 'posts', params={
                    'status': 'publish',
                    'per_page': per_page,
                    'page': page
                })
                posts = response.json()
                if not posts or not isinstance(posts, list):
                    break
                all_posts.extend(posts)
                if len(posts) < per_page:
                    break
                page += 1
            except Exception as e:
                logger.error(f"投稿取得エラー: {e}")
                break
        
        return all_posts[:limit]
