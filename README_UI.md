# 血糖管理系统 - UI 使用指南

## 系统架构

```
用户浏览器
    ↓
CCCC Web UI (http://localhost:8848)
    ↓
MedicalTab (新增血糖管理模块)
    ├── PatientList - 患者列表
    ├── PatientDetail - 患者详情 + 血糖趋势
    ├── ConsultationPanel - 专家咨询
    └── EvolutionReport - 自进化报告
    ↓
后端 API (http://localhost:8001)
    ├── GET /api/patients - 患者列表
    ├── GET /api/patients/{id} - 患者详情
    ├── POST /api/consultation - 提交咨询
    ├── GET /api/evolution/report - 自进化报告
    └── GET /api/evolution/timeline - 进化时间线
    ↓
血糖管理系统核心
    ├── 4 Expert Agents (主治医生/药剂师/营养师/代谢病医生)
    ├── Memory Palace (记忆管理)
    └── Self-Evolution Loop (自进化)
```

## 启动步骤

### 1. 启动后端 API 服务

```bash
cd H:\project\cccc_test
python api_server.py
# 服务将运行在 http://localhost:8001
```

### 2. 启动 CCCC Web UI

```bash
cd cccc_medical-main\web
npm install  # 首次运行
npm run dev
# 访问 http://localhost:5173
```

### 3. 访问血糖管理模块

在 CCCC Web UI 中，点击新增的 **"Medical"** Tab，进入血糖管理模块。

## 功能说明

### 患者列表页
- 显示所有 50 名患者的基本信息
- 血糖概览卡片展示最近血糖趋势
- 点击患者查看详情

### 患者详情页
- 血糖历史记录表
- GlucoseChart 可视化趋势图
- 相关记忆展示

### 咨询面板
- 输入健康问题
- 4 个专家 Agent 分别给出建议
- 综合评分展示（医学准确性/安全性/完整性/个性化/一致性）

### 自进化报告页
- 总体评分：8.30/10
- 4 轮迭代改进历史
- 各维度能力雷达图
- Agent 表现对比

## API 文档

### 获取患者列表
```http
GET http://localhost:8001/api/patients
```

**响应示例：**
```json
[
  {
    "id": "PAT_bjhl2nvy9f",
    "name": "...",
    "age": 39,
    "gender": "男",
    "glucose_history": [
      {"date": "", "value": 5.6, "type": ""},
      ...
    ]
  }
]
```

### 提交咨询
```http
POST http://localhost:8001/api/consultation
Content-Type: application/json

{
  "patient_id": "PAT_bjhl2nvy9f",
  "query": "我的血糖控制得怎么样？"
}
```

**响应示例：**
```json
{
  "query": "我的血糖控制得怎么样？",
  "primary_response": "...",
  "expert_opinions": {
    "pharmacist": "...",
    "nutritionist": "...",
    "doctor": "..."
  },
  "evaluation_score": {
    "medical_accuracy": 8.5,
    "safety": 7.8,
    "overall": 8.0
  }
}
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| API 连接失败 | 确认 `python api_server.py` 已运行 |
| 患者数据为空 | 检查 `data/patient_structured/` 目录 |
| 前端无法加载 | 确认 CCCC Web UI 已启动 |

## 测试验证

运行自动化测试：
```bash
python test_api.py
python integration_test.py
```

## 项目文件结构

```
cccc_test/
├── api_server.py              # 后端 API
├── test_api.py                # API 测试
├── integration_test.py        # 集成测试
├── README_UI.md               # 本文件
├── src/                       # 核心系统代码
│   ├── agents/                # 4 Expert Agents
│   ├── evolution/             # 自进化系统
│   ├── memory/                # 记忆管理
│   └── workflow/              # 工作流编排
└── cccc_medical-main/web/src/
    └── pages/medical/         # 前端页面
        ├── MedicalTab.tsx
        ├── PatientList.tsx
        ├── PatientDetail.tsx
        ├── ConsultationPanel.tsx
        └── EvolutionReport.tsx
```

---

**系统状态：** 所有功能已就绪，可进行完整测试。
