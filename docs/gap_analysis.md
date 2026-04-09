# Gap 分析报告：新开发指南 vs 现有实现

> 日期：2026-04-09 | 目的：为代码层面的后续重构提供依据
>
> 本文对比新的「多智能体协作开发约束与验收指南」与现有代码实现的差距，
> 按优先级排列，每项标注严重程度和影响范围。

---

## 总览

| 维度 | 新指南要求 | 当前实现 | 差距等级 |
|------|-----------|---------|:---:|
| 在线/离线环分离 | 硬性分离 | 代码层面混在一起 | 🔴 大 |
| Safety Reviewer | 独立角色、强约束 | 不存在 | 🔴 大 |
| 记忆元数据 | 8 项必备字段 | 仅有 category/priority | 🔴 大 |
| 失败分类 | 11 种细分类型 | 4 种粗粒度标签 | 🟡 中 |
| Trace / 可观测性 | 11 项追踪字段 | 基本缺失 | 🟡 中 |
| 专家输出结构化 | 强制结构化+不确定性 | 自由文本 | 🟡 中 |
| 问题重述 | Coordinator 必须做 | 未实现 | 🟡 中 |
| 冲突处理 | 记忆冲突共存标注 | 覆盖式写入 | 🟡 中 |
| 写回审核 | 写回候选需可审查 | 自动写入无审核 | 🟡 中 |
| 版本比较 | 有证据的版本对比 | 不存在 | 🟡 中 |
| 前端 Trace 审阅 | 必须支持 | ~10% 覆盖 | 🟡 中 |
| 前端运维界面 | 必须支持 | ~5% 覆盖 | 🟡 中 |
| 异常处理 | 7 种场景显式处理 | 部分静默吞掉 | 🟢 小 |
| Mock/Real 边界 | 文档化+可区分 | 基本可用 | 🟢 小 |

---

## 详细分析

### 1. 🔴 Safety Reviewer 完全缺失

**新指南要求：**
- 独立的安全审查角色
- 检查危险建议、遗漏升级提醒、过度自信、患者信息冲突
- 是强约束层，有权拦截不安全答复

**现有代码：**
- `workflow.py` 中没有安全审查步骤
- Doctor Agent 部分承担安全职能但不是独立环节
- 不安全答复可以直接到达用户

**影响范围：**
- `src/agents/workflow.py`：需要在 Coordinator 汇总后、返回用户前插入 Safety Gate
- 需新建 `src/agents/safety_reviewer.py`
- `api_server.py` 的咨询链路需调整

**修复建议：**
1. 新建 SafetyReviewer Agent
2. 在 workflow 中 primary_result 之后、返回之前加入 safety check
3. 安全检查不通过时返回 fallback 回复 + 升级提醒

---

### 2. 🔴 在线环/离线环架构混杂

**新指南要求：**
- 在线服务逻辑与离线优化逻辑在设计上、实现上、权限上分离

**现有代码：**
- `api_server.py` 同时暴露咨询 API 和评价/优化 API（同一个 FastAPI app）
- `src/evolution/self_evolution_loop.py` 可以直接修改 prompts 并应用到在线服务
- 没有权限隔离

**影响范围：**
- 需要将评价/优化 API 从主服务分离（至少在路由层面隔离）
- `self_evolution_loop.py` 的写入动作需要人类审批中间步骤
- 长期应拆成独立进程

**修复建议：**
1. 短期：在 API 路由层加明确的 `/online/` 和 `/offline/` 前缀区分
2. 中期：evolution 相关接口需要鉴权或审批流程
3. 长期：拆成独立服务

---

### 3. 🔴 记忆元数据严重不足

**新指南要求（8 项必备）：**
1. 来源（用户自述 / 专家推断 / 医生确认 / 系统抽取）
2. 时间或有效期
3. 置信度
4. 验证状态
5. 敏感级别
6. 是否与旧记录冲突
7. 是否替代旧记录
8. 属于哪类 memory type

