# 后端开发约束文档

> 血糖管理多智能体系统 — 后端行为规范与工程约束
>
> 文档状态：**活跃** | 最后更新：2026-04-09

---

## 1. 后端目标

后端不是为了"让 demo 跑起来"。后端的设计目标是支撑以下五项核心要求，缺一不可：

| 目标 | 含义 | 不合格的表现 |
|------|------|-------------|
| **端到端可运行的咨询链路** | 从患者输入到最终响应，完整经过记忆检索→专家路由→汇总→安全检查→记忆写回→输出，每步都真实执行 | 跳过任何环节直接返回 mock 字符串；链路中某步骤静默失败但仍返回 200 |
| **可观测的多智能体协作** | 每轮咨询产生结构化 trace，记录哪些 agent 参与、输入输出是什么、耗时多长、有无降级 | 只有最终 response，无法回溯中间过程 |
| **受控的记忆读取与写回** | 记忆检索有明确上下文窗口和优先级；写回有候选提取和存储确认；失败有显式报告 | 记忆操作在 try-except 中被吞掉，或无条件写入未经提取的原始对话 |
| **明确的安全审查** | 最终输出经过安全门控检查，包含必要的风险提醒、禁忌信息、就医建议 | 输出直接拼接专家文本，无安全校验步骤 |
| **可评价可复盘可比较的版本行为** | 同样输入在同版本下行为可复现；不同版本间行为差异可追踪；评测结果可存储供人类审阅 | 行为随机不可控，无评测入口，无法比较两次运行 |

### 设计原则

1. **显式优于隐式** — 每一步处理都产生可检查的中间结构，而非在函数内部闭合消化
2. **失败是一等公民** — 失败路径和成功路径一样需要设计、记录、测试
3. **Mock 和 Real 是两种明确模式** — 不是"差不多"，是"行为边界完全清楚"
4. **可审阅优于可运行** — 一个跑通但不可审阅的链路，价值为零

---

## 2. 后端核心能力清单

后端必须围绕以下 10 项能力进行设计。每项能力对应明确的入口、输入、输出和失败行为。

### 能力矩阵

| # | 能力 | 入口 | 核心职责 | 当前实现文件 |
|---|------|------|---------|-------------|
| C1 | **启动咨询** | `POST /api/consultation` (已废弃) → CCCC 工作组 API | 接收患者 ID + 自然语言问题，创建咨询会话，触发多智能体链路 | `api_server.py` L589–608, `workflow.py` L37–121 |
| C2 | **管理会话** | 工作组 ledger / session 机制 | 维护咨询的生命周期：创建、进行中、完成、失败；关联 session_id | `api_server.py` 通过 CCCC 工作组 |
| C3 | **检索记忆上下文** | `MemoryAgent.build_agent_context()` | 从 Memory Palace 检索患者 profile + 相关记忆，构建 agent 可用的上下文字符串 | `memory_agent.py` L147–172 |
| C4 | **动态路由专家** | `GlucoseManagementWorkflow.process_patient_query()` | 根据当前查询和上下文，确定调用哪些专家 agent（当前为固定三路并发） | `workflow.py` L52–68 |
| C5 | **汇总专家输出** | `PrimaryAgent.process_sync()` | Primary Agent 接收所有专家意见，生成面向患者的综合建议 | `primary_agent.py` L27–31, `workflow.py` L75–79 |
| C6 | **进行安全检查** | 应由 Safety Gate 模块负责 | 对最终输出执行安全审查：检查禁忌遗漏、危险建议、缺失的就医提醒 | `evaluator.py` L245–250（仅评测时） |
| C7 | **写回记忆候选** | `MemoryAgent.extract_and_store()` | 从交互中提取结构化事实，按类别和优先级写入 Memory Palace | `memory_agent.py` L249–292 |
| C8 | **生成 trace** | 咨询结果的返回结构 | 记录本次咨询的完整执行链路：路由决策、各 agent 输入输出、时延、模式 | `workflow.py` L109–121（部分） |
| C9 | **创建评测任务** | `POST /api/evaluations/pending` | 咨询完成后为人类医生创建待评测记录，包含原始问题、系统回复、专家意见 | `api_server.py` L614–634 |
| C10 | **拉取运维与分析信息** | `GET /api/health`, `GET /api/evaluations/stats`, `GET /api/evolution/report` | 提供系统健康状态、评测统计、演化报告，支撑运维和分析界面 | `api_server.py` L686–758, L870–892 |

