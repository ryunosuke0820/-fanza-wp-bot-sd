"""
サイトルーター - FANZAジャンルに基づいて投稿先サイトを決定する

10個のサブドメインサイトにコンテンツを振り分けるためのルーティングロジック
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SiteConfig:
    """サイト設定"""
    subdomain: str
    title: str
    keywords: list[str]  # このサイトにマッチするキーワード


# サイト定義（優先順位順）
# 上にあるサイトほど優先度が高い
SITE_ROUTING_CONFIG = [
    SiteConfig(
        subdomain="sd01-chichi",
        title="乳ラブ",
        keywords=["巨乳", "爆乳", "美乳", "Iカップ", "Jカップ", "Kカップ", "おっぱい", "パイズリ"]
    ),
    SiteConfig(
        subdomain="sd02-shirouto",
        title="素人専門屋",
        keywords=["素人", "ナンパ", "投稿", "ハメ撮り", "個人撮影", "地味"]
    ),
    SiteConfig(
        subdomain="sd03-gyaru",
        title="ギャルしか！",
        keywords=["ギャル", "黒ギャル", "日焼け", "ビッチ", "GAL"]
    ),
    SiteConfig(
        subdomain="sd04-chijo",
        title="痴女プリーズ",
        keywords=["痴女", "誘惑", "逆ナン", "強制", "M男", "責め", "淫語"]
    ),
    SiteConfig(
        subdomain="sd05-seiso",
        title="清楚特集",
        keywords=["清楚", "お嬢様", "美少女", "女子大生", "処女", "初体験", "恥じらい"]
    ),
    SiteConfig(
        subdomain="sd06-hitozuma",
        title="人妻・愛",
        keywords=["人妻", "団地妻", "不倫", "寝取られ", "NTR", "浮気"]
    ),
    SiteConfig(
        subdomain="sd07-oneesan",
        title="お姉さん集め",
        keywords=["お姉さん", "OL", "女医", "女教師", "秘書", "キャリアウーマン", "美人"]
    ),
    SiteConfig(
        subdomain="sd08-jukujo",
        title="熟女の家",
        keywords=["熟女", "四十路", "五十路", "六十路", "美魔女", "お母さん", "継母"]
    ),
    SiteConfig(
        subdomain="sd09-iyashi",
        title="夜の癒し♡",
        keywords=["癒し", "マッサージ", "エステ", "介護", "中出し", "やさしい", "添い寝"]
    ),
    SiteConfig(
        subdomain="sd10-cos",
        title="コスでシコ",
        keywords=["コスプレ", "制服", "ナース", "看護師", "メイド", "バニー", "ミニスカ", "スクール水着"]
    ),
]


class SiteRouter:
    """FANZAジャンルに基づいてサイトを選択するルーター"""
    
    def __init__(self, base_domain: str = "av-kantei.com"):
        self.base_domain = base_domain
        self.sites = SITE_ROUTING_CONFIG
        logger.info(f"SiteRouter初期化: {len(self.sites)}サイト登録済み")
    
    def get_site_for_item(self, item: dict) -> SiteConfig:
        """
        FANZAアイテムのジャンルに基づいて最適なサイトを選択
        
        Args:
            item: FANZAから取得した商品情報
            
        Returns:
            最適なSiteConfig
        """
        genres = item.get("genre", [])
        title = item.get("title", "")
        
        # ジャンルとタイトルを結合して検索対象に
        search_text = " ".join(genres) + " " + title
        
        # 優先順位順にマッチングを試行
        for site in self.sites:
            for keyword in site.keywords:
                if keyword in search_text:
                    logger.info(f"サイト選択: {site.title} (キーワード: '{keyword}')")
                    return site
        
        # どのサイトにもマッチしない場合はデフォルト（コスでシコ - 企画的なもの）
        default_site = self.sites[-1]
        logger.info(f"サイト選択: {default_site.title} (デフォルト)")
        return default_site
    
    def get_site_url(self, site: SiteConfig) -> str:
        """サイトのフルURLを取得"""
        return f"https://{site.subdomain}.{self.base_domain}"
    
    def get_all_sites(self) -> list[SiteConfig]:
        """全サイト設定を取得"""
        return self.sites


# シングルトンインスタンス
_router: SiteRouter | None = None


def get_site_router() -> SiteRouter:
    """サイトルーターを取得（シングルトン）"""
    global _router
    if _router is None:
        _router = SiteRouter()
    return _router
