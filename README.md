# MoneyTrancker

个人记账与消费分析系统。命令行 + 网页双入口，支持筛选、分页、统计、图表。

## 功能

### 命令行 (cli.py)
- 添加 / 查看 / 修改 / 删除交易
- 按月份、类型、分类、关键词筛选
- 汇总：总收入、总支出、结余、笔数
- 按月 / 分类汇总
- 生成图表 PNG (柱状图、饼图、折线图)
- 预算：设置 / 更新预算、预算提醒、删除预算
- 数据导入导出

### 网页 (app.py)
- 登录 / 注册 / 登出
- 仪表盘：4 张统计卡片 + 最近 5 条交易
- 交易列表：筛选 + 分页
- 添加 / 编辑 / 删除表单 (含服务端校验)
- 图表区：matplotlib PNG (可一键刷新)
- 预算管理

### 认证与数据隔离
- 注册 / 登录 / 登出 （werkzeug 密码哈希）
- 每个用户只能看到自己的交易、预算、图表

### 数据导入导出
- CLI / Web 双入口
- CSV UTF-8 + BOM，Excel 双击不乱码
- 坏行跳过并报告行数，支持去重

### 预算提醒
- 分类级月度预算
- 进度条 + 三档状态（ok / warning / over）
- 仪表盘顶部自动警告

### 界面
- Bootstrap 5 响应式布局
- 暗黑模式切换（localStorage 记忆）

## 技术栈

- Python 3.12
- SQLite (`sqlite3` 标准库)
- pandas / numpy / matplotlib (分析与绘图)
- Flask + Jinja2 (Web) + Bootstrap (页面美化)
- pytest + pytest-cov (测试及覆盖率)
- ruff 代码检查和格式化
- Werkzeug Security 安全机制与数据验证

## 项目结构

```
money-tracker/
|—— cli.py           # 命令行入口
|—— app.py           # Flask 应用
|—— db.py            # 数据库 CRUD / 筛选 / 汇总
|—— analytics.py     # pandas 分析
|—— charts.py        # matplotlib 图表
|—— display.py       # 终端格式化输出
|—— model.py         # 数据模型 (dataclass)
|—— io_csv.py        # 数据导入导出(CSV)
|—— run_prod.py      # 本地启动模拟生产环境
|—— templates/       # Jinja2 模板 + Bootstrap 响应式布局
|—— static/    
|   |—— style.css
|   |—— charts/      # 生成的 PNG
|—— tests/           # pytest / pytest-cov
|—— data/            # finance.db (不入库)
|—— scripts/         # check.ps1 一键检测脚本（Windows powershell）
|—— requirements.txt
|—— pyproject.toml
```

## 安装
```bash
git clone <repo>
cd money-trancker

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

首次运行会自动建表

## 命令行用法
```bash
# 交互式菜单
python cli.py

# 一次性命令
python cli.py add --date 2026-09-10 --type income --category 工资 --amount 8000
python cli.py list --month 2026-09
python cli.py list --type expense --keyword 午饭
python cli.py summary
python cli.py summary --by month
python cli.py summary --by category --type expense
python cli.py chart
python cli.py delete 5 -y
```

## 网页用法
```bash
python app.py
```

浏览器打开 http://127.0.0.1:5000

页面：

- `/` 仪表盘
- `/transactions` 交易列表 (支持 `?month=&type=&category=&keyword=&page=`)
- `/add` 添加
- `/edit/<id>` 编辑

## 测试

```bash
pytest -v
```

## 开发

### 一键质量检查
```powershell
.\scripts\check.ps1
```

依次跑：ruff lint → ruff format 检查 → pytest + 覆盖率。

### 代码风格

项目使用 [ruff](https://docs.astral.sh/ruff/) 做 lint 和格式化：
```bash
ruff check .       # 检查
ruff check . --fix # 自动修复能修的
ruff format .      # 格式化
```

配置见 `pyproject.toml`。

### 测试覆盖率
```bash
pytest --cov=. --cov-report=term-missing
pytest --cov=. --cov-report=html  # 生成htmlcov/index.html
```

核心模块目标：
- `db.py` ≥ 90%
- `analytics.py` ≥ 90%
- `app.py` ≥ 70%

### 依赖更新

```bash
pip install -r requirements.txt
pip freeze > requirements.txt  # 改完后锁版本
```

## 部署

见 [DEPLOY.md](DEPLOY.md)。本地快速模拟生产：

```bash
python run_prod.py
```

## 环境变量
| 变量 | 说明 | 默认 |
|---|---|---|
| `SECRET_KEY` | Flask session 密钥，生产必填 | `dev-secret-change-me...` |
| `DB_PATH` | SQLite 路径 | `data/finance.db` |
| `FLASK_DEBUG` | 是否开 debug（生产设为 0） | `1` |
| `HOST` / `PORT` | run_prod.py 绑定地址 | `127.0.0.1` / `8000` |

## 版本记录

- **v2.0** (Day 21) 最终版：用户认证、数据隔离、CSV 导入导出、预算提醒、Bootstrap 5 UI、暗黑模式、可部署
- **v1.0** (Day 14) Web 完整：仪表盘、筛选分页、增删改、图表、pytest 全绿
- **v0.3** (Day 7) 命令行完整：CRUD、筛选、汇总、图表、单元测试
- **v0.1** (Day 2) 基础 CLI + SQLite

## 许可

MIT