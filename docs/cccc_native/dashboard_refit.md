---
title: 血糖管理看板/配置面板改造方案
scope: docs/cccc_native only — no code changes in this doc
---

## 1. 页面需要显示的 CCCC-native 状态

### 医疗主组状态面板
| 状态项 | 数据来源 | 说明 |
|--------|----------|------|
| Actor 在线状态 | CCCC actor registry | primary/pharmacist/nutritionist/doctor/memory 各自 idle/active/error |
| Memory Palace 连接 | memory actor heartbeat | 连接正常 / 断开 / 延迟 ms |
| 当前加载患者 | memory actor session | 当前 session 绑定的 patient_id |
| 活跃咨询线程 | primary actor | 当前是否有进行中的咨询 |

### 评测组状态面板
| 状态项 | 数据来源 | 说明 |
|--------|----------|------|
| 评测循环状态 | evaluator actor | idle / evaluating / waiting_optimizer |
| 当前迭代轮次 | evaluator actor | iteration N |
| 最新总分 | evaluator actor | X/50 |
| 优化器状态 | prompt_optimizer / memory_optimizer | idle / running |

---

## 2. 现有页面保留 / 降级决策

### 患者页 — **保留，小改**
- 保留：患者基础信息、血糖历史图表（`GlucoseChart`）
- 改动：移除直接展示 `memories[]` 列表（记忆由 memory actor 管理，不在 UI 直接暴露）
- 新增：Memory Palace 三层记忆摘要（短期/中期/长期各一行状态）

### 咨询页 — **保留，必须修改**
- 保留：患者选择、问题输入、primary 回复展示
- **必须移除**：`ConsultationResponse.expert_opinions`（pharmacist/nutritionist/doctor 的内部意见）不得在 UI 展示 — 违反"用户只见 primary"规则
- 改动：evaluation_score 可保留作为质量指示器

### 演化页 — **保留，重新定位**
- 保留：`EvolutionTimeline` 组件、迭代得分趋势
- 重新定位：从"系统自动演化结果"改为"评测组运行日志"，展示 evaluator→analyzer→optimizer 的执行链
- 降级：`PromptChange.diff` 字段折叠默认隐藏（技术细节，非主要信息）

### Agent 表现雷达图 — **降级为折叠面板**
- 当前作为主要内容展示，改为可展开的"高级视图"
- 主看板优先展示 actor 状态和最新评分，不默认展示雷达图

---

## 3. 最小改造清单

### 类型层（`web/src/components/medical/types.ts`）
- [ ] `ConsultationResponse.expert_opinions` 标记为 `@internal`，或从类型中移除（UI 不消费）
- [ ] 新增 `ActorStatus` 类型：`{ actor_id: string; role: string; status: 'idle'|'active'|'error'; last_seen: string }`
- [ ] 新增 `MemoryPalaceStatus` 类型：`{ connected: boolean; latency_ms?: number; current_patient_id?: string }`

### 组件层（`web/src/components/medical/`）
- [ ] 新增 `ActorGroupPanel.tsx`：展示医疗主组 + 评测组 actor 状态网格
- [ ] 修改咨询页：隐藏 `expert_opinions` 渲染逻辑
- [ ] `EvolutionTimeline` 新增 `executionChain` prop，展示 evaluator→analyzer→optimizer 链路

### 页面层
- [ ] 主看板首屏：Actor 状态面板（上）+ 最新评分摘要（下），替换当前的患者列表首屏
- [ ] 咨询页：移除专家意见区块

**不需要改动**：`GlucoseChart.tsx`、路由结构、API 调用层
