# 评测体系重设计文档

> 状态：设计草案 | 作者：claude-dev (foreman) | 日期：2026-04-07

## 1. 设计目标

**摒弃 Agent/LLM 自评，引入真实医生的人工评价标准。**

### 1.1 用户明确的核心原则

> "agent 去评价永远都是错的，我们为真正的医生引入评价的标准"

评价维度简化为离散标签：**好 / 坏 / 中立 / 错误（需额外评价）**

### 1.2 当前问题

现有 `src/evolution/evaluator.py` 的设计存在根本性问题：
- `EvaluatorAgent` 让 LLM 给自己打分（0-10 分五维度）— **不可信**
- 规则评估 (`_evaluate_with_rules`) 过于简陋（检查关键词/长度）— **不准确**
- 复杂的加权综合分数 — **假精确**
- 没有人类医生参与的通道 — **核心缺失**

### 1.3 目标状态

- 评价由**真实医生**完成
- 评价维度简化为**离散标签**，而非虚假的精细打分
- 系统提供**评价收集接口**，方便医生快速标注
- 评价数据可回流到自进化优化环节

## 2. 评价标签体系

### 2.1 核心标签

| 标签 | 含义 | 后续动作 |
|------|------|---------|
| `GOOD` (好) | 回答准确、安全、有帮助 | 记录为正样本，用于强化当前策略 |
| `BAD` (坏) | 回答有明显问题（不准确、不完整、不合适） | 触发归因分析 + 优化 |
| `NEUTRAL` (中立) | 回答可以接受但无特别价值 | 记录，不触发优化 |
| `ERROR` (错误/需额外评价) | 存在医学安全风险或无法判断 | 标记为高优先级，需要详细审查 |

### 2.2 扩展维度（可选，医生可以不填）

| 维度 | 选项 | 说明 |
|------|------|------|
| 安全性 | 安全 / 有风险 / 危险 | 是否存在医学安全隐患 |
| 个性化 | 有 / 无 | 是否结合了患者具体情况 |
| 建议方向 | 正确 / 部分正确 / 错误 | 医学建议的方向性判断 |

扩展维度是可选的——核心标签（好/坏/中立/错误）是必填的最小集。

### 2.3 自由文本备注

每条评价可以附带可选的文本备注，用于：
- 医生说明为什么打了这个标签
- 指出具体哪部分有问题
- 提供正确的建议方向

## 3. 系统架构

### 3.1 数据流

```
患者提问 → 多Agent协作生成回答 → 回答呈现给患者
                                      ↓
                              系统同时记录待评价记录
                                      ↓
                        医生在评价界面上进行标注
                              (好 / 坏 / 中立 / 错误)
                                      ↓
                        评价数据存入评价记录存储
                                      ↓
                    自进化模块根据评价数据进行优化
```

### 3.2 核心数据结构

```python
@dataclass
class HumanEvaluation:
    """一条人类医生的评价记录"""
    evaluation_id: str          # 唯一标识
    patient_id: str             # 患者ID
    query: str                  # 患者原始问题
    response: str               # 系统回答
    expert_opinions: Dict[str, str]  # 各专家Agent的意见
    
    # 核心评价
    label: str                  # GOOD / BAD / NEUTRAL / ERROR
    
    # 可选扩展
    safety: Optional[str] = None        # safe / risky / dangerous
    personalized: Optional[bool] = None  # True / False
    advice_direction: Optional[str] = None  # correct / partial / wrong
    
    # 备注
    reviewer_notes: str = ""    # 医生的自由文本备注
    reviewer_id: str = ""       # 评价医生标识
    
    # 元信息
    timestamp: str = ""         # 评价时间
    consultation_timestamp: str = ""  # 原始咨询时间
```

### 3.3 评价记录存储

评价记录也存入 Memory Palace：

```
medical://
└── evaluations/
    ├── pending/           # 待评价记录
    │   └── {eval_id}
    ├── completed/         # 已评价记录
    │   └── {eval_id}
    └── summary/           # 评价统计摘要
```

## 4. 重构方案

### 4.1 现有代码变更

**`src/evolution/evaluator.py`（大幅重构）**

从 `EvaluatorAgent`（LLM 自评）变成 `EvaluationService`（人工评价服务）：

