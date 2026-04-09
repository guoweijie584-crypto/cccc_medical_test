# 记忆治理约束文档

> 状态：设计规范 | 日期：2026-04-09
> 前置文档：`memory_module_redesign.md`

---

## 1. 设计方向

### 1.1 核心思路：统一记忆底座 + 记忆治理角色

本系统的记忆架构**不再**以"三层记忆（短期 / 中期 / 长期）"为组织原则。三层模型的问题在于：它只回答了"信息放在哪一层"，却没有回答以下更本质的问题：

| 问题 | 三层模型的回答 | 本文档要求的回答 |
|------|---------------|-----------------|
| 什么信息**应该记** | 全部存入某一层 | 由治理规则判定 |
| 什么信息**不应该记** | 无机制 | 由 Write Guard + 写入候选审核决定 |
| 什么信息**需要验证后再记** | 无机制 | 标记为 `unverified`，等待人类确认或专家二次验证 |
| 什么信息**已经过期** | 无机制 | 通过有效期 + vitality score 衰减自动降级 |
| 信息**彼此冲突**怎么办 | 新覆盖旧 | 冲突共存 + 标记 + 人工裁决 |
| 当前问题**应该取回哪些信息** | 按层返回 | 按相关性 + priority + disclosure 触发条件检索 |

**统一记忆底座**是 Memory Palace。所有记忆操作（写入、检索、更新、删除、压缩、治理）都通过 Memory Palace 完成，不在应用层做自己的记忆分层。

**记忆治理角色**是系统中新增的逻辑职责——不一定是单独的 agent，但必须有明确的代码路径负责：
- 写入前审核（这条信息值得持久化吗？）
- 冲突检测（这条信息和已有记录矛盾吗？）
- 过期清理（哪些信息已经不再有效？）
- 检索解释（本次检索为什么返回了这些结果？）

### 1.2 解决的核心问题

记忆治理要解决的不是"数据怎么存"，而是"数据怎么管"：

1. **写入治理**：不是所有对话内容都值得变成长期记忆。闲聊、重复确认、系统内部协调消息不应该进入患者记忆。
2. **冲突治理**：患者自述"我没吃药"和医生记录"患者已开药"可以共存，但必须标记冲突关系，不能默认以新信息覆盖旧信息。
3. **时效治理**：三个月前的血糖读数和今天的血糖读数不应该有相同的检索权重。
4. **来源治理**：用户自述、专家推断、医生确认、系统抽取——这四类来源的可信度天然不同，必须在元数据中区分。
5. **检索治理**：每次检索结果必须可解释——人类能看懂"这次回答用到了哪些历史信息，为什么用了这些"。

---

## 2. 核心原则

### 2.1 不要把所有数据都当成"存一下就好"

> **反模式**：对话结束 -> 把整段对话文本存入记忆 -> 下次检索时全文匹配。

这种做法的问题：
- 记忆库迅速膨胀，检索噪声增大
- 无法区分"患者说过的事实"和"系统的中间推理过程"
- 无法判断信息是否仍然有效
- 无法在冲突时做出合理选择

**正确做法**：对话结束后，由记忆治理流程提取**结构化事实**（fact extraction），每个事实附带完整元数据后再决定是否写入。原始对话可以作为审计日志保留，但不作为记忆检索的主要来源。

### 2.2 持久化层必须服务于六个目标

持久化不是"怕丢数据所以存一下"。系统的每一次持久化操作都必须能回答"你在服务于哪个目标"：

| 目标 | 含义 | 示例 |
|------|------|------|
| **患者上下文连续性** | 跨会话保持对患者的理解 | 患者的基础档案、用药方案、过敏信息跨会话可用 |
| **历史可回放** | 能还原任意一次咨询的完整上下文 | 三周前那次咨询，系统看到了什么信息、做了什么判断 |
| **失败可归因** | 能追溯错误回答的根因 | 这次回答错了，是因为记忆缺失、记忆过期、还是检索遗漏 |
| **记忆可治理** | 能对记忆做增删改查和生命周期管理 | 过期记忆降级、冲突记忆标记、低质量记忆清除 |
| **版本可比较** | 能比较不同版本系统的记忆使用质量 | v1.2 比 v1.1 在药物交互检索上召回率提高了多少 |
| **改动可回滚** | 任何记忆写入都能撤销 | 误写入的信息可以通过 snapshot 回滚 |

