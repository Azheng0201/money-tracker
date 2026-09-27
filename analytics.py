"""pandas 分析层： 从 SQLite 读数据，做 SQL 不方便做的查询。"""

import numpy as np
import pandas as pd
from flask import g

import db


def load_df(user_id: int, date_from: str | None = None, date_to: str | None = None) -> pd.DataFrame:
    """
    读取交易到 DataFrame，已做类型转换。
    列：id, date(datetime64), type, category, amount(float), note, month, day
    - date_from / date_to 格式: YYYY-MM-DD，半开区间[date_from, date_to)
    """
    sql = "SELECT * FROM transactions WHERE user_id=?"
    params: list = [user_id]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date < ?"
        params.append(date_to)
    sql += " ORDER BY date"

    with db.get_conn() as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    if df.empty:
        # 保证空表也有正确的列类型，后续函数不会因为 dtype 报错
        df = pd.DataFrame(columns=["id", "date", "type", "category", "amount", "note"])
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = df["amount"].astype(float)
    else:
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = df["amount"].astype(float)

    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["day"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def summary_df(df: pd.DataFrame) -> dict:
    """DateFrame 版汇总，输出结构与 db.summary() 一致。"""
    if df.empty:
        return {
            "income": 0.0,
            "expense": 0.0,
            "balance": 0.0,
            "count": 0,
            "income_count": 0,
            "expense_count": 0,
        }

    income = df.loc[df["type"] == "income", "amount"].sum()
    expense = df.loc[df["type"] == "expense", "amount"].sum()
    income_count = int((df["type"] == "income").sum())
    expense_count = int((df["type"] == "expense").sum())

    return {
        "income": float(income),
        "expense": float(expense),
        "balance": float(income - expense),
        "count": len(df),
        "income_count": income_count,
        "expense_count": expense_count,
    }


def monthly_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    按月汇总，返回 DataFrame (index 为 month，升序)。
    列： income, expense, balance, count
    """
    if df.empty:
        return pd.DataFrame(columns=["income", "expense", "balance", "count"])

    pivot = df.pivot_table(
        index="month",
        columns="type",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    # 补上可能完全缺失的列
    for col in ("income", "expense"):
        if col not in pivot.columns:
            pivot[col] = 0.0

    result = pd.DataFrame(
        {
            "income": pivot["income"].astype(float),
            "expense": pivot["expense"].astype(float),
            "count": df.groupby("month").size(),
        }
    )
    result["balance"] = result["income"] - result["expense"]
    return result[["income", "expense", "balance", "count"]].sort_index()


def mom_growth(df: pd.DataFrame, col: str = "expense") -> pd.DataFrame:
    """
    环比：每月相比上个月的增幅。
    返回 DataFrame, 含 col, prev, diff, pct(百分比，保留 1 位)。
    第一个月的 pct 为 NaN。
    """
    m = monthly_df(df)
    if m.empty:
        return pd.DataFrame(columns=[col, "prev", "diff", "pct"])

    out = pd.DataFrame(
        {
            col: m[col],
            "prev": m[col].shift(1),
        }
    )
    out["diff"] = out[col] - out["prev"]
    out["pct"] = (out["diff"] / out["prev"].replace(0, np.nan)) * 100
    out["pct"] = out["pct"].round(1)
    return out


def top_categories(
    df: pd.DataFrame, type_: str = "expense", n: int = 5, by: str = "total"
) -> pd.DataFrame:
    """
    分类 Top N。
    by='total' 按总金额排序，by='count' 按笔数排序。
    返回：category, total, count, percent(占该类型总额的百分比)
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "total", "count", "percent"])

    sub = df[df["type"] == type_]
    if sub.empty:
        return pd.DataFrame(columns=["category", "total", "count", "percent"])

    g = (
        sub.groupby("category")
        .agg(
            total=("amount", "sum"),
            count=("amount", "size"),
        )
        .reset_index()
    )

    grand = g["total"].sum() or 1.0
    g["percent"] = (g["total"] / grand * 100).round(1)

    g = g.sort_values(by=by, ascending=False).head(n).reset_index(drop=True)
    return g[["category", "total", "count", "percent"]]


def daily_avg(
    df: pd.DataFrame,
    type_: str = "expense",
    date_from: str | None = None,
    date_to: str | None = None,
) -> float:
    """
    日均支出（或收入）。
    默认按数据实际跨度计算(最早日期 - 最晚日期，含首尾)。
    也可以显示指定区间。
    """
    if df.empty:
        return 0.0

    sub = df[df["type"] == type_]
    if sub.empty:
        return 0.0

    total = sub["amount"].sum()
    if date_from and date_to:
        start = pd.to_datetime(date_from)
        end = pd.to_datetime(date_to)
    else:
        start = sub["date"].min()
        end = sub["date"].max()

    days = (end - start).days + 1
    return float(total / days) if days > 0 else float(total)


def weekday_spending(df: pd.DataFrame, type_: str = "expense") -> pd.DataFrame:
    """
    按星期几汇总支出或收入（0=周一，6=周日）。
    返回：weekday, name, total, count
    """
    if df.empty:
        return pd.DataFrame(columns=["weekday", "name", "total", "count"])

    sub = df[df["type"] == type_].copy()
    if sub.empty:
        return pd.DataFrame(columns=["weekday", "name", "total", "count"])

    sub["weekday"] = sub["date"].dt.dayofweek
    g = (
        sub.groupby("weekday")
        .agg(
            total=("amount", "sum"),
            count=("amount", "size"),
        )
        .reindex(range(7), fill_value=0)
        .reset_index()
    )

    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    g["name"] = g["weekday"].map(lambda i: names[i])
    return g[["weekday", "name", "total", "count"]]


if __name__ == "__main__":
    import display

    df = load_df(g.user["id"])
    display.print_demo_report(
        df=df,
        summary=summary_df(df),
        monthly=monthly_df(df),
        mom=mom_growth(df, "expense"),
        top=top_categories(df, "expense", 5),
        daily=daily_avg(df),
        weekday=weekday_spending(df),
    )
