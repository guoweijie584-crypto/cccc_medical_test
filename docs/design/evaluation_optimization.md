# 评价与受控优化约束文档

> 血糖管理多智能体系统 — 评价体系设计与优化流程约束
>
> 状态：规范性文档（所有优化行为必须遵守本文档约束）
>
> 最后更新：2026-04-09

---

## 1. 核心原则

### 1.1 评价先于优化

没有可靠的评价体系，**不允许宣称系统在进化**。

任何"系统变好了"的断言都必须有可追溯的评价证据支撑。仅凭 LLM 自评分数的变化不构成有效证据——因为 LLM 评价自己输出的可靠性尚未在本系统中得到校验。

### 1.2 优化必须建立在以下基础之上

| 基础要素 | 说明 |
|---|---|
| **Consultation trace** | 完整的咨询轨迹记录：患者问题、专家意见、最终回答、路由决策、检索到的记忆 |
| **人类专家评分/标签** | 医生对 case 的标注（GOOD / BAD / NEUTRAL / ERROR）及维度扩展（safety、advice_direction、personalized） |
| **失败分类** | 对每个 BAD/ERROR case 进行结构化归因，见第 2 节 |
| **稳定回归集** | 一组固定的、有已知正确期望的测试用例，用于检测优化是否引入退化 |
| **版本比较结果** | 新旧版本在相同用例集上的对比数据，包含量化指标和人类抽检 |

缺少上述任何一项，优化流程不得推进到生产环境。

### 1.3 不信任 Agent 自评

系统内 `EvaluatorAgent` 提供的数值评分（0-10 维度打分）**仅作为内部开发调试参考**，不得作为对外宣称质量改进的依据。所有质量判断的最终权威来自真实人类医生的标注。

---

## 2. 建议的失败分类 (Failure Taxonomy)

系统至少能在人类评审和自动分析中表达以下失败类型：

| 失败类型 | 标识 | 含义 | 严重度 |
|---|---|---|---|
| 安全错误 | `safety_error` | 回答包含可能导致患者伤害的建议（如错误剂量、遗漏禁忌、未升级急症） | **Critical** |
| 事实错误 | `factual_error` | 医学事实不正确（如药理机制、指南推荐与权威来源矛盾） | **Critical** |
| 个性化缺失 | `personalization_miss` | 回答未考虑患者具体情况（年龄、合并症、用药史、近期血糖趋势） | High |
| 路由错误 | `wrong_routing` | 问题被分派给了不合适的专家 Agent，或漏掉了应参与的专家 | High |
| 记忆缺失 | `memory_miss` | 系统未检索到本应可用的患者历史信息，导致回答缺少关键上下文 | High |
| 过时记忆使用 | `stale_memory_use` | 系统引用了已过期或已被更新的患者信息（如旧用药方案） | High |
| 冲突未解决 | `conflict_not_resolved` | 多位专家 Agent 给出矛盾意见，Primary Agent 未识别或未调和 | Medium |
| 过度自信未升级 | `overconfident_no_escalation` | 系统对超出能力范围的问题给出了确定性回答，未建议就医 | **Critical** |
| 专家冗余 | `specialist_redundancy` | 多个专家 Agent 给出了本质相同的意见，浪费计算且增加综合难度 | Low |
| 综合矛盾 | `synthesis_contradiction` | Primary Agent 的综合回答内部自相矛盾 | High |
| 沟通质量差 | `poor_user_communication` | 回答语言对患者不友好（过于专业、歧义、缺少行动指引） | Medium |

### 2.1 使用方式

- 人类评审时：reviewer 在标注 BAD/ERROR 时，必须同时勾选至少一个失败类型
- 自动分析时：`AnalyzerAgent` 从 reviewer notes 和评价维度自动映射到失败类型
- 优化决策时：根据失败类型的频率分布确定优化优先级

### 2.2 与当前标签体系的关系

当前 `EvaluationService` 提供的标签为 `{GOOD, BAD, NEUTRAL, ERROR}` + 可选维度 `{safety, personalized, advice_direction}`。失败分类是对 BAD/ERROR 标签的**细化归因**，不替代现有标签，而是在其基础上增加结构化原因。

---

## 3. 允许优化的对象

以下对象可以通过受控流程（见第 5 节）进行优化修改：

