# 血糖管理智能助手 — MVP 产品需求文档

> 版本：v1.1 | 日期：2026-04-08 | 作者：claude-dev (foreman)
> 状态：**待审核（claude-1 + claude-2）**
> 变更说明：整合 claude-1 审核意见 + 后端配套要求 + 用户反馈

---

## 一、总体概述

### 1.1 产品定位

一个**独立的、面向用户友好的血糖管理智能助手 MVP 产品**。

- 用户（糖尿病患者）通过与 AI Agent **对话**来获取血糖管理建议（线1）
- 系统通过 **Memory Palace**（记忆宫殿）管理用户的健康记忆，并提供可视化管理界面（线2）
- **医生/评审员**对系统回答进行人工评价，评价数据驱动系统的自进化优化（线3）

三线独立运行，互不耦合。

### 1.2 与 CCCC 开发工作组的关系

本产品是一个**独立的 Web 应用**，不是 CCCC Web UI 的一部分。

```
┌────────────────────────┐   ┌────────────────────────┐
│ 产品界面 (medical-ui/) │   │ CCCC 协作界面 (:8858)  │
│ /medical/              │   │ /ui/                   │
│ → 用户/评委看到的       │   │ → Agent 开发协作用      │
│ → 本文档的交付物        │   │ → 不受影响             │
└───────────┬────────────┘   └────────────────────────┘
            ↕ HTTP
┌────────────────────────────────────────────────────┐
│               API Server (:8001)                    │
│               FastAPI + Python                      │
├────────────────────┬───────────────────────────────┤
│  Memory Palace     │   Multi-Agent Workflow         │
│  (:8000)           │   + Evaluation Service         │
│  记忆存储与治理     │   + HumanEval Evolution Loop  │
└────────────────────┴───────────────────────────────┘
```

### 1.3 用户角色

| 角色 | 说明 | 核心功能 |
|------|------|---------|
| **患者** | 产品的主要使用者 | 和 Agent 对话咨询、查看个人健康档案 |
| **医生/评审员** | 对系统回答进行评价 | 评价管理、评价统计、触发自进化优化 |

### 1.4 技术选型

| 技术 | 用途 | 版本 |
|------|------|------|
| React 18 | UI 框架 | ^18.3 |
| TypeScript | 类型安全 | ^5.7 |
| Vite | 构建工具 | ^6.0 |
| Tailwind CSS | 样式系统 | ^3.4 |
| framer-motion | 动效引擎 | latest |
| zustand | 状态管理 | ^5.0 |
| recharts | 图表库（血糖趋势图） | latest |

> **v1.1 变更**：新增 recharts（轻量 React 图表库），用于患者档案中的血糖趋势图。

### 1.5 项目结构

```
medical-ui/
├── index.html
├── package.json
├── vite.config.ts                  # 注意：base 必须配为 '/medical/'
├── tailwind.config.ts
├── tsconfig.json
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx                    # 入口
    ├── App.tsx                     # 根组件（路由 + 布局）
    ├── api/
    │   └── client.ts              # API 请求封装（含错误处理）
    ├── stores/
    │   ├── patientStore.ts        # 全局患者选择状态 ★ v1.1 新增
    │   ├── chatStore.ts           # 对话状态（含 localStorage 持久化）
    │   ├── memoryStore.ts         # 记忆数据状态
    │   └── evaluationStore.ts     # 评价数据状态
    ├── pages/
    │   ├── ChatPage.tsx           # 对话页（默认首页）
    │   ├── MemoryPalacePage.tsx   # 记忆宫殿页
    │   ├── EvaluationPage.tsx     # 评价管理页
    │   └── ProfilePage.tsx        # 患者档案页
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx       # 整体布局（侧边栏 + 内容区）
    │   │   ├── Sidebar.tsx        # 侧边导航栏（含患者选择器）
    │   │   └── Header.tsx         # 顶部标题栏（含当前患者信息）
    │   ├── chat/
    │   │   ├── ChatWindow.tsx     # 对话窗口
    │   │   ├── MessageBubble.tsx  # 单条消息气泡
    │   │   ├── MessageInput.tsx   # 消息输入框
    │   │   ├── ExpertOpinions.tsx # 专家意见折叠组件 ★ v1.1 新增
    │   │   └── AgentTyping.tsx    # Agent 正在输入动画
    │   ├── memory/
    │   │   ├── MemoryStarMap.tsx  # 记忆星图（Canvas 渲染）
    │   │   ├── MemoryDetail.tsx   # 记忆详情面板
    │   │   ├── MemorySearch.tsx   # 记忆搜索
    │   │   ├── MemoryCreate.tsx   # 新建记忆弹窗
    │   │   └── MemoryEmpty.tsx    # 空状态引导 ★ v1.1 新增
    │   ├── evaluation/
    │   │   ├── EvalStats.tsx      # 评价统计卡片
    │   │   ├── EvalCard.tsx       # 单条评价卡片（含 personalized 字段）
    │   │   ├── EvalPending.tsx    # 待评价列表
    │   │   ├── EvalHistory.tsx    # 历史评价
    │   │   └── EvolutionTrigger.tsx # 触发优化按钮 ★ v1.1 新增
    │   ├── profile/
    │   │   ├── PatientInfo.tsx    # 患者基础信息
    │   │   ├── GlucoseChart.tsx   # 血糖趋势图（recharts）
    │   │   └── MedicationList.tsx # 用药列表
    │   └── common/
    │       ├── ErrorToast.tsx     # 错误提示 ★ v1.1 新增
    │       └── LoadingSkeleton.tsx # 加载骨架屏
    └── styles/
        └── globals.css            # 全局样式
```

