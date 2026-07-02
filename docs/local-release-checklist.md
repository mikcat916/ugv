# Local Web Release Checklist

## Scope

- [ ] 仅验收 Web 后端和浏览器页面
- [ ] 不验收桌面端启动、连接状态、断线/重连

## 1. Fresh Clone

- [ ] 在临时目录全新 clone `https://github.com/mikcat916/ugv.git`
- [ ] 进入仓库根目录
- [ ] 确认 Python 3.11、Node.js、MySQL 8 可用

## 2. Install Dependencies

- [ ] 后端依赖：`python -m pip install -r backend/requirements.txt`
- [ ] 开发检查依赖：`python -m pip install -r requirements-dev.txt`

## 3. Configure Environment

- [ ] 复制 `.env.example` 为 `.env`
- [ ] 修改 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- [ ] 保留默认本地账号 `admin / admin123`

## 4. Initialize Database

- [ ] 运行 `python scripts/create_database.py --with-device-pin`
- [ ] 如需清库重来，先运行 `mysql -u root -p robot_monitor < backend/db/reset-db-dev.sql`

## 5. Static Smoke

- [ ] `python scripts/local_release_smoke.py --static`

## 6. Start Backend

- [ ] `python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload`
- [ ] 打开 `http://127.0.0.1:8000/health`

## 7. Web Smoke

- [ ] `python scripts/local_release_smoke.py --web --backend-url http://127.0.0.1:8000`
- [ ] 打开 `http://127.0.0.1:8000/login`
- [ ] 使用 `admin / admin123` 登录
- [ ] 确认 Dashboard 正常加载
- [ ] 确认设备管理页面正常加载
- [ ] 确认用户/集群/编队导航页正常加载

## Acceptance

- [ ] 自动检查全部通过
- [ ] Web 页面无 500 / 无明显空白页
- [ ] 本轮不包含桌面端验收
