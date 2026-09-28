"""命令行界面：增删改查交易"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import analytics
import charts
import db
import display
import io_csv


# ---------- 输入辅助 ----------
def ask(prompt: str, default: str | None = None) -> str:
    """要求输入非空文本，default 不为空时允许回车跳过。"""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        if raw:
            return raw
        print("⚠️ 不能为空，请重新输入。")


def ask_float(prompt: str, default: float | None = None) -> float:
    """要求输入浮点数，default 不为空时允许回车跳过。"""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            value = float(raw)
            if value < 0:
                print("⚠️ 金额不能为负。")
                continue
            return value
        except ValueError:
            print("⚠️ 请输入数字。")


def ask_date(prompt: str, default: str | None = None) -> str:
    """要求输入日期，格式 YYYY-MM-DD，合法才返回。"""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("⚠️ 日期格式错误，请输入 YYYY-MM-DD。")


def ask_type(prompt: str = "类型（1收入/2支出）：") -> str:
    """要求输入交易类型，income 或 expense。"""
    while True:
        raw = input(prompt).strip().lower()
        if raw in {"1", "收入", "i"}:
            return "income"
        if raw in ("2", "支出", "e"):
            return "expense"
        print("⚠️ 请输入 1 或 2。")


def ask_int(prompt: str) -> str:
    """要求输入整数，合法才返回。"""
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("⚠️ 请输入整数。")


def _inclusive_to_exclusive(d: str | None) -> str | None:
    """CLI 用户输入的日期是含当天的， 转成内部排他式边界。"""
    if not d:
        return None
    return (date.fromisoformat(d) + timedelta(days=1)).isoformat()


def _date_arg(s: str) -> str:
    """argparse 的类型校验：非法日期直接报错。"""
    try:
        date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"日期格式应为 YYYY-MM-DD, 收到 {s!r}")
    return s


def _current_user_id() -> int:
    """
    从环境变量 MT_USER 取用户名；不设则取第一个用户。
    没有用户时提示先去网页注册。
    """
    username = os.environ.get("MT_USER", "").strip()

    if username:
        u = db.get_user_by_username(username)
        if not u:
            print(f"⚠️ 用户 '{username}' 不存在。")
            print("  请先到网页 /register 注册，或用 MT_USER=<其他用户名>。")
            sys.exit(1)
        return u["id"]

    # 没设环境变量：取第一个用户
    with db.get_conn() as conn:
        row = conn.execute("SELECT id, username FROM users ORDER BY id LIMIT 1").fetchone()
    if not row:
        print("⚠️ 还没有任何用户。")
        print("  请先运行 python app.py 并到 /register 注册一个账号。")
        sys.exit(1)

    print(f"(未设置 MT_USER, 使用第一个用户：{row['username']}) ")
    return row["id"]


_USER_ID: int = 0


# ---------- 各功能 ----------
def action_add() -> None:
    print("\n➕ 添加交易")
    date = ask_date("日期（YYYY-MM-DD，回车=今天）：", default=datetime.now().strftime("%Y-%m-%d"))
    type_ = ask_type()
    category = ask("分类（如餐饮/交通/工资）：")
    amount = ask_float("金额：")
    note = input("备注（可选）：").strip()
    new_id = db.add_transaction(_USER_ID, date, type_, category, amount, note)
    print(f"✅ 添加成功，ID={new_id}。")


def action_list() -> None:
    print("\n🗒️ 所有交易记录：")
    rows = db.list_all(_USER_ID)
    display.print_rows(rows)


def action_update() -> None:
    print("\n✏️ 更新交易")
    tid = ask_int("请输入要更新的交易 ID：")
    row = db.get_by_id(_USER_ID, tid)
    if not row:
        print(f"⚠️ 找不到 ID={tid} 的交易。")
        return
    print("当前记录：")
    display.print_rows([row])
    print("  (直接回车 = 保持原值)")

    date = ask_date(f"  新日期 [{row['date']}]：", default=row["date"])
    type_ = _ask_type_optional(f"  新类型 [{row['type']}] (1收入/2支出)：", row["type"])
    category = ask(f"  新分类 [{row['category']}]：", default=row["category"])
    amount = ask_float(f"  新金额 [{row['amount']}]：", default=row["amount"])
    note = ask(f"  新备注 [{row['note']}]：", default=row["note"])
    ok = db.update_transaction(
        _USER_ID, tid, date=date, type=type_, category=category, amount=amount, note=note
    )
    if ok:
        print("✅ 更新成功。")
    else:
        print("⚠️ 更新失败。")


def _ask_type_optional(prompt: str, current: str) -> str:
    while True:
        raw = input(prompt).strip()
        if not raw:
            return current
        if raw in {"1", "income", "i"}:
            return "income"
        if raw in ("2", "expense", "e"):
            return "expense"
        print("⚠️ 请输入 1 或 2，或直接回车跳过。")


def action_delete() -> None:
    print("\n🗑️ 删除交易")
    tid = ask_int("请输入要删除的交易 ID：")
    row = db.get_by_id(_USER_ID, tid)
    if not row:
        print(f"⚠️ 找不到 ID={tid} 的交易。")
        return
    display.print_rows([row])
    confirm = input(f"⚠️ 确认删除 ID={tid} 吗？(y/N)：").strip().lower()
    if confirm != "y":
        print("↩️ 已取消删除。")
        return
    ok = db.delete_transaction(_USER_ID, tid)
    print("✅ 删除成功。" if ok else "⚠️ 删除失败。")


def action_summary() -> None:
    print("\n📊 汇总")
    print("  1. 全部")
    print("  2. 指定月份")
    print("  3. 按月表格")
    print("  4. 按分类（支出）")
    print("  5. 按分类（收入）")
    sub = input("  请选择（1-5）：").strip()

    if sub == "1":
        display.print_summary(db.summary(_USER_ID), "全部汇总")
    elif sub == "2":
        ym = input(" 月份（YYYY-MM，回车=本月）：").strip() or datetime.now().strftime("%Y-%m")
        try:
            df, dt = _month_range(ym)
        except ValueError as e:
            print(f"  ⚠️ {e}")
            return
        display.print_summary(db.summary(_USER_ID, df, dt), f"{ym} 汇总")
    elif sub == "3":
        display.print_month_table(db.summary_by_month(_USER_ID))
    elif sub == "4":
        display.print_category_table(db.summary_by_category(_USER_ID, "expense"), "expense")
    elif sub == "5":
        display.print_category_table(db.summary_by_category(_USER_ID, "income"), "income")
    else:
        print("  ⚠️ 无效选项。")


def _month_range(ym: str) -> tuple[str, str]:
    """把 'YYYY-MM' 换成 （本月1号，下月1号）的半开区间。"""
    if len(ym) != 7 or ym[4] != "-":
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = ym.split("-")
    if not (y.isdigit() and m.isdigit() and 1 <= int(m) <= 12):
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = int(y), int(m)
    start = f"{y:04d}-{m:02d}-01"
    end = f"{y + 1:04d}-01-01" if m == 12 else f"{y:04d}-{m + 1:02d}-01"
    return start, end


# ---------- 交互菜单 ----------
MENU = """
================ Money Tracker ================
1. 添加交易
2. 查看全部
3. 筛选查询
4. 按月份查看
5. 修改交易
6. 删除交易
7. 查看分类
8. 汇总统计
9. 退出
================================================
"""


def action_query() -> None:
    print("\n🔍 筛选查询 (直接回车 = 不限制) ")
    date_from = input("  起始日期 YYYY-MM-DD: ").strip() or None
    date_to = input("  结束日期 YYYY-MM-DD: ").strip() or None
    type_raw = input("  类型（1收入/2支出/回车不限）: ").strip()
    type_ = {"1": "income", "2": "expense"}.get(type_raw)
    category = input("  分类（精确匹配）：").strip() or None
    keyword = input("  关键字（模糊匹配备注/分类）：").strip() or None

    rows = db.query(
        _USER_ID,
        date_from=date_from,
        date_to=date_to,
        type_=type_,
        category=category,
        keyword=keyword,
    )
    print(f"\n  共 {len(rows)} 条：")
    display.print_rows(rows)


def action_month() -> None:
    ym = input("\n  月份 (YYYY-MM, 回车=本月)：").strip()
    if not ym:
        ym = datetime.now().strftime("%Y-%m")
    try:
        rows = db.query_by_month(ym)
    except ValueError as e:
        print(f"⚠️ {e}")
        return
    print(f"\n 📅 {ym} 共 {len(rows)} 条：")
    display.print_rows(rows)


def action_categories() -> None:
    cats = db.list_categories(_USER_ID)
    print("\n📂 已用分类：", "、".join(cats) if cats else " (无) ")


ACTIONS = {
    "1": action_add,
    "2": action_list,
    "3": action_query,
    "4": action_month,
    "5": action_update,
    "6": action_delete,
    "7": action_categories,
    "8": action_summary,
}


def interactive_loop() -> None:
    while True:
        print(MENU)
        choice = input("请选择操作（1-9）：").strip()
        if choice == "9":
            print("👋 再见！")
            return
        action = ACTIONS.get(choice)
        if not action:
            print("⚠️ 无效选择，请输入 1-9。")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\n↩️ 操作已取消。")
        except Exception as e:
            print(f"⚠️ 出现错误：{e}")


# ---------- argparse 一次性命令 ----------
def cmd_add(args) -> None:
    """一次性添加。必填项缺失时退化成交互式。"""
    if not args.date or not args.type or not args.category or args.amount is None:
        print("⚠️ 参数不全，进入交互添加模式。")
        action_add()
        return
    new_id = db.add_transaction(
        _USER_ID, args.date, args.type, args.category, args.amount, args.note or ""
    )
    print(f"✅ 添加成功，ID={new_id}。")


def cmd_list(args) -> None:
    if args.month:
        try:
            rows = db.query_by_month(args.month)
        except ValueError as e:
            print(f"⚠️ {e}")
            return
    else:
        rows = db.query(
            _USER_ID,
            date_from=args.date_from,
            date_to=_inclusive_to_exclusive(args.date_to),
            type_=args.type,
            category=args.category,
            keyword=args.keyword,
        )
    print(f"\n  共 {len(rows)} 条：")
    display.print_rows(rows)


def cmd_delete(args) -> None:
    row = db.get_by_id(_USER_ID, args.id)
    if not row:
        print(f"⚠️ 找不到 ID={args.id} 的交易。")
        return
    if not args.yes:
        confirm = input("⚠️ 确认删除? (y/N)：").strip().lower()
        if confirm != "y":
            print("↩️ 已取消删除。")
            return
    db.delete_transaction(_USER_ID, args.id)
    print("✅ 已删除。")


def cmd_categories(args) -> None:
    cats = db.list_categories(_USER_ID, type_=args.type)
    print("\n📂 已用分类：", "、".join(cats) if cats else " (无) ")


def cmd_summary(args) -> None:
    date_from = args.date_from
    date_to = _inclusive_to_exclusive(args.date_to)
    title = "全部汇总"
    if args.month:
        try:
            date_from, date_to = _month_range(args.month)
        except ValueError as e:
            print(f"⚠️ {e}")
            return
        title = f"{args.month} 汇总"

    if args.by == "month":
        display.print_month_table(db.summary_by_month(_USER_ID, date_from, date_to))
    elif args.by == "category":
        display.print_category_table(
            db.summary_by_category(_USER_ID, args.type, date_from, date_to), args.type
        )
    else:
        display.print_summary(db.summary(_USER_ID, date_from, date_to), title)


def cmd_chart(args) -> None:
    date_from = args.date_from
    date_to = _inclusive_to_exclusive(args.date_to)
    if args.month:
        try:
            date_from, date_to = _month_range(args.month)
        except ValueError as e:
            print(f"⚠️ {e}")
            return
    df = analytics.load_df(date_from=date_from, date_to=date_to)
    if df.empty:
        print(" ⚠️ 没有可绘制的数据。")
        return

    generated: list = []
    if args.kind in ("all", "bar"):
        try:
            generated.append(charts.bar_monthly(df))
        except ValueError as e:
            print(f"⚠️ 柱状图: {e}")
    if args.kind in ("all", "line"):
        try:
            generated.append(charts.line_balance(df))
        except ValueError as e:
            print(f"⚠️ 折线图: {e}")
    if args.kind in ("all", "bar"):
        try:
            generated.append(charts.pie_categories(df, "expense"))
        except ValueError as e:
            print(f"⚠️ 饼图: {e}")

    if not generated:
        print("⚠️ 未生成任何图表。")
        return
    print("✅ 已生成：")
    for p in generated:
        print(f"  {p}")


def cmd_export(args) -> None:
    content = io_csv.export_rows(_USER_ID)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"✅ 已导出到 {path.resolve()}")


def cmd_import(args) -> None:
    path = Path(args.file)
    if not path.exists():
        print(f"⚠️ 文件不存在：{path}")
        return
    content = path.read_text(encoding="utf-8-sig")

    report = io_csv.import_csv(
        _USER_ID, content, skip_duplicates=args.skip_duplicates
    )

    print(f"✅ 导入完成: 成功 {report['imported']} 条")
    if report["skipped"]:
        print(f"⏭️ 跳过重复 {report['skipped']} 条")
    if report["errors"]:
        print(f"❌ 失败 {len(report['errors'])} 条：")
        for lineno, err in report["errors"][:20]:
            print(f"  第 {lineno} 行：{err}")
        if len(report["errors"]) > 20:
            print(f"  ...还有 {len(report['errors']) - 20} 条未显示")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Money Tracker 命令行工具")
    subparsers = parser.add_subparsers(dest="cmd")

    # 添加交易
    parser_add = subparsers.add_parser("add", help="添加交易")
    parser_add.add_argument("--date", help="YYYY-MM-DD, 默认今天")
    parser_add.add_argument("--type", choices=["income", "expense"])
    parser_add.add_argument("--category")
    parser_add.add_argument("--amount", type=float)
    parser_add.add_argument("--note", default="")

    # 查看交易
    parser_list = subparsers.add_parser("list", help="列出/筛选交易")
    parser_list.add_argument("--from", dest="date_from", type=_date_arg, help="起始日期 YYYY-MM-DD")
    parser_list.add_argument("--to", dest="date_to", type=_date_arg, help="结束日期 YYYY-MM-DD")
    parser_list.add_argument("--type", choices=["income", "expense"])
    parser_list.add_argument("--category")
    parser_list.add_argument("--keyword", help="备注/分类模糊搜索")
    parser_list.add_argument("--month", help="按月份查询 YYYY-MM")

    # 删除交易
    parser_delete = subparsers.add_parser("delete", help="按id删除")
    parser_delete.add_argument("id", type=int)
    parser_delete.add_argument("-y", "--yes", action="store_true", help="跳过确认")

    # 查看分类
    parser_cats = subparsers.add_parser("categories", help="列出已用分类")
    parser_cats.add_argument("--type", choices=["income", "expense"])

    # 汇总统计
    parser_summary = subparsers.add_parser("summary", help="汇总统计")
    parser_summary.add_argument("--month", help="只统计某月 YYYY-MM")
    parser_summary.add_argument(
        "--from", dest="date_from", type=_date_arg, help="起始日期 YYYY-MM-DD"
    )
    parser_summary.add_argument("--to", dest="date_to", type=_date_arg, help="结束日期 YYYY-MM-DD")
    parser_summary.add_argument("--by", choices=["category", "month"], help="按分类或按月展开")
    parser_summary.add_argument(
        "--type",
        choices=["income", "expense"],
        default="expense",
        help="配合 --by category 使用， 默认 expense",
    )

    # 生成图表
    parser_chart = subparsers.add_parser("chart", help="生成图表 PNG")
    parser_chart.add_argument(
        "--kind", choices=["all", "bar", "pie", "line"], default="all", help="生成哪张图，默认all"
    )
    parser_chart.add_argument("--from", dest="date_from", type=_date_arg)
    parser_chart.add_argument("--to", dest="date_to", type=_date_arg)
    parser_chart.add_argument("--month", help="只画某月 YYYY-MM")

    # CSV 导出导入
    parser_export = subparsers.add_parser("export", help="导出为 CSV")
    parser_export.add_argument("--output", default="data/export.csv",
                               help="输出路径，默认 data/export.csv")

    parser_import = subparsers.add_parser("import", help="从 CSV 导入")
    parser_import.add_argument("file", help="CSV 文件路径")
    parser_import.add_argument("--skip_duplicates", action="store_true",
                               help="跳过和现有记录完全相同的行")

    return parser


def main(argv: list[str] | None = None) -> None:
    global _USER_ID
    db.init_db()
    _USER_ID = _current_user_id()
    argv = sys.argv[1:] if argv is None else argv

    # 无参数进入交互菜单
    if not argv:
        interactive_loop()
        return

    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "menu": lambda a: interactive_loop(),
        "add": cmd_add,
        "list": cmd_list,
        "delete": cmd_delete,
        "categories": cmd_categories,
        "summary": cmd_summary,
        "chart": cmd_chart,
        "export": cmd_export,
        "import": cmd_import,
    }

    handler = handlers.get(args.cmd)
    if not handler:
        parser.print_help()
        return
    handler(args)


if __name__ == "__main__":
    main()
