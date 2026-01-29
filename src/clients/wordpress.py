"""
WordPress REST APIクライアント
"""
import base64
import logging
import time
from typing import Any
from pathlib import Path
import re
import html as _html
from urllib.parse import unquote as _url_unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class WPClient:
    """WordPress REST APIクライアント"""

    _FANZA_ID_RE = re.compile(r"(?i)([0-9a-z_]+(?:-[0-9a-z_]+)*-\d{2,10})$")
    _CID_RE_LIST = (
        re.compile(r"(?i)cid=([A-Za-z0-9_\\-]+)"),
        re.compile(r"(?i)cid%3d([A-Za-z0-9_\\-]+)"),
        re.compile(r"(?i)content_id=([A-Za-z0-9_\\-]+)"),
    )
    
    def __init__(
        self,
        base_url: str,
        username: str,
        app_password: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        
        # Basic認証ヘッダー
        credentials = f"{username}:{app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
        
        # リトライ設定付きセッション
        self.session = requests.Session()
        retry_strategy = Retry(
            total=2,  # 最大2回リトライ
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.timeout = 20  # タイムアウト20秒
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # カテゴリ/タグのキャッシュ
        self._category_cache: dict[str, int] = {}
        self._tag_cache: dict[str, int] = {}
        self._posted_fanza_ids_cache: set[str] | None = None
        self._posted_fanza_ids_cache_at: float = 0.0

    @classmethod
    def _extract_fanza_id_from_slug(cls, slug: str) -> str | None:
        """投稿slug末尾からFANZA product_idを推定（例: actress-ipx-123 -> ipx-123）"""
        if not slug:
            return None
        m = cls._FANZA_ID_RE.search(slug)
        return m.group(1).lower() if m else None

    @classmethod
    def _extract_fanza_id_from_content(cls, rendered_html: str) -> str | None:
        """
        投稿本文（rendered HTML）から cid を抽出する。
        メインサイトでは slug/meta に product_id が残らないケースがあるため最重要。
        """
        if not rendered_html:
            return None
        # WPのrenderedにはエスケープ/URLエンコードが混ざることがあるのでゆるく正規化
        s = _html.unescape(rendered_html)
        s = _url_unquote(s)
        for cre in cls._CID_RE_LIST:
            m = cre.search(s)
            if m:
                return m.group(1).lower()
        return None
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """APIリクエストを実行"""
        url = f"{self.api_url}/{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.auth_header
        
        response = self.session.request(
            method,
            url,
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )
        
        # 429エラー時はRetry-Afterを尊重
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"WP APIレート制限。{retry_after}秒待機...")
            time.sleep(retry_after)
            return self._request(method, endpoint, headers=headers, **kwargs)
        
        return response
    
    def create_post(
        self,
        title: str,
        content: str,
        excerpt: str = "",
        slug: str = "",
        status: str = "draft",
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        featured_media: int | None = None,
        fanza_product_id: str | None = None,
    ) -> dict[str, Any]:
        """投稿を作成"""
        data = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "status": status,
        }
        
        if slug:
            data["slug"] = slug
        
        if categories:
            data["categories"] = categories
        
        if tags:
            data["tags"] = tags
        
        if featured_media:
            data["featured_media"] = featured_media
        
        if fanza_product_id:
            data["meta"] = {"fanza_product_id": fanza_product_id}
        
        logger.info(f"WP投稿作成: {title[:30]}... status={status}")
        
        response = self._request("POST", "posts", json=data)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"投稿作成成功: id={result['id']}, link={result.get('link', '')}")
        
        return result
    
    def get_posted_fanza_ids(
        self,
        per_page: int = 100,
        max_pages: int = 5,
        use_cache: bool = True,
        cache_ttl_seconds: int = 600,
    ) -> set[str]:
        """既存投稿からFANZA商品IDを取得"""
        if use_cache and self._posted_fanza_ids_cache is not None:
            if (time.time() - self._posted_fanza_ids_cache_at) < cache_ttl_seconds:
                return set(self._posted_fanza_ids_cache)

        posted_ids: set[str] = set()
        for page in range(1, max_pages + 1):
            try:
                params = {
                    "per_page": per_page,
                    "page": page,
                    "status": "any",
                    "_fields": "id,slug,meta,content",
                }
                response = self._request("GET", "posts", params={**params, "context": "edit"})
                if response.status_code in (403, 404, 401):
                    response = self._request("GET", "posts", params=params)
                if response.status_code == 400:
                    break
                response.raise_for_status()
                posts = response.json()
                if not posts:
                    break
                for post in posts:
                    meta = post.get("meta", {})
                    fanza_id: str | None = None
                    if isinstance(meta, dict):
                        fanza_id = meta.get("fanza_product_id")
                    if not fanza_id:
                        slug = post.get("slug", "") or ""
                        fanza_id = self._extract_fanza_id_from_slug(slug)
                    if not fanza_id:
                        content = post.get("content", {})
                        rendered = ""
                        if isinstance(content, dict):
                            rendered = content.get("rendered", "") or ""
                        else:
                            rendered = str(content or "")
                        fanza_id = self._extract_fanza_id_from_content(rendered)
                    if fanza_id:
                        posted_ids.add(str(fanza_id).lower())
                if len(posts) < per_page:
                    break
            except Exception as e:
                logger.warning(f"WP投稿取得エラー page={page}: {e}")
                break
        logger.info(f"WordPress投稿済みID抽出結果: {len(posted_ids)}件")
        self._posted_fanza_ids_cache = set(posted_ids)
        self._posted_fanza_ids_cache_at = time.time()
        return posted_ids

    def check_post_exists_by_slug(self, product_id: str) -> bool:
        """スラッグに商品IDが含まれる投稿が存在するかチェック"""
        try:
            # WP REST API の `search` は slug を検索対象にしないため、直近投稿を走査する
            needle = str(product_id).lower()
            posts = self.get_recent_posts(limit=100, status="any")
            for post in posts:
                slug = (post.get("slug", "") or "").lower()
                if needle and needle in slug:
                    logger.info(f"WP上で重複記事を発見 (slug scan): {product_id} -> ID {post['id']}")
                    return True
            return False
        except Exception as e:
            logger.warning(f"重複チェックリクエスト失敗: {e}")
            return False

    def check_post_exists_by_fanza_id(self, product_id: str) -> bool:
        """FANZA商品ID (メタ情報) を持つ投稿が存在するかチェック"""
        try:
            needle = str(product_id).lower()

            # 1) search で候補を絞り、meta/slug/本文(cid=)で照合（最速）
            params = {
                "search": needle,
                "status": "any",
                "per_page": 20,
                "_fields": "id,slug,meta,content",
                "context": "edit",
            }
            resp = self._request("GET", "posts", params=params)
            if resp.status_code in (401, 403):
                params.pop("context", None)
                resp = self._request("GET", "posts", params=params)
            if resp.status_code not in (400,):
                resp.raise_for_status()
                for post in resp.json() or []:
                    meta = post.get("meta", {})
                    if isinstance(meta, dict) and str(meta.get("fanza_product_id", "")).lower() == needle:
                        logger.info(f"WP上で重複記事を発見 (meta match): {product_id} -> ID {post.get('id')}")
                        return True
                    slug = (post.get("slug", "") or "").lower()
                    if needle and needle in slug:
                        logger.info(f"WP上で重複記事を発見 (slug contains): {product_id} -> ID {post.get('id')}")
                        return True
                    content = post.get("content", {})
                    rendered = content.get("rendered", "") if isinstance(content, dict) else str(content or "")
                    cid = self._extract_fanza_id_from_content(rendered)
                    if cid == needle:
                        logger.info(f"WP上で重複記事を発見 (content cid match): {product_id} -> ID {post.get('id')}")
                        return True

            # 2) posted_ids キャッシュ（広域だが重いので2番手）
            posted_ids = self.get_posted_fanza_ids(use_cache=True)
            if needle in posted_ids:
                logger.info(f"WP上で重複記事を発見 (posted_ids): {product_id}")
                return True

            return False
        except Exception as e:
            logger.warning(f"FANZA ID重複チェック失敗: {e}")
            return False

    def get_recent_posts(self, limit: int = 50, status: str = "any") -> list[dict]:
        """最近の投稿を取得"""
        response = self._request("GET", "posts", params={
            "per_page": limit,
            "status": status,
            "context": "edit",
            "orderby": "date",
            "order": "desc",
        })
        response.raise_for_status()
        return response.json()

    def get_post(self, post_id: int) -> dict:
        """投稿を取得"""
        response = self._request("GET", f"posts/{post_id}", params={"context": "edit"})
        response.raise_for_status()
        return response.json()

    def get_media(self, media_id: int) -> dict:
        """メディア情報を取得"""
        response = self._request("GET", f"media/{media_id}")
        response.raise_for_status()
        return response.json()

    def get_categories(self, per_page: int = 100) -> list[dict]:
        """カテゴリ一覧を取得"""
        response = self._request("GET", "categories", params={"per_page": per_page})
        response.raise_for_status()
        return response.json()
    
    def update_post(self, post_id: int, data: dict) -> dict:
        """投稿を更新"""
        response = self._request("POST", f"posts/{post_id}", json=data)
        response.raise_for_status()
        return response.json()
    
    def delete_post(self, post_id: int, force: bool = False) -> dict:
        """投稿を削除 (force=Trueで永久削除, Falseでゴミ箱)"""
        params = {"force": "true" if force else "false"}
        response = self._request("DELETE", f"posts/{post_id}", params=params)
        response.raise_for_status()
        return response.json()
    
    def post_draft(self, title: str, content: str, excerpt: str = "", slug: str = "", featured_media: int | None = None, categories: list[int] | None = None, fanza_product_id: str | None = None) -> int:
        """投稿を作成（本番公開）"""
        result = self.create_post(
            title=title, 
            content=content, 
            excerpt=excerpt, 
            slug=slug,
            status="publish",
            featured_media=featured_media,
            categories=categories,
            fanza_product_id=fanza_product_id
        )
        return result["id"]
    
    def upload_media(
        self,
        file_path: Path | None = None,
        file_bytes: bytes | None = None,
        filename: str = "image.jpg",
        mime_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        """メディアをアップロード"""
        if file_path:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        if not file_bytes:
            raise ValueError("file_pathまたはfile_bytesを指定してください")
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime_type,
        }
        logger.info(f"メディアアップロード: {filename}")
        response = self._request("POST", "media", headers=headers, data=file_bytes)
        response.raise_for_status()
        result = response.json()
        logger.info(f"メディアアップロード成功: id={result['id']}")
        return result
    
    def get_or_create_category(self, name: str) -> int:
        """カテゴリを取得または作成"""
        if name in self._category_cache:
            return self._category_cache[name]
        response = self._request("GET", "categories", params={"search": name})
        response.raise_for_status()
        categories = response.json()
        for cat in categories:
            if cat["name"].lower() == name.lower():
                self._category_cache[name] = cat["id"]
                return cat["id"]
        response = self._request("POST", "categories", json={"name": name})
        response.raise_for_status()
        cat = response.json()
        self._category_cache[name] = cat["id"]
        logger.info(f"カテゴリ作成: {name} -> id={cat['id']}")
        return cat["id"]
    
    def get_or_create_tag(self, name: str) -> int:
        """タグを取得または作成"""
        if name in self._tag_cache:
            return self._tag_cache[name]
        response = self._request("GET", "tags", params={"search": name})
        response.raise_for_status()
        tags = response.json()
        for tag in tags:
            if tag["name"].lower() == name.lower():
                self._tag_cache[name] = tag["id"]
                return tag["id"]
        response = self._request("POST", "tags", json={"name": name})
        response.raise_for_status()
        tag = response.json()
        self._tag_cache[name] = tag["id"]
        logger.info(f"タグ作成: {name} -> id={tag['id']}")
        return tag["id"]
    
    def prepare_taxonomies(
        self,
        genres: list[str],
        actresses: list[str],
    ) -> tuple[list[int], list[int]]:
        """ジャンルと女優名からカテゴリ/タグIDを準備"""
        category_ids = []
        tag_ids = []
        for genre in genres[:5]:
            try:
                cat_id = self.get_or_create_category(genre)
                category_ids.append(cat_id)
            except Exception as e:
                logger.warning(f"カテゴリ作成失敗: {genre}, error={e}")
        for actress in actresses[:10]:
            try:
                tag_id = self.get_or_create_tag(actress)
                tag_ids.append(tag_id)
            except Exception as e:
                logger.warning(f"タグ作成失敗: {actress}, error={e}")
        return category_ids, tag_ids
