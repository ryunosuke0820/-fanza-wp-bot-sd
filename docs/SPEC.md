# 自動投稿システム - 実行フロー定義 (SPEC)

リファクタリング前の `main.py` に基づく実行フローを以下に固定する。この順序と仕様を維持することを最優先とする。

## 1. 初期化フェーズ
1.  **設定読込**: `config.py` の `get_config()` を呼び出し。
2.  **クライアント初期化**:
    - `FanzaClient`: 商品検索用
    - `OpenAIClient`: AI文章生成用
    - `WPClient`: WordPress REST API同期用
    - `Renderer`: HTMLレンダリング用
    - `ObsidianTools`: オプションのバックアップ用
    - `DedupeStore`: SQLite重複管理用

## 2. 候補取得フェーズ
1.  **WP既投稿ID取得**: `WPClient.get_posted_fanza_ids()` を実行。
2.  **FANZA API検索**: 指定されたページ分ループし、`FanzaClient.fetch()` で候補取得。
3.  **初期重複フィルタ**: 取得した `product_id` が以下に含まれる場合はスキップ。
    - WP側の履歴セット
    - SQLite側の `is_posted(pid)`

## 3. 個別投稿フェーズ (各商品ループ)
1.  **処理開始記録**: `DedupeStore.record_start(product_id)`。
2.  **最終ガード (WP確認)**: 
    - `WPClient.check_post_exists_by_fanza_id()`
    - `WPClient.check_post_exists_by_slug()`
3.  **画像選定**: サンプル画像リストから、記事本文用(3枚)とアイキャッチ用(1枚)を選択。
4.  **AI生成**: `OpenAIClient.generate()` (マルチモーダル)。
5.  **画像アップロード**: `WPClient.upload_media()` を使い、パッケージ画像とシーン画像をWPに登録。URLをWP側のURLに置換。
6.  **HTML生成**: `Renderer.render_post_content()`。
7.  **タクソノミー準備**: `WPClient.prepare_taxonomies()` でカテゴリ・タグIDを解決。
8.  **WordPress投稿**: `WPClient.post_draft()`。
9.  **成功記録**: `DedupeStore.record_success(product_id, wp_post_id)`.

## 4. 統計フェーズ
1.  **件数集計**: 成功/失敗/ドライランの件数をログ出力して終了。