### 能力间的依赖关系

```
C1 启动咨询
 ├── C2 管理会话（创建 session）
 ├── C3 检索记忆上下文
 │    └── Memory Palace 服务可用
 ├── C4 动态路由专家
 │    ├── PharmacistAgent
 │    ├── NutritionistAgent
 │    └── DoctorAgent
 ├── C5 汇总专家输出
 │    └── PrimaryAgent
 ├── C6 进行安全检查
 ├── C7 写回记忆候选
 │    └── Memory Palace 服务可用
 └── C8 生成 trace
      └── C9 创建评测任务（可选，post-consultation）

C10 拉取运维与分析信息（独立，可随时调用）
```

---

## 3. 后端必须明确的行为

### 3.1 用户输入结构

用户（患者）输入经过前端提交，到达后端时必须为以下结构：

```python
# 最小必需字段
{
    "patient_id": str,   # 患者 UUID，对应 patients.json 中的 "患者UUID"
    "query": str,        # 自然语言问题，例如 "我的二甲双胍能和维生素B12一起吃吗？"
}
```

**约束：**
- `patient_id` 必须在患者数据文件中可查到，否则返回 404
- `query` 不得为空字符串，最大长度应有限制（建议 2000 字符）
- 后端不对 query 做自然语言预处理，直接传递给 agent 链路

### 3.2 Coordinator（Primary Agent）接收的结构

Primary Agent 作为协调者，接收以下输入：

```python
# build_full_prompt() 构建的完整上下文
{
    "context": str,          # 由 MemoryAgent.build_agent_context() 构建的上下文字符串
                             # 包含：Agent 类型、当前查询、患者 Profile、相关记忆
    "query": str,            # 原始患者问题
    "expert_opinions": {     # 各专家 agent 的文本输出
        "pharmacist": str,
        "nutritionist": str,
        "doctor": str,
    }
}
```

**当前实现参考：** `workflow.py` L75–79, `base_agent.py` L62–83

### 3.3 Specialist 输出结构

每个专家 agent（Pharmacist / Nutritionist / Doctor）的输出结构统一为：

```python
{
    "agent_type": str,     # "pharmacist" | "nutritionist" | "doctor"
    "agent_name": str,     # 中文名："药剂师" | "营养师" | "代谢病医生"
    "response": str,       # 自然语言建议文本
    "success": bool,       # 是否成功生成
}
```

**约束：**
- `response` 为空字符串时，`success` 应为 `False`
- Mock 模式下返回预设文本，`success` 恒为 `True`
- Real 模式下 LLM 调用失败时，必须在返回结构中体现，不得静默降级

### 3.4 Memory Dossier 结构

Memory dossier（记忆档案）是传递给 agent 的患者上下文，由 `MemoryAgent.build_agent_context()` 构建：

```
Agent: {agent_type}
Current query: {current_query}

## Patient Profile
{profile_text}               # 来自 Memory Palace 的患者画像
                              # 包含：年龄、性别、糖尿病类型、诊断时间、用药、并发症

## Relevant Memories
- [glucose] 血糖读数 7.8 mmol/L (2026-04-08T10:30:00)
- [medication] 咨询涉及medication管理 (2026-04-07T15:20:00)
- [consultation] 常规糖尿病管理咨询 (2026-04-06T09:00:00)
...最多 8 条
```

**约束：**
- 记忆检索使用 hybrid 模式（keyword + semantic），最多返回 10 条
- 路径前缀必须限定在 `patients/{patient_id}` 下，防止跨患者信息泄露
- Profile 不存在时，dossier 中 profile 部分为空但链路不中断

