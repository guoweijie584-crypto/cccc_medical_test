# 血糖管理系统重构 - 独立测试计划 v1

> 测试 Owner: kimi-3
> 状态: 等待《重构执行方案 v1》细化

---

## 1. 测试范围

### 1.1 阶段验收测试（按重构阶段划分）

| 阶段 | 验收项 | 验收标准 |
|-----|-------|---------|
| Phase 1 | Memory Palace 桥接 | 记忆读写延迟 < 200ms |
| Phase 2 | CCCC Actor 化 | 5个医疗Agent可独立响应 |
| Phase 3 | 自进化闭环 | 评分迭代收敛 |
| Phase 4 | 评测可视化 | Dashboard 数据准确性 |

### 1.2 回归测试

- 原有患者数据查询功能
- 血糖图表渲染
- 专家咨询接口

### 1.3 运行时核查

- CCCC 群聊消息流转
- Memory Palace 连接状态
- Agent 响应延迟

### 1.4 结果复核

- 验收测试通过率
- 性能基准对比
- 用户场景端到端验证

---

## 2. 测试方法

### 2.1 自动化测试
```bash
# API 测试
python test_api.py

# 集成测试  
python integration_test.py

# 新增：Actor 行为测试
python test_actor_behavior.py
```

### 2.2 运行时核查脚本
```bash
# 服务健康检查
./scripts/health_check.sh

# Agent 响应测试
./scripts/agent_ping_test.sh

# Memory Palace 连通性
./scripts/mp_connectivity_test.sh
```

### 2.3 人工验证清单
- [ ] 患者可在 CCCC 群中@专家Agent
- [ ] 记忆Agent自动补充上下文
- [ ] 4个专家给出差异化建议

---

## 3. 验收标准（硬指标）

| 指标 | 基准值 | 验收值 |
|-----|-------|-------|
| Memory Palace 查询延迟 | - | < 200ms |
| Agent 响应延迟 | - | < 3s |
| 消息成功率 | - | > 99% |
| 血糖图表渲染 | - | < 1s |

---

## 4. 待填充项（依赖重构方案）

- [ ] 具体 Actor 配置清单
- [ ] 消息路由规则
- [ ] 记忆分层策略
- [ ] 自进化触发条件

---

等待 kimi-1 《重构执行方案 v1》补充后完善。
