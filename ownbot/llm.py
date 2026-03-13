from __future__ import annotations
 
import httpx
from loguru import logger
 
from ownbot.config import LLMConfig
 
 
class OpenAICompatibleClient:
     """Minimal OpenAI-compatible chat.completions client (no tool calls for MVP)."""
 
     def __init__(self, cfg: LLMConfig):
         self.cfg = cfg
 
     async def chat(self, user_text: str) -> str:
         if not self.cfg.api_key:
             return "错误：未配置 LLM apiKey（~/.ownbot/config.json -> llm.apiKey）"
 
         url = self.cfg.api_base.rstrip("/") + "/chat/completions"
         headers = {
             "Authorization": f"Bearer {self.cfg.api_key}",
             "Content-Type": "application/json",
         }
         payload = {
             "model": self.cfg.model,
             "messages": [
                 {"role": "system", "content": "你是 OwnBot，一个简洁的个人助理。请用中文简体回答。"},
                 {"role": "user", "content": user_text},
             ],
         }
 
         try:
             async with httpx.AsyncClient(timeout=self.cfg.timeout_s) as client:
                 r = await client.post(url, headers=headers, json=payload)
                 r.raise_for_status()
                 data = r.json()
             return (
                 data.get("choices", [{}])[0]
                 .get("message", {})
                 .get("content", "")
                 .strip()
                 or "(empty)"
             )
         except Exception as e:
             logger.exception("LLM call failed")
             return f"错误：调用 LLM 失败：{e}"