---

## 二、全局状态管理 ★ v1.1 新增章节

### 2.1 患者选择（patientStore）

所有页面共享"当前选中的患者"。

```typescript
// stores/patientStore.ts
interface PatientStore {
  patients: Patient[];
  selectedPatientId: string | null;
  loading: boolean;
  
  fetchPatients: () => Promise<void>;
  selectPatient: (id: string) => void;
  getSelectedPatient: () => Patient | null;
}
```

- **患者选择器**位于 Sidebar 底部或 Header 中
- 切换患者后，Chat / Memory / Evaluation / Profile 四个页面都自动刷新数据
- 初次进入时自动加载患者列表并选中第一个

### 2.2 对话状态（chatStore）

```typescript
interface ChatStore {
  messages: Message[];            // 当前对话消息列表
  isLoading: boolean;             // Agent 是否正在处理
  
  sendMessage: (query: string) => Promise<void>;
  clearMessages: () => void;
}
```

- 对话历史通过 **localStorage** 按患者 ID 持久化
- 切换患者时加载该患者的历史对话
- 刷新页面后对话恢复

### 2.3 API 请求封装（api/client.ts）

```typescript
// 通过 nginx 代理，/api/ 已指向 :8001
// 所以 base 为空字符串（不是 '/api'）
const API_BASE = import.meta.env.VITE_API_BASE || '';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, error.detail || 'Unknown error');
  }
  return response.json();
}
```

> **v1.1 变更**：API base URL 逻辑与 nginx 代理对齐（base 为空字符串）。增加结构化错误处理。

---

## 三、模块一：Chat 对话（线1 — 核心功能）

### 3.1 功能概述

用户通过对话界面与血糖管理 AI Agent 进行交流。这是产品的**核心入口**，用户打开产品后默认进入此页面。

### 3.2 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  🏥 血糖管理智能助手              患者：张三 · 58岁 · 2型   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Agent ──────────────────────────────────────────────┐   │
│  │ 您好！我是您的血糖管理助手。根据您的健康档案，您最近   │   │
│  │ 的空腹血糖控制在 7.2 mmol/L 左右，稍有偏高。          │   │
│  │ 有什么我可以帮您的吗？                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│                    ┌─ 用户 ─────────────────────────────┐   │
│                    │ 我最近血糖一直偏高，该怎么调整？     │   │
│                    └────────────────────────────────────┘   │
│                                                              │
│  ┌─ Agent ──────────────────────────────────────────────┐   │
│  │ 根据您的情况，我为您整合了多位专家的建议：             │   │
│  │                                                       │   │
│  │ 综合建议：建议您先调整饮食结构，同时预约一次...        │   │
│  │                                                       │   │
│  │ ▸ 查看专家详细意见                    ← 默认折叠      │   │
│  │  ┌────────────────────────────────────────────────┐   │   │
│  │  │ 💊 药剂师：考虑调整二甲双胍剂量...              │   │   │
│  │  │ 🥗 营养师：减少高GI食物摄入...                  │   │   │
│  │  │ 🏥 代谢医生：建议检查HbA1c水平...              │   │   │
│  │  └────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Agent 正在思考... ●●● ──────────────────────────────┐   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [输入您的健康问题...]                              [发送]  │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 功能需求

