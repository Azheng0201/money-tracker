# MoneyTrancker

个人记账与消费分析系统。命令行 + 网页双入口，支持筛选、分页、统计、图表。

## 功能

### 命令行 (cli.py)
- 添加 / 查看 / 修改 / 删除交易
- 按月份、类型、分类、关键词筛选
- 汇总：总收入、总支出、结余、笔数
- 按月 / 分类汇总
- 生成图表 PNG (柱状图、饼图、折线图)

### 网页 (app.py)
- 仪表盘：4 张统计卡片 + 最近 5 条交易
- 交易列表：筛选 + 分页
- 添加 / 编辑 / 删除表单 (含服务端校验)
- 图表区：matplotlib PNG (可一键刷新)
- 交互式图表：Chart.js 月度收支

## 技术栈

- Python 3.10+
- SQLite (`sqlite3` 标准库)
- pandas / matplotlib (分析与绘图)
- Flask + Jinja2 (Web)
- pytest (测试)

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
|—— templates/       # Jinja2 模板
|—— static/    
|   |—— style.css
|   |—— charts/      # 生成的 PNG
|—— tests/           # pytest
|—— data/            # finance.db (不入库)
|—— requirements.txt
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

## 版本记录

- **v1.0** (Day 14) Web 完整：仪表盘、筛选分页、增删改、图表、pytest 全绿
- **v0.3** (Day 7) 命令行完整：CRUD、筛选、汇总、图表、单元测试
- **v0.1** (Day 2) 基础 CLI + SQLite

## 许可

MIT