# CCCC 可视化界面集成方案

## 目标
利用 CCCC 自带 Web UI，展示血糖管理 Agent 自进化系统的评测结果和运行状态。

---

## CCCC Web UI 能力分析

基于 `cccc_medical-main/web/` 目录：

### 已有功能
- Agent 管理界面（创建、配置、监控）
- 消息/对话界面
- 状态展示
- 配置文件管理

### 可扩展点
- 通过标准化数据格式（JSON/CSV）与 UI 对接
- 利用 CCCC 的 capability 系统注册可视化组件
- 使用 Web UI 的图表库展示趋势数据

---

## 集成方案设计

### 方案 A: 数据文件对接（推荐）

**思路**: 系统生成标准化数据文件，用户通过 CCCC Web UI 上传或查看

**数据输出**: 
```
data/
├── evaluation/
│   ├── summary.json           # 评测摘要
│   ├── iteration_history.csv  # 迭代历史
│   └── agent_performance.json # Agent 表现
└── evolution/
    ├── prompt_changes.json    # 提示词变更
    └── memory_changes.json    # 记忆变更
```

**UI 展示**:
- 评测得分仪表板
- 迭代趋势图
- Agent 对比雷达图

---

### 方案 B: CCCC Capability 集成

**思路**: 将可视化作为 CCCC capability 注册，直接在 UI 中调用

**实现**:
1. 创建 `capability/visualization/` 模块
2. 注册到 CCCC capability 系统
3. Web UI 自动加载可视化组件

---

## 推荐实施方案

采用 **方案 A + 方案 B 混合**

### 阶段 1: 数据标准化（kimi-3）
1. 整理现有输出格式
2. 设计供 UI 消费的数据结构
3. 实现数据导出脚本

### 阶段 2: UI 配置模板（kimi-2）
1. 设计 CCCC Web UI 配置
2. 创建 dashboard 布局模板
3. 配置图表组件

### 阶段 3: Capability 封装（kimi-1）
1. 封装为 CCCC capability
2. 实现 UI 事件响应
3. 集成到主系统

---

## 数据接口设计

### 1. 评测摘要 (evaluation_summary.json)
```json
{
  "timestamp": "2026-03-25T00:54:07",
  "overall_score": 8.30,
  "dimensions": {
    "medical_accuracy": 8.64,
    "safety": 7.92,
    "completeness": 8.44,
    "personalization": 7.80,
    "consistency": 8.72
  },
  "category_scores": {
    "medication": 8.18,
    "lifestyle": 8.54,
    "complication": 8.46
  },
  "safety_critical": {
    "total": 17,
    "passed": 5,
    "pass_rate": 29.4
  }
}
```

### 2. 迭代历史 (iteration_history.csv)
```csv
iteration,timestamp,overall_score,medical_accuracy,safety,completeness,personalization,consistency
0,2026-03-25T00:54:07,8.30,8.64,7.92,8.44,7.80,8.72
1,2026-03-25T00:55:00,8.35,8.70,8.00,8.50,7.85,8.75
2,2026-03-25T00:56:00,8.40,8.75,8.10,8.55,7.90,8.80
```

### 3. Agent 表现 (agent_performance.json)
```json
{
  "agents": [
    {
      "agent_id": "pharmacist",
      "name": "药剂师",
      "avg_score": 8.25,
      "test_count": 8,
      "strengths": ["药物剂量", "禁忌症识别"],
      "weaknesses": ["新药信息"]
    }
  ]
}
```

### 4. 提示词变更 (prompt_evolution.json)
```json
{
  "iterations": [
    {
      "iteration": 1,
      "agent_id": "pharmacist",
      "changes": [
        {"type": "added", "content": "增加肾功能评估要求"}
      ],
      "before_score": 7.5,
      "after_score": 8.2
    }
  ]
}
```

---

## UI 展示设计

### 页面 1: 评测概览 Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  总体得分: 8.30/10                     [趋势图]          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │医学 8.64│ │安全 7.92│ │完整 8.44│ │个性 7.80│       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────┤
│  [类别得分柱状图]                                        │
├─────────────────────────────────────────────────────────┤
│  Agent 表现雷达图                                        │
└─────────────────────────────────────────────────────────┘
```

### 页面 2: 迭代分析
```
┌─────────────────────────────────────────────────────────┐
│  [得分趋势折线图]  迭代 0 → 1 → 2 → 3                   │
├─────────────────────────────────────────────────────────┤
│  提示词变更历史                                          │
│  - 迭代 1: pharmacist +肾功能评估 (7.5→8.2)             │
│  - 迭代 2: nutritionist +饮食示例 (7.8→8.3)             │
└─────────────────────────────────────────────────────────┘
```

### 页面 3: 测试详情
```
┌─────────────────────────────────────────────────────────┐
│  筛选: [全部] [medication] [complication] ...            │
├─────────────────────────────────────────────────────────┤
│  TC001 │ medication │ 8.10 │ ⚠️ 安全关键               │
│  TC002 │ lifestyle  │ 8.25 │                            │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 分工安排

| 任务 | 负责人 | 交付物 | 工期 |
|------|--------|--------|------|
| 数据标准化 | kimi-3 | 4 个标准数据文件 | 2h |
| UI 配置模板 | kimi-2 | dashboard 配置文件 | 2h |
| Capability 封装 | kimi-1 | capability 模块 | 2h |
| 集成测试 | 全体 | UI 展示验证 | 1h |

**总计**: 约 7 小时

---

## 实施步骤

### Step 1: 数据标准化（kimi-3）
```bash
# 运行数据导出
python tests/export_for_ui.py
# 生成: data/ui/*.json, data/ui/*.csv
```

### Step 2: UI 配置（kimi-2）
```bash
# 创建 CCCC Web UI 配置
web/src/config/dashboard.json
web/src/components/EvaluationDashboard.vue
```

### Step 3: Capability 封装（kimi-1）
```bash
# 注册 capability
src/capabilities/visualization/
```

### Step 4: 验证
```bash
# 启动 CCCC Web UI
# 访问 dashboard
# 验证数据展示
```

---

## 优先级

1. **P0**: 数据标准化（立即开始）
2. **P1**: UI 配置模板
3. **P2**: Capability 封装
4. **P3**: 高级交互（可选）

---

*方案设计: kimi-3*  
*待确认: 是否按此方案执行？*
