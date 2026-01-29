from __future__ import annotations
"""
共通データモデル定義
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional, Dict

@dataclass
class Product:
    """FANZA商品データ"""
    product_id: str
    title: str
    actress: List[str]
    maker: str
    genre: List[str]
    release_date: str
    summary: str
    package_image_url: str
    affiliate_url: str
    sample_image_urls: List[str]  # サンプル画像URL（最大10枚）
    sample_movie_url: str = ""    # サンプル動画URL
    
    # 内部処理用フラグ
    _featured_media_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（互換性維持のため残す）"""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "actress": self.actress,
            "maker": self.maker,
            "genre": self.genre,
            "release_date": self.release_date,
            "summary": self.summary,
            "package_image_url": self.package_image_url,
            "affiliate_url": self.affiliate_url,
            "sample_image_urls": self.sample_image_urls,
            "sample_movie_url": self.sample_movie_url,
        }

@dataclass
class AIResponse:
    """AIによる生成結果"""
    title: str
    short_description: str
    highlights: List[str]
    meters: Dict[str, Any]
    scenes: List[Dict[str, Any]]
    checklist: Dict[str, Any]
    ratings: Dict[str, Any]
    summary: str
    faq: List[Dict[str, str]]
    cta_text: str = "今すぐ堪能する"
    excerpt: str = ""
    raw_response: Optional[str] = None