**现有代码（`memory_agent.py`）：**
- ✅ 有 `category`（memory type）
- ✅ 有 `timestamp`
- ✅ 有 `priority`
- ❌ 没有 `source`（来源分类）
- ❌ 没有 `confidence`（置信度）
- ❌ 没有 `verification_status`
- ❌ 没有 `sensitivity_level`
- ❌ 没有冲突/替代关系标注
- ❌ 没有有效期（expiry）

**影响范围：**
- `src/memory/memory_agent.py`：`extract_and_store` 和 `store_consultation_record` 的写入数据结构
- Memory Palace 的存储 schema 需要扩展
- 检索时需要按元数据过滤

**修复建议：**
1. 定义 `MemoryRecord` dataclass，包含全部 8 项元数据
2. 修改所有写入方法使用新 schema
3. 检索时增加元数据过滤（如只取 verified/recent 的记忆）

---

### 4. 🟡 失败分类粒度不足

**新指南要求（11 种）：**
safety_error, factual_error, personalization_miss, wrong_routing, memory_miss, stale_memory_use, conflict_not_resolved, overconfident_no_escalation, specialist_redundancy, synthesis_contradiction, poor_user_communication

**现有代码（`evaluation_service.py`）：**
- 只有 4 种标签：GOOD / BAD / NEUTRAL / ERROR
- 无法区分 BAD 的具体原因

**修复建议：**
1. 在 `HumanEvaluation` dataclass 中新增 `failure_tags: List[str]` 字段
2. 定义 `VALID_FAILURE_TAGS` 常量集
3. 评测界面支持多选 failure tag
4. 统计 API 按 failure tag 聚合

---

### 5. 🟡 Trace / 可观测性基本缺失

**新指南要求（每轮至少追踪 11 项）：**
request_id, session_id, patient_id, routed_agents, retrieved_context_keys, synthesized_from, safety_result, final_status, created_evaluation, latency, errors

**现有代码：**
- `workflow.py` 返回 `processing_time` 和基本字段
- 没有 request_id / session_id
- 没有独立的 trace 记录
- 没有 safety_result 字段

**修复建议：**
1. 定义 `ConsultationTrace` dataclass
2. 在 `process_patient_query` 中生成 trace
3. 持久化 trace（写入 Memory Palace 或独立存储）
4. 前端 Trace 审阅界面消费此数据

---

### 6. 🟡 专家输出缺少结构化约束

**新指南要求：**
- 结构化意见（不是散文）
- 明确不确定性和置信度
- 指出潜在风险与升级条件

**现有代码：**
- 专家返回 `{"agent_type": ..., "response": "自由文本", "success": true}`
- Mock 模式下是格式化文本，但 LLM 模式下无强制格式

**修复建议：**
1. 定义专家输出 schema：
   ```python
   {
     "agent_type": str,
     "recommendations": List[str],
     "risks": List[str],
     "uncertainties": List[str],
     "escalation_needed": bool,
     "escalation_reason": str,
     "confidence": float,  # 0.0-1.0
   }
   ```
2. 在 prompt 中强制要求结构化输出
3. 添加解析和验证逻辑

---

### 7. 🟡 Coordinator 缺少问题重述逻辑

**新指南要求：**
- Coordinator 必须重述和规范化用户问题
- 消除歧义，识别问题类型

**现有代码：**
- `PrimaryAgent.process_sync` 直接将原始 query 传给 LLM
- 没有 rewrite/classify 步骤

**修复建议：**
1. 在 `workflow.py` 的 `process_patient_query` 开头增加 query rewrite 步骤
2. 输出规范化的问题 + 问题类型标签
3. 问题类型用于后续路由决策

---

### 8. 🟡 记忆冲突处理缺失

**新指南要求：**
- 不能默认新信息覆盖旧信息
- 冲突信息必须共存标注

**现有代码：**
- `update_patient_profile` 直接 `current.update(updates)` — 覆盖式
- `extract_and_store` 每次都创建新记录但不检查冲突

**修复建议：**
1. 写入前检查同类型已有记录
2. 如发现冲突，标注 `conflict_with` 字段
3. 不默认覆盖，而是标注状态 `superseded` / `conflicting` / `coexisting`

---

