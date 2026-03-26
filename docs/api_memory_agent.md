# Memory Agent API 文档

## 概述

Memory Agent 负责血糖管理系统的患者记忆提取、组织和管理。它是 CCCC 多智能体系统与 Memory Palace 记忆层的桥梁。

## 核心类

### `MemoryAgent`

主类，提供记忆管理功能。

```python
from src.memory import MemoryAgent, get_memory_agent

# 创建实例
agent = MemoryAgent()

# 或使用单例
agent = get_memory_agent()
```

---

## API 方法

### 1. 检索患者上下文

```python
def retrieve_patient_context(
    self,
    patient_id: str,
    query: str = "",
    context_type: str = "full"
) -> Dict[str, Any]
```

**参数**：
- `patient_id` (str): 患者唯一标识
- `query` (str, optional): 搜索关键词
- `context_type` (str): 上下文类型 (`full`/`recent`/`glucose`/`medication`)

**返回**：
```python
{
    "patient_id": str,
    "profile": Optional[str],           # 患者画像
    "recent_memories": List[Dict],      # 近期记忆
    "session_history": List[Dict],      # 当前对话历史
    "context_type": str
}
```

**示例**：
```python
context = agent.retrieve_patient_context(
    patient_id="PAT_bjhl2nvy9f",
    query="血糖控制",
    context_type="full"
)
```

---

### 2. 提取并存储记忆

```python
def extract_and_store(
    self,
    patient_id: str,
    dialogue: Dict[str, Any],
    extracted_facts: List[Dict[str, str]]
) -> List[str]
```

**参数**：
- `patient_id` (str): 患者ID
- `dialogue` (Dict): 对话记录
  ```python
  {
      "turn": int,
      "speaker": str,  # "patient" | "agent"
      "content": str
  }
  ```
- `extracted_facts` (List[Dict]): 提取的事实列表
  ```python
  [
      {
          "category": str,      # "glucose" | "medication" | "diet" | "symptom"
          "content": str,       # 事实内容
          "importance": str     # "high" | "normal" | "low"
      }
  ]
  ```

**返回**：存储的记忆 URI 列表

**示例**：
```python
uris = agent.extract_and_store(
    patient_id="PAT_bjhl2nvy9f",
    dialogue={"turn": 1, "speaker": "patient", "content": "今天空腹血糖8.5"},
    extracted_facts=[
        {
            "category": "glucose",
            "content": "空腹血糖 8.5 mmol/L，偏高",
            "importance": "high"
        }
    ]
)
```

---

### 3. 更新患者画像

```python
def update_patient_profile(
    self,
    patient_id: str,
    updates: Dict[str, Any]
) -> bool
```

**参数**：
- `patient_id` (str): 患者ID
- `updates` (Dict): 更新的字段

**返回**：是否成功

**示例**：
```python
success = agent.update_patient_profile(
    patient_id="PAT_bjhl2nvy9f",
    updates={
        "current_medication": ["二甲双胍", "格列美脲"],
        "target_hba1c": 7.0,
        "last_visit": "2024-03-15"
    }
)
```

---

### 4. 搜索相关记忆

```python
def search_relevant_memories(
    self,
    query: str,
    patient_id: Optional[str] = None,
    time_range: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]
```

**参数**：
- `query` (str): 搜索查询
- `patient_id` (str, optional): 患者ID过滤
- `time_range` (str, optional): 时间范围 (`recent`/`week`/`month`)
- `max_results` (int): 最大结果数

**返回**：相关记忆列表

---

### 5. 构建 Agent 上下文

```python
def build_agent_context(
    self,
    patient_id: str,
    agent_type: str,
    current_query: str
) -> str
```

**参数**：
- `patient_id` (str): 患者ID
- `agent_type` (str): Agent 类型
  - `primary`: 主治医生
  - `pharmacist`: 药剂师
  - `nutritionist`: 营养师
  - `doctor`: 代谢病医生
- `current_query` (str): 当前查询

**返回**：格式化的上下文字符串

**示例**：
```python
context = agent.build_agent_context(
    patient_id="PAT_bjhl2nvy9f",
    agent_type="pharmacist",
    current_query="二甲双胍可以和格列美脲一起吃吗"
)
```

输出示例：
```markdown
## 患者画像
患者ID: PAT_bjhl2nvy9f
姓名: 张三
年龄: 45岁
糖尿病类型: 2型
发现时间: 2019-10-31

## 相关历史记录
- [medication] 当前用药：二甲双胍 500mg bid
- [glucose] 近期空腹血糖 7.2-8.5 mmol/L

## 本轮对话
- [symptom] 患者主诉：胃部不适
```

---

## 数据结构

### `PatientMemory`

患者记忆数据模型。

```python
from src.memory import PatientMemory

# 从 JSON 数据创建
patient = PatientMemory(
    patient_id="PAT_bjhl2nvy9f",
    data=json_data
)

# 属性
patient.name          # 姓名
patient.age           # 年龄
patient.gender        # 性别
patient.diabetes_type # 糖尿病类型
patient.complications # 并发症

# 方法
patient.to_context_string()           # 转换为上下文字符串
patient.get_recent_glucose(limit=5)   # 获取最近血糖记录
```

---

## Memory Palace URI 约定

| 类型 | URI 格式 | 示例 |
|------|----------|------|
| 患者画像 | `medical://patient/{id}/profile` | `medical://patient/PAT001/profile` |
| 血糖记录 | `medical://patient/{id}/glucose/{timestamp}` | `medical://patient/PAT001/glucose/20240315` |
| 用药记录 | `medical://patient/{id}/medication/{timestamp}` | `medical://patient/PAT001/medication/20240315` |
| 饮食记录 | `medical://patient/{id}/diet/{timestamp}` | `medical://patient/PAT001/diet/20240315` |
| 咨询记录 | `medical://patient/{id}/consultation/{timestamp}` | `medical://patient/PAT001/consultation/20240315` |

---

## 三层记忆结构

### 短期记忆 (Session Memory)
- 存储位置：`MemoryAgent.session_memories` (内存)
- 内容：当前对话中的关键信息
- 生命周期：单次对话会话

### 中期记忆 (Recent Memories)
- 存储位置：Memory Palace，近 1-4 周数据
- 内容：近期血糖趋势、用药调整、饮食记录
- 检索方式：按时间倒序 + 相关性

### 长期记忆 (Patient Profile)
- 存储位置：Memory Palace，`medical://patient/{id}/profile`
- 内容：患者画像、病史、过敏史、重要事件
- 更新频率：每次咨询后更新

---

## 配置

环境变量：
```bash
# Memory Palace 连接
MEMORY_PALACE_HOST=127.0.0.1
MEMORY_PALACE_PORT=8000
MCP_API_KEY=your-api-key

# LLM API (用于记忆提取)
LLM_API_KEY=sk-...
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

---

## 错误处理

所有方法在出错时返回空结果或 False，不会抛出异常（除非严重错误）。

日志输出：
```
[MemoryPalace] Search error: Connection refused
[MemoryAgent] Profile update failed for PAT001
```