| 优化对象 | 说明 | 当前是否有工具支持 |
|---|---|---|
| **Prompt / Template** | 各 Agent 的系统提示词（primary、pharmacist、nutritionist、doctor、memory） | 是 — `PromptOptimizer` 已实现规则式优化和版本管理 |
| **路由规则** | 决定哪些专家 Agent 参与某次咨询的分发逻辑 | 否 — 需要新建 |
| **Memory extraction template** | 记忆 Agent 从对话中提取事实的指令模板 | 部分 — memory prompt 优化已覆盖，但提取模板本身尚未独立管理 |
| **Retrieval / Filtering / Ranking 策略** | 记忆检索的查询构建、过滤条件、排序权重 | 否 — 检索策略硬编码于 `MemoryPalaceClient` |
| **Synthesis 模板** | Primary Agent 综合多位专家意见的指令模板 | 部分 — 包含在 primary prompt 中，未独立管理 |
| **UI 文案** | 前端界面中的提示文字、标签说明、帮助文本 | 否 — 前端暂未对接优化流程 |
| **人类评测表单与标签组织方式** | 评审界面的标签选项、表单结构、评测流程设计 | 否 — 评测表单设计尚未实现 |

---

## 4. 不允许自动在线修改的对象

以下对象的修改**必须经过人类审批**，系统不得自动在线变更：

| 受保护对象 | 理由 | 修改方式 |
|---|---|---|
| **核心安全红线** | 涉及患者安全的阈值和规则（如低血糖紧急阈值 < 3.9 mmol/L 必须告警），错误修改可能直接伤害患者 | 仅通过代码 review + 人类审批 |
| **高风险医疗策略阈值** | 如胰岛素剂量调整上限、需要紧急就医的血糖临界值等 | 需要医学专家参与审批 |
| **人类审批门槛** | 决定"哪些优化需要人工审批"的规则本身，不能被自动优化 | 仅项目管理者可修改 |
| **生产版本的重要配置** | 如 `EVOLUTION_CONFIG` 中的 `max_iterations`、`improvement_threshold`、`regression_tolerance` | 通过配置管理流程 + 人类审批 |
| **数据 Schema 主结构** | `HumanEvaluation`、`EvaluationReport` 等核心数据结构的字段定义 | 通过设计评审 + 数据迁移计划 |

### 4.1 原则

> 优化系统不能优化自己的安全约束。
> 元规则（meta-rules）的修改权限永远高于优化系统的权限。

---

## 5. 优化流程必须经过的步骤

