"""Shared LLM client with async and sync helpers."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Iterable, Optional

from config.settings import read_runtime_llm_settings


class LLMClient:
    """Thin wrapper around OpenAI-compatible chat completions with fallback mocks."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        runtime_settings = read_runtime_llm_settings()
        self.api_key = (api_key if api_key is not None else runtime_settings.get("api_key") or os.getenv("LLM_API_KEY", "")).strip()
        self.api_base = (api_base if api_base is not None else runtime_settings.get("api_base") or os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")).strip()
        self.model = (model if model is not None else runtime_settings.get("model") or os.getenv("LLM_MODEL", "deepseek-chat")).strip()
        self._available = False
        self.client = None
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
            self._available = bool(self.api_key)
        except Exception:
            self.client = None
            self._available = False

    @property
    def available(self) -> bool:
        return bool(self._available and self.client is not None)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        if not self.available:
            return self._mock_response(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return str(response.choices[0].message.content or "").strip()
        except Exception:
            return self._mock_response(messages)

    def chat_completion_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.chat_completion(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            )

        result: list[str] = [""]
        error: list[BaseException | None] = [None]

        def _runner() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(
                    self.chat_completion(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                )
                loop.close()
            except BaseException as exc:  # pragma: no cover - defensive
                error[0] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if error[0] is not None:
            raise error[0]
        return result[0]

    def json_completion_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        raw = self.chat_completion_sync(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if self.available else None,
        )
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _mock_response(self, messages: Iterable[dict[str, str]]) -> str:
        user_msg = ""
        for msg in reversed(list(messages)):
            if str(msg.get("role") or "") == "user":
                user_msg = str(msg.get("content") or "")
                break

        if "JSON" in user_msg or "json" in user_msg:
            return json.dumps(
                {
                    "medical_accuracy": 7.8,
                    "safety": 8.2,
                    "completeness": 7.4,
                    "personalization": 6.8,
                    "consistency": 7.5,
                    "issues": [],
                    "comments": "Mock 模式评估结果",
                },
                ensure_ascii=False,
            )

        if "胰岛素" in user_msg or "药" in user_msg or "剂量" in user_msg or "用药" in user_msg:
            return (
                "【用药建议】\n"
                "1. 二甲双胍是2型糖尿病的一线用药，主要通过减少肝脏葡萄糖输出来降低血糖。\n"
                "2. 服药时间建议餐中或餐后，可减少胃肠道不适。\n"
                "3. 定期监测肾功能，肾功能不全时需调整剂量。\n\n"
                "【注意事项】\n"
                "- 不要自行调整剂量，任何用药变化请咨询主治医生\n"
                "- 如出现严重胃肠反应、乳酸酸中毒症状（肌肉酸痛、呼吸急促），请立即就医\n"
                "- 定期监测血糖和肾功能\n\n"
                "[⚠️] 具体剂量调整请咨询您的主治医生。"
            )
        if "饮食" in user_msg or "水果" in user_msg or "吃" in user_msg or "食物" in user_msg or "碳水" in user_msg:
            return (
                "【饮食建议】\n"
                "1. 控制每餐碳水化合物摄入量，选择低GI（血糖生成指数）食物。\n"
                "2. 推荐食物：糙米饭、全麦面包、绿叶蔬菜、瘦肉、鱼类、豆腐。\n"
                "3. 限制食物：精制糖、甜饮料、油炸食品、白面包、白米饭过量。\n\n"
                "【实用技巧】\n"
                "- 进餐顺序：先吃蔬菜 → 再吃蛋白质 → 最后吃主食\n"
                "- 每餐主食约一个拳头大小\n"
                "- 水果选择低糖品种（如草莓、蓝莓），控制在200g以内\n\n"
                "【重要提醒】\n"
                "个体差异较大，建议结合血糖监测结果调整饮食方案。"
            )
        if "血糖" in user_msg or "mmol" in user_msg or "空腹" in user_msg or "餐后" in user_msg:
            return (
                "【血糖管理建议】\n"
                "1. 血糖控制目标：空腹 4.4-7.0 mmol/L，餐后2小时 < 10.0 mmol/L。\n"
                "2. 建议每周监测2-3次空腹及餐后血糖，记录变化趋势。\n"
                "3. 如持续偏高，建议1-3个月内复查糖化血红蛋白（HbA1c）。\n\n"
                "【需要关注的情况】\n"
                "- 血糖持续 > 13.9 mmol/L → 请及时就医\n"
                "- 血糖 < 3.9 mmol/L（低血糖）→ 立即进食含糖食物，严重时拨打120\n"
                "- 出现酮症酸中毒症状（恶心、呕吐、呼吸急促）→ 立即急诊\n\n"
                "如有异常波动，请及时联系您的主治医生。"
            )
        if "运动" in user_msg or "锻炼" in user_msg or "步行" in user_msg:
            return (
                "【运动建议】\n"
                "1. 推荐有氧运动：快走、游泳、骑车，每次30-45分钟，每周至少5天。\n"
                "2. 运动时间建议餐后1小时开始，有助于降低餐后血糖。\n"
                "3. 避免空腹运动，运动前血糖低于5.6 mmol/L时应先进食。\n\n"
                "【安全提醒】\n"
                "- 随身携带含糖食物预防低血糖\n"
                "- 穿合适的鞋袜，保护双足\n"
                "- 运动前后监测血糖\n"
                "- 身体不适时暂停运动"
            )
        if "低血糖" in user_msg or "头晕" in user_msg or "晕" in user_msg or "急" in user_msg:
            return (
                "【紧急处理建议】\n"
                "如果您正在经历头晕、心慌、出汗、手抖等症状，这可能是低血糖的表现。\n\n"
                "【立即处理】\n"
                "1. 立即进食15-20克快速升糖食物（如3-4颗糖果、半杯果汁、1汤匙蜂蜜）\n"
                "2. 15分钟后重新测血糖\n"
                "3. 如血糖仍低于3.9 mmol/L，再次进食\n"
                "4. 症状缓解后吃一份正餐或小食\n\n"
                "【何时就医】\n"
                "- 意识模糊或无法自行进食 → 立即拨打120\n"
                "- 反复发生低血糖 → 尽快联系主治医生调整方案\n\n"
                "⚠️ 如症状严重或持续不缓解，请立即就医或拨打120急救电话。"
            )
        return (
            "【综合建议】\n"
            "感谢您的咨询。根据您的问题，以下是一些基本的糖尿病管理建议：\n\n"
            "1. **规律监测**：保持定期血糖监测，记录变化趋势。\n"
            "2. **均衡饮食**：控制碳水摄入，选择低GI食物，保持营养均衡。\n"
            "3. **适量运动**：每天至少30分钟中等强度运动，如快走、游泳。\n"
            "4. **按时用药**：严格按照医嘱服药，不自行调整剂量。\n"
            "5. **定期复查**：每3-6个月复查糖化血红蛋白及相关指标。\n\n"
            "【特别提醒】\n"
            "如血糖持续高于13.9或低于3.9 mmol/L，请及时就医。\n"
            "如遇紧急情况（严重低血糖、意识模糊、酮症酸中毒症状），请立即拨打120。\n\n"
            "以上建议仅供参考，具体方案请遵医嘱。"
        )


_llm_client: Optional[LLMClient] = None
_llm_signature: Optional[tuple[str, str, str]] = None


def get_llm_client() -> LLMClient:
    global _llm_client, _llm_signature
    settings = read_runtime_llm_settings()
    signature = (
        str(settings.get("api_key") or "").strip(),
        str(settings.get("api_base") or "").strip(),
        str(settings.get("model") or "").strip(),
    )
    if _llm_client is None or _llm_signature != signature:
        _llm_client = LLMClient(
            api_key=signature[0],
            api_base=signature[1],
            model=signature[2],
        )
        _llm_signature = signature
    return _llm_client