---

## 3. 数据类型

系统中必须支持以下逻辑实体。每个实体不一定对应一张表，但必须在数据模型中有明确的表达方式。

### 3.1 核心业务实体

| 实体 | 说明 | 生命周期 |
|------|------|---------|
| **用户 / 患者（Patient）** | 系统的服务对象，拥有唯一标识 | 长期存在，档案持续更新 |
| **会话（Session）** | 一次连续的交互过程 | 会话开始到结束，结束后压缩为摘要 |
| **咨询轮次（Consultation Turn）** | 一次完整的问答交互（用户提问 -> 系统回答） | 随会话产生，结束后归档 |
| **消息（Message）** | 单条用户输入或系统输出 | 会话内实时存在，归档后降级为审计日志 |
| **最终答复（Final Response）** | 系统经过多专家协调后给出的最终回答 | 永久保留，关联到咨询轮次 |

### 3.2 专家调用与协调实体

| 实体 | 说明 | 生命周期 |
|------|------|---------|
| **专家调用记录（Expert Invocation Record）** | 某次咨询中调用了哪些专家 agent、每个专家返回了什么 | 永久保留，用于归因和评价 |

### 3.3 记忆系统实体

| 实体 | 说明 | 生命周期 |
|------|------|---------|
| **Memory Record** | 经过治理流程写入的结构化记忆条目 | 受 vitality score 和有效期管理 |
| **Memory Retrieval Trace** | 某次咨询中检索记忆的过程记录：查询了什么、返回了什么、排序依据是什么 | 永久保留，用于检索质量分析 |
| **Memory Writeback Candidate** | 对话结束后提取的待写入记忆候选项 | 短期存在：审核通过后转为 Memory Record，拒绝则丢弃 |

### 3.4 评价与改进实体

| 实体 | 说明 | 生命周期 |
|------|------|---------|
| **Evaluation Task** | 一个待评价的咨询案例 | 从创建到完成评价 |
| **Evaluation Label** | 人类评审员给出的评价标签 | 永久保留 |
| **Failure Taxonomy Label** | 对失败案例的分类标签（记忆缺失 / 检索遗漏 / 推理错误 / ...） | 永久保留 |
| **Improvement Candidate** | 从失败分析中提炼的改进建议 | 跟踪到实施或关闭 |

### 3.5 系统管理实体

| 实体 | 说明 | 生命周期 |
|------|------|---------|
| **Version Metadata** | 系统版本信息（提示词版本、模型版本、记忆策略版本） | 每次部署更新 |
| **Audit Log** | 所有关键操作的不可变日志（记忆写入、删除、修改、检索） | 永久保留，只追加不修改 |

---

## 4. 记忆记录的元数据要求

每条写入 Memory Palace 的重要记忆（Memory Record）必须携带以下元数据。这不是"可选的附加信息"，而是记忆治理的基础设施。

### 4.1 必需元数据字段

```yaml
memory_record:
  # -- 核心内容 --
  content: "患者当前使用二甲双胍 500mg bid"
  memory_type: "medication_regimen"       # 记忆类型分类

  # -- 来源 --
  source:
    type: "patient_self_report"           # 见 4.2 来源类型枚举
    session_id: "sess_20260409_001"       # 产生该记忆的会话
    turn_id: "turn_003"                   # 产生该记忆的咨询轮次
    agent_id: "medication_expert"         # 提取该记忆的 agent
    original_text: "我现在吃的是二甲双胍，一天两次，一次一片"  # 原始文本引用

  # -- 时间与有效期 --
  created_at: "2026-04-09T14:30:00+08:00"
  effective_from: "2026-04-09"            # 信息的生效时间
  effective_until: null                   # null 表示无明确过期时间
  staleness_hint: "3_months"             # 建议的新鲜度窗口

  # -- 置信度 --
  confidence:
    level: 0.7                            # 0.0 ~ 1.0
    reason: "patient_self_report_not_verified"  # 置信度依据

  # -- 验证状态 --
  verification:
    status: "unverified"                  # unverified / verified / disputed / retracted
    verified_by: null                     # 谁验证的
    verified_at: null                     # 何时验证的

  # -- 敏感级别 --
  sensitivity: "phi"                      # public / internal / phi / restricted

  # -- 冲突与替代关系 --
  conflicts_with: []                      # 与哪些已有记录存在冲突
  supersedes: []                          # 替代了哪些旧记录（旧记录不删除，标记为 superseded）
  superseded_by: null                     # 被哪条新记录替代
```

