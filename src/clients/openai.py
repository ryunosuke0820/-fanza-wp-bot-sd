"""
OpenAI APIクライアント
"""
import json
import random
import logging
from pathlib import Path
from typing import Any
import httpx
from openai import OpenAI
import openai

logger = logging.getLogger(__name__)

class OpenAIClient:
    """OpenAI GPTによる記事生成"""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        prompts_dir: Path,
        viewpoints_path: Path,
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.prompts_dir = prompts_dir
        self.system_prompt = self._load_template("system.txt")
        self.user_template = self._load_template("user.txt")
        self.viewpoints = self._load_viewpoints(viewpoints_path)
        logger.info(f"OpenAIクライアント初期化: model={model}, 観点数={len(self.viewpoints)}")
    
    def _load_template(self, filename: str) -> str:
        """テンプレートファイルを読み込む"""
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"プロンプトテンプレートが見つかりません: {path}")
        return path.read_text(encoding="utf-8")
    
    def _load_viewpoints(self, path: Path) -> list[dict[str, str]]:
        """観点カードを読み込む"""
        if not path.exists():
            logger.warning(f"viewpoints.jsonが見つかりません: {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("viewpoints", [])
    
    def _select_viewpoints(self, count: int = 2) -> list[dict[str, str]]:
        """ランダムに観点を選択"""
        if len(self.viewpoints) < count:
            return self.viewpoints
        return random.sample(self.viewpoints, count)
    
    def generate_article(self, product: dict[str, Any], sample_image_urls: list[str] | None = None, site_info: Any = None) -> dict[str, str]:
        """商品データから記事を生成（マルチモーダル対応）"""
        selected_viewpoints = self._select_viewpoints(2)
        viewpoint_text = "\n".join([f"- {v['name']}: {v['description']}" for v in selected_viewpoints])
        
        site_context = ""
        if site_info:
            site_context = f"## サイトコンセプト\nサイト名: {site_info.title}\n説明: {site_info.tagline}\nこのサイトのテーマに合わせたトーンで執筆してください。\n\n"

        logger.info(f"記事生成開始: {product['product_id']}")
        user_prompt = f"{site_context}" + self.user_template.format(
            product_id=product["product_id"],
            title=product["title"],
            actress=", ".join(product["actress"]) if product["actress"] else "情報なし",
            maker=product["maker"] or "情報なし",
            genre=", ".join(product["genre"]) if product["genre"] else "情報なし",
            release_date=product["release_date"] or "情報なし",
            duration=product.get("duration") or "情報なし",
            summary=product["summary"] or "情報なし",
            affiliate_url=product["affiliate_url"],
            viewpoints=viewpoint_text,
        )
        sample_image_urls = sample_image_urls or []
        if sample_image_urls and "gpt-4" in self.model:
            user_content = [{"type": "text", "text": user_prompt + "\n\n## シーン画像\n以下の画像を見て、それぞれの画像に対応したシーン説明を生成してください。"}]
            for img_url in sample_image_urls[:3]:
                user_content.append({"type": "image_url", "image_url": {"url": img_url, "detail": "low"}})
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_content}]
        else:
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_prompt}]
        try:
            timeout = httpx.Timeout(90.0, connect=10.0)
            response = self.client.chat.completions.with_raw_response.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=2000,
                timeout=timeout,
                response_format={ "type": "json_object" } if any(m in self.model for m in ["gpt-4", "gpt-3.5-turbo-0125"]) else None
            )
            chat_completion = response.parse()
            raw_response = chat_completion.choices[0].message.content
            result = self._parse_response(raw_response)
            result["raw_response"] = raw_response
            return result
        except Exception as e:
            logger.error(f"OpenAI APIエラー: {e}")
            raise
    
    def generate(self, item: dict, sample_image_urls: list[str] | None = None, site_info: Any = None) -> dict:
        """商品データからAI応答を生成"""
        return self.generate_article(item, sample_image_urls, site_info=site_info)
    
    def _parse_response(self, response: str) -> dict:
        """OpenAIの応答をパース"""
        try:
            data = json.loads(response)
            return {
                "title": data.get("title", ""),
                "short_description": data.get("short_description", ""),
                "highlights": data.get("highlights", []),
                "meters": data.get("meters", {}),
                "scenes": data.get("scenes", []),
                "checklist": data.get("checklist", {}),
                "ratings": data.get("ratings", {}),
                "summary": data.get("summary", ""),
                "faq": data.get("faq", []),
                "cta_text": data.get("cta_text", "今すぐ堪能する"),
                "excerpt": data.get("excerpt", ""),
            }
        except json.JSONDecodeError:
            return {"title": "レビュー", "summary": response[:200], "scenes": [], "ratings": {}, "short_description": "", "cta_text": "今すぐ堪能する", "excerpt": ""}
