# Memory 模块重构设计文档

> 状态：设计草案 | 作者：claude-dev (foreman) | 日期：2026-04-07

## 1. 设计目标

**摒弃三层记忆设计，完全采用 Memory Palace 架构管理记忆。**

### 1.1 当前问题

现有 `src/memory/memory_agent.py` 的 `MemoryAgent` 仍保留三层记忆概念：
- `retrieve_patient_context()` 返回 `short_term` / `mid_term` / `long_term`
- `build_agent_context()` 按三层组织上下文
- 短期记忆用 `session_memories` (内存字典) 管理

这与用户的决策方向不符。Memory Palace 本身有更成熟的记忆管理架构。

### 1.2 目标状态

- 记忆的存储、检索、治理、生命周期全部委托给 Memory Palace
- `MemoryAgent` 变成面向医疗场景的**接口适配层**，不做自己的记忆分层
- 利用 Memory Palace 原生的 URI 寻址、Write Guard、混合检索、vitality 治理

## 2. Memory Palace 核心能力（基于代码研读）

### 2.1 MCP 工具清单

Memory Palace 暴露 9 个 MCP 工具：

| 工具 | 功能 | 医疗场景用途 |
|------|------|-------------|
| `read_memory(uri)` | 读取记忆，支持分块/范围读取 | 读取患者档案、历史记录 |
| `create_memory(parent_uri, content, priority, title, disclosure)` | 在父节点下创建记忆 | 存储新的咨询记录、事实 |
| `update_memory(uri, old_string, new_string, append, priority, disclosure)` | 补丁/追加更新 | 更新患者档案、修正信息 |
| `delete_memory(uri)` | 删除记忆路径 | 清理过时/错误记忆 |
| `add_alias(new_uri, target_uri)` | 创建别名 URI 指向同一记忆 | 多角度索引（按患者/按类别/按时间） |
| `search_memory(query, mode, filters)` | 混合检索（keyword/semantic/hybrid） | 查询相关病史、用药记录 |
| `compact_context(reason, force)` | 压缩会话上下文为持久摘要 | 对话结束后保存关键信息 |
| `rebuild_index(memory_id, sleep_consolidation)` | 重建检索索引 | 维护操作 |
| `index_status()` | 索引状态查询 | 健康检查 |

### 2.2 URI 寻址体系

Memory Palace 用 `domain://path` 形式的 URI 寻址：
- `core://` — 默认 domain
- 支持嵌套路径：`core://medical/patients/P001/profile`
- 支持别名：同一内容多个 URI 入口

### 2.3 核心机制

| 机制 | 说明 |
|------|------|
| **Write Guard** | 每次写入前预检，决定 ADD / UPDATE / NOOP / DELETE，防止重复或低质量写入 |
| **Snapshot & Review** | 每次修改前自动创建快照，支持回滚 |
| **Priority** | 数值越低优先级越高，影响检索排序和冲突解决 |
| **Disclosure** | 触发条件描述，指示何时应该读取该记忆 |
| **Vitality Score** | 记忆活力评分，随时间衰减，用于治理和清理 |
| **混合检索** | keyword + semantic + hybrid 三种模式，支持 intent-aware 查询分类 |
| **Session Management** | 会话级别的记忆追踪，支持 compact_context 压缩为持久摘要 |

## 3. 医疗场景 URI 规划

### 3.1 URI 结构设计

```
medical://
├── patients/
│   ├── {patient_id}/
│   │   ├── profile          # 患者基础档案（长期）
│   │   ├── consultations/   # 咨询记录
│   │   │   └── {timestamp}  # 单次咨询记录
│   │   ├── medications/     # 用药记录
│   │   ├── glucose/         # 血糖记录
│   │   ├── diet/            # 饮食记录
│   │   └── alerts/          # 安全警示
│   └── ...
├── knowledge/               # 医学知识库
│   ├── guidelines/          # 临床指南
│   └── medications/         # 药物信息
└── system/                  # 系统配置
    └── agent_prompts/       # Agent 提示词
```

### 3.2 Priority 规划

| Priority 值 | 含义 | 示例 |
|-------------|------|------|
| 0 | 安全警示/红线 | 药物过敏、禁忌症 |
| 1 | 患者核心档案 | 基础信息、诊断、病史 |
| 2 | 近期关键事件 | 最近用药调整、异常血糖 |
| 3 | 常规咨询记录 | 标准对话记录 |
| 4 | 辅助信息 | 饮食偏好、运动习惯 |
| 5+ | 低优先级 | 历史记录、参考信息 |

