# SD1専用仕様 (sd01-chichi)

このファイルは `sd01-chichi.av-kantei.com` 向けの運用仕様をまとめたもの。
SD1の変更は原則この仕様に合わせる。

## 1. 対象
- サイトID: `sd01-chichi`
- エイリアス: `sd1`, `sd01`

## 2. 文字数運用
- 既定レンジ: `1400` - `1700` 文字
- 参照実装: `scripts/run_batch.py`
- 環境変数で上書き可能:
  - `ARTICLE_MIN_CHARS`
  - `ARTICLE_MAX_CHARS`

## 3. レイアウト順 (現行)
1. ファーストビュー
2. 導入
3. 見どころ3選
4. サンプル動画
5. 作品スペック
6. CTA (スペック直下)
7. 短評レビュー
8. FAQ
9. まとめ
10. 18歳表記 (下部)

## 4. 固定要件
- 目次は非表示 (`.toc` 系を CSS で `display:none`)
- FAQはCV寄り固定3問:
  - FANZAクーポン
  - セール/ポイント還元の確認
  - 購入前にサンプルで見るポイント
- サンプル動画:
  - `sample_movie_url` があれば `<video>` を表示
  - なければ公式ページ案内を表示

## 5. 実装ファイル
- レンダリング本体: `src/processor/renderer.py`
  - `render_sd01_intro`
  - `_render_post_content_sd01`
- 既存投稿の再生成: `scripts/rewrite_sd01_existing_posts.py`
  - FANZA APIから `sample_movie_url` を取得して反映

## 6. 既存記事へ反映する時の基本方針
- 既存投稿を更新して使う（新規乱立しない）
- 反映前後で以下を確認:
  - 文字化け (`�`, `???`) がない
  - セクション順が仕様通り
  - CTAが「作品スペック」の直下
