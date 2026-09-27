"""终端显示：所有“打印”相关的函数集中在这里。"""


def print_rows(rows) -> None:
    """交易列表"""
    if not rows:
        print("  （暂无记录）")
        return
    print(f"  {'ID':>4} {'日期':<12} {'类型':<8} {'分类':<6} {'金额':>10} 备注")
    print("  " + "-" * 56)
    for r in rows:
        sign = "+" if r["type"] == "income" else "-"
        print(
            f"  {r['id']:>4} {r['date']:<12} {r['type']:<8} "
            f"{r['category']:<6} {sign}￥{r['amount']:>8.2f} {r['note']}"
        )


def print_summary(s: dict, title: str = "") -> None:
    """收入/支出/结余汇总。"""
    if title:
        print(f"\n 📊 {title}")
    print(f"  收入：  +￥{s['income']:>10.2f}  ({s['income_count']} 笔)")
    print(f"  支出：  -￥{s['expense']:>10.2f}  ({s['expense_count']} 笔)")
    sign = "🟢" if s["balance"] >= 0 else "🔴"
    print(f"  结余：  {sign} ￥{s['balance']:>10.2f}  共 {s['count']} 笔")


def print_month_table(rows: list[dict]) -> None:
    """按月汇总表。"""
    if not rows:
        print("  （暂无数据）")
        return
    print(f"  {'月份':<9}{'收入':>12}{'支出':>12}{'结余':>12}{'笔数':>6}")
    print("  " + "-" * 51)
    for r in rows:
        print(
            f"  {r['month']:<9}"
            f"{r['income']:>12.2f}"
            f"{r['expense']:>12.2f}"
            f"{r['balance']:>12.2f}"
            f"{r['count']:>6}"
        )


def print_category_table(rows: list[dict], type_: str) -> None:
    """分类汇总表。"""
    label = "收入" if type_ == "income" else "支出"
    if not rows:
        print(f"  （暂无{label}数据）")
        return
    print(f"  {'分类':<10}{label + '金额':>12}{'占比':>8}{'笔数':>6}")
    print("  " + "-" * 36)
    for r in rows:
        print(f"  {r['category']:<10}{r['total']:>12.2f}{r['percent']:>7.1f}{r['count']:>6}")


def print_demo_report(df, summary: dict, monthly, mom, top, daily, weekday) -> None:
    """analytics 层的演示报表"""
    if df.empty:
        print(" （暂无数据） ")
        return

    print("=" * 44)
    print(f"  数据跨度: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  共 {len(df)} 条，{df['category'].nunique()} 个分类")
    print("=" * 44)

    print("\n 【总览】 ")
    print(
        f"  收入 ￥{summary['income']:.2f}  "
        f"支出 ￥{summary['expense']:.2f}  "
        f"结余 ￥{summary['balance']:.2f}"
    )

    print("\n  【按月】")
    print(monthly.to_string())

    print("\n  【支出环比】 ")
    print(mom.to_string())

    print("\n  【Top 5 支出分类】 ")
    print(top.to_string(index=False))

    print(f"\n  【日均支出】 ￥{daily:.2f}")

    print("\n  【按星期支出】")
    print(weekday.to_string(index=False))