### 4.2 来源类型枚举

| source.type | 含义 | 默认置信度参考 |
|-------------|------|---------------|
| `patient_self_report` | 患者自述 | 0.6 ~ 0.8 |
| `expert_inference` | 专家 agent 推断 | 0.5 ~ 0.7 |
| `doctor_confirmed` | 医生 / 人类专业人员确认 | 0.9 ~ 1.0 |
| `system_extraction` | 系统从结构化数据中自动抽取 | 0.7 ~ 0.9 |
| `lab_result` | 检验报告 | 0.95 ~ 1.0 |
| `device_reading` | 设备读数（血糖仪等） | 0.85 ~ 0.95 |

### 4.3 记忆类型枚举（memory_type）

| memory_type | 说明 | 典型 priority |
|-------------|------|--------------|
| `allergy_alert` | 过敏 / 禁忌症 | 0 (SAFETY_ALERT) |
| `contraindication` | 用药禁忌 | 0 (SAFETY_ALERT) |
| `diagnosis` | 诊断信息 | 1 (CORE_PROFILE) |
| `medication_regimen` | 当前用药方案 | 1 (CORE_PROFILE) |
| `lab_result` | 检验结果 | 2 (RECENT_KEY_EVENT) |
| `glucose_reading` | 血糖读数 | 2 (RECENT_KEY_EVENT) |
| `lifestyle_habit` | 生活习惯（饮食、运动） | 4 (AUXILIARY) |
| `consultation_summary` | 咨询摘要 | 3 (CONSULTATION) |
| `patient_preference` | 患者偏好 | 4 (AUXILIARY) |
| `system_note` | 系统内部备注 | 5 (LOW_PRIORITY) |

---

## 5. 记忆系统硬性要求

以下是不可违反的系统约束。任何代码变更都不得破坏这些要求。

### 5.1 禁止：把对话原文直接当长期记忆

```
错误做法：
   store_memory(content=entire_dialogue_text)

正确做法：
   facts = extract_facts(dialogue)
   for fact in facts:
       candidate = create_writeback_candidate(fact, metadata)
       if governance_check(candidate):
           store_memory(candidate)
   store_audit_log(dialogue)  # 原文进审计日志，不进记忆检索
```

**原因**：对话原文包含大量噪声（寒暄、确认、重复、系统内部消息），直接存储会污染检索结果。结构化事实才是记忆的正确形态。

### 5.2 禁止：默认新信息覆盖旧信息

```
错误做法：
   update_memory(path, new_content)  # 直接覆盖

正确做法：
   conflict = detect_conflict(new_fact, existing_facts)
   if conflict:
       mark_conflict(new_fact, existing_fact)
       # 两条记录共存，等待人工裁决或自动消解规则
   else:
       if new_fact.supersedes(existing_fact):
           mark_superseded(existing_fact, by=new_fact)
           store_memory(new_fact)
       else:
           store_memory(new_fact)  # 新增，不覆盖
```

**原因**：医疗场景中，信息冲突往往反映真实世界的复杂性（患者记忆不准确、不同来源信息不一致），粗暴覆盖会丢失重要线索。

### 5.3 禁止：过期信息与当前信息地位相同

系统必须在检索时考虑信息的时效性：

- 带有 `effective_until` 且已过期的记录，检索权重必须显著降低
- 超过 `staleness_hint` 窗口的记录，检索权重应适当降低
- Memory Palace 的 vitality score 衰减机制应被积极利用
- 在构建患者上下文时，过期的用药方案不能和当前方案并列呈现，必须标注时间状态

### 5.4 禁止：缺少"人类验证"与"系统推断"的区分

每条记忆的 `verification.status` 和 `source.type` 必须被正确设置：

- 患者自述但未经医生确认的信息 -> `unverified` + `patient_self_report`
- 系统从对话中推断的信息 -> `unverified` + `expert_inference`
- 医生明确确认的信息 -> `verified` + `doctor_confirmed`
- 实验室检验结果 -> `verified` + `lab_result`

在向用户呈现信息时，未验证信息必须有明确标识（如"据您此前描述"），不得和已验证信息混为一谈。

### 5.5 禁止：检索结果不可解释

每次记忆检索必须生成 `Memory Retrieval Trace`，至少包含：