### 3.5 Safety Gate 输入/输出

**目标输入：**

```python
{
    "patient_id": str,
    "query": str,                    # 原始问题
    "primary_response": str,         # Primary Agent 的汇总建议
    "expert_opinions": Dict[str, str],
    "patient_context": {             # 关键患者信息摘要
        "medications": List[str],
        "complications": List[str],
        "recent_glucose": List[Dict],
    }
}
```

**目标输出：**

```python
{
    "passed": bool,                  # 是否通过安全检查
    "risk_level": str,               # "safe" | "caution" | "danger"
    "flags": List[str],              # 触发的安全标志列表
    "modifications": str | None,     # 建议的修改（如需要）
    "requires_disclaimer": bool,     # 是否需要附加免责声明
}
```

**当前状态：** Safety Gate 作为独立模块尚未实现。安全检查逻辑目前分散在：
- `evaluator.py` 中的关键词检查（L245–250）——仅在评测阶段
- Mock 响应中的硬编码安全提醒文本
- 无实时安全拦截机制

### 3.6 Trace 必须记录的信息

每轮咨询的 trace 必须包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | str | 本次请求的唯一标识 |
| `session_id` | str | 会话标识（同一患者多轮对话） |
| `patient_id` | str | 患者 UUID |
| `timestamp` | str | ISO 8601 时间戳 |
| `mode` | str | `"mock"` 或 `"llm"` |
| `routed_agents` | List[str] | 本次路由了哪些专家 agent |
| `context_retrieved` | Dict | 检索到的关键上下文摘要（profile 是否存在、记忆条数、相关度分布） |
| `expert_outputs` | Dict[str, Dict] | 各专家的输出和状态（response 摘要、success、耗时） |
| `synthesis_input` | Dict | 传递给 Primary Agent 的汇总输入摘要 |
| `safety_check` | Dict | Safety Gate 的检查结果 |
| `final_response` | str | 最终返回给患者的文本 |
| `memory_writeback` | Dict | 写回了哪些记忆（URI 列表、提取的事实数） |
| `evaluation_created` | bool | 是否创建了评测任务 |
| `processing_time_ms` | float | 总处理时间 |
| `errors` | List[Dict] | 处理过程中的错误列表（步骤、错误信息、是否降级处理） |

**当前状态：** `workflow.py` L109–121 返回部分 trace 信息，但缺少 `request_id`、`session_id`、`safety_check`、`evaluation_created`、分步耗时、错误列表。

### 3.7 失败时的退化处理

失败不允许被静默吞掉。每种失败场景必须有明确的退化策略：

| 失败场景 | 退化策略 | 输出要求 |
|---------|---------|---------|
| Memory Palace 不可达 | 跳过记忆检索，使用空上下文继续链路 | trace 标记 `context_retrieved.degraded = true`，最终响应附加 "基于有限信息" 声明 |
| 某个专家 agent 超时 | 使用已完成专家的输出继续汇总 | trace 记录失败 agent 和超时时间 |
| 所有专家 agent 均失败 | 返回预设安全响应，建议患者咨询医生 | 不得返回空字符串或内部错误信息 |
| 记忆写回失败 | 咨询结果正常返回，写回错误记录到 trace | 不影响患者看到的响应 |
| LLM API 不可用 | 自动切换到 mock 模式 | 响应中明确标记 `mode: "mock"` |
| Safety Gate 检测到危险内容 | 替换为安全的通用建议 + 就医提醒 | trace 记录原始输出和替换原因 |

---

## 4. 异常处理要求

每种异常场景需要明确的检测条件、处理方式、日志行为和对外表现。

### 4.1 没检索到足够上下文

