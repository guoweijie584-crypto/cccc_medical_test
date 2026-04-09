# PROJECT — 面向智能客服的 AI Agent 血糖管理自进化系统

> **读这一份就够了。** 新 agent 上手时先读完本文件，再按需深入。

## 项目一句话

用多智能体模拟血糖管理医疗团队，以三层记忆管理和双闭环自进化为核心创新。

## 项目背景

- 课程/研究原型项目（九安医疗课题）
- 目标场景：智能客服环境下的慢病（糖尿病）血糖管理
- GitHub 仓库：`github.com/guoweijie584-crypto/cccc_medical_test`

## 三条主线

### 1. 多 Agent 医疗协作

| 角色 | 状态 | 职责 |
|------|------|------|
| Primary / 主治医生 | 代码+文档 | 最终患者回复、综合各专家意见 |
| Pharmacist / 药剂师 | 代码+文档 | 用药建议 |
| Nutritionist / 营养师 | 代码+文档 | 饮食方案 |
| Doctor / 代谢医生 | 代码+文档 | 代谢/并发症推理 |
| Memory Agent / 记忆管理 | 代码+文档 | 上下文治理、记忆读写、档案更新 |
| Educator / 科普老师 | 仅文档 | 健康教育（扩展角色） |
| Counselor / 心理咨询师 | 仅文档 | 心理支持（扩展角色） |

### 2. 三层记忆管理（核心创新）

- **短期记忆**：当前对话、本轮专家输出（设计 TTL ~1h）
- **中期记忆**：近期趋势、药物调整、饮食运动（设计 TTL ~30h）
- **长期记忆**：用户画像、病史、过敏史（持久化）
- 存储方案（设计级）：SQLite + sqlite-vec

### 3. 双闭环自进化

```
Evaluator 评分 → Analyzer 归因 → 路由分发
                                    ├→ Prompt Optimizer（提示词优化）
                                    └→ Memory Optimizer（记忆优化）
→ 重新评测验证
```

- 触发条件（设计级）：每 5 轮对话 或 评分 < 35/50
- 根因分类：Prompt_Issue / Memory_Issue / Coordination_Issue

## 标准业务流程

1. 接收用户查询
2. Memory Agent 读取患者上下文
3. 各专家并行分析
4. Primary 综合生成最终回复
5. 返回答复给用户
6. 提取关键事实、写回记忆
7. 按条件触发自进化评测

## 当前项目状态

**一句话：原型联调阶段。**

- **已有代码**：多 Agent workflow、记忆管理、Evaluator/Analyzer/Optimizer、本地 API、集成测试脚手架
- **已有设计但未完全实现**：完整记忆写入/遗忘机制、端到端自进化验证、生产级运行时
- **约束**：不把设计级细节表述为已验证实现；任务书 PDF 提取失败，细项需人工复核

## 目录结构

```
cccc_test/app/
├── src/                        # Python 业务代码
│   ├── agents/                 #   Agent 实现（primary, doctor, nutritionist, pharmacist）
│   ├── memory/                 #   记忆管理模块
│   ├── evolution/              #   自进化模块（evaluator, analyzer, optimizer）
│   ├── cccc_native/            #   CCCC 原生集成
│   ├── llm_client.py           #   LLM 调用客户端
│   └── visualization/          #   可视化工具
├── config/                     # 配置文件
├── prompts/                    # 各角色提示词（.txt）
├── cccc_medical-main/          # CCCC 医疗主工程（含 web）
├── Memory-Palace-main/         # Memory Palace 记忆服务
├── web/                        # 前端
├── api_server.py               # 本地 API 服务（:8001）
├── main.py                     # 功能测试入口
├── tests/                      # 测试
├── deploy/                     # 部署配置
│
│── # === 项目文档（从 18an 仓库导入） ===
├── docs_forAI/                 # AI 上下文层（新 agent 优先读这里）
│   ├── 00_project_context.md   #   项目全貌
│   ├── 01_source_index.md      #   资料索引与信任分层
│   ├── 02_extraction_status.md #   文本提取状态
│   └── 03_system_reference.md  #   系统参考（最结构化）
├── docs_forHuman/              # 人类可读文档
│   ├── 项目梳理与理解.md        #   项目全面理解
│   ├── 系统设计与模块设计.md    #   系统设计详述
│   ├── 阶段进度与里程碑.md      #   进度跟踪
│   ├── 资料分类与阅读顺序.md    #   材料导读
│   ├── 汇报阶段总览.md          #   汇报阶段导航
│   ├── 阶段入口/               #   各阶段汇报入口
│   └── 汇报辅助/               #   汇报辅助材料
├── docs_shared/                # 共享证据边界
│   └── 证据边界与事实口径.md    #   事实分层标准（重要！）
├── incoming_round2/            # 第二次汇报输入
├── archive/                    # 原始材料归档（PDF/PPTX）
│   ├── requirements_and_constraints/  # 任务书、策略 memo
│   ├── round1_baseline/        #   第一轮主稿基线
│   ├── round1_candidates/      #   第一轮候选版本
│   ├── round1_history/         #   历史版本
│   └── reference_materials/    #   参考/展示材料
├── PROJECT_18an.md             # 18an 原始 PROJECT.md
└── README_18an.md              # 18an 原始 README.md
```

## 新 Agent 快速上手路径

1. **读本文件** (`PROJECT.md`) — 建立全局理解
2. **读 `docs_forAI/03_system_reference.md`** — 结构化系统参考，含证据等级标注
3. **读 `docs_shared/证据边界与事实口径.md`** — 理解什么能说、什么不能说
4. **浏览 `src/` 目录** — 了解代码结构
5. **按需深入** `docs_forHuman/` 或 `archive/` — 获取更多背景

## 技术栈

- Python 3.10+ 后端 + LLM API 调用
- Node.js 18+ 前端 (Vite dev server :5173)
- CCCC Daemon (:9766) + Web (:8858)
- Memory Palace 服务 (:8000)
- 本地 API 服务 (:8001)

## 证据分层标准

在写代码、文档或汇报时，遵循四级分层：

| 等级 | 含义 | 可以写成 |
|------|------|---------|
| 代码已证实 | 代码仓库有对应实现 | "已有源码原型" |
| 文档已明确 | 主稿/流程图有设计表达 | "当前设计/当前方案" |
| 设计级细节 | 有具体参数但未实现 | "当前设计方案/配置口径" |
| 待复核 | 需回任务书确认 | "待复核" |

**绝对不要写**："已稳定运行"、"已完整实现"、"已跑通闭环"、"已验证效果显著提升"
