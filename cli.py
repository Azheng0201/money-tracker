"""命令行界面：增删改查交易"""
import sys
import argparse
from datetime import datetime

import db

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

# ---------- 显示 ----------
def print_rows(rows) -> None:
    if not rows:
        print("⚠️ 没有记录。")
        return
    print(f"  {'ID':>4} {'日期':<12} {'类型':<8} {'分类':<6} {'金额':>10} 备注")
    print("  " + "-" * 56)
    for r in rows:
        sign = "+" if r["type"] == "income" else "-"
        print(f"  {r['id']:>4} {r['date']:<12} {r['type']:<8} {r['category']:<6} {sign}￥{r['amount']:>8.2f} {r['note']}")

# ---------- 各功能 ----------
def action_add() -> None:
    print("\n➕ 添加交易")
    date = ask_date("日期（YYYY-MM-DD，回车=今天）：",
                    default=datetime.now().strftime("%Y-%m-%d"))
    type_ = ask_type()
    category = ask("分类（如餐饮/交通/工资）：")
    amount = ask_float("金额：")
    note = input("备注（可选）：").strip()
    new_id = db.add_transaction(date, type_, category, amount, note)
    print(f"✅ 添加成功，ID={new_id}。")

def action_list() -> None:
    print("\n🗒️ 所有交易记录：")
    rows = db.list_all()
    print_rows(rows)

def action_update() -> None:
    print("\n✏️ 更新交易")
    tid = ask_int("请输入要更新的交易 ID：")
    row = db.get_by_id(tid)
    if not row:
        print(f"⚠️ 找不到 ID={tid} 的交易。")
        return
    print("当前记录：")
    print_rows([row])
    print("  (直接回车 = 保持原值)")

    date = ask_date(f"  新日期 [{row['date']}]：", default=row["date"])
    type_ = _ask_type_optional(f"  新类型 [{row['type']}] (1收入/2支出)：", row["type"])
    category = ask(f"  新分类 [{row['category']}]：", default=row["category"])
    amount = ask_float(f"  新金额 [{row['amount']}]：", default=row["amount"])
    note = ask(f"  新备注 [{row['note']}]：", default=row["note"])
    ok = db.update_transaction(tid, date=date, type=type_, category=category, amount=amount, note=note)
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
    row = db.get_by_id(tid)
    if not row:
        print(f"⚠️ 找不到 ID={tid} 的交易。")
        return
    print_rows([row])
    confirm = input(f"⚠️ 确认删除 ID={tid} 吗？(y/N)：").strip().lower()
    if confirm != "y":
        print("↩️ 已取消删除。")
        return
    ok = db.delete_transaction(tid)
    print("✅ 删除成功。" if ok else "⚠️ 删除失败。")

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
8. 退出
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

    rows = db.query(date_from=date_from, date_to=date_to, type_=type_, category=category, keyword=keyword)
    print(f"\n  共 {len(rows)} 条：")
    print_rows(rows)

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
    print_rows(rows)

def action_categories() -> None:
    cats = db.list_categories()
    print("\n📂 已用分类：", "、".join(cats) if cats else " (无) ")

ACTIONS = {
    "1": action_add,
    "2": action_list,
    "3": action_query,
    "4": action_month,
    "5": action_update,
    "6": action_delete,
    "7": action_categories
}

def interactive_loop() -> None:
    while True:
        print(MENU)
        choice = input("请选择操作（1-8）：").strip()
        if choice == "8":
            print("👋 再见！")
            return
        action = ACTIONS.get(choice)
        if not action:
            print("⚠️ 无效选择，请输入 1-8。")
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
    new_id = db.add_transaction(args.date, args.type, args.category, args.amount, args.note or "")
    print(f"✅ 添加成功，ID={new_id}。")

def cmd_list(args) -> None:
    if args.month:
        try:
            rows = db.query_by_month(args.month)
        except ValueError as e:
            print(f"⚠️ {e}")
            return
    else:
        rows = db.query(date_from=args.date_from, date_to=args.date_to,
                        type_=args.type, category=args.category, keyword=args.keyword)
    print(f"\n  共 {len(rows)} 条：")
    print_rows(rows)

def cmd_delete(args) -> None:
    row = db.get_by_id(args.id)
    if not row:
        print(f"⚠️ 找不到 ID={args.id} 的交易。")
        return
    if not args.yes:
        confirm = input(f"⚠️ 确认删除? (y/N)：").strip().lower()
        if confirm != "y":
            print("↩️ 已取消删除。")
            return
    db.delete_transaction(args.id)
    print("✅ 已删除。")

def cmd_categories(args) -> None:
    cats = db.list_categories(type_=args.type)
    print("\n📂 已用分类：", "、".join(cats) if cats else " (无) ")

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
    parser_list.add_argument("--from", dest="date_from", help="起始日期 YYYY-MM-DD")
    parser_list.add_argument("--to", dest="date_to", help="结束日期 YYYY-MM-DD")
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

    return parser

def main(argv: list[str] | None = None) -> None:
    db.init_db()

    argv = sys.argv[1:] if argv is None else argv

    # 无参数进入交互菜单
    if not argv:
        interactive_loop()
        return
    
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "menu":       lambda a: interactive_loop(),
        "add" :       cmd_add,
        "list":       cmd_list,
        "delete":     cmd_delete,
        "categories": cmd_categories,
    }

    handler = handlers.get(args.cmd)
    if not handler:
        parser.print_help()
        return
    handler(args)

if __name__ == "__main__":
    main()