- **检测条件：** `memory_count == 0` 或 Memory Palace 返回错误
- **处理方式：** 链路继续执行，但 agent 上下文中只包含基础查询信息
- **日志行为：** 记录警告，附带 patient_id 和查询内容
- **对外表现：** 响应可正常返回，但 trace 中标记上下文不足；响应质量预期降低
- **当前实现：** `memory_agent.py` L131 中 profile 为 None 时返回空 dict，链路不中断——**基本满足**

### 4.2 某个专家调用失败

- **检测条件：** `future.result()` 抛出异常或超时（当前 15s）
- **处理方式：** 该专家输出置为空字符串，其余专家正常参与汇总
- **日志行为：** 记录失败 agent 类型、异常信息、耗时
- **对外表现：** 最终响应中该专家观点缺失
- **当前实现：** `workflow.py` L58–63 中 `future.result(timeout=15)` 会抛出异常，但**外层无 try-except 保护**——**需要修复**

### 4.3 专家结论彼此冲突

- **检测条件：** 汇总阶段 Primary Agent 发现专家意见矛盾（如药剂师建议加药、医生建议减药）
- **处理方式：** Primary Agent 应在汇总中明确说明分歧，并建议患者咨询主治医生
- **日志行为：** trace 中记录冲突检测结果
- **对外表现：** 响应中包含 "不同专家观点存在差异" 的说明
- **当前实现：** 完全依赖 LLM（Primary Agent）的自然语言理解能力来处理冲突——**无结构化冲突检测**

### 4.4 记忆写回失败

- **检测条件：** `client.create()` 返回包含 `"error"` 的 result
- **处理方式：** 咨询结果正常返回，写回错误不影响用户侧
- **日志行为：** 记录失败的 path、error 信息、待写内容摘要
- **对外表现：** 响应正常，trace 中标记写回状态
- **当前实现：** `memory_agent.py` L282–291 中检查 error 并跳过——**部分满足**，但无日志记录

### 4.5 安全审查不通过

- **检测条件：** Safety Gate 返回 `passed: false`
- **处理方式：** 替换 Primary Agent 的输出为安全的通用建议，附加就医提醒
- **日志行为：** trace 记录原始输出（不返回给用户）和安全标志
- **对外表现：** 用户看到安全版本的响应
- **当前实现：** **Safety Gate 模块未实现**——评测阶段的安全检查（`evaluator.py`）不在在线链路中

### 4.6 模型不可用或部分降级

- **检测条件：** `llm_client.available == False` 或 API 调用返回错误
- **处理方式：** 整体切换到 mock 模式（`use_mock=True`）
- **日志行为：** 记录降级原因和时间点
- **对外表现：** 响应中 `mode` 字段为 `"mock"`
- **当前实现：** `api_server.py` L252 根据 `llm_client.available` 决定模式——**全局级别满足**，但不支持单 agent 粒度的降级

### 4.7 Mock 和 Real 模式结果差异

- **风险：** Mock 模式返回硬编码文本，行为与 Real 模式的 LLM 输出在结构和内容上可能差异巨大
- **要求：**
  - Mock 输出必须遵循与 Real 输出相同的结构约定
  - Mock 文本中的医学内容必须合理（当前已实现，见 `base_agent.py` L125–195）
  - Trace 中必须明确标记 `mode` 字段
  - 评测系统必须区分 mock 评测和 real 评测，不得混为一谈
  - 前端审阅界面必须显式展示当前模式
- **当前实现：** Mock agent 返回结构与 Real agent 一致（均通过 `format_response()`）——**结构层面满足**，但缺少 Mock/Real 评测隔离

---

## 5. 可观测性要求

### 5.1 每轮咨询必须追踪的信息