### 3.3 Disclosure 规划

每条记忆都应设置 `disclosure`（触发条件），例如：

| 记忆类型 | Disclosure 示例 |
|----------|----------------|
| 药物过敏 | "当讨论任何用药建议时" |
| 胰岛素方案 | "当讨论胰岛素剂量或注射方案时" |
| 血糖趋势 | "当评估血糖控制情况时" |
| 饮食限制 | "当给出饮食建议时" |

## 4. 重构方案

### 4.1 现有代码变更

**`src/memory/palace_client.py`（保留，重构）**

现有的 `MemoryPalaceClientSync` 已经对接了 Memory Palace HTTP API（browse 接口），但：
- URI 映射逻辑过于复杂（硬编码三层记忆的路径转换）
- 没有利用 priority、disclosure 等核心能力
- search 用的是 observability 接口而非 MCP 标准接口

重构方向：
1. 简化 URI 处理 — 直接使用上面规划的 URI 结构
2. 添加 priority 和 disclosure 参数支持
3. 搜索走 MCP 标准接口或对应 HTTP 端点

**`src/memory/memory_agent.py`（大幅重构）**

从"三层记忆管理器"变成"医疗场景 Memory Palace 适配层"：

```python
class MemoryAgent:
    """Medical Memory Palace adapter.
    
    不做自己的记忆分层。所有记忆存储、检索、治理
    全部委托给 Memory Palace。
    """
    
    def retrieve_patient_context(self, patient_id, query):
        """从 Memory Palace 检索患者相关上下文。
        
        不再区分 short/mid/long term。
        使用 search_memory 做混合检索，
        按 priority 排序返回。
        """
        
    def store_consultation_record(self, patient_id, record):
        """存储一次咨询记录到 Memory Palace。
        
        使用 create_memory + 合理的 priority 和 disclosure。
        """
        
    def update_patient_profile(self, patient_id, updates):
        """更新患者档案。
        
        使用 update_memory 的 patch 模式。
        """
        
    def extract_and_store_facts(self, patient_id, interaction):
        """从对话中提取事实并存储。
        
        每个事实作为独立记忆，设置恰当的 URI / priority / disclosure。
        """
        
    def compact_session(self, patient_id):
        """会话结束时压缩上下文。
        
        调用 compact_context。
        """
```

**`src/memory/palace_client_mcp.py`（移除或合并）**

目前有两个 client 文件，造成混淆。统一为一个。

### 4.2 去掉的内容

- `session_memories` 内存字典（短期记忆）→ 改用 Memory Palace session 管理
- `retrieve_patient_context` 里的三层返回结构 → 改为统一的检索结果列表
- `build_agent_context` 里的三层组织逻辑 → 改为按 priority 和相关性组织
- URI 映射里的 `medical://patient/{id}/profile` 硬编码转换逻辑 → 直接用新 URI 规划

### 4.3 保留的内容

- `extract_facts_from_interaction` 的事实提取逻辑（但输出格式要适配 Memory Palace）
- `MemoryPalaceClientSync` 的 HTTP 通信框架（但简化 URI 处理）
- 患者档案读写的基本流程（但用 Memory Palace 原生方式）

## 5. 实现步骤

1. **Step 1**：重构 `palace_client.py` — 简化 URI 处理、添加 priority/disclosure 支持
2. **Step 2**：重构 `memory_agent.py` — 移除三层记忆，改为 Memory Palace 适配层
3. **Step 3**：合并/移除 `palace_client_mcp.py` — 统一 client
4. **Step 4**：更新 `src/agents/workflow.py` 中的 memory 调用 — 适配新接口
5. **Step 5**：更新提示词 `prompts/memory_agent.txt` — 反映新的职责定义
6. **Step 6**：更新测试和集成验证

## 6. 风险与注意事项

1. **Memory Palace 服务依赖**：系统运行时需要 Memory Palace 后端在线（:8000）
2. **数据迁移**：如果已有用旧格式存储的数据，需要迁移脚本
3. **域名配置**：需要在 Memory Palace 的 `.env` 里添加 `medical` 到 `VALID_DOMAINS`
4. **Write Guard 适配**：确保医疗场景的写入模式不被 Write Guard 误拦