```yaml
retrieval_trace:
  session_id: "sess_20260409_001"
  turn_id: "turn_003"
  query: "患者当前用药方案"
  search_mode: "hybrid"
  results_returned: 5
  results:
    - uri: "medical://patients/P001/medications/current"
      score: 0.92
      match_reason: "keyword_match: 用药方案; semantic_relevance: high"
      priority: 1
      verification_status: "verified"
    - uri: "medical://patients/P001/consultations/20260401"
      score: 0.75
      match_reason: "semantic_relevance: medium; mentioned medication adjustment"
      priority: 3
      verification_status: "unverified"
  filters_applied:
    path_prefix: "patients/P001"
    mode: "hybrid"
  timestamp: "2026-04-09T14:30:05+08:00"
```

**目的**：当人类评审员发现系统回答有误时，可以直接查看 retrieval trace 判断是"没检索到正确信息"还是"检索到了但推理出错"。

---

## 6. 当前 Memory Palace 集成状态

### 6.1 已实现的部分

基于对 `memory_agent.py` 和 `palace_client.py` 的代码审查，以下能力已经落地：

| 能力 | 实现状态 | 对应代码 |
|------|---------|---------|
| 三层记忆已移除 | 已完成 | `memory_agent.py` 不再有 `short_term` / `mid_term` / `long_term` |
| Memory Palace HTTP 客户端 | 已完成 | `palace_client.py` — `MemoryPalaceClient` 类 |
| URI 寻址体系 | 已完成 | `patients/{id}/profile`, `patients/{id}/consultations/*` 等 |
| Priority 分级 | 已完成 | `Priority` 类定义了 0~5 级优先级 |
| Disclosure 触发条件 | 已完成 | `create()` 和 `store_consultation_record()` 传入 disclosure |
| 混合检索 | 已完成 | `search()` 支持 keyword / semantic / hybrid 三种模式 |
| 事实提取 | 基本完成 | `extract_facts_from_interaction()` 基于关键词的规则提取 |
| 患者档案读写 | 已完成 | `update_patient_profile()`, `retrieve_patient_context()` |
| 父路径自动创建 | 已完成 | `_ensure_parent_path()` |
| 连接容错 | 已完成 | cooldown 机制，Memory Palace 不可用时不阻塞主流程 |

### 6.2 尚未实现的部分（差距）

| 差距 | 严重程度 | 说明 |
|------|---------|------|
| **记忆元数据不完整** | 高 | 当前写入的记忆只有 `priority` 和 `disclosure`，缺少 `source`、`confidence`、`verification_status`、`effective_until`、`sensitivity`、`conflicts_with`、`supersedes` 等治理必需的元数据 |
| **无冲突检测** | 高 | 写入新记忆前不检查是否与已有记录冲突，直接创建新节点 |
| **无写入候选审核** | 高 | `extract_and_store()` 提取事实后直接写入，没有 writeback candidate 审核环节 |
| **无 retrieval trace** | 高 | `retrieve_patient_context()` 和 `search_memories()` 不记录检索过程 |
| **事实提取过于简单** | 中 | `extract_facts_from_interaction()` 基于简单关键词匹配，无法提取结构化的医疗实体（药物名称+剂量+频次等） |
| **无过期 / 时效管理** | 中 | 写入记忆时不设置有效期，检索时不考虑时效性 |
| **无 Memory Palace 原生 Write Guard 利用** | 中 | `palace_client.py` 的 `create()` 直接调用 API，未利用 Write Guard 的 ADD / UPDATE / NOOP / DELETE 预检机制 |
| **无 snapshot / 回滚利用** | 中 | Memory Palace 支持 snapshot & review，但当前代码未使用 |
| **无 vitality score 利用** | 中 | Memory Palace 的 vitality score 衰减机制未被主动管理 |
| **无审计日志** | 中 | 记忆操作（写入、更新、删除）没有写入不可变审计日志 |
| **搜索走 observability 端点** | 低 | `search()` 用的是 `/maintenance/observability/search`，不是 MCP 标准接口，功能可用但不够规范 |

### 6.3 集成架构现状