| 追踪项 | 来源 | 当前是否追踪 |
|--------|------|-------------|
| Request ID | 系统生成 UUID | **否** — 无 request_id 生成 |
| Session ID | 会话管理 | **否** — 无 session 管理 |
| Patient ID | 请求入参 | **是** — `workflow.py` L109 |
| 路由了哪些角色 | 路由决策 | **部分** — 当前固定三路，未记录路由决策 |
| 检索了哪些关键上下文 | Memory Agent | **部分** — 返回 `context` 但无结构化摘要 |
| 哪些信息被用于汇总 | Primary Agent 输入 | **部分** — `expert_opinions` 已记录 |
| 安全审查结果 | Safety Gate | **否** — Safety Gate 未实现 |
| 最终输出状态 | 链路结束 | **是** — `primary_response` |
| 是否创建评测任务 | 评测服务 | **否** — 咨询链路与评测创建未关联 |
| 时延信息 | 计时器 | **部分** — 有总耗时，无分步耗时 |
| 失败信息 | 错误处理 | **否** — 无结构化错误列表 |

### 5.2 可观测性实现目标

```python
# 目标 trace 结构（每轮咨询输出）
{
    "trace_version": "1.0",
    "request_id": "req_20260409_143022_abc123",
    "session_id": "sess_patient001_20260409",
    "patient_id": "patient_uuid_001",
    "timestamp": "2026-04-09T14:30:22.456Z",
    "mode": "llm",                              # "llm" | "mock"

    "context_retrieval": {
        "profile_found": true,
        "memory_count": 6,
        "memory_categories": ["glucose", "medication", "consultation"],
        "retrieval_time_ms": 120,
        "degraded": false,
    },

    "routing": {
        "strategy": "fixed_parallel",           # 未来可扩展为 "dynamic"
        "routed_agents": ["pharmacist", "nutritionist", "doctor"],
        "routing_reason": "default_all_specialists",
    },

    "specialist_outputs": {
        "pharmacist": {
            "success": true,
            "response_length": 342,
            "processing_time_ms": 1850,
            "error": null,
        },
        "nutritionist": {
            "success": true,
            "response_length": 456,
            "processing_time_ms": 2100,
            "error": null,
        },
        "doctor": {
            "success": true,
            "response_length": 389,
            "processing_time_ms": 1920,
            "error": null,
        },
    },

    "synthesis": {
        "input_expert_count": 3,
        "response_length": 520,
        "processing_time_ms": 2300,
    },

    "safety_check": {
        "executed": false,                      # 当前未实现
        "passed": null,
        "risk_level": null,
        "flags": [],
    },

    "memory_writeback": {
        "facts_extracted": 3,
        "facts_stored": 3,
        "stored_uris": ["memory://patients/xxx/glucose/20260409_143025_000001_0"],
        "errors": [],
    },

    "evaluation": {
        "pending_created": false,
        "evaluation_id": null,
    },

    "total_processing_time_ms": 4850,
    "errors": [],
}
```

### 5.3 健康检查端点要求

`GET /api/health` 必须返回：

| 字段 | 说明 | 当前状态 |
|------|------|---------|
| `status` | 整体健康状态 | **已实现** |
| `llm_mode` | LLM 可用性 | **已实现** |
| `memory_palace_status` | Memory Palace 连接状态 | **已实现** |
| `version` | API 版本 | **已实现** |
| `uptime` | 服务运行时间 | **未实现** |
| `cccc_native_status` | CCCC 工作组状态 | **未实现**（需通过 `/api/cccc-native/status` 单独获取） |

---

## 6. 当前实现状态

以下是对照 `api_server.py` 和 `workflow.py` 代码的诚实评估。

### 6.1 API 服务器 (`api_server.py`)

**已实现且可用：**
- 患者数据加载与规范化（`_normalize_patient()`，L163–227）——支持中文字段到标准字段的映射，健壮
- Memory Palace 完整 CRUD API（`/api/memory/*`，L396–586）——树形读取、搜索、创建、更新、删除均已实现
- LLM 配置管理（`/api/config/llm`，L784–799）——支持运行时切换
- CCCC Native 工作组管理（`/api/cccc-native/*`，L802–867）——启动、停止、状态查看
- 评测系统 API（`/api/evaluations/*`，L614–722）——创建待评测、提交评测、统计查询
- 演化报告 API（`/api/evolution/*`，L726–781）——报告生成与缓存
- 健康检查（`/api/health`，L870–892）