### 9. 🟡 写回缺少审核流程

**新指南要求：**
- 产出写回候选而非直接写入
- 人类能快速判断写回是否合理

**现有代码：**
- `workflow.py` 中 `extract_and_store` 直接写入 Memory Palace
- 没有"候选"概念，也没有审核环节

**修复建议：**
1. 改为先生成 `writeback_candidates`
2. 低风险信息可自动写入
3. 高优先级/安全相关信息需人工确认
4. 前端记忆审阅界面展示写回候选

---

### 10. 🟡 前端缺少 Trace 审阅和运维界面

**新指南要求：**
- B. 个案详情/Trace 审阅界面
- E. 运维/管理界面

**现有代码：**
- 已有：ChatPage (~70%), MemoryPalacePage (~45%), EvaluationPage (~65%), ProfilePage
- 缺少：Trace 审阅页面（~10%）、运维管理页面（~5%）

**修复建议：**
1. 新建 `TraceReviewPage.tsx`：展示每轮咨询的完整 trace
2. 新建 `AdminDashboardPage.tsx`：路由统计、错误情况、待评测队列、版本变化

---

### 11. 🟢 异常处理部分不完整

**新指南要求：** 7 种场景显式处理

**现有代码：**
- `workflow.py` 中专家并行调用用 `ThreadPoolExecutor`，有 `timeout=15`
- 但单个专家超时会导致整体报错，没有优雅降级
- 记忆写回失败是静默的（不影响返回但不记录）

**修复建议：**
1. 各专家调用加 try/except，失败的跳过但记录到 trace
2. 记忆写回失败记录到 trace
3. 增加部分成功状态

---

## 优先级排序的行动清单

| 优先级 | 行动 | 涉及文件 | 工作量估计 |
|:---:|------|---------|:---------:|
| P0 | 新建 Safety Reviewer 角色 | 新建 safety_reviewer.py, 改 workflow.py | 中 |
| P0 | 记忆元数据扩展（8 项） | memory_agent.py | 中 |
| P1 | Trace 生成与持久化 | workflow.py, 新建 trace 模块 | 中 |
| P1 | 失败分类扩展到 11 种 | evaluation_service.py, api_server.py | 小 |
| P1 | 专家输出结构化 | base_agent.py, 各专家 agent | 中 |
| P1 | 在线/离线环 API 隔离 | api_server.py | 小 |
| P2 | Coordinator 问题重述 | workflow.py, primary_agent.py | 中 |
| P2 | 记忆冲突检测与标注 | memory_agent.py | 中 |
| P2 | 写回候选机制 | memory_agent.py, workflow.py | 中 |
| P2 | 前端 Trace 审阅页面 | 新建 TraceReviewPage.tsx | 大 |
| P2 | 前端运维管理页面 | 新建 AdminDashboardPage.tsx | 大 |
| P3 | 异常优雅降级 | workflow.py | 小 |
| P3 | 版本比较工具 | 新建模块 | 中 |

---

## 现有代码中与新指南已一致的部分

为了公正，以下是已经符合新指南的部分：

- ✅ 多智能体协作框架已建立（5 个核心角色可运行）
- ✅ Memory Palace 集成已完成（不再是三层记忆）
- ✅ 评价生命周期管理（pending → completed）
- ✅ Mock/Real 模式切换
- ✅ 前端 MVP（4 个页面、20+ 组件）
- ✅ 患者数据规范化
- ✅ 记忆的 CRUD API
- ✅ 评价的 CRUD API
- ✅ 证据分层标准已建立
- ✅ 统一口径已建立

---

## 总结

现有实现覆盖了约 **50-60%** 的新指南要求。主要差距集中在三个方面：

1. **安全与治理**：Safety Reviewer 缺失、记忆元数据不足、写回无审核
2. **可观测性**：Trace 缺失、异常处理不完整、可解释性不足
3. **评价闭环**：失败分类粗粒度、无版本比较、无回归验证

建议按 P0 → P1 → P2 → P3 的顺序逐步推进代码重构，每完成一轮都需要验证是否满足对应的 DoD 标准。
