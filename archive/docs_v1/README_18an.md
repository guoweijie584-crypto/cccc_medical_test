# 18an 文档总入口

## 先说最重要的

进入这个工作区后，不要先在根目录里随便翻零散文件。

先看这一份 `README.md`，然后再按这里的入口往下走。

这个工作区现在不是三套并行文档。

它采用的是：

- 一套跨阶段的 canonical 内容
- 一层按汇报阶段组织的入口页
- 一层共享的证据边界说明

这样做的原因很简单：

- 避免第一次汇报、第二次汇报、最终汇报各写一份正文，后面口径一起漂
- 保留同一份系统理解、模块设计、里程碑说明作为长期主干
- 让你既能按“现在要干什么”进入，也能按“这句话到底有多稳”进入

再补一条当前特别重要的原则：

- 根目录现在已经不再堆放历史 `pdf/pptx`
- 这些历史原始材料已经按类别迁入 `archive/`
- 组员和 AI 都应该先从这一份 `README.md` 进入

## 零散文件怎么处理

如果你现在的困惑是：

- 历史 `pdf/pptx` 现在分别被放到了哪里
- 我不知道它们该算哪一类
- 我也不知道该先发哪份给组员或 AI

那先看：

1. `docs_forHuman/根目录资料落位说明.md`
2. `docs_forHuman/资料分类与阅读顺序.md`

其中：

- `根目录资料落位说明.md` 解决“历史文件现在分别被归到哪里”
- `资料分类与阅读顺序.md` 解决“这些资料应该按什么顺序看”

## 一、如果你现在只想知道该点哪里

### 1. 你要快速理解整个项目

先看：

1. `docs_forHuman/README.md`
2. `docs_forHuman/资料分类与阅读顺序.md`
3. `docs_forHuman/项目梳理与理解.md`

### 2. 你要按汇报阶段进入

先看：

1. `docs_forHuman/汇报阶段总览.md`
2. `docs_forHuman/阶段入口/第一次汇报.md`
3. `docs_forHuman/阶段入口/第二次汇报准备.md`
4. `docs_forHuman/阶段入口/最终汇报准备.md`

如果当前重点已经转到第二次汇报，再补这两份：

5. `incoming_round2/第二次汇报-输入清单与方向草案.md`
6. `incoming_round2/给组员和AI的共享入口.md`

### 3. 你要今晚直接生成第一次汇报 PPT

先看：

1. `docs_forHuman/PPT生成提示词.md`
2. `docs_forHuman/超精简6分钟汇报版.md`

### 4. 你要确认一句话能不能写重

先看：

1. `docs_shared/README.md`
2. `docs_shared/证据边界与事实口径.md`

### 5. 你要核对“现在代码到底做到哪了”

先看：

1. `tmp/source_repo/cccc_medical_test/`
2. `docs_forAI/03_system_reference.md`
3. `docs_shared/证据边界与事实口径.md`

## 二、这个仓库现在按什么逻辑组织

### A. 跨阶段 canonical 内容

这些文件不是某一轮汇报专属，而是整个项目都要反复复用的主干：

- `docs_forHuman/项目梳理与理解.md`
- `docs_forHuman/系统设计与模块设计.md`
- `docs_forHuman/阶段进度与里程碑.md`
- `docs_forHuman/资料分类与阅读顺序.md`
- `docs_shared/证据边界与事实口径.md`

### B. 阶段入口层

这些文件只负责导读，不复制正文：

- `docs_forHuman/汇报阶段总览.md`
- `docs_forHuman/阶段入口/第一次汇报.md`
- `docs_forHuman/阶段入口/第二次汇报准备.md`
- `docs_forHuman/阶段入口/最终汇报准备.md`

当前状态要明确：

- 第一次汇报材料最完整
- 第二次汇报和最终汇报目前是准备区，不是假装已经成稿的完整文档包

### C. 第一次汇报直接交付物

这些文件是能直接拿去生成或压缩第一次汇报的：

- `docs_forHuman/PPT生成提示词.md`
- `docs_forHuman/超精简6分钟汇报版.md`
- `docs_forHuman/汇报辅助/`