**已废弃：**
- `POST /api/consultation`（L589–608）——返回 410 Gone，已迁移至 CCCC 工作组 API

**存在的问题：**
- 咨询链路入口已废弃但新入口（CCCC 工作组 API）不在本文件中，链路的完整可追溯性被分散
- 记忆操作的错误处理使用 `_safe_*` 包装函数（L255–282），错误信息返回给前端但不记录到 trace
- 无 request_id / session_id 生成和传递
- 无中间件级别的请求追踪

### 6.2 工作流引擎 (`workflow.py`)

**已实现且可用：**
- 多 agent 并发调用（`ThreadPoolExecutor`，L52–63）
- 串行调用备选路径（`enable_parallel=False`，L64–68）
- 记忆上下文构建（`memory_agent.build_agent_context()`，L46–49）
- 专家意见收集与传递（L70–73）
- Primary Agent 汇总（L75–79）
- 事实提取与记忆写回（L88–98）
- 咨询记录存储（L101–106）
- 处理时间计算（L108，L118）
- 批处理支持（`process_batch()`，L136–149）

**存在的问题：**

| 问题 | 严重程度 | 位置 |
|------|---------|------|
| 专家并发调用无 try-except 保护，单个 agent 超时会导致整个请求失败 | **高** | L58–63 |
| 路由策略硬编码为固定三路（pharmacist + nutritionist + doctor），无动态路由 | 中 | L54–57 |
| 无 Safety Gate 环节——汇总输出直接返回，无安全拦截 | **高** | L75–80 |
| 无 request_id / session_id 生成 | 中 | 全文件 |
| 分步耗时不记录，只有总耗时 | 中 | L108 |
| 记忆写回失败不影响返回但也不记录错误 | 中 | L94–98 |
| Mock/Real 模式在构造时一次性决定，不支持运行时切换或单 agent 粒度降级 | 低 | L20–35 |

### 6.3 Agent 体系

**架构概述：**
- `BaseAgent` → 提供 LLM 调用、prompt 构建、响应格式化
- `MockAgent` → 提供无需 LLM 的硬编码响应
- 四个具体 Agent：Primary（主治医生/协调者）、Pharmacist（药剂师）、Nutritionist（营养师）、Doctor（代谢病医生）
- 每个 Agent 同时提供 `process()`（异步）和 `process_sync()`（同步）接口

**当前温度设置：**
| Agent | Temperature | 合理性 |
|-------|------------|--------|
| Primary | 0.7 | 偏高——协调者应更确定性 |
| Pharmacist | 0.5 | 合理——用药建议需要准确性 |
| Nutritionist | 0.7 | 合理——饮食建议可适度灵活 |
| Doctor | 0.3 | 合理——诊疗建议需要高确定性 |

### 6.4 记忆系统

**已实现且可用：**
- Memory Palace 全委托架构（无本地三层记忆）
- URI 体系：`patients/{patient_id}/{category}/*`
- 优先级体系：SAFETY_ALERT(0) → CORE_PROFILE(1) → RECENT_KEY_EVENT(2) → CONSULTATION(3) → AUXILIARY(4) → LOW_PRIORITY(5)
- 事实提取：基于关键词的类别检测（glucose / medication / diet / exercise / complication / safety）
- Disclosure 条件：每条记忆附带披露条件描述

**存在的问题：**
- 事实提取完全基于关键词匹配，无 LLM 辅助的语义理解
- 无记忆容量管理和过期策略
- 跨患者信息隔离依赖路径前缀，无额外权限控制

---

## 7. 验收标准

### 7.1 能跑通一条完整在线咨询链路

- [ ] 提交 patient_id + query，系统返回包含 `primary_response` 的结构化结果
- [ ] 链路经过：记忆检索 → 专家路由 → 并发调用 → 汇总 → 安全检查 → 记忆写回
- [ ] 链路中每一步都有可检查的中间输出
- [ ] 在 LLM 不可用时自动降级到 mock 模式，链路仍可跑通
- [ ] 在 Memory Palace 不可达时链路仍可跑通（降级）