#### 3.3.1 对话消息展示
- 用户消息（右侧气泡，主色调）和 Agent 消息（左侧气泡，深色背景）
- Agent 回答结构：**综合建议在前**，专家详细意见默认折叠（点击展开）★ v1.1 变更
- 支持 Markdown 渲染（列表、加粗等）
- 消息带时间戳
- 对话历史通过 localStorage 持久化 ★ v1.1 新增

#### 3.3.2 消息输入
- 底部固定的输入框
- 支持回车发送、按钮发送
- 发送后输入框清空
- 发送中禁用输入（防重复提交）

#### 3.3.3 Agent 状态
- Agent 处理中显示"正在思考"动画（脉动圆点）
- 多 Agent 协作过程对用户透明

#### 3.3.4 对话与三线联动
- 系统自动读取患者的 Memory Palace 记忆作为上下文（线2→线1）
- 每轮对话完成后，系统自动提取事实并写入 Memory Palace（线1→线2）
- 每轮对话完成后，系统自动创建待评价记录（线1→线3）★ 需后端修复

#### 3.3.5 错误处理 ★ v1.1 新增
- 网络错误：显示 ErrorToast，提供重试按钮
- API 超时（多 Agent 处理可能较慢）：前端设 30s 超时，超时后提示"处理中，请稍候"
- 后端返回错误：显示错误信息

### 3.4 前后端对接

| API | 方法 | 状态 | 说明 |
|-----|------|------|------|
| `/api/consultation` | POST | ⚠️ 需修复 | 需补上 `create_pending_evaluation` 调用（线1→线3 断链） |
| `/api/patients/{id}` | GET | ✅ 就绪 | 获取当前患者信息 |
| `/api/patients/{id}/memories` | GET | ✅ 就绪 | 获取患者记忆 |

**后端修复项（P0）：**
- `/api/consultation` 完成后必须调用 `evaluation_service.create_pending_evaluation()` 自动创建待评价记录

**后端预留项（P2）：**
- `POST /api/consultation/stream` — SSE 流式响应，推送 Agent 处理各阶段状态（"正在收集专家意见..."→"药剂师已回复..."→"综合建议生成中..."）。MVP 阶段不实现，但需求需要记录。

### 3.5 视觉与交互要求

- 深色主题，医疗科技感
- 消息气泡有柔和阴影和圆角
- Agent "思考中" 动画流畅、有科技感
- 专家意见折叠/展开有平滑过渡动画
- 页面打开时有平滑的加载过渡

---

## 四、模块二：记忆宫殿（线2 — 视觉高光）

### 4.1 功能概述

以可视化方式展示和管理患者在 Memory Palace 中的所有健康记忆。这是本产品最核心的**视觉亮点**，需要做到"上帝管理记忆的感觉"，让评委眼前一亮。

### 4.2 页面布局

```
┌──────────────────────────────────────────────────────────────┐
│  🏛️ 记忆宫殿                                    [搜索🔍]    │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│ 患者选择    │        记忆星图（Canvas 全屏渲染）               │
│ (全局联动)  │                                                 │
│            │     ★ profile (金色大星)                        │
│ ● 张三     │    /  |  \                                      │
│ ○ 李四     │  ★   ★    ★                                    │
│            │ glucose medication diet                         │
│            │                                                 │
│ [+ 新建]   │   能量粒子在连接线上流动...                      │
│            │   星尘粒子漂浮在深空背景中...                     │
│            │                                                 │
│            ├─────────────────────────────────────────────────┤
│            │  📋 记忆详情（选中节点后展开）                    │
│            │  类别：血糖   优先级：2   活力：85%               │
│            │  内容：空腹血糖 7.2 mmol/L                       │
│            │  触发条件：当评估血糖控制情况时                   │
│            │  [编辑] [删除]                                   │
└────────────┴─────────────────────────────────────────────────┘

─── 无记忆时的空状态 ─────────────────────────────────
│                                                    │
│   🌌 记忆宫殿尚为空白                               │
│                                                    │
│   开始和AI助手对话后，系统将自动为您积累健康记忆。    │
│   您也可以手动添加记忆。                             │
│                                                    │
│   [开始对话]  [手动添加]                             │
──────────────────────────────────────────────────────
```

