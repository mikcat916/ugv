# UAV Desktop

本目录是本地自用的 PyQt 桌面端，运行栈统一为 `Python 3.11 + PyQt5 + qfluentwidgets`。

## 启动顺序

1. 先启动后端：在仓库根目录运行 `.\start-dev.ps1`
2. 再启动桌面端：在仓库根目录运行 `.\start-desktop.ps1`

## 环境要求

- Windows
- Python 3.11（推荐）
- PyQt5
- PyQtWebEngine
- PyQt-Fluent-Widgets

## 安装依赖

```powershell
cd E:\Code\Project4\desktop
python -m pip install -r requirements.txt
```

## 数据库配置

桌面端读取根目录 `.env` 中的 `UAV_DB_*` 配置；未设置时会回退到本地默认值。

推荐配置：

```env
UAV_DB_HOST=127.0.0.1
UAV_DB_PORT=3306
UAV_DB_USER=root
UAV_DB_PASSWORD=
UAV_DB_NAME=robot_monitor
```

## 运行

```powershell
cd E:\Code\Project4\desktop
python main.py
```

或从仓库根目录启动，并自动检查后端是否在线：

```powershell
cd E:\Code\Project4
.\start-desktop.ps1
```

登录默认密码：`123456`。

## 目录结构

- `main.py`：主入口（登录 -> 主界面 -> 子页面切换）
- `app/`：业务层逻辑
- `UI/forms/`：Qt Designer 的 `.ui` 原始文件
- `UI/generated/`：由 `.ui` 生成的 Python 文件，不建议手改
- `UI/pages/`：页面逻辑与美化代码
- `modules/`：桌面端功能模块
- `assets/`：图片与图标资源

## UI 开发流程

1. 先在 `UI/forms/` 修改 `.ui` 文件
2. 生成对应的 `UI/generated/*.py`
3. 在 `UI/pages/` 或对应 `modules/*/pages/` 中编写美化与逻辑

生成命令示例：

```powershell
python -m PyQt5.uic.pyuic -x UI/forms/<name>.ui -o UI/generated/<name>.py
```

## 常见问题

- `ModuleNotFoundError: No module named 'UI'`：请确保从 `desktop/` 目录运行 `python main.py`。
- 缺少 PyQt 依赖：运行 `python -m pip install -r requirements.txt`。
- 数据库连接失败：确认根目录 `.env` 中的 `UAV_DB_*` 与 MySQL 配置一致。
