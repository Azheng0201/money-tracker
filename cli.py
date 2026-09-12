"""命令行界面：增删改查交易"""
import sys
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

# ---------- 主菜单 ----------
MENU = """
================ Money Tracker ================
1. 添加交易
2. 查看全部
3. 更新交易
4. 删除交易
5. 退出
================================================
"""

ACTIONS = {
    "1": action_add,
    "2": action_list,
    "3": action_update,
    "4": action_delete
}

def main() -> None:
    db.init_db()
    while True:
        print(MENU)
        choice = input("请选择操作（1-5）：").strip()
        if choice == "5":
            print("👋 再见！")
            sys.exit(0)
        action = ACTIONS.get(choice)
        if not action:
            print("⚠️ 无效选择，请输入 1-5。")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\n↩️ 操作已取消。")
        except Exception as e:
            print(f"⚠️ 出现错误：{e}")

if __name__ == "__main__":
    main()