"""
Evaluator Agent - 质检员

职责：
1. 评估血糖管理 Agent 的回答质量
2. 评估记忆内容的质量
3. 生成结构化评分报告
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResponseScore:
    """回答质量评分"""
    medical_accuracy: float = 0.0  # 医学准确性 (0-10)
    safety: float = 0.0            # 安全性 (0-10)
    completeness: float = 0.0      # 完整性 (0-10)
    personalization: float = 0.0   # 个性化 (0-10)
    consistency: float = 0.0       # 一致性 (0-10)
    overall: float = 0.0           # 综合得分 (0-10)
    comments: str = ""             # 评语
    issues: List[str] = field(default_factory=list)  # 发现的问题
    
    def to_dict(self) -> Dict:
        return {
            "medical_accuracy": self.medical_accuracy,
            "safety": self.safety,
            "completeness": self.completeness,
            "personalization": self.personalization,
            "consistency": self.consistency,
            "overall": self.overall,
            "comments": self.comments,
            "issues": self.issues
        }


@dataclass
class MemoryScore:
    """记忆质量评分"""
    completeness: float = 0.0      # 完整性 (0-10)
    accuracy: float = 0.0          # 准确性 (0-10)
    timeliness: float = 0.0        # 时效性 (0-10)
    relevance: float = 0.0         # 相关性 (0-10)
    structure: float = 0.0         # 结构性 (0-10)
    overall: float = 0.0           # 综合得分 (0-10)
    comments: str = ""             # 评语
    issues: List[str] = field(default_factory=list)  # 发现的问题
    
    def to_dict(self) -> Dict:
        return {
            "completeness": self.completeness,
            "accuracy": self.accuracy,
            "timeliness": self.timeliness,
            "relevance": self.relevance,
            "structure": self.structure,
            "overall": self.overall,
            "comments": self.comments,
            "issues": self.issues
        }


@dataclass
class EvaluationReport:
    """评估报告"""
    evaluation_id: str
    patient_id: str
    query: str
    response_score: ResponseScore
    memory_score: MemoryScore
    timestamp: str
    iteration: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "evaluation_id": self.evaluation_id,
            "patient_id": self.patient_id,
            "query": self.query,
            "response_score": self.response_score.to_dict(),
            "memory_score": self.memory_score.to_dict(),
            "timestamp": self.timestamp,
            "iteration": self.iteration
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class EvaluatorAgent:
    """
    Evaluator Agent - 质检员
    
    评估维度：
    - 回答质量：医学准确性、安全性、完整性、个性化、一致性
    - 记忆质量：完整性、准确性、时效性、相关性、结构性
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.evaluation_history: List[EvaluationReport] = []
    
    def evaluate_response(
        self,
        patient_id: str,
        query: str,
        response: str,
        expert_opinions: Dict[str, str],
        patient_context: Dict[str, Any],
        use_llm: bool = False
    ) -> ResponseScore:
        """
        评估回答质量
        
        Args:
            patient_id: 患者ID
            query: 原始查询
            response: Primary Agent 的回答
            expert_opinions: 各专家 Agent 的意见
            patient_context: 患者上下文
            use_llm: 是否使用 LLM 辅助评估
        
        Returns:
            ResponseScore 评分对象
        """
        score = ResponseScore()
        
        if use_llm and self.llm_client:
            # 使用 LLM 进行评估
            score = self._evaluate_with_llm(
                query, response, expert_opinions, patient_context
            )
        else:
            # 使用规则-based 评估（快速/离线）
            score = self._evaluate_with_rules(
                query, response, expert_opinions, patient_context
            )
        
        # 计算综合得分
        score.overall = round(
            (score.medical_accuracy * 0.3 +
             score.safety * 0.25 +
             score.completeness * 0.2 +
             score.personalization * 0.15 +
             score.consistency * 0.1),
            2
        )
        
        return score
    
    def evaluate_memory(
        self,
        patient_id: str,
        memories: List[Dict[str, Any]],
        patient_data: Dict[str, Any],
        use_llm: bool = False
    ) -> MemoryScore:
        """
        评估记忆质量
        
        Args:
            patient_id: 患者ID
            memories: 记忆列表
            patient_data: 完整患者数据
            use_llm: 是否使用 LLM 辅助评估
        
        Returns:
            MemoryScore 评分对象
        """
        score = MemoryScore()
        
        if use_llm and self.llm_client:
            score = self._evaluate_memory_with_llm(memories, patient_data)
        else:
            score = self._evaluate_memory_with_rules(memories, patient_data)
        
        # 计算综合得分
        score.overall = round(
            (score.completeness * 0.25 +
             score.accuracy * 0.25 +
             score.timeliness * 0.2 +
             score.relevance * 0.15 +
             score.structure * 0.15),
            2
        )
        
        return score
    
    def generate_report(
        self,
        patient_id: str,
        query: str,
        response_score: ResponseScore,
        memory_score: MemoryScore,
        iteration: int = 0
    ) -> EvaluationReport:
        """
        生成评估报告
        
        Args:
            patient_id: 患者ID
            query: 查询
            response_score: 回答评分
            memory_score: 记忆评分
            iteration: 迭代次数
        
        Returns:
            EvaluationReport 报告对象
        """
        from datetime import datetime
        import uuid
        
        report = EvaluationReport(
            evaluation_id=f"eval_{uuid.uuid4().hex[:8]}",
            patient_id=patient_id,
            query=query,
            response_score=response_score,
            memory_score=memory_score,
            timestamp=datetime.now().isoformat(),
            iteration=iteration
        )
        
        self.evaluation_history.append(report)
        return report
    
    def _evaluate_with_rules(
        self,
        query: str,
        response: str,
        expert_opinions: Dict[str, str],
        patient_context: Dict[str, Any]
    ) -> ResponseScore:
        """基于规则的评估（快速/离线）"""
        score = ResponseScore()
        issues = []
        
        # 医学准确性检查
        medical_keywords = ["二甲双胍", "胰岛素", "格列", "血糖", "HbA1c", "糖化"]
        has_medical_term = any(kw in response for kw in medical_keywords)
        score.medical_accuracy = 7.0 if has_medical_term else 5.0
        if not has_medical_term:
            issues.append("缺少医学术语，可能不够专业")
        
        # 安全性检查
        safety_keywords = ["咨询医生", "注意", "风险", "禁忌"]
        has_safety_reminder = any(kw in response for kw in safety_keywords)
        score.safety = 8.0 if has_safety_reminder else 6.0
        if not has_safety_reminder:
            issues.append("缺少安全提醒")
        
        # 完整性检查
        score.completeness = 7.0 if len(response) > 100 else 5.0
        if len(response) < 100:
            issues.append("回答过于简短，可能不够完整")
        
        # 个性化检查
        patient_info = patient_context.get("profile", "")
        has_personalization = patient_info and any(
            info in response for info in ["岁", "型", "年"]
        )
        score.personalization = 7.0 if has_personalization else 5.0
        if not has_personalization:
            issues.append("缺少个性化信息")
        
        # 一致性检查
        score.consistency = 8.0  # 默认较高，复杂检查需要 LLM
        
        score.issues = issues
        score.comments = f"规则评估完成，发现 {len(issues)} 个问题"
        
        return score
    
    def _evaluate_with_llm(
        self,
        query: str,
        response: str,
        expert_opinions: Dict[str, str],
        patient_context: Dict[str, Any]
    ) -> ResponseScore:
        """使用 LLM 进行评估"""
        if not self.llm_client or not self.llm_client._available or not self.llm_client.api_key:
            # Fallback to rule-based evaluation
            return self._evaluate_with_rules(
                query, response, expert_opinions, patient_context
            )

        try:
            # 构建评估提示词
            evaluation_prompt = self._build_response_evaluation_prompt(
                query, response, expert_opinions, patient_context
            )

            # 调用 LLM（同步包装异步调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            llm_result = loop.run_until_complete(
                self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "你是一位专业的医疗质量评估专家，负责评估血糖管理AI系统的回答质量。"},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
            )

            # 解析 LLM 返回的评分
            score = self._parse_llm_response_score(llm_result)
            return score

        except Exception as e:
            print(f"[Evaluator] LLM evaluation failed: {e}, falling back to rules")
            return self._evaluate_with_rules(
                query, response, expert_opinions, patient_context
            )
    
    def _evaluate_memory_with_rules(
        self,
        memories: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> MemoryScore:
        """基于规则的记忆评估"""
        score = MemoryScore()
        issues = []
        
        # 完整性检查
        expected_categories = {"glucose", "medication", "diet", "symptom"}
        actual_categories = set()
        for mem in memories:
            cat = mem.get("category", "")
            if cat:
                actual_categories.add(cat)
        
        missing = expected_categories - actual_categories
        score.completeness = 10.0 - len(missing) * 1.5
        if missing:
            issues.append(f"缺少记忆类别: {missing}")
        
        # 准确性检查（简化）
        score.accuracy = 8.0  # 假设基本准确
        
        # 时效性检查
        score.timeliness = 7.0 if len(memories) > 0 else 5.0
        
        # 相关性检查
        score.relevance = 7.0
        
        # 结构性检查
        well_structured = sum(
            1 for m in memories 
            if isinstance(m.get("content"), dict) and "timestamp" in m
        )
        score.structure = 8.0 if well_structured > len(memories) * 0.5 else 6.0
        
        score.issues = issues
        score.comments = f"记忆评估完成，共 {len(memories)} 条记忆"
        
        return score
    
    def _evaluate_memory_with_llm(
        self,
        memories: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> MemoryScore:
        """使用 LLM 评估记忆"""
        if not self.llm_client or not self.llm_client._available or not self.llm_client.api_key:
            # Fallback to rule-based evaluation
            return self._evaluate_memory_with_rules(memories, patient_data)

        try:
            # 构建记忆评估提示词
            evaluation_prompt = self._build_memory_evaluation_prompt(
                memories, patient_data
            )

            # 调用 LLM（同步包装异步调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            llm_result = loop.run_until_complete(
                self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "你是一位专业的医疗记忆质量评估专家，负责评估血糖管理系统的患者记忆质量。"},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
            )

            # 解析 LLM 返回的评分
            score = self._parse_llm_memory_score(llm_result)
            return score

        except Exception as e:
            print(f"[Evaluator] LLM memory evaluation failed: {e}, falling back to rules")
            return self._evaluate_memory_with_rules(memories, patient_data)
    
    def _build_response_evaluation_prompt(
        self,
        query: str,
        response: str,
        expert_opinions: Dict[str, str],
        patient_context: Dict[str, Any]
    ) -> str:
        """构建回答质量评估提示词"""
        experts_text = "\n".join(
            f"- {name}: {opinion[:200]}" for name, opinion in expert_opinions.items()
        )
        context_text = str(patient_context.get("profile", "无患者画像"))[:300]

        return f"""请评估以下血糖管理AI系统的回答质量，按5个维度打分（0-10分），并以JSON格式返回。

患者问题：{query}

患者上下文：{context_text}

专家意见：
{experts_text}

系统最终回答：{response[:500]}

请按以下JSON格式返回评分（只返回JSON，不要其他文字）：
{{
  "medical_accuracy": <0-10>,
  "safety": <0-10>,
  "completeness": <0-10>,
  "personalization": <0-10>,
  "consistency": <0-10>,
  "comments": "<简短评语>",
  "issues": ["<问题1>", "<问题2>"]
}}

评分标准：
- medical_accuracy: 建议是否符合糖尿病管理指南，用药剂量是否安全
- safety: 是否有安全提醒，是否避免了危险建议
- completeness: 是否覆盖了患者问题的所有方面
- personalization: 是否结合了患者具体情况（年龄、病史、用药等）
- consistency: 各专家意见是否一致、互补"""

    def _parse_llm_response_score(self, llm_result: str) -> ResponseScore:
        """解析 LLM 返回的回答评分"""
        score = ResponseScore()
        try:
            # 提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', llm_result, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group())
            score.medical_accuracy = float(data.get("medical_accuracy", 5.0))
            score.safety = float(data.get("safety", 5.0))
            score.completeness = float(data.get("completeness", 5.0))
            score.personalization = float(data.get("personalization", 5.0))
            score.consistency = float(data.get("consistency", 5.0))
            score.comments = data.get("comments", "")
            score.issues = data.get("issues", [])

            # 限制分数范围 0-10
            for field in ["medical_accuracy", "safety", "completeness", "personalization", "consistency"]:
                val = getattr(score, field)
                setattr(score, field, max(0.0, min(10.0, val)))

        except Exception as e:
            print(f"[Evaluator] Failed to parse LLM response score: {e}")
            # 返回中等分数作为 fallback
            score.medical_accuracy = 5.0
            score.safety = 5.0
            score.completeness = 5.0
            score.personalization = 5.0
            score.consistency = 5.0
            score.comments = f"LLM评分解析失败: {e}"

        return score

    def _build_memory_evaluation_prompt(
        self,
        memories: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> str:
        """构建记忆质量评估提示词"""
        memories_text = json.dumps(memories[:5], ensure_ascii=False, indent=2)[:800]
        patient_text = json.dumps(patient_data, ensure_ascii=False)[:300] if patient_data else "无患者数据"

        return f"""请评估以下血糖管理系统的患者记忆质量，按5个维度打分（0-10分），并以JSON格式返回。

患者数据参考：{patient_text}

当前存储的记忆（前5条）：
{memories_text}

总记忆条数：{len(memories)}

请按以下JSON格式返回评分（只返回JSON，不要其他文字）：
{{
  "completeness": <0-10>,
  "accuracy": <0-10>,
  "timeliness": <0-10>,
  "relevance": <0-10>,
  "structure": <0-10>,
  "comments": "<简短评语>",
  "issues": ["<问题1>", "<问题2>"]
}}

评分标准：
- completeness: 关键信息（血糖记录、用药、饮食、症状）是否都被记录
- accuracy: 记忆内容是否与患者实际情况一致
- timeliness: 是否有过时信息，近期变化是否及时更新
- relevance: 记忆内容是否与血糖管理相关，是否有噪音信息
- structure: 记忆组织是否合理，分类是否清晰"""

    def _parse_llm_memory_score(self, llm_result: str) -> MemoryScore:
        """解析 LLM 返回的记忆评分"""
        score = MemoryScore()
        try:
            import re
            json_match = re.search(r'\{.*\}', llm_result, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group())
            score.completeness = float(data.get("completeness", 5.0))
            score.accuracy = float(data.get("accuracy", 5.0))
            score.timeliness = float(data.get("timeliness", 5.0))
            score.relevance = float(data.get("relevance", 5.0))
            score.structure = float(data.get("structure", 5.0))
            score.comments = data.get("comments", "")
            score.issues = data.get("issues", [])

            # 限制分数范围 0-10
            for field in ["completeness", "accuracy", "timeliness", "relevance", "structure"]:
                val = getattr(score, field)
                setattr(score, field, max(0.0, min(10.0, val)))

        except Exception as e:
            print(f"[Evaluator] Failed to parse LLM memory score: {e}")
            score.completeness = 5.0
            score.accuracy = 5.0
            score.timeliness = 5.0
            score.relevance = 5.0
            score.structure = 5.0
            score.comments = f"LLM评分解析失败: {e}"

        return score

    def get_average_scores(self, last_n: Optional[int] = None) -> Dict[str, float]:
        """获取平均评分"""
        if not self.evaluation_history:
            return {}
        
        reports = self.evaluation_history[-last_n:] if last_n else self.evaluation_history
        
        return {
            "avg_response_overall": round(
                sum(r.response_score.overall for r in reports) / len(reports), 2
            ),
            "avg_memory_overall": round(
                sum(r.memory_score.overall for r in reports) / len(reports), 2
            ),
            "total_evaluations": len(reports)
        }
