import os
import sys
import logging
import requests
import base64
from pathlib import Path

# srcルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from scripts.configure_sites import SITES

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 設定
WP_USERNAME = "moco"
WP_APP_PASSWORD = "LS3q H0qN 6PNB dTHN W07W iHh3"
NEW_LOGIN_PASSWORD = "FanzaBot2026!" # ユーザーに伝えるログイン用パスワード

def reset_password(site):
    base_url = f"https://{site.subdomain}.av-kantei.com"
    # ユーザー名 'moco' のID 1 を更新 (確認済み)
    api_url = f"{base_url}/wp-json/wp/v2/users/1"
    
    # Basic認証ヘッダー (App Passwordを使用)
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }
    
    data = {
        "password": NEW_LOGIN_PASSWORD
    }
    
    try:
        logger.info(f"Resetting login password for {site.title} ({base_url})...")
        response = requests.post(api_url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Successfully reset password for {site.subdomain}")
        else:
            logger.error(f"Failed to reset {site.subdomain}: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Error resetting {site.subdomain}: {e}")

def main():
    logger.info("Starting password resets for all 10 sites...")
    for site in SITES:
        reset_password(site)
    logger.info("Finished.")

if __name__ == "__main__":
    main()