```
+---------------------------------------------------+
|              Workflow (workflow.py)                 |
|                      |                             |
|                      v                             |
|           MemoryAgent (memory_agent.py)             |
|           +------------------------+               |
|           | retrieve_patient_ctx   | <- 无 trace    |
|           | store_consultation     | <- 无冲突检测   |
|           | extract_and_store      | <- 无审核环节   |
|           | update_profile         | <- 直接覆盖     |
|           +----------+-------------+               |
|                      |                             |
|                      v                             |
|        MemoryPalaceClient (palace_client.py)        |
|           +------------------------+               |
|           | create / read /        |               |
|           | update / delete /      |               |
|           | search                 |               |
|           +----------+-------------+               |
|                      | HTTP                        |
+----------------------+-----------------------------+
                       v
              Memory Palace (:8000)
              +------------------------+
              | Write Guard        <- 未被利用       |
              | Snapshot & Review  <- 未被利用       |
              | Vitality Score     <- 未被利用       |
              | Hybrid Search      <- 已使用         |
              | URI Addressing     <- 已使用         |
              +------------------------+
```

---

## 7. 验收标准

### 7.1 人类可读性

- [ ] 给定一轮咨询记录，人类评审员能在系统中找到该轮咨询使用了哪些历史记忆（通过 retrieval trace）
- [ ] retrieval trace 包含每条被检索记忆的来源、置信度、验证状态
- [ ] 评审员能理解"为什么系统选择了这些记忆而不是其他"

### 7.2 结构化与原始数据分离

- [ ] 系统能区分**结构化实体**（患者档案、用药方案、血糖读数）和**原始对话痕迹**（对话文本、中间推理过程）
- [ ] 记忆检索默认只搜索结构化实体，原始对话仅在审计和归因场景中被访问
- [ ] 每条结构化实体都有完整的元数据（来源、置信度、验证状态、有效期）

### 7.3 冲突信息共存

- [ ] 当新信息与旧信息冲突时，两条记录都保留，通过 `conflicts_with` 字段关联
- [ ] 冲突记录在检索结果中有明确标识
- [ ] 系统不会把未验证的冲突信息当作确定事实呈现给用户
- [ ] 人工裁决冲突后，被否决的记录标记为 `retracted`，而非删除

### 7.4 评价与版本比较支持

- [ ] 每次咨询的 retrieval trace 和 expert invocation record 都被持久化
- [ ] 可以按版本（version metadata）筛选和比较不同版本系统的记忆使用表现
- [ ] evaluation task 能关联到具体的 retrieval trace，支持"这次回答用了错误的记忆"类型的失败标注
- [ ] failure taxonomy label 中包含记忆相关的失败类型（记忆缺失、记忆过期、检索遗漏、冲突未处理）

### 7.5 可扩展性

- [ ] 新增一种 memory_type 不需要修改核心的写入 / 检索逻辑
- [ ] 新增一种 source.type 不需要修改元数据 schema（枚举可扩展）
- [ ] 记忆治理规则（写入审核、冲突检测、过期清理）是可配置的，不硬编码在业务逻辑中
- [ ] 未来接入真实医疗数据源（HIS、LIS、PACS）时，只需新增对应的 source.type 和转换适配器，不需要重构记忆模型
- [ ] URI 体系支持新增顶层分类（如 `clinical_trials://`、`research://`）而不影响现有路径

---

## 附录 A：从当前实现到目标状态的差距摘要

```
当前状态                              目标状态
---------------------------------     ---------------------------------
extract -> 直接 store                  extract -> candidate -> audit -> store
无元数据                               完整元数据（来源/置信度/验证/时效/冲突）
无冲突检测                             冲突检测 + 共存 + 人工裁决
新信息覆盖旧信息                        supersedes 关系链 + 旧记录保留
无检索 trace                           每次检索生成 retrieval trace
无审计日志                             不可变审计日志
Write Guard 未利用                     Write Guard 预检 + NOOP 防重复
Vitality score 未利用                  vitality 驱动的过期降级
Snapshot 未利用                        变更前自动 snapshot + 可回滚
```

## 附录 B：与 memory_module_redesign.md 的关系

`memory_module_redesign.md` 定义了**技术重构方案**——如何从三层记忆迁移到 Memory Palace 架构、URI 规划、API 对接、代码变更计划。

本文档定义了**治理约束**——在技术架构之上，记忆系统必须遵守的行为规范和质量要求。两份文档是互补关系：

- `memory_module_redesign.md`：回答"记忆系统的技术架构是什么"
- `memory_governance.md`（本文档）：回答"记忆系统的行为边界是什么"

后续实现时，所有代码变更必须同时满足两份文档的要求。
