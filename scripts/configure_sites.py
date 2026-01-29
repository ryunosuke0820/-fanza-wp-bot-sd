import os
import sys
import logging
import requests
import base64
from dataclasses import dataclass

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SiteConfig:
    subdomain: str
    title: str
    tagline: str
    color: str
    keywords: list[str] # FANZA検索用キーワード

# サイトのリスト定義
SITES = [
    SiteConfig("sd01-chichi", "乳ラブ", "おっぱい鑑定所", "#FF69B4", ["巨乳", "爆乳", "着衣巨乳"]),
    SiteConfig("sd02-shirouto", "素人専門屋", "リアルAV鑑定", "#87CEEB", ["素人", "ナンパ", "投稿"]),
    SiteConfig("sd03-gyaru", "ギャルしか！", "ギャル特化鑑定", "#FFFF00", ["ギャル", "黒ギャル"]),
    SiteConfig("sd04-chijo", "痴女プリーズ", "攻めAV鑑定", "#FF0000", ["痴女", "誘惑", "露出"]),
    SiteConfig("sd05-seiso", "清楚特集", "ギャップ鑑定所", "#FFFFFF", ["清楚", "お嬢様", "美少女"]),
    SiteConfig("sd06-hitozuma", "人妻・愛", "至福のひとときを…", "#722F37", ["人妻", "不倫"]),
    SiteConfig("sd07-oneesan", "お姉さん集め", "綺麗なお姉さんは好きですか？", "#000080", ["お姉さん", "綺麗なお姉さん"]),
    SiteConfig("sd08-jukujo", "熟女の家", "大人の色気たっぷり", "#5C4033", ["熟女", "美魔女"]),
    SiteConfig("sd09-iyashi", "夜の癒し♡", "今夜はあなたを包みたい", "#E6E6FA", ["癒やし", "マッサージ", "エステ"]),
    SiteConfig("sd10-otona", "大人な時間", "究極の大人向けAV鑑定", "#40E0D0", ["コスプレ", "制服", "イベント"]),
]

# 共通ログイン情報（マスターと同じと想定）
WP_USERNAME = "moco"
WP_APP_PASSWORD = "LS3q H0qN 6PNB dTHN W07W iHh3" 

def get_site_config(subdomain: str) -> SiteConfig | None:
    """サブドメイン名からサイト設定を取得"""
    for site in SITES:
        if site.subdomain == subdomain:
            return site
    return None

def update_site_settings(site: SiteConfig):
    base_url = f"https://{site.subdomain}.av-kantei.com"
    api_url = f"{base_url}/wp-json/wp/v2/settings"
    
    # Basic認証ヘッダー
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }
    
    data = {
        "title": site.title,
        "description": site.tagline
    }
    
    try:
        logger.info(f"Updating settings for {base_url}...")
        response = requests.post(api_url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Successfully updated title/tagline for {site.subdomain}")
            
            # 再取得して検証
            verify_res = requests.get(api_url, headers=headers, timeout=10)
            if verify_res.status_code == 200:
                current = verify_res.json()
                if current.get("title") == site.title:
                    logger.info(f"Verification Success: {site.subdomain} is now '{site.title}'")
                else:
                    logger.warning(f"Verification Mismatch: Expected '{site.title}', got '{current.get('title')}'")
        else:
            logger.error(f"Failed to update {site.subdomain}: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Error updating {site.subdomain}: {e}")

def main():
    logger.info("Starting site configuration updates...")
    for site in SITES:
        update_site_settings(site)
    logger.info("All site updates completed.")

if __name__ == "__main__":
    main()
