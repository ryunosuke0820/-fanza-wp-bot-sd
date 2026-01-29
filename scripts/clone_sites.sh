#!/bin/bash

# WordPress 10 Sites Cloning Script
# Run this from /home/aoxacgmk/

MASTER_PATH="/home/aoxacgmk/public_html"
MASTER_DB="aoxacgmk_wp_xzsws"
BACKUP_SQL="/home/aoxacgmk/master_clone_temp.sql"

# List of Subdomains
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

echo "--- Starting Cloning Process ---"

# 1. Export Master Database
echo "Exporting master database..."
wp db export $BACKUP_SQL --path=$MASTER_PATH --quiet

if [ $? -ne 0 ]; then
    echo "Error: Failed to export master database."
    exit 1
fi

for SITE in "${SITES[@]}"; do
    SITE_PATH="/home/aoxacgmk/public_html/$SITE.av-kantei.com"
    # MySQLではDB名にハイフンが使いにくいためアンダースコアに置換
    DB_SUFFIX=$(echo $SITE | sed 's/-/_/g')
    NEW_DB="aoxacgmk_$DB_SUFFIX"
    
    echo "--- Processing: $SITE ---"
    
    # 2. Check if directory exists (created by cPanel)
    if [ ! -d "$SITE_PATH" ]; then
        echo "Warning: Directory $SITE_PATH does not exist. Please create subdomain in cPanel first."
        continue
    fi
    
    # 3. Copy Files (excluding large backups, logs, and UPLOADS to save space)
    echo "Copying files from master (excluding uploads and other subdomains)..."
    rsync -avq --exclude='wp-config.php' --exclude='.git' --exclude='*.log' --exclude='wp-content/uploads' --exclude='sd*-*' $MASTER_PATH/ $SITE_PATH/
    
    # Create Symbolic Link for uploads to save disk space
    echo "Creating symbolic link for uploads..."
    ln -s $MASTER_PATH/wp-content/uploads $SITE_PATH/wp-content/uploads
    
    # 4. Copy wp-config.php and Update DB Name
    echo "Setting up wp-config.php..."
    cp $MASTER_PATH/wp-config.php $SITE_PATH/wp-config.php
    
    # 既存のDB名を確実に入れ替える (正規表現を使用)
    sed -i "s/define(\s*'DB_NAME',\s*'.*'\s*);/define( 'DB_NAME', '$NEW_DB' );/g" $SITE_PATH/wp-config.php
    
    # .htaccess 内のドメイン指定も修正
    if [ -f "$SITE_PATH/.htaccess" ]; then
        sed -i "s/av-kantei.com/$SITE.av-kantei.com/g" $SITE_PATH/.htaccess
    fi
    
    # リダイレクト防止のためURLを強制指定 (wp-config.phpの末尾、または「stop editing」の前に追加)
    sed -i "/Happy publishing/i define( 'WP_HOME', 'https://$SITE.av-kantei.com' );\ndefine( 'WP_SITEURL', 'https://$SITE.av-kantei.com' );" $SITE_PATH/wp-config.php

    # 5. Import Database
    # Note: Database $NEW_DB must be created in cPanel first!
    echo "Resetting and Importing database to $NEW_DB..."
    wp db reset --yes --path=$SITE_PATH --quiet
    wp db import $BACKUP_SQL --path=$SITE_PATH --quiet
    
    if [ $? -eq 0 ]; then
        # 6. Search and Replace URL
        echo "Replacing URL: av-kantei.com -> $SITE.av-kantei.com"
        wp search-replace "https://av-kantei.com" "https://$SITE.av-kantei.com" --path=$SITE_PATH --all-tables --quiet
        echo "Success: $SITE cloned."
    else
        echo "Error: Failed to import database for $SITE. Make sure $NEW_DB exists."
    fi
done

# Cleanup
rm $BACKUP_SQL
echo "--- Cloning Process Finished ---"
