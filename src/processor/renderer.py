import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class Renderer:
    """記事HTMLレンダラー"""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        
        # テンプレート読み込み
        self._hero_template = self._load_template("hero.html")
        self._scene_template = self._load_template("scene.html")
        self._rating_template = self._load_template("rating.html")
        self._summary_template = self._load_template("summary.html")
        self._cta_bottom_template = self._load_template("cta_bottom.html")
        self._video_template = self._load_template("video.html")
        self._styles_template = self._load_template("styles.html")
        
        logger.info(f"Renderer初期化完了: templates_dir={templates_dir}")

    def _load_template(self, name: str) -> str:
        """テンプレートファイルを読み込む"""
        path = self.templates_dir / name
        if not path.exists():
            logger.error(f"テンプレートファイルが見つかりません: {path}")
            return ""
        return path.read_text(encoding="utf-8")

    def render_hero(
        self,
        package_image_url: str,
        title: str,
        short_description: str,
        highlights: list[str],
        meters: dict,
        product_id: str,
        aff_url: str,
        external_link_label: str = "DMMで詳細を見る",
    ) -> str:
        """Heroセクションをレンダリング"""
        html = self._hero_template
        html = html.replace("{EYECATCH_URL}", package_image_url)
        html = html.replace("{TITLE}", title)
        html = html.replace("{SHORT_DESCRIPTION}", short_description)
        html = html.replace("{HIGHLIGHT_1}", highlights[0] if len(highlights) > 0 else "")
        html = html.replace("{HIGHLIGHT_2}", highlights[1] if len(highlights) > 1 else "")
        html = html.replace("{HIGHLIGHT_3}", highlights[2] if len(highlights) > 2 else "")
        
        # Meters
        html = html.replace("{METER_LABEL_TEMPO}", "テンポ")
        html = html.replace("{METER_TEMPO_LEVEL}", str(meters.get("tempo_level", 3)))
        html = html.replace("{METER_LABEL_VOLUME}", "ボリューム")
        html = html.replace("{METER_VOLUME_LEVEL}", str(meters.get("volume_level", 3)))
        
        # Labels/Notes
        html = html.replace("{EXTERNAL_LINK_LABEL}", external_link_label)
        html = html.replace("{NOTICE_18}", "18歳未満閲覧禁止")
        html = html.replace("{NOTICE_EXTERNAL}", "外部サイトへ移動します")
        html = html.replace("{CTA_BUTTON_LABEL_TOP}", "今すぐ作品をチェックする")
        html = html.replace("{CTA_URL_TOP}", aff_url)
        html = html.replace("{CTA_SUBLINE_1}", "会員登録なしですぐにデモ視聴可能")
        html = html.replace("{CTA_SUBLINE_2}", "安心の公式リンク（DMM.co.jp）")
        html = html.replace("{EXTERNAL_LINK_LINE}", f"※{external_link_label}へ移動します")
        
        # Placeholder for visual
        html = html.replace("{EYECATCH_PLACEHOLDER}", "")
        
        return html
    
    def render_spec(self, item: dict, site_id: str = "default") -> str:
        """作品スペックセクションをレンダリング"""
        html = self._load_template("spec.html")
        
        spec_title = "作品詳細スペック"
        if site_id == "sd02-shirouto":
            spec_title = "素人詳細スペック"
            
        html = html.replace("{SPEC_TITLE}", spec_title)
        html = html.replace("{SPEC_TOGGLE_HINT}", "クリックで詳細を表示")
        
        labels = ["配信開始日", "収録時間", "出演者", "メーカー", "品番"]
        values = [
            item.get("release_date", "不明"),
            item.get("duration", "不明"),
            ", ".join(item.get("actress", [])) if item.get("actress") else "記載なし",
            item.get("maker", "記載なし"),
            item.get("product_id", "不明"),
        ]
        
        for i in range(5):
            html = html.replace(f"{{SPEC_LABEL_{i+1}}}", labels[i])
            html = html.replace(f"{{SPEC_VALUE_{i+1}}}", values[i])
            
        html = html.replace("{SPEC_NOTE}", "※情報は配信当時のものです。最新の情報はリンク先でご確認ください。")
        return html

    def render_feature(self, index: int, scene: dict, image_url: str) -> str:
        """特徴（見どころ）カードを1枚レンダリング"""
        html = self._load_template("feature.html") # 新規作成
        html = html.replace("{FEATURE_INDEX}", str(index + 1))
        html = html.replace("{FEATURE_LABEL}", scene.get("feature_label", f"見どころ {index + 1}"))
        html = html.replace("{FEATURE_CHECK}", scene.get("feature_check", "ここが最高！"))
        html = html.replace("{FEATURE_DESCRIPTION}", scene.get("points", ""))
        html = html.replace("{FEATURE_METER_LABEL}", "興奮度")
        html = html.replace("{FEATURE_LEVEL}", str(scene.get("feature_level", 4)))
        
        # 画像スロット
        if image_url:
            img_tag = f'<img src="{image_url}" alt="scene {index+1}" class="aa-img" />'
            html = html.replace("{FEATURE_1_IMAGE_SLOT}", img_tag) # 汎用プレースホルダ
        else:
            html = html.replace("{FEATURE_1_IMAGE_SLOT}", "画像準備中")
            
        return html

    def render_checklist(self, checklist_data: dict, site_id: str = "default") -> str:
        """要素チェック表をレンダリング"""
        html = self._load_template("checklist.html")
        
        checklist_title = "要素別チェックリスト"
        if site_id == "sd02-shirouto":
            checklist_title = "素人鑑定チェックリスト"
            
        html = html.replace("{CHECKLIST_TITLE}", checklist_title)
        html = html.replace("{CHECKLIST_NOTE}", "ベテランレビュアーによる俺得評価")
        
        items = checklist_data.get("items", [])
        for i in range(10):
            label = items[i]["label"] if i < len(items) else "-"
            state = items[i]["state"] if i < len(items) else "off"
            html = html.replace(f"{{TAG_{i+1}_LABEL}}", label)
            html = html.replace(f"{{TAG_{i+1}_STATE}}", state)
            
        html = html.replace("{LEGEND_ON}", "アリ")
        html = html.replace("{LEGEND_OFF}", "ナシ")
        html = html.replace("{LEGEND_MAYBE}", "微妙")
        return html

    def render_safety(self) -> str:
        """安心・注意カードをレンダリング"""
        html = self._load_template("safety.html") # 新規作成
        html = html.replace("{SAFETY_TITLE}", "安心してご利用いただくために")
        html = html.replace("{CALLOUT_1_TITLE}", "18歳未満禁止")
        html = html.replace("{CALLOUT_1_BODY}", "本作品は成人向けです。18歳未満の方は閲覧・購入できません。")
        html = html.replace("{CALLOUT_2_TITLE}", "公式リンク")
        html = html.replace("{CALLOUT_2_BODY}", "当サイトはDMMアフィリエイトとして公式の正規配信サイトへのみ誘導します。")
        html = html.replace("{CALLOUT_3_TITLE}", "ネタバレ配慮")
        html = html.replace("{CALLOUT_3_BODY}", "レビューには一部内容が含まれますが、結末等の重大なネタバレは避けています。")
        return html

    def render_faq(self, faqs: list[dict]) -> str:
        """FAQセクションをレンダリング"""
        html = self._load_template("faq.html") # 新規作成
        html = html.replace("{FAQ_TITLE}", "よくある質問")
        for i in range(5):
            q = faqs[i]["q"] if i < len(faqs) else "視聴に会員登録は必要ですか？"
            a = faqs[i]["a"] if i < len(faqs) else "はい、DMMの無料会員登録が必要です。一部デモ動画は登録なしでも見られます。"
            html = html.replace(f"{{FAQ_Q{i+1}}}", q)
            html = html.replace(f"{{FAQ_A{i+1}}}", a)
        return html

    def render_post_content(
        self,
        item: dict,
        ai_response: dict,
        site_id: str = "default",
    ) -> str:
        """投稿本文全体を生成"""
        parts = []
        
        # 全体をSITE_IDでラップ
        parts.append(f'<div class="aa-wrap aa-site-{site_id}">')
        
        # 1. Sticky Badge
        parts.append(f'''
  <div class="aa-sticky-badge" aria-label="notice">
    <span class="aa-badge aa-badge-18">18+</span>
    <span class="aa-badge aa-badge-ext">DMM公式</span>
  </div>
        ''')
        
        # 2. Hero (A)
        hero_html = self.render_hero(
            package_image_url=item.get("package_image_url", ""),
            title=item.get("title", ""),
            short_description=ai_response.get("short_description", ""),
            highlights=ai_response.get("highlights", []),
            meters=ai_response.get("meters", {}),
            product_id=item.get("product_id", ""),
            aff_url=item.get("affiliate_url", ""),
        )
        parts.append(hero_html)
        
        # 3. Spec (B)
        parts.append(self.render_spec(item, site_id=site_id))
        
        # 4. Features (C: Highlights x3)
        sample_urls = item.get("sample_image_urls", [])
        scenes = ai_response.get("scenes", [])
        parts.append('<section class="aa-stack" aria-label="feature cards">')
        for i in range(min(3, len(scenes))):
            parts.append(self.render_feature(i, scenes[i], sample_urls[i] if i < len(sample_urls) else ""))
        parts.append('</section>')
        
        # 5. Mid CTA (D)
        parts.append(self.render_cta_mid(item.get("affiliate_url", "")))
        
        # 6. Checklist (E)
        parts.append(self.render_checklist(ai_response.get("checklist", {}), site_id=site_id))
        
        # 7. Safety (F)
        parts.append(self.render_safety())
        
        # 8. Summary (G)
        parts.append(self.render_summary(ai_response.get("summary", "")))
        
        # 9. FAQ (H)
        parts.append(self.render_faq(ai_response.get("faq", [])))
        
        # 10. Final CTA (I)
        parts.append(self.render_cta_final(item.get("affiliate_url", "")))
        
        parts.append('</div>')
        
        # スタイルシートを追加
        parts.append(self._styles_template)
        
        body = "\n\n".join(parts)
        # ブロックエディタのHTMLブロックとして包み、wpautopの崩れを抑制
        return f"<!-- wp:html -->\n{body}\n<!-- /wp:html -->"

    def render_summary(self, summary_text: str) -> str:
        """総評セクションをレンダリング"""
        html = self._summary_template
        html = html.replace("{SUMMARY_TITLE}", "まとめ")
        return html.replace("{SUMMARY_TEXT}", summary_text)

    def render_cta_mid(self, aff_url: str) -> str:
        """中間CTA (D) をレンダリング"""
        html = self._load_template("cta.html")
        html = html.replace("{CTA_URL_MID}", aff_url)
        html = html.replace("{CTA_BUTTON_LABEL_MID}", "まずは無料デモで興奮を確かめる")
        html = html.replace("{CTA_MID_SUBLINE_1}", "会員登録なしで1分以上のサンプル視聴が可能")
        html = html.replace("{CTA_MID_SUBLINE_2}", "※リンク先で「動画サンプル」をクリック")
        html = html.replace("{EXTERNAL_LINK_LINE}", "※DMM.co.jp（公式）へ移動します")
        return html

    def render_cta_final(self, aff_url: str) -> str:
        """最終CTA (I) をレンダリング"""
        html = self._load_template("cta_bottom.html")
        html = html.replace("{CTA_URL_FINAL}", aff_url)
        html = html.replace("{CTA_BUTTON_LABEL_FINAL}", "今すぐこの快楽を本編で堪能する")
        html = html.replace("{CTA_FINAL_NOTE_1}", "DMMなら最高画質ですぐに視聴開始")
        html = html.replace("{CTA_FINAL_NOTE_2}", "今ならキャンペーンポイント還元中")
        html = html.replace("{EXTERNAL_LINK_LINE}", "※DMM.co.jp（公式）へ移動します")
        return html

    def render_rating(self, ratings: dict) -> str:
        """評価セクションをレンダリング"""
        html = self._rating_template
        # テンプレートは {{...}} 形式を使用している
        mapping = {
            "{{RATING_EASE}}": ratings.get("ease", "★★★★☆"),
            "{{RATING_EASE_NOTE}}": ratings.get("ease_note", "初心者でも安心"),
            "{{RATING_FETISH}}": ratings.get("fetish", "★★★★★"),
            "{{RATING_FETISH_NOTE}}": ratings.get("fetish_note", "性癖に刺さる"),
            "{{RATING_VOLUME}}": ratings.get("volume", "★★★★☆"),
            "{{RATING_VOLUME_NOTE}}": ratings.get("volume_note", "大満足のボリューム"),
            "{{RATING_REPEAT}}": ratings.get("repeat", "★★★★☆"),
            "{{RATING_REPEAT_NOTE}}": ratings.get("repeat_note", "何度でも見たい"),
        }
        for k, v in mapping.items():
            html = html.replace(k, v)
        return html

    def render_video(self, sample_movie_url: str) -> str:
        """動画セクションをレンダリング"""
        if not sample_movie_url:
            return ""
        html = self._video_template
        return html.replace("{{SAMPLE_MOVIE_URL}}", sample_movie_url)