### 4.3 功能需求

#### 4.3.1 记忆星图可视化（Canvas 渲染，已有基础实现）
- **深空背景**：深蓝/紫渐变 + 120+ 颗实时闪烁的星尘粒子
- **中心枢纽**：紫色脉动光球，代表患者的记忆核心
- **记忆节点**：3D 感发光球体，径向渐变模拟球体光泽
  - 按类别着色：profile=金色, glucose=青色, medication=蓝色, diet=绿色, safety=红色, complication=橙色, consultation=紫色
  - 按 priority 决定大小（priority 0 = 最大）
  - 按 vitality 决定脉搏频率和亮度
- **能量脉络**：中心到节点的连线，带流动的发光粒子
- **交互**：悬停 tooltip、点击详情、搜索高亮
- **中文类别标签**：环绕在星图边缘

#### 4.3.2 记忆管理操作
- 搜索（350ms 防抖）
- 查看详情
- 新建记忆（类别/优先级/触发条件）
- 编辑记忆（内容/优先级/触发条件）
- 删除记忆（确认弹窗）

#### 4.3.3 空状态处理 ★ v1.1 新增
- 新患者无记忆时，显示引导提示而不是空白画布
- 引导"开始对话"（跳转 Chat）或"手动添加"

#### 4.3.4 降级处理 ★ v1.1 新增
- Memory Palace 服务不可达时，显示降级 UI（"记忆服务暂时不可用"）
- 检查后端返回的 `memoryStatus: "degraded"` 字段

### 4.4 前后端对接

| API | 方法 | 状态 | 说明 |
|-----|------|------|------|
| `/api/memory/tree/{patient_id}` | GET | ⚠️ 性能注意 | 递归 3 层，N+1 查询（P2 优化） |
| `/api/memory/search?q=&patient_id=&mode=hybrid` | GET | ⚠️ 需修复 | mode 默认值需改为 hybrid |
| `/api/memory/create` | POST | ✅ 就绪 | |
| `/api/memory/{path}` | PUT | ⚠️ 需修复 | 需支持 priority/disclosure 参数 |
| `/api/memory/{path}` | DELETE | ✅ 就绪 | |
| `/api/memory/stats?patient_id=` | GET | ⚠️ 性能注意 | O(patients×categories)（P2 优化） |

**后端修复项（P0）：**
- `/api/memory/search` — mode 默认值从 "keyword" 改为 "hybrid"
- `/api/memory/{path}` PUT — MemoryUpdateRequest 增加 `priority: Optional[int]` 和 `disclosure: Optional[str]`

### 4.5 视觉与交互要求

- **全产品视觉高光**，必须惊艳
- Canvas 渲染，60fps 流畅
- 深空主题统一
- 节点出现/消失有凝聚/碎裂动画
- tooltip 和详情面板有毛玻璃效果

---

## 五、模块三：人工评价系统（线3）

### 5.1 功能概述

供医生/评审员对系统的回答质量进行人工评价。评价数据驱动系统的自进化优化。

### 5.2 页面布局

