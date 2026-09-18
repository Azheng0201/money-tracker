# MoneyTrancker

个人记账与消费分析系统。

## 技术栈
Python 3.12 · SQLite · pandas · matplotlib · Flask · pytest

## 已完成
- [x] 项目骨架与虚拟环境
- [x] SQLite 表结构与索引
- [x] add / list / get_by_id 基础函数

## 版本记录

### v0.3 (Day 7)
- SQLite CRUD + 通用筛选 + 月度/分类汇总
- pandas 分析层：环比、TopN、日均、按星期
- matplotlib 图表：柱状图 / 饼图 / 折线图
- CLI: 交互菜单 + argparse 子命令
- pytest 单测覆盖 db / analytics 核心逻辑

## 测试
pytest -v

## 运行
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python db.py