### D. AI 侧上下文层

这部分不是给人直接汇报用的，而是给后续 AI 或整理工作快速建立上下文：

- `docs_forAI/README.md`
- `docs_forAI/03_system_reference.md`
- `docs_forAI/01_source_index.md`
- `docs_forAI/02_extraction_status.md`

如果是给组员自己的 AI 快速补上下文，最小组合是：

- `README.md`
- `docs_forHuman/资料分类与阅读顺序.md`
- `docs_shared/证据边界与事实口径.md`
- `incoming_round2/第二次汇报-输入清单与方向草案.md`

### E. 原始证据层

这里放的是“到底依据什么说”的原始来源：

- 课程要求：`archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`
- 当前主稿：`archive/round1_baseline/3.26-SR-14.11.pdf` / `archive/round1_baseline/3.26-SR-14.11.pptx`
- 同线候选改版：`archive/round1_candidates/3.27-SR-0.06.pptx` / `archive/round1_candidates/汇报0327.pptx`
- 精简展示稿：`archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx`
- 机制图：`archive/round1_baseline/流程架构.pptx`
- 策略口径：`archive/requirements_and_constraints/Multi Agent框架-0326.pdf`
- 源码证据：`tmp/source_repo/cccc_medical_test/`

这里有一个当前归档判断也要明确：

- `archive/round1_candidates/3.27-SR-0.06.pptx` 和 `archive/round1_candidates/汇报0327.pptx` 已完成首轮文本比对，但仍然留在“主稿候选池”
- 它们目前不直接替换 `3.26-SR-14.11.*` 的基线主稿地位
- `archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx` 当前更适合放在“参考/展示材料”里，而不是主稿线

### F. 第二次汇报输入层

这部分是第一次汇报结束后新增整理出来的第二阶段准备区：

- `incoming_round2/README.md`
- `incoming_round2/第二次汇报-输入清单与方向草案.md`
- `incoming_round2/给组员和AI的共享入口.md`
- `incoming_round2/0327宣怀学院汇报.md`
- `incoming_round2/第二次汇报-补强方向笔记.md`
- `incoming_round2/第二次汇报-开放问题池.md`
- `incoming_round2/微信图片_*.jpg`

当前状态要明确：

- 这些内容已经被整理进“第二次汇报输入层”
- 但还没有正式并进旧的 canonical 主文档

## 三、除了按用途进，还可以按证据强弱进

如果你更关心“哪个更稳”，现在可以按下面理解：

- `主稿`：`3.26-SR-14.11.*`
- `主稿候选`：`archive/round1_candidates/3.27-SR-0.06.pptx`、`archive/round1_candidates/汇报0327.pptx`
- `精简展示稿`：`archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx`
- `机制图`：`archive/round1_baseline/流程架构.pptx`
- `策略口径`：`archive/requirements_and_constraints/Multi Agent框架-0326.pdf`
- `代码证据`：`tmp/source_repo/cccc_medical_test/`
- `共享边界`：`docs_shared/证据边界与事实口径.md`
- `待复核要求源`：`archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`

其中还要保留一个限制：

- `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf` 的保存提取文本当前仍然失败
- 所以凡是特别细的课程要求、阶段名、评分标准，仍然要按“待复核”处理

## 四、最短导航建议

如果你只记 5 个入口，记这 5 个：

1. `docs_forHuman/README.md`
2. `docs_forHuman/汇报阶段总览.md`
3. `docs_shared/README.md`
4. `docs_shared/证据边界与事实口径.md`
5. `docs_forAI/03_system_reference.md`

如果你现在已经进入第二次汇报准备阶段，再额外记 2 个：

6. `incoming_round2/第二次汇报-输入清单与方向草案.md`
7. `incoming_round2/给组员和AI的共享入口.md`

## 五、一句话收口

这个仓库现在的结构不是“把材料堆在一起”，而是：

`用一套跨阶段主文档承载项目理解，用阶段入口承载汇报路径，用共享证据边界约束口径，再用源码和原始材料回答“这句话到底凭什么成立”。`
