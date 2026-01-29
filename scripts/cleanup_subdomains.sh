#!/bin/bash

# サブドメイン、データベース、ディレクトリを全削除するスクリプト
# SSH経由でサーバーで実行

echo "=== サブドメイン・DB一括削除スクリプト ==="

DOMAIN="av-kantei.com"
HOME_DIR="/home/aoxacgmk"

SITES=(
    "sd01-chichi"
    "sd02-shirouto"
    "sd03-gyaru"
    "sd04-chijo"
    "sd05-seiso"
    "sd06-hitozuma"
    "sd07-oneesan"
    "sd08-jukujo"
    "sd09-iyashi"
    "sd10-otona"
)

# 最終確認
read -p "本当に全てのサブドメインとデータベースを削除しますか？ (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "中止しました。"
    exit 0
fi

for SITE in "${SITES[@]}"; do
    SUBDOMAIN="$SITE.$DOMAIN"
    DOC_ROOT="$HOME_DIR/public_html/$SUBDOMAIN"
    DB_SUFFIX=$(echo $SITE | sed 's/-/_/g')
    DB_NAME="aoxacgmk_$DB_SUFFIX"
    
    echo ""
    echo "--- Deleting: $SUBDOMAIN ---"
    
    # 1. サブドメイン削除 (uapi)
    echo "Deleting subdomain: $SUBDOMAIN..."
    uapi SubDomain deletesubdomain domain="$SITE" rootdomain="$DOMAIN" 2>/dev/null
    
    # 2. データベース削除 (uapi)
    echo "Deleting database: $DB_NAME..."
    uapi Mysql delete_database name="$DB_NAME" 2>/dev/null
    
    # 3. ディレクトリ削除
    if [ -d "$DOC_ROOT" ]; then
        echo "Removing directory: $DOC_ROOT"
        rm -rf "$DOC_ROOT"
    fi
    
    echo "Done: $SUBDOMAIN"
done

echo ""
echo "=== 全サブドメイン・DB削除完了 ==="
echo ""