```python
class EvaluationService:
    """人工评价管理服务。
    
    不做任何自动评分。
    负责创建待评价记录、收集医生评价、查询评价结果。
    """
    
    def create_pending_evaluation(self, patient_id, query, response, expert_opinions):
        """创建一条待评价记录。
        
        每次对话完成后自动调用，
        将 query + response + expert_opinions 打包为待评价记录。
        """
        
    def submit_evaluation(self, evaluation_id, label, **optional_fields):
        """医生提交一条评价。
        
        label 必填：GOOD / BAD / NEUTRAL / ERROR
        其余字段可选。
        """
        
    def get_pending_evaluations(self, limit=20):
        """获取待评价列表。
        
        供医生评价界面调用。
        """
        
    def get_evaluation_stats(self, patient_id=None, time_range=None):
        """获取评价统计。
        
        例如：最近50条中，GOOD 占比多少、BAD 占比多少。
        """
        
    def get_bad_evaluations(self, limit=10):
        """获取最近的 BAD/ERROR 评价。
        
        供自进化模块分析使用。
        """
```

**`src/evolution/analyzer.py`（更新触发条件）**

- 原来靠 LLM 评分低于阈值触发
- 改为靠人工评价中出现 `BAD` 或 `ERROR` 标签触发

**`src/evolution/self_evolution_loop.py`（更新数据源）**

- 优化决策的依据从 LLM 评分改为人工评价标签 + 备注

### 4.2 去掉的内容

- `ResponseScore` / `MemoryScore` 多维度打分数据结构
- `_evaluate_with_rules` / `_evaluate_with_llm` 自动评估方法
- `_evaluate_memory_with_rules` / `_evaluate_memory_with_llm`
- 加权综合分数计算
- LLM 评估提示词构建

### 4.3 保留的内容

- `EvaluationReport` 概念（但字段大幅简化）
- `evaluation_history` 历史记录（但内容改为人工评价）
- 与 Memory Palace 的存储集成

### 4.4 新增内容

- 评价记录的 CRUD API（供前端/API 调用）
- 待评价队列管理
- 评价统计查询
- `BAD` / `ERROR` 评价的自动通知（通知自进化模块）

## 5. API 接口设计

### 5.1 评价管理 API

```
POST   /api/evaluations/pending      # 创建待评价记录（系统自动调用）
GET    /api/evaluations/pending      # 获取待评价列表（医生界面调用）
POST   /api/evaluations/{id}/submit  # 提交评价（医生操作）
GET    /api/evaluations/stats        # 获取评价统计
GET    /api/evaluations/bad          # 获取 BAD/ERROR 评价（自进化使用）
GET    /api/evaluations/{id}         # 获取单条评价详情
```

### 5.2 请求/响应示例

**提交评价：**
```json
POST /api/evaluations/{id}/submit
{
    "label": "BAD",
    "safety": "risky",
    "advice_direction": "partial",
    "reviewer_notes": "胰岛素剂量建议偏高，应该考虑患者肾功能",
    "reviewer_id": "dr_zhang"
}
```

**评价统计：**
```json
GET /api/evaluations/stats
{
    "total": 120,
    "good": 78,
    "bad": 15,
    "neutral": 22,
    "error": 5,
    "good_rate": 0.65,
    "needs_attention": 20
}
```

## 6. 实现步骤

1. **Step 1**：定义 `HumanEvaluation` 数据结构 + 存储方案
2. **Step 2**：重构 `evaluator.py` → `evaluation_service.py`
3. **Step 3**：实现 API 接口（在 `api_server.py` 中）
4. **Step 4**：更新 `analyzer.py` 和 `self_evolution_loop.py` 的触发条件
5. **Step 5**：更新 workflow 集成 — 每次对话自动创建待评价记录
6. **Step 6**：更新测试

## 7. 与自进化的衔接

评价数据如何驱动自进化：

| 评价标签 | 自进化动作 |
|----------|-----------|
| `GOOD` | 记录为正样本，强化当前 prompt/memory 策略 |
| `BAD` | 触发 Analyzer 归因 → 路由到 Prompt/Memory Optimizer |
| `NEUTRAL` | 不触发，仅记录 |
| `ERROR` | 高优先级归因 + 人工审查 flag |

Analyzer 拿到 BAD 评价后的归因依据：
- 医生的 `reviewer_notes`（最重要的信号）
- `safety` / `advice_direction` 扩展标签
- 原始 query + response + expert_opinions 对照分析

## 8. 风险与注意事项

1. **医生参与成本**：简化标签降低了标注门槛，但仍需医生愿意参与
2. **评价延迟**：人工评价不是实时的，自进化优化有滞后
3. **样本量**：初期评价数据少，自进化信号弱——可以先积累再触发
4. **评价者一致性**：不同医生可能标准不同——通过简化标签减轻此问题
