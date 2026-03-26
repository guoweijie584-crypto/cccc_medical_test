# CCCC Test（血糖管理 Agent + CCCC + Memory Palace）

这是一个本地集成测试项目，用于联调以下组件：

- `cccc_medical-main`（医疗多智能体主工程）
- `Memory-Palace-main`（记忆服务）
- 本仓库的编排脚本与 API（如 `start_cccc_test.bat`、`api_server.py`）

项目目标是提供一个**隔离的本地运行环境**，在不污染默认用户目录的前提下，快速拉起 Daemon / Web / API / Memory Palace / 前端开发 UI。

---

## 目录结构（核心）

```text
cccc_test/
├─ start_system.bat               # 总入口（调用 start_cccc_test.bat）
├─ start_cccc_test.bat            # 一键拉起全部本地服务（Windows）
├─ main.py                        # 功能测试入口（--test / --info）
├─ start.py                       # 简化启动检查脚本
├─ api_server.py                  # 本地 API 服务（8001）
├─ bootstrap_cccc_native.py       # CCCC native 组初始化
├─ config/                        # 项目配置
├─ src/                           # Python 业务代码
├─ prompts/                       # 各角色提示词
├─ cccc_medical-main/             # CCCC 医疗主工程（含 web）
└─ Memory-Palace-main/            # Memory Palace 服务
```

---

## 环境要求

- Windows 10/11（已针对 `.bat` 流程适配）
- Python 3.10+
- Node.js 18+（用于 `cccc_medical-main/web`）
- npm

建议先确认：

```powershell
python --version
node --version
npm --version
```

---

## 首次准备

在项目根目录执行：

```powershell
cd H:\project\cccc_test
pip install -r requirements.txt
```

然后安装前端依赖：

```powershell
cd H:\project\cccc_test\cccc_medical-main\web
npm install
```

> 说明：`start_cccc_test.bat` 默认会使用隔离目录 `.cccc_home` 作为运行态目录，不走 `C:\Users\<you>\.cccc`。

---

## 一键启动（推荐）

在项目根目录双击或命令行执行：

```powershell
start_system.bat
```

它会调用 `start_cccc_test.bat`，按顺序启动：

1. 清理端口占用（`5173 / 8000 / 8001 / 8858 / 9766`）
2. 启动 CCCC Daemon（`9766`）
3. 执行 native 医疗组 bootstrap
4. 启动 Memory Palace（`8000`）
5. 启动 CCCC Web（`8858`）并做健康检查
6. 启动本地 API（`8001`）
7. 启动前端 Dev UI（`5173`）

启动后可访问：

- Dev UI: `http://127.0.0.1:5173/ui/`
- CCCC UI: `http://127.0.0.1:8858/ui/`
- API: `http://127.0.0.1:8001/`
- Memory Health: `http://127.0.0.1:8000/health`

---

## 常用命令

### 查看系统信息

```powershell
cd H:\project\cccc_test
python main.py --info
```

### 运行功能测试

```powershell
cd H:\project\cccc_test
python main.py --test
```

### 简化环境检查/初始化

```powershell
cd H:\project\cccc_test
python start.py
```

---

## 配置说明

关键配置位于：

- `config/settings.py`
- `config/*.json`
- `prompts/*.txt`

若你接入真实 LLM，请设置环境变量（示例）：

```powershell
$env:LLM_API_KEY="your-key"
```

---

## 数据与隐私

项目中可能包含本地测试数据与运行态文件，默认不建议上传：

- `data/patient_structured/`
- `.cccc_home/`
- `logs/`
- `.env*`

请在提交前检查 `.gitignore` 与 `git status`，避免上传敏感信息或大文件。

---

## 常见问题

### 1) 端口被占用
重新运行 `start_system.bat`，脚本会尝试自动释放常用端口；若失败可手动关闭占用进程。

### 2) 前端未启动
确认已执行：

```powershell
cd H:\project\cccc_test\cccc_medical-main\web
npm install
```

### 3) Memory Palace 健康检查失败
确认 `Memory-Palace-main/backend` 可正常执行：

```powershell
cd H:\project\cccc_test\Memory-Palace-main\backend
python main.py
```

---

## 说明

本仓库定位是**集成测试与本地联调工程**，并非单一可独立发布的 SDK。若用于团队协作，建议在 PR 中明确：

- 运行前置条件（Python/Node 版本）
- 需要启动的服务与端口
- 是否依赖本地私有数据
