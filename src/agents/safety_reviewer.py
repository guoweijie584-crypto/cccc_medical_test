"""
Safety Reviewer Agent - 安全审查 Agent
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, MockAgent


@dataclass
class SafetyReviewResult:
    """安全审查结果"""

    passed: bool  # 是否通过安全审查
    risk_level: str  # "safe" / "caution" / "warning" / "danger"
    issues: List[str] = field(default_factory=list)  # 发现的安全问题列表
    escalation_needed: bool = False  # 是否需要升级人工医生
    escalation_reason: str = ""  # 升级原因
    modified_response: Optional[str] = None  # 如果需要修改答复（添加警告等）
    review_notes: str = ""  # 审查备注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_level": self.risk_level,
            "issues": self.issues,
            "escalation_needed": self.escalation_needed,
            "escalation_reason": self.escalation_reason,
            "modified_response": self.modified_response,
            "review_notes": self.review_notes,
        }


# ---------------------------------------------------------------------------
# 关键词 / 正则规则
# ---------------------------------------------------------------------------

# 危险建议关键词 —— 出现即标记为 issue
_DANGEROUS_ADVICE_PATTERNS: List[re.Pattern] = [
    re.compile(r"停药"),
    re.compile(r"自行调整剂量"),
    re.compile(r"自行增[加大].*剂量"),
    re.compile(r"自行减[少小].*剂量"),
    re.compile(r"不需要看医生"),
    re.compile(r"不[用必]去医院"),
    re.compile(r"不需要就医"),
    re.compile(r"可以自己.*调[整节]"),
]

# 紧急状况关键词 —— 如果回复中提及但未建议就医，则标记
_EMERGENCY_KEYWORDS: List[str] = [
    "酮症酸中毒",
    "DKA",
    "严重低血糖",
    "低血糖昏迷",
    "高渗性昏迷",
    "糖尿病酮症",
    "意识模糊",
    "意识丧失",
    "昏迷",
]

# 就医提醒关键词 —— 用于判断回复是否包含就医建议
_SEEK_MEDICAL_KEYWORDS: List[str] = [
    "就医",
    "就诊",
    "看医生",
    "去医院",
    "急诊",
    "拨打120",
    "拨打急救",
    "联系医生",
    "咨询医生",
    "咨询主治医生",
]


class SafetyReviewerAgent(BaseAgent):
    """安全审查 Agent - 对最终回复进行安全检查"""

    def __init__(self, llm_client=None):
        super().__init__("safety_reviewer", llm_client)

    # ------------------------------------------------------------------
    # 构建审查 prompt
    # ------------------------------------------------------------------

    def _build_review_prompt(
        self,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
        patient_context: Optional[str] = None,
    ) -> str:
        parts = [
            "## 待审查的患者问题",
            query,
            "\n## 待审查的回复内容",
            response,
        ]
        if expert_opinions:
            parts.append("\n## 各专家原始意见")
            for expert, opinion in expert_opinions.items():
                parts.append(f"### {expert}")
                parts.append(opinion)
        if patient_context:
            parts.append("\n## 患者上下文")
            parts.append(patient_context)
        parts.append("\n请按照系统提示词中的格式输出安全审查结果。")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # LLM 模式
    # ------------------------------------------------------------------

    async def process(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """异步处理 - 通用接口"""
        response = kwargs.get("response", "")
        expert_opinions = kwargs.get("expert_opinions")
        result = await self.review(query, response, expert_opinions, context)
        return {
            "agent_type": self.agent_type,
            "agent_name": self.name_zh,
            "response": result.review_notes,
            "safety_review": result.to_dict(),
            "success": True,
        }

    def process_sync(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """同步处理 - 通用接口"""
        response = kwargs.get("response", "")
        expert_opinions = kwargs.get("expert_opinions")
        result = self.review_sync(query, response, expert_opinions, context)
        return {
            "agent_type": self.agent_type,
            "agent_name": self.name_zh,
            "response": result.review_notes,
            "safety_review": result.to_dict(),
            "success": True,
        }

    async def review(
        self,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
        patient_context: Optional[str] = None,
    ) -> SafetyReviewResult:
        """异步安全审查"""
        prompt = self._build_review_prompt(query, response, expert_opinions, patient_context)
        raw = await self._call_llm(prompt, temperature=0.2)
        return self._parse_llm_result(raw)

    def review_sync(
        self,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
        patient_context: Optional[str] = None,
    ) -> SafetyReviewResult:
        """同步安全审查"""
        prompt = self._build_review_prompt(query, response, expert_opinions, patient_context)
        raw = self._call_llm_sync(prompt, temperature=0.2)
        return self._parse_llm_result(raw)

    # ------------------------------------------------------------------
    # 解析 LLM 输出
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_llm_result(raw: str) -> SafetyReviewResult:
        """从 LLM 原始输出中解析安全审查结果。

        期望 LLM 返回包含以下标记的文本：
          risk_level: safe|caution|warning|danger
          issues: ...
          escalation_needed: true|false
          escalation_reason: ...
          modified_response: ...
          review_notes: ...
        如果解析失败，保守地返回 caution。
        """
        text = raw.strip()

        def _extract(key: str) -> str:
            pattern = rf"(?:^|\n)\s*{key}\s*[:：]\s*(.*?)(?=\n\s*\w+\s*[:：]|\Z)"
            m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else ""

        risk_level = _extract("risk_level").lower() or "caution"
        if risk_level not in ("safe", "caution", "warning", "danger"):
            risk_level = "caution"

        issues_raw = _extract("issues")
        issues = [line.strip("- ").strip() for line in issues_raw.splitlines() if line.strip()] if issues_raw else []

        escalation_str = _extract("escalation_needed").lower()
        escalation_needed = escalation_str in ("true", "是", "yes", "1")

        escalation_reason = _extract("escalation_reason")
        modified_response = _extract("modified_response") or None
        review_notes = _extract("review_notes") or text

        passed = risk_level in ("safe", "caution") and not escalation_needed

        return SafetyReviewResult(
            passed=passed,
            risk_level=risk_level,
            issues=issues,
            escalation_needed=escalation_needed,
            escalation_reason=escalation_reason,
            modified_response=modified_response,
            review_notes=review_notes,
        )


class MockSafetyReviewerAgent(SafetyReviewerAgent):
    """Mock 安全审查 Agent - 基于关键词规则的安全检查（无需 LLM）"""

    def __init__(self):
        # 使用 MockAgent 风格：不传 llm_client，直接初始化 config
        super().__init__(llm_client=None)

    # 覆盖 review / review_sync，不调用 LLM
    async def review(
        self,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
        patient_context: Optional[str] = None,
    ) -> SafetyReviewResult:
        return self._keyword_review(query, response, expert_opinions)

    def review_sync(
        self,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
        patient_context: Optional[str] = None,
    ) -> SafetyReviewResult:
        return self._keyword_review(query, response, expert_opinions)

    async def process(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        response = kwargs.get("response", "")
        expert_opinions = kwargs.get("expert_opinions")
        result = self._keyword_review(query, response, expert_opinions)
        return {
            "agent_type": self.agent_type,
            "agent_name": self.name_zh,
            "response": result.review_notes,
            "safety_review": result.to_dict(),
            "success": True,
        }

    def process_sync(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        response = kwargs.get("response", "")
        expert_opinions = kwargs.get("expert_opinions")
        result = self._keyword_review(query, response, expert_opinions)
        return {
            "agent_type": self.agent_type,
            "agent_name": self.name_zh,
            "response": result.review_notes,
            "safety_review": result.to_dict(),
            "success": True,
        }

    # ------------------------------------------------------------------
    # 关键词规则引擎
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_review(
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> SafetyReviewResult:
        """基于关键词的安全审查"""
        issues: List[str] = []
        escalation_needed = False
        escalation_reason = ""
        combined = response

        # 1. 危险建议检测
        for pattern in _DANGEROUS_ADVICE_PATTERNS:
            if pattern.search(combined):
                issues.append(f"检测到危险建议关键词：{pattern.pattern}")

        # 2. 紧急状况识别 —— 提及紧急状况但未建议就医
        has_seek_medical = any(kw in combined for kw in _SEEK_MEDICAL_KEYWORDS)
        emergency_found: List[str] = []
        for kw in _EMERGENCY_KEYWORDS:
            if kw in combined or kw in query:
                emergency_found.append(kw)
        if emergency_found and not has_seek_medical:
            issues.append(f"提及紧急状况（{', '.join(emergency_found)}）但未建议就医")
            escalation_needed = True
            escalation_reason = f"涉及紧急状况：{', '.join(emergency_found)}，但回复中缺少就医建议"

        # 3. 紧急状况本身就需要升级
        if emergency_found:
            escalation_needed = True
            if not escalation_reason:
                escalation_reason = f"涉及紧急状况：{', '.join(emergency_found)}"

        # 4. 判断 risk_level
        if not issues and not emergency_found:
            risk_level = "safe"
        elif emergency_found and not has_seek_medical:
            risk_level = "danger"
        elif emergency_found and has_seek_medical:
            risk_level = "warning"
        elif issues:
            risk_level = "warning"
        else:
            risk_level = "caution"

        passed = risk_level in ("safe", "caution") and not escalation_needed

        review_notes_parts = []
        if not issues:
            review_notes_parts.append("关键词安全审查通过，未发现明显风险。")
        else:
            review_notes_parts.append(f"关键词安全审查发现 {len(issues)} 个问题。")
        if emergency_found:
            review_notes_parts.append(f"紧急状况关键词：{', '.join(emergency_found)}。")
        review_notes = " ".join(review_notes_parts)

        return SafetyReviewResult(
            passed=passed,
            risk_level=risk_level,
            issues=issues,
            escalation_needed=escalation_needed,
            escalation_reason=escalation_reason,
            modified_response=None,
            review_notes=review_notes,
        )