```
┌──────────────────────────────────────────────────────────────┐
│  📋 评价管理                               待评价：12 条     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌── 统计概览（可按患者筛选）────────────────────────────┐   │
│  │ 总计: 120  ✅好: 78  ❌坏: 15  ➖中立: 22  ⚠️错误: 5 │   │
│  │ 好评率: 65%                    需关注: 20             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌── 待评价 ────────────────────────────────────────────┐   │
│  │  [患者P001] "我的血糖控制得怎么样？"                  │   │
│  │  系统回答: "根据您近期的血糖记录..."                   │   │
│  │  ▸ 展开查看完整回答和专家意见                         │   │
│  │                                                       │   │
│  │  [👍 好]  [👎 坏]  [➖ 中立]  [⚠️ 错误]              │   │
│  │                                                       │   │
│  │  ▸ 安全性: [安全] [有风险] [危险]          (可选)      │   │
│  │  ▸ 个性化: [是] [否]                       (可选) ★   │   │
│  │  ▸ 建议方向: [正确] [部分正确] [错误]      (可选)      │   │
│  │  ▸ 备注: [________________]                            │   │
│  │                                                [提交]  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌── 历史评价 ──────────────────────────────────────────┐   │
│  │  [全部] [好] [坏] [中立] [错误]    ← 筛选标签         │   │
│  │  ...                                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌── 自进化优化 ────────────────────────────────────────┐   │
│  │  BAD/ERROR 评价: 20 条                                │   │
│  │  [🔄 触发自进化优化]                    ★ v1.1 新增   │   │
│  │  最近优化: 2026-04-07 · 处理了 15 条 BAD 评价          │   │
│  │  → 3 个提示词优化 + 2 个记忆强化                       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 功能需求

#### 5.3.1 统计概览
- 8 张统计卡片
- 支持按患者筛选 ★ 需后端加 patient_id 过滤参数
- 提交评价后自动刷新

#### 5.3.2 待评价列表
- 展示所有待评价记录
- 可展开查看完整回答和专家意见
- 四个标签按钮：**好(GOOD) / 坏(BAD) / 中立(NEUTRAL) / 错误(ERROR)**
- 可选扩展字段：安全性、**个性化** ★ v1.1 补全、建议方向、备注
- 提交成功：toast 提示 + 列表刷新
- 提交失败：ErrorToast + 重试选项 ★ v1.1 新增

#### 5.3.3 历史评价
- 按标签筛选（全部/好/坏/中立/错误）
- 标签 badge、患者、问题、时间

#### 5.3.4 自进化优化触发 ★ v1.1 新增
- 显示当前 BAD/ERROR 评价累积数量
- "触发自进化优化"按钮（调用 `POST /api/evolution/human-driven`）
- 显示最近一次优化的结果摘要

### 5.4 前后端对接

| API | 方法 | 状态 | 说明 |
|-----|------|------|------|
| `/api/evaluations/pending` | GET | ⚠️ P1 优化 | 需加 patient_id 过滤参数 |
| `/api/evaluations/pending` | POST | ✅ 就绪 | 系统自动调用 |
| `/api/evaluations/{id}/submit` | POST | ✅ 就绪 | |
| `/api/evaluations/stats?patient_id=` | GET | ✅ 就绪 | |
| `/api/evaluations/bad` | GET | ✅ 就绪 | |
| `/api/evaluations/{id}` | GET | ✅ 就绪 | |
| `/api/evolution/human-driven` | POST | ✅ 就绪 | |
| `/api/evolution/report` | GET | ✅ 就绪 | 可用于展示优化历史 |

**后端修复项（P1）：**
- `/api/evaluations/pending` GET — 增加可选 `patient_id` 查询参数

---

## 六、模块四：患者档案

### 6.1 功能概述

展示当前患者的基础信息、血糖趋势图、用药列表。

### 6.2 功能需求

- 患者基础信息（姓名/年龄/性别/糖尿病类型/确诊时间/用药/并发症）
- 血糖趋势图（**recharts** 折线图，支持空腹/餐后/随机筛选）★ v1.1 明确图表库
- 血糖目标线标注（空腹 4.4-7.0, 餐后 <10.0）
- 血糖记录表（时间/类型/数值/状态标注）
- 用药列表

### 6.3 前后端对接

| API | 方法 | 状态 | 说明 |
|-----|------|------|------|
| `/api/patients` | GET | ✅ 就绪 | |
| `/api/patients/{id}` | GET | ✅ 就绪 | |

---

## 七、公共组件与 UI 规范

### 7.1 整体布局 (AppShell)

```
┌─────────┬────────────────────────────────────────────┐
│         │  Header（产品名 + 当前患者信息）             │
│  Side   ├────────────────────────────────────────────┤
│  bar    │                                            │
│         │  内容区域（根据路由切换）                    │
│  💬 对话 │                                            │
│  🏛️ 记忆 │                                            │
│  📋 评价 │                                            │
│  👤 档案 │                                            │
│         │                                            │
│ ─────── │                                            │
│ 患者选择 │  ★ v1.1: 患者选择器放在 Sidebar 底部       │
│ [张三 ▾] │                                            │
└─────────┴────────────────────────────────────────────┘
```

### 7.2 设计语言

- **主题**：深色主题为主
- **主色**：靛蓝 (#6366f1)
- **辅色**：青色 (#06b6d4)
- **强调色**：琥珀 (#f59e0b)
- **字体**：系统字体栈 + 等宽字体
- **圆角**：卡片 12px，按钮 8px
- **动效**：framer-motion 平滑过渡

### 7.3 错误处理规范 ★ v1.1 新增

- 所有 API 调用都必须有 try/catch
- 网络错误：ErrorToast（底部弹出，3 秒自动消失）
- 表单提交失败：内联错误提示 + 重试按钮
- 服务不可用：降级 UI（如 Memory Palace 不可达时）

---

## 八、后端修复清单 ★ v1.1 新增章节

### 8.1 P0 — 必须在前端开发前完成

| # | 文件 | 修改内容 | 工作量 |
|---|------|---------|--------|
| 1 | `api_server.py` | `/api/consultation` 完成后调用 `create_pending_evaluation()` | 5 行 |
| 2 | `api_server.py` | `/api/memory/{path}` PUT 的 `MemoryUpdateRequest` 增加 priority/disclosure | 10 行 |
| 3 | `api_server.py` | `/api/memory/search` mode 默认值改为 "hybrid" | 1 行 |

### 8.2 P1 — 可与前端并行

| # | 文件 | 修改内容 | 工作量 |
|---|------|---------|--------|
| 4 | `api_server.py` | `/api/evaluations/pending` GET 增加 patient_id 过滤参数 | 10 行 |

### 8.3 P2 — 后续优化

| # | 文件 | 修改内容 | 工作量 |
|---|------|---------|--------|
| 5 | `api_server.py` | `/api/memory/tree` N+1 查询优化 | 中 |
| 6 | `api_server.py` | `/api/memory/stats` 性能优化 | 中 |
| 7 | `api_server.py` | `POST /api/consultation/stream` SSE 流式响应 | 大 |

---

## 九、部署与路由配置

### 9.1 Vite 配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  base: '/medical/',    // ★ 必须配置，否则资源路径 404
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
});
```

