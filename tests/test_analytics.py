"""analytics.py 的单元测试。"""
import pandas as pd
import pytest

import analytics

def test_load_df_empty_has_columns(temp_db):
    """空表也要有 date / amount 列， 避免下游 .dt 崩溃"""
    df = analytics.load_df()
    assert df.empty
    assert "date" in df.columns
    assert "amount" in df.columns
    assert "month" in df.columns

def test_load_df_types(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    df = analytics.load_df()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_float_dtype(df["amount"])
    assert df.iloc[0]["month"] == "2026-09"

def test_summary_df_matches_db(temp_db):
    """pandas 版汇总和 SQL 版汇总结果必须一致。"""
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-11", "expense", "交通", 10)
    s_sql = temp_db.summary()
    s_pd = analytics.summary_df(analytics.load_df())
    assert s_sql == s_pd

def test_summary_df_empty(temp_db):
    s = analytics.summary_df(analytics.load_df())
    assert s["income"] == 0
    assert s["expense"] == 0
    assert s["count"] == 0

def test_monthly_df_two_months(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-10-01", "income", "工资", 8000)
    m = analytics.monthly_df(analytics.load_df())
    assert list(m.index) == ["2026-09", "2026-10"]
    assert m.loc["2026-09", "balance"] == 7950
    assert m.loc["2026-10", "balance"] == 8000

def test_monthly_df_missing_income_column(temp_db):
    """整月只有支出时，income 列必须存在且为 0。"""
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    m = analytics.monthly_df(analytics.load_df())
    assert "income" in m.columns
    assert m.loc["2026-09", "income"] == 0
    assert m.loc["2026-09", "balance"] == -50

def test_mom_growth(temp_db):
    temp_db.add_transaction("2026-09-01", "expense", "餐饮", 100)
    temp_db.add_transaction("2026-10-01", "expense", "餐饮", 150)
    g = analytics.mom_growth(analytics.load_df(), "expense")
    assert pd.isna(g.iloc[0]["pct"])
    assert g.iloc[1]["pct"] == 50.0

def test_mom_growth_zero_prev(temp_db):
    """上月为 0 时不返回 inf，而是 NaN。"""
    temp_db.add_transaction("2026-09-01", "income", "工资", 0.001)
    temp_db.add_transaction("2026-10-01", "expense", "餐饮", 50)
    g = analytics.mom_growth(analytics.load_df(), "expense")
    assert pd.isna(g.loc["2026-10", "pct"])

def test_top_categories_order_by_amount(temp_db):
    temp_db.add_transaction("2026-09-01", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-02", "expense", "餐饮", 30)
    temp_db.add_transaction("2026-09-03", "expense", "交通", 20)
    top = analytics.top_categories(analytics.load_df(), "expense", 2)
    assert len(top) == 2
    assert top.iloc[0]["category"] == "餐饮"
    assert top.iloc[0]["total"] == 80
    assert top.iloc[0]["percent"] == 80.0

def test_top_categories_order_by_count(temp_db):
    temp_db.add_transaction("2026-09-01", "expense", "餐饮", 5)
    temp_db.add_transaction("2026-09-02", "expense", "餐饮", 5)
    temp_db.add_transaction("2026-09-03", "expense", "餐饮", 5)
    temp_db.add_transaction("2026-09-04", "expense", "交通", 100)
    top = analytics.top_categories(analytics.load_df(), "expense", 2, by="count")
    assert top.iloc[0]["category"] == "餐饮"

def test_daily_avg_span_inclusive(temp_db):
    """3 天跨度，首尾都算 → 平均 = 60 / 3 = 20。"""
    temp_db.add_transaction("2026-09-01", "expense", "餐饮", 10)
    temp_db.add_transaction("2026-09-02", "expense", "餐饮", 20)
    temp_db.add_transaction("2026-09-03", "expense", "餐饮", 30)
    assert analytics.daily_avg(analytics.load_df()) == 20

def test_daily_avg_explicit_range(temp_db):
    temp_db.add_transaction("2026-09-01", "expense", "餐饮", 100)
    # 显示指定 10 天 → 100 / 10 = 10
    avg = analytics.daily_avg(analytics.load_df(), "expense",
                              "2026-09-01", "2026-09-10")
    assert avg == 10.0

def test_daily_avg_empty(temp_db):
    assert analytics.daily_avg(analytics.load_df()) == 0.0

def test_weekday_spending(temp_db):
    temp_db.add_transaction("2026-09-14", "expense", "餐饮", 10)
    temp_db.add_transaction("2026-09-15", "expense", "餐饮", 20)
    w = analytics.weekday_spending(analytics.load_df())
    assert len(w) == 7
    assert w.loc[w["weekday"] == 0, "total"].iloc[0] == 10
    assert w.loc[w["weekday"] == 1, "total"].iloc[0] == 20
    assert w.loc[w["weekday"] == 6, "total"].iloc[0] == 0