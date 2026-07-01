# UAV UI 项目

该项目是基于 PyQt5 + qfluentwidgets 的桌面 UI，包含登录页、主界面以及任务执行管理等子页面。

## 环境要求

- Windows（已在本机测试）
- Python 3.8+（推荐 3.9）
- PyQt5
- qfluentwidgets

## 安装（Windows + conda）

```bash
conda create -n Env11 python=3.9
conda activate Env11
pip install PyQt5 
pip install PyQt-Fluent-Widgets
```

## ??????MySQL?

???????????

- `UAV_DB_HOST`??? `127.0.0.1`?
- `UAV_DB_PORT`??? `3306`?
- `UAV_DB_USER`??? `root`?
- `UAV_DB_PASSWORD`??? `123456`?
- `UAV_DB_NAME`??? `Edgesidesystem`?

PowerShell ???

```powershell
$env:UAV_DB_HOST="127.0.0.1"
$env:UAV_DB_PORT="3306"
$env:UAV_DB_USER="root"
$env:UAV_DB_PASSWORD="123456"
$env:UAV_DB_NAME="Edgesidesystem"
```

## 运行

在项目根目录执行：

```bash
python main.py
```

登录默认密码：`123456`。

## 目录结构说明

- `main.py`：主入口（登录 -> 主界面 -> 子页面切换）
- `app/`：业务层逻辑（如 `MainInterface.py`）
- `UI/`：界面层
  - `UI/forms/`：Qt Designer 的 `.ui` 原始文件
  - `UI/generated/`：由 `.ui` 生成的 `.py`（**不建议手改**）
  - `UI/pages/`：页面逻辑与美化代码（建议只在这里写样式和交互）
- `assets/`：图片与图标等资源

## UI 开发流程

1. 先在 `UI/forms/` 修改 `.ui` 文件  
2. 生成对应的 `UI/generated/*.py`  
3. 在 `UI/pages/` 中编写美化与逻辑（避免直接改 generated）

生成命令示例：

```bash
python -m PyQt5.uic.pyuic -x UI/forms/<name>.ui -o UI/generated/<name>.py
```

## 备注

- `UI/pages/1.py` 用于调试 content 页面。
- 若运行报 `ModuleNotFoundError: No module named 'UI'`，请确保从项目根目录运行 `main.py`。

## 环境下载
- pip install -r requirements.txt



### 项目结构
11111

## MICCProject Note

- `MICCProject1` is the PyQt5 implementation used by the main application.
- `MICCProject2` is kept only as a migration reference and is not part of the runtime path.