任何优化（无论是 prompt 调整还是策略变更）都必须经过以下完整流程：

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 形成候选 (Candidate Generation)                 │
│  ─ 基于失败分类的频率和严重度确定优化方向                     │
│  ─ 生成具体的候选变更（新 prompt、新规则等）                  │
│  ─ 记录变更意图和预期效果                                   │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: 回放验证 (Replay Verification)                  │
│  ─ 在固定用例集或历史轨迹上回放候选变更                       │
│  ─ 记录候选版本在每个用例上的输出                            │
│  ─ 如果无回放基础设施，此步骤阻塞后续流程                     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 与旧版本对比 (Version Comparison)               │
│  ─ 在相同用例集上对比新旧版本的输出                          │
│  ─ 量化差异：好转的 case 数、恶化的 case 数、不变的 case 数   │
│  ─ 生成人类可读的对比报告                                   │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: 回归检查 (Regression Check)                     │
│  ─ 验证候选变更不会导致已知好 case 退化                      │
│  ─ 退化容忍度由 regression_tolerance 配置控制               │
│  ─ 任何 safety 类 case 的退化一票否决                       │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: 人类审批 (Human Approval) — 按风险等级             │
│  ─ 低风险（仅 UI 文案等）：团队 lead 审批                    │
│  ─ 中风险（prompt/routing 变更）：技术 + 医学双审批           │
│  ─ 高风险（安全阈值、数据 schema）：不允许自动优化，见第 4 节    │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: 上线并进入下一轮使用 (Deploy & Monitor)           │
│  ─ 记录版本号、变更内容、审批人                              │
│  ─ 保留回滚能力（旧版本必须可恢复）                          │
│  ─ 在下一轮真实使用中收集新的评价数据，形成闭环               │
└─────────────────────────────────────────────────────────┘
```

### 5.1 当前系统对此流程的覆盖情况

| 步骤 | 当前状态 | 说明 |
|---|---|---|
| Step 1 形成候选 | **部分实现** | `PromptOptimizer._optimize_with_rules()` 可基于问题分析生成候选 prompt；`MemoryOptimizer` 可生成记忆操作候选 |
| Step 2 回放验证 | **未实现** | `SelfEvolutionLoop.run()` 在 test_cases 上运行，但没有固定回放基础设施，用例集不稳定 |
| Step 3 版本对比 | **部分实现** | `PromptOptimizer` 生成 diff 并记录版本历史，但缺少系统化的输出对比报告 |
| Step 4 回归检查 | **部分实现** | `SelfEvolutionLoop` 有 `regression_tolerance` 和回滚逻辑，但仅基于数值分数，未接入人类评价 |
| Step 5 人类审批 | **未实现** | 没有审批门控，优化直接应用 |
| Step 6 上线监控 | **部分实现** | `PromptOptimizer._persist_version()` 保存版本文件，有回滚方法 `rollback()`，但没有部署流程和监控 |

---

## 6. 当前实现状态 — 诚实评估

### 6.1 EvaluationService（`evaluation_service.py`）

**已实现：**

- `HumanEvaluation` 数据结构：包含 `patient_id`、`query`、`response`、`expert_opinions`，以及评价字段 `label`、`safety`、`personalized`、`advice_direction`、`reviewer_notes`
- 评价生命周期管理：`create_pending_evaluation()` → `submit_evaluation()` → 状态从 `pending` 转为 `completed`
- 持久化存储：通过 `MemoryPalaceClient` 将评价记录存储在 `evaluations/pending/` 和 `evaluations/completed/` 路径下
- 查询接口：`get_pending_evaluations()`、`get_evaluation()`、`get_bad_evaluations()`
- 统计汇总：`EvaluationStats` 提供 `good_rate`、`needs_attention` 等聚合指标
- 输入验证：label、safety、advice_direction 的合法值校验

**还差：**

- 缺少失败分类（Failure Taxonomy）字段 — 当前只有粗粒度的 `label` + 三个可选维度，无法表达第 2 节定义的 11 种失败类型
- 缺少 consultation trace 的关联 — 评价记录中有 `query` 和 `response`，但没有路由决策、检索到的记忆、Agent 调用链等完整轨迹
- 缺少评审者可信度/权限管理 — 任何人都能提交评价，没有 reviewer 资质校验
- 缺少批量导出和分析接口 — 统计只有简单计数，无法按时间段、失败类型、Agent 维度做聚合分析
- 缺少评价间一致性检查 — 没有 inter-rater agreement 机制

### 6.2 EvaluatorAgent（`evaluator.py`）

**已实现：**

- 规则式评估：基于关键词检测的 5 维度打分（medical_accuracy、safety、completeness、personalization、consistency）
- LLM 辅助评估：通过 prompt 让 LLM 返回 JSON 格式的评分
- 记忆质量评估：5 维度打分（completeness、accuracy、timeliness、relevance、structure）
- 评估报告生成和历史记录

**还差：**

- 规则式评估过于粗糙 — 仅检测关键词出现与否，无法捕捉语义错误
- LLM 自评不可靠 — 这是核心文档明确指出的，但代码中仍将 LLM 评分作为优化决策依据
- 没有与人类评价的校准机制 — 无法知道自动评分与人类评价的相关度

### 6.3 AnalyzerAgent（`analyzer.py`）

**已实现：**

- 从数值评分映射到问题列表（`ProblemAnalysis`）
- 从人类评价映射到问题列表（`analyze_human_evaluation()`）
- 问题分类：PROMPT / MEMORY / WORKFLOW / UNKNOWN
- reviewer notes 关键词挖掘（安全、记忆、准确性关键词）

**还差：**

- 问题分类粒度不足 — 只有 4 种 `ProblemType`，无法映射到第 2 节的 11 种失败类型
- reviewer notes 挖掘过于简陋 — 仅做关键词匹配，无法理解上下文
- 缺少跨 case 模式发现 — 只分析单个 case，不能识别系统性问题（如某个 Agent 反复出错）

### 6.4 优化器（`optimizers.py`）

**已实现：**

- `PromptOptimizer`：规则式 prompt 修改、版本管理、diff 生成、持久化、回滚
- `MemoryOptimizer`：缺失记忆提取、过时记忆清理、可疑记忆标记

**还差：**

- prompt 优化是纯追加式的 — 只往 prompt 末尾加 block，不会重构或精简
- 没有候选比较机制 — 直接应用优化结果，不比较多个候选
- 没有人类审批门控 — 优化结果直接生效
- 记忆优化的"自动提取"质量未验证 — 提取内容是硬编码模板，不确保正确性

### 6.5 SelfEvolutionLoop / HumanEvalEvolutionLoop（`self_evolution_loop.py`）

**已实现：**

- `SelfEvolutionLoop`：完整的 evaluate → analyze → optimize 循环，支持多轮迭代、回归检测、最优 prompt 保存
- `HumanEvalEvolutionLoop`：从人类 BAD/ERROR 评价出发，经 AnalyzerAgent 分析，驱动 prompt 和 memory 优化
- 结果导出：JSON 格式保存迭代历史、prompt 演化日志、memory 操作日志

**还差：**

- `SelfEvolutionLoop` 完全依赖不可靠的 Agent 自评分数做决策
- `HumanEvalEvolutionLoop` 虽然从人类评价出发，但优化后没有回放验证和回归检查
- 两个 loop 都没有固定回归测试集
- 没有版本对比报告生成
- 没有人类审批步骤

### 6.6 总体差距小结

```
已有的 ✓                          缺少的 ✗
─────────────────────────────    ─────────────────────────────
✓ 人类评价数据结构和生命周期       ✗ 失败分类体系（11 种类型）
✓ 评价持久化和查询                ✗ 完整 consultation trace 关联
✓ 人类标签驱动的优化入口          ✗ 固定回归测试集
✓ Prompt 版本管理和回滚           ✗ 回放验证基础设施
✓ 基本问题分析和归因              ✗ 新旧版本系统化对比
✓ Memory 操作的候选生成           ✗ 人类审批门控
✓ 结果导出为 JSON                ✗ 跨 case 模式分析
                                 ✗ 评审者管理和一致性检查
                                 ✗ 监控和告警
