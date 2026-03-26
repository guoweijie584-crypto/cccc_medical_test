# 阶段四输出格式规范

## 概述
阶段四评测结果输出结构化数据（JSON/CSV），供 CCCC Web 界面消费。

---

## 输出文件

### 1. 评测结果 JSON
**文件名**: `evaluation_results_{timestamp}.json`

```json
{
  "metadata": {
    "run_id": "run_20240324_154500",
    "timestamp": "2024-03-24T15:45:00+08:00",
    "iteration": 3,
    "total_cases": 25,
    "agent_version": "v1.2.0"
  },
  "summary": {
    "overall_score": 7.8,
    "medical_accuracy_avg": 8.2,
    "safety_avg": 9.0,
    "completeness_avg": 7.5,
    "personalization_avg": 7.0,
    "consistency_avg": 8.0,
    "category_scores": {
      "medication": 8.1,
      "lifestyle": 7.5,
      "glucose_monitoring": 8.0,
      "complication": 7.8,
      "nutrition": 7.9,
      "exercise": 7.6,
      "special_population": 8.2,
      "emergency": 9.0
    }
  },
  "results": [
    {
      "test_id": "TC001",
      "category": "medication",
      "question": "我刚确诊2型糖尿病...",
      "expected_points": [...],
      "agent_response": "...",
      "scores": {
        "medical_accuracy": 8.5,
        "safety": 9.0,
        "completeness": 7.0,
        "personalization": 7.5,
        "consistency": 8.0,
        "total": 8.0
      },
      "evaluation": {
        "matched_points": [...],
        "missed_points": [...],
        "hallucinations": [],
        "safety_warnings": []
      },
      "memory_usage": {
        "retrieved_memories": 3,
        "relevance_score": 0.85,
        "stored_new_memories": 1
      }
    }
  ]
}
```

---

### 2. 迭代对比 CSV
**文件名**: `iteration_comparison.csv`

| 字段 | 类型 | 说明 |
|------|------|------|
| iteration | int | 迭代轮次 |
| timestamp | string | 时间戳 |
| overall_score | float | 总分 (0-10) |
| medical_accuracy | float | 医学准确性均分 |
| safety | float | 安全性均分 |
| completeness | float | 完整性均分 |
| personalization | float | 个性化均分 |
| consistency | float | 一致性均分 |
| pass_count | int | 通过用例数 |
| fail_count | int | 失败用例数 |
| improvement | float | 相比上轮的改进 |

---

### 3. Agent 表现对比 JSON
**文件名**: `agent_performance.json`

```json
{
  "agents": [
    {
      "agent_id": "pharmacist",
      "name": "药剂师 Agent",
      "test_cases_count": 8,
      "average_score": 8.2,
      "category_scores": {
        "medication": 8.5,
        "drug_interaction": 8.0
      },
      "strengths": ["药物剂量准确", "禁忌症识别"],
      "weaknesses": ["新药信息滞后"]
    },
    {
      "agent_id": "nutritionist",
      "name": "营养师 Agent",
      "test_cases_count": 5,
      "average_score": 7.8,
      "category_scores": {
        "nutrition": 8.0,
        "dietary_structure": 7.5
      },
      "strengths": ["饮食建议详细"],
      "weaknesses": ["个性化不足"]
    }
  ]
}
```

---

### 4. 提示词优化日志 JSON
**文件名**: `prompt_evolution_log.json`

```json
{
  "iterations": [
    {
      "iteration": 1,
      "timestamp": "2024-03-24T15:00:00",
      "agent_id": "pharmacist",
      "changes": [
        {
          "type": "added",
          "content": "增加肾功能评估要求",
          "reason": "TC011 测试发现缺失肾功能检查"
        }
      ],
      "before_score": 7.5,
      "after_score": 8.2
    }
  ]
}
```

---

### 5. 记忆优化日志 JSON
**文件名**: `memory_evolution_log.json`

```json
{
  "iterations": [
    {
      "iteration": 1,
      "timestamp": "2024-03-24T15:00:00",
      "operations": [
        {
          "type": "add",
          "memory_id": "mem_001",
          "content": "患者肾功能：eGFR 45",
          "reason": "补充缺失的患者信息"
        },
        {
          "type": "update",
          "memory_id": "mem_002",
          "changes": "更新用药剂量",
          "reason": "剂量错误纠正"
        }
      ],
      "memory_count_before": 12,
      "memory_count_after": 13
    }
  ]
}
```

---

## CCCC Web 界面消费方式

### 趋势图数据
```javascript
// 从 iteration_comparison.csv 加载
// X轴: iteration
// Y轴: overall_score, medical_accuracy, safety...
```

### 提示词 Diff 展示
```javascript
// 从 prompt_evolution_log.json 加载
// 展示 added/removed/modified 的段落
```

### 记忆变化时间线
```javascript
// 从 memory_evolution_log.json 加载
// 按时间展示 add/update/delete 操作
```

### Agent 表现雷达图
```javascript
// 从 agent_performance.json 加载
// 维度: medical_accuracy, safety, completeness, personalization, consistency
```

---

## 输出目录结构
```
tests/output/
├── {run_id}/
│   ├── evaluation_results.json      # 完整评测结果
│   ├── iteration_comparison.csv     # 迭代对比
│   ├── agent_performance.json       # Agent 表现
│   ├── prompt_evolution_log.json    # 提示词优化
│   ├── memory_evolution_log.json    # 记忆优化
│   └── raw_responses/               # 原始回答
│       ├── TC001_response.txt
│       ├── TC002_response.txt
│       └── ...
```
