"""analytics.py 的单元测试。"""

import pandas as pd

import analytics


def test_load_df_empty_has_columns(temp_db, test_user):
    """空表也要有 date / amount 列， 避免下游 .dt 崩溃"""
    df = analytics.load_df(test_user)
    assert df.empty
    assert "date" in df.columns
    assert "amount" in df.columns
    assert "month" in df.columns


def test_load_df_types(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    df = analytics.load_df(test_user)
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_float_dtype(df["amount"])
    assert df.iloc[0]["month"] == "2026-09"


def test_load_df_date_from_or_date_to(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "income", "工资", 8000)
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction(test_user, "2026-11-10", "income", "工资", 8000)
    df1 = analytics.load_df(test_user, date_from="2026-09-10")
    assert len(df1) == 2
    df2 = analytics.load_df(test_user, date_to="2026-09-10")
    assert len(df2) == 1  # [date_from, date_to) 不包含date_to
    df3 = analytics.load_df(test_user, "2026-09-01", "2026-11-10")
    assert len(df3) == 2


def test_summary_df_matches_db(temp_db, test_user):
    """pandas 版汇总和 SQL 版汇总结果必须一致。"""
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction(test_user, "2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction(test_user, "2026-09-11", "expense", "交通", 10)
    s_sql = temp_db.summary(test_user)
    s_pd = analytics.summary_df(analytics.load_df(test_user))
    assert s_sql == s_pd


def test_summary_df_empty(temp_db, test_user):
    s = analytics.summary_df(analytics.load_df(test_user))
    assert s["income"] == 0
    assert s["expense"] == 0
    assert s["count"] == 0


def test_monthly_df_two_months(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction(test_user, "2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction(test_user, "2026-10-01", "income", "工资", 8000)
    m = analytics.monthly_df(analytics.load_df(test_user))
    assert list(m.index) == ["2026-09", "2026-10"]
    assert m.loc["2026-09", "balance"] == 7950
    assert m.loc["2026-10", "balance"] == 8000


def test_monthly_df_missing_income_column(temp_db, test_user):
    """整月只有支出时，income 列必须存在且为 0。"""
    temp_db.add_transaction(test_user, "2026-09-11", "expense", "餐饮", 50)
    m = analytics.monthly_df(analytics.load_df(test_user))
    assert "income" in m.columns
    assert m.loc["2026-09", "income"] == 0
    assert m.loc["2026-09", "balance"] == -50


def test_monthly_df_empty(temp_db, test_user):
    m = analytics.monthly_df(analytics.load_df(test_user))
    assert len(m) == 0
    assert "income" in m.columns


def test_mom_growth(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "expense", "餐饮", 100)
    temp_db.add_transaction(test_user, "2026-10-01", "expense", "餐饮", 150)
    g = analytics.mom_growth(analytics.load_df(test_user), "expense")
    assert pd.isna(g.iloc[0]["pct"])
    assert g.iloc[1]["pct"] == 50.0


def test_mom_growth_zero_prev(temp_db, test_user):
    """上月为 0 时不返回 inf，而是 NaN。"""
    temp_db.add_transaction(test_user, "2026-09-01", "income", "工资", 0.001)
    temp_db.add_transaction(test_user, "2026-10-01", "expense", "餐饮", 50)
    g = analytics.mom_growth(analytics.load_df(test_user), "expense")
    assert pd.isna(g.loc["2026-10", "pct"])


def test_mom_growth_empty(temp_db, test_user):
    df = analytics.mom_growth(analytics.load_df(test_user), "expense")
    assert "expense" in df.columns
    assert "prev" in df.columns


def test_top_categories_order_by_amount(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "expense", "餐饮", 50)
    temp_db.add_transaction(test_user, "2026-09-02", "expense", "餐饮", 30)
    temp_db.add_transaction(test_user, "2026-09-03", "expense", "交通", 20)
    top = analytics.top_categories(analytics.load_df(test_user), "expense", 2)
    assert len(top) == 2
    assert top.iloc[0]["category"] == "餐饮"
    assert top.iloc[0]["total"] == 80
    assert top.iloc[0]["percent"] == 80.0


def test_top_categories_order_by_count(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "expense", "餐饮", 5)
    temp_db.add_transaction(test_user, "2026-09-02", "expense", "餐饮", 5)
    temp_db.add_transaction(test_user, "2026-09-03", "expense", "餐饮", 5)
    temp_db.add_transaction(test_user, "2026-09-04", "expense", "交通", 100)
    top = analytics.top_categories(analytics.load_df(test_user), "expense", 2, by="count")
    assert top.iloc[0]["category"] == "餐饮"


def test_top_categories_empty(temp_db, test_user):
    top = analytics.top_categories(analytics.load_df(test_user), "expense", 2, by="count")
    assert len(top) == 0
    assert "percent" in top.columns


def test_top_categoties_without_expense(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "income", "红包", 5)
    temp_db.add_transaction(test_user, "2026-09-02", "income", "红包", 5)
    temp_db.add_transaction(test_user, "2026-09-03", "income", "红包", 5)
    temp_db.add_transaction(test_user, "2026-09-04", "income", "红包", 10)
    top = analytics.top_categories(analytics.load_df(test_user), "expense", 2, by="count")
    assert len(top) == 0
    assert "percent" in top.columns


def test_daily_avg_span_inclusive(temp_db, test_user):
    """3 天跨度，首尾都算 → 平均 = 60 / 3 = 20。"""
    temp_db.add_transaction(test_user, "2026-09-01", "expense", "餐饮", 10)
    temp_db.add_transaction(test_user, "2026-09-02", "expense", "餐饮", 20)
    temp_db.add_transaction(test_user, "2026-09-03", "expense", "餐饮", 30)
    assert analytics.daily_avg(analytics.load_df(test_user)) == 20


def test_daily_avg_explicit_range(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "expense", "餐饮", 100)
    # 显示指定 10 天 → 100 / 10 = 10
    avg = analytics.daily_avg(analytics.load_df(test_user), "expense", "2026-09-01", "2026-09-10")
    assert avg == 10.0


def test_daily_avg_empty(temp_db, test_user):
    assert analytics.daily_avg(analytics.load_df(test_user)) == 0.0


def test_daily_avg_sub_empty(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-01", "income", "红包", 10)
    assert analytics.daily_avg(analytics.load_df(test_user), "expense") == 0.0


def test_weekday_spending(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-14", "expense", "餐饮", 10)
    temp_db.add_transaction(test_user, "2026-09-15", "expense", "餐饮", 20)
    w = analytics.weekday_spending(analytics.load_df(test_user))
    assert len(w) == 7
    assert w.loc[w["weekday"] == 0, "total"].iloc[0] == 10
    assert w.loc[w["weekday"] == 1, "total"].iloc[0] == 20
    assert w.loc[w["weekday"] == 6, "total"].iloc[0] == 0


def test_weekday_spending_empty(temp_db, test_user):
    w = analytics.weekday_spending(analytics.load_df(test_user))
    assert len(w) == 0
    assert "weekday" in w.columns


def test_weekday_spending_sub_empty(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-14", "income", "红包", 10)
    temp_db.add_transaction(test_user, "2026-09-15", "income", "红包", 20)
    w = analytics.weekday_spending(analytics.load_df(test_user), "expense")
    assert len(w) == 0
    assert "weekday" in w.columns
