# 部署指南

## 本地生产模式

```bash
# 1. 复制 .env
cp .env.example .env
# 编辑 .env, 把 SECRET_KEY 改成随机长字符串：
# python -c "import secrets; print(secrets.token_hex(32))"

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python run_prod.py
# 或
waitress-serve --listen=127.0.0.1:8000 app:app
```

浏览器打开 http://127.0.0.1:8000

## 部署到 Render (免费，5 分钟)

### 前置
- 代码已推到 Github
- 注册 [Render](https://render.com)

### 步骤

1. 在 Render 控制台点 **New → Web Service**
2. 连接你的 Github 仓库
3. 配置:
   - **Environment**: `Python 3`
   - **Build Command** `pip install -r requirements.txt`
   - **Start Command** `gunicorn app:app`
4. **Environment Variables** 加:
   - `SECRET_KEY` = 随机 64 位 hex
   - `PYTHON_VERSION` = `3.12.0`
   - `DB_PATH` = `/data/finance.db` (**见下方警告**)
5. 点 **Create Web Service**

### ⚠️ SQLite 持久化警告

**Render 默认的磁盘是临时的，每次重启容器都会丢数据。**

免费方案（二选一）：

**A. 使用 Render 的 Disk （需要付费计划）**
- 在 Render 服务里加一个 Disk, Mount Path 填 `/data`
- 环境变量 `DB_PATH=/data/finance.db`

**B. 接受数据会丢（学习/演示项目可接受）**
- 不挂 Disk，每次重启数据清空
- 适合 demo，不适合真是记账

**C. 迁移到 PostgreSQL（进阶）**
- 把 `db.py` 里的 `sqlite3` 换成 `psycopg2` 或 SQLAlchemy
- 需要重写大约 1/3 的 db.py
- 留作后续挑战

## 部署到 PythonAnywhere（免费，SQLite 持久）

1. 注册 [PythonAnywhere](https://www.pythonanywhere.com)
2. 上传代码（git clone 或用 Files 上传）
3. 创建 virtualenv，`pip install -r requirements.txt`
4. Web 标签 → Add a new wep app → 选 **Flask**
5. 配置 WSGI 文件指向你的 `app.py`
6. Reload

SQLite 文件持久存在账号磁盘里，**不会丢**。

## 安全清单

上线前确认：

- [ ] `SECRET_KEY` 是随机 64 位，不是代码里的默认值
- [ ] `debug=False` （生产环境）
- [ ] `.env` 不在 git 里（`.gitignore` 已排除）
- [ ] 数据库有定期备份（`copy data/finance.db data/finance.db.bak`）
- [ ] HTTPS 由平台自动提供（Render / PythonAnywhere 默认开）
- [ ] 日志级别不是 DEBUG（waitress 默认是 INFO）
