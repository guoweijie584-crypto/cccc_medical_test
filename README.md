# 血糖管理 Agent 自进化系统

基于 CCCC + Memory Palace 的双闭环自进化血糖管理多智能体系统。

## 项目结构

```
cccc_test/
├── src/                    # 源代码
│   ├── memory/            # Memory Agent 和 Palace 客户端
│   │   ├── __init__.py
│   │   ├── palace_client.py   # Memory Palace MCP 客户端
│   │   └── memory_agent.py    # Memory Agent 实现
│   ├── agents/            # 血糖管理 Agent（阶段二）
│   └── evolution/         # 自进化闭环（阶段三）
├── config/                # 配置文件
│   └── settings.py        # 系统配置
├── prompts/               # Agent 提示词
├── data/                  # 数据目录
│   └── patient_structured/   # 患者数据
├── docs/                  # 文档
│   └── api_memory_agent.md   # Memory Agent API 文档
├── main.py                # 主入口
├── start.py               # 一键启动脚本
└── requirements.txt       # 依赖
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
python --version

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env，设置 LLM_API_KEY 和 MCP_API_KEY
```

### 2. 启动 Memory Palace

```bash
cd Memory-Palace-main/backend
python main.py
# 或
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. 运行测试

```bash
python main.py --test    # 功能测试
python main.py --info    # 系统信息
```

## 架构

### 三层记忆结构

- **短期记忆**: 当前对话历史（内存）
- **中期记忆**: 近期趋势（Memory Palace，近 1-4 周）
- **长期记忆**: 患者画像（Memory Palace，持久化）

### 双闭环自进化

1. **提示词优化闭环**
   - Evaluator 评估回答质量
   - Analyzer 归因分析
   - Prompt Optimizer 生成改进提示词
   - 验证并生效

2. **记忆优化闭环**
   - Memory Evaluator 评估记忆质量
   - Analyzer 分析记忆问题
   - Memory Optimizer 执行增删改
   - 验证并生效

## Agent 列表

| Agent | 角色 | 职责 |
|-------|------|------|
| Primary | 主治医生 | 综合决策，协调专家 |
| Pharmacist | 药剂师 | 用药指导 |
| Nutritionist | 营养师 | 饮食建议 |
| Doctor | 代谢病医生 | 诊疗方向 |
| Memory | 记忆管理 | 记忆提取与存储 |
| Evaluator | 质检员 | 质量评估 |
| Analyzer | 分析师 | 问题归因 |
| Prompt Optimizer | 提示词优化师 | 优化提示词 |
| Memory Optimizer | 记忆优化师 | 优化记忆内容 |

## 开发阶段

- [x] 阶段一: Memory Palace 桥接
- [ ] 阶段二: 血糖管理 Agent 系统
- [ ] 阶段三: 自进化闭环
- [ ] 阶段四: 评测与可视化

## API 文档

详见 [docs/api_memory_agent.md](docs/api_memory_agent.md)