### 9.2 nginx 配置

```nginx
# 新增：独立的血糖管理产品前端
location /medical/ {
    proxy_pass http://127.0.0.1:5173/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 9.3 访问地址

- **产品界面**：`http://47.94.106.206/medical/`
- **开发协作**：`http://47.94.106.206/ui/`（不变）

---

## 十、开发分工

### 10.1 执行顺序

```
Phase 0: 后端 P0 修复（claude-1，约 30min）
    ↓
Phase 1: 基础设施（claude-1 优先，约 1-2h）
  - 项目脚手架 (claude-dev)
  - API client + stores 基础设施 (claude-1) ★ 其他模块依赖此项
  - nginx 配置 (claude-dev)
    ↓
Phase 2: 四大模块并行
  - Chat 对话 (claude-1)
  - 记忆宫殿 (claude-dev)
  - 评价系统 + 患者档案 (claude-2)
    ↓
Phase 3: 联调 + 动效打磨
```

### 10.2 分工详情

| 任务 | 负责人 | 阶段 | 依赖 |
|------|--------|------|------|
| 后端 P0 修复（3 项） | claude-1 | Phase 0 | 无 |
| 项目脚手架 + AppShell + Sidebar + 路由 | claude-dev | Phase 1 | 无 |
| API client + patientStore + chatStore | claude-1 | Phase 1 | 脚手架 |
| nginx 配置 | claude-dev | Phase 1 | 脚手架 |
| Chat 对话完整模块 | claude-1 | Phase 2 | Phase 1 |
| 记忆宫殿完整模块 | claude-dev | Phase 2 | Phase 1 |
| 评价系统完整模块 | claude-2 | Phase 2 | Phase 1 |
| 患者档案完整模块 | claude-2 | Phase 2 | Phase 1 |
| 联调 + 动效打磨 | 共同 | Phase 3 | Phase 2 |

---

## 十一、验收标准

### MVP 必须达成

1. ✅ 产品可通过 `http://47.94.106.206/medical/` 独立访问
2. ✅ Chat 对话功能可正常与后端 API 交互，对话持久化
3. ✅ 对话完成后自动创建待评价记录（线1→线3 联通）
4. ✅ 对话完成后自动提取事实写入 Memory Palace（线1→线2 联通）
5. ✅ 记忆宫殿可视化达到"让评委眼前一亮"的效果
6. ✅ 记忆支持 CRUD 操作
7. ✅ 评价系统可完成完整的评价流程（创建→打标签→统计）
8. ✅ 可触发人工评价驱动的自进化优化（线3 闭环）
9. ✅ 患者档案展示正常（含血糖趋势图）
10. ✅ 深色主题统一、动效流畅
11. ✅ 不影响 CCCC 工作组（`/ui/`）的正常使用
12. ✅ 全局患者选择联动正常
