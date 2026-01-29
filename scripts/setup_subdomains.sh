#!/bin/bash

# サブドメインとデータベースを自動作成するスクリプト
# SSH経由でサーバーで実行

echo "=== サブドメイン・DB自動作成スクリプト ==="

DOMAIN="av-kantei.com"
HOME_DIR="/home/aoxacgmk"
DB_USER="aoxacgmk_wp_j5ozx"

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

for SITE in "${SITES[@]}"; do
    SUBDOMAIN="$SITE.$DOMAIN"
    DOC_ROOT="$HOME_DIR/public_html/$SUBDOMAIN"
    DB_SUFFIX=$(echo $SITE | sed 's/-/_/g')
    DB_NAME="aoxacgmk_$DB_SUFFIX"
    
    echo ""
    echo "--- Creating: $SUBDOMAIN ---"
    
    # 1. サブドメイン作成 (uapi)
    echo "Creating subdomain..."
    uapi SubDomain addsubdomain domain="$SITE" rootdomain="$DOMAIN" dir="$DOC_ROOT" 2>/dev/null
    
    # 2. ディレクトリが存在しない場合は作成
    if [ ! -d "$DOC_ROOT" ]; then
        mkdir -p "$DOC_ROOT"
        echo "Created directory: $DOC_ROOT"
    fi
    
    # 3. データベース作成 (uapi)
    echo "Creating database: $DB_NAME..."
    uapi Mysql create_database name="$DB_NAME" 2>/dev/null
    
    # 4. ユーザーをDBに追加
    echo "Adding user to database..."
    uapi Mysql set_privileges_on_database user="$DB_USER" database="$DB_NAME" privileges="ALL PRIVILEGES" 2>/dev/null
    
    echo "Done: $SUBDOMAIN"
done

echo ""
echo "=== 全サブドメイン・DB作成完了 ==="
echo ""
echo "次のステップ: clone_sites.sh を実行してください"