### 7.2 关键决策可追踪

- [ ] 每轮咨询产生 trace，包含第 5.2 节定义的完整字段
- [ ] Trace 可通过 request_id 检索
- [ ] 路由决策有记录（即使当前是固定路由）
- [ ] 各专家的输入输出和耗时可独立查看
- [ ] 安全检查结果有记录（即使当前是 pass-through）

### 7.3 失败路径不是静默吞掉

- [ ] 单个专家超时不导致整个请求失败
- [ ] 记忆写回失败有显式错误记录
- [ ] LLM 不可用时有明确的模式切换日志
- [ ] 所有 `try-except` 块中的异常都被记录，不存在空 `except: pass`
- [ ] 前端可获知当前是否处于降级状态

### 7.4 运行行为与文档描述一致

- [ ] 本文档第 3 节描述的输入/输出结构与代码实际一致
- [ ] 本文档第 4 节描述的异常处理策略在代码中有对应实现
- [ ] 文档中标记为"未实现"的功能在代码中确实不存在
- [ ] 文档中标记为"已实现"的功能经过测试确认可用

### 7.5 Mock 能力和真实能力边界清楚

- [ ] Mock 模式和 Real 模式的行为差异有文档说明
- [ ] 响应中始终包含 `mode` 字段（"mock" 或 "llm"）
- [ ] Mock 输出与 Real 输出遵循相同的结构约定
- [ ] 评测结果区分 mock 评测和 real 评测
- [ ] Mock agent 的硬编码文本在医学上合理

### 7.6 上层界面能基于后端数据做有效审阅

- [ ] 后端提供的 trace 数据足以让审阅者理解本次咨询的完整过程
- [ ] 评测 API 支持按患者、按状态、按时间筛选
- [ ] 记忆 API 支持树形浏览和搜索，审阅者可检查记忆写回是否合理
- [ ] 健康检查 API 可让运维人员快速判断系统状态
- [ ] 演化报告 API 可展示跨版本的质量趋势

---

## 附录 A：需要优先修复的问题

按优先级排序：

1. **[P0] 专家并发调用无异常保护** — `workflow.py` L58–63，单个 agent 超时会抛异常导致整个请求 500
2. **[P0] 无 Safety Gate** — 最终输出未经安全审查直接返回用户
3. **[P1] 无 request_id / session_id** — 无法追踪和关联请求
4. **[P1] 无结构化 trace** — 当前返回的 dict 缺少关键追踪字段
5. **[P2] 记忆写回错误无日志** — 写回失败被静默跳过
6. **[P2] 无分步耗时记录** — 只有总耗时，无法定位性能瓶颈
7. **[P3] 路由策略不可配置** — 固定三路，无法根据问题类型动态路由
8. **[P3] 事实提取无语义理解** — 纯关键词匹配，遗漏率高

## 附录 B：文件索引

| 文件 | 职责 |
|------|------|
| `api_server.py` | FastAPI REST 服务，所有 HTTP 端点 |
| `src/agents/workflow.py` | 多智能体工作流编排 |
| `src/agents/base_agent.py` | Agent 基类 + Mock 基类 |
| `src/agents/primary_agent.py` | 主治医生/协调者 Agent |
| `src/agents/pharmacist_agent.py` | 药剂师 Agent |
| `src/agents/nutritionist_agent.py` | 营养师 Agent |
| `src/agents/doctor_agent.py` | 代谢病医生 Agent |
| `src/memory/memory_agent.py` | Memory Palace 适配器 |
| `src/memory/palace_client.py` | Memory Palace HTTP 客户端 |
| `src/evolution/evaluator.py` | 评测 Agent（含安全检查逻辑） |
| `src/evolution/evaluation_service.py` | 人类医生评测服务 |
| `src/evolution/optimizers.py` | Prompt/Memory 优化器 |
| `src/cccc_native/runtime_manager.py` | CCCC 工作组运行时管理 |