```

---

## 7. 验收标准

以下标准用于判断评价与优化体系是否达到可接受状态：

### 7.1 人类能方便地对 case 打标签

- [ ] 评审界面存在，医生可以浏览 pending 评价列表
- [ ] 标注操作不超过 3 步：选择 case → 打 label + 失败类型 → 提交
- [ ] 支持在评价中关联完整 consultation trace（不仅是 query/response，还包括路由、记忆、专家意见）
- [ ] 支持批量评审模式（一次评审多个 case）

### 7.2 团队能看懂"为什么建议改这个"

- [ ] 每个优化候选都附带：触发的失败 case 列表、失败类型分布、具体变更意图说明
- [ ] 优化建议以人类可读的格式呈现（不是只有 diff，还有自然语言解释）
- [ ] 团队成员（包括非技术人员）能理解优化报告

### 7.3 新旧版本有可比证据

- [ ] 存在至少 20 个固定测试用例的回归集
- [ ] 每次优化候选都有在回归集上的运行结果
- [ ] 对比报告包含：好转 / 恶化 / 不变的 case 计数，以及具体恶化 case 的 diff
- [ ] safety 类 case 的退化为一票否决条件

### 7.4 改进不是只依赖主观感觉

- [ ] 质量趋势有量化指标支撑（如 good_rate 随时间变化、各失败类型频率变化）
- [ ] 人类评价数据量足够（每个优化周期至少有 N 个已标注 case，N 由团队约定）
- [ ] 自动评分与人类评价有校准（即使不完美，至少有相关度数据）

### 7.5 高风险改动有明确审批和回滚方式

- [ ] 优化变更按风险等级分类，高风险变更有人类审批记录
- [ ] 所有已部署的优化都有版本号和回滚路径
- [ ] 回滚操作不超过 1 分钟（prompt 回滚已有 `PromptOptimizer.rollback()`，需扩展到其他对象）
- [ ] 审批记录可追溯：谁审批的、什么时候、基于什么证据

---

## 附录 A：术语对照

| 术语 | 说明 |
|---|---|
| Consultation trace | 一次完整咨询的全部中间状态：输入、路由、各 Agent 输出、记忆检索结果、最终回答 |
| Regression set | 一组固定的、有已知预期输出的测试用例，用于检测优化引入的退化 |
| Failure taxonomy | 结构化的失败原因分类体系 |
| Candidate | 一个待验证的优化变更（如新 prompt、新路由规则） |
| Replay | 在历史数据或固定用例上重新运行系统，收集输出用于对比 |
| Gate | 优化流程中的门控点，需要满足条件或经人类审批才能通过 |

## 附录 B：与现有代码文件的映射

| 本文档章节 | 相关代码文件 |
|---|---|
| 核心原则 / 不信任 Agent 自评 | `evaluation_service.py` (Line 4: "Agent self-evaluation is unreliable") |
| 失败分类 | 待实现 — 需扩展 `HumanEvaluation` 和 `AnalyzerAgent` |
| 允许优化的对象 | `optimizers.py` (`PromptOptimizer`, `MemoryOptimizer`) |
| 优化流程 | `self_evolution_loop.py` (`SelfEvolutionLoop`, `HumanEvalEvolutionLoop`) |
| 问题分析 | `analyzer.py` (`AnalyzerAgent`, `ProblemType`, `ProblemAnalysis`) |
| 数值评估（仅调试参考） | `evaluator.py` (`EvaluatorAgent`) |
