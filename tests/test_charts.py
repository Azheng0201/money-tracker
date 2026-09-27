"""charts.py 的单元测试。"""

import pytest

import analytics
import charts


def _make_df(temp_db, user_id):
    temp_db.add_transaction(user_id, "2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction(user_id, "2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction(user_id, "2026-09-12", "expense", "交通", 10)
    temp_db.add_transaction(user_id, "2026-10-01", "expense", "购物", 200)
    return analytics.load_df(user_id)


# ---------- 正常生成 ----------
def test_bar_monthly_creates_file(temp_db, test_user, tmp_path):
    df = _make_df(temp_db, test_user)
    out = tmp_path / "bar.png"
    path = charts.bar_monthly(df, out)
    assert path.exists()
    assert path.stat().st_size > 0


def test_pie_categories_creates_file(temp_db, test_user, tmp_path):
    df = _make_df(temp_db, test_user)
    out = tmp_path / "pie.png"
    path = charts.pie_categories(df, "expense", path=out)
    assert path.exists()
    assert path.stat().st_size > 0


def test_line_balance_creates_file(temp_db, test_user, tmp_path):
    df = _make_df(temp_db, test_user)
    out = tmp_path / "line.png"
    path = charts.line_balance(df, out)
    assert path.exists()
    assert path.stat().st_size > 0


def test_generate_all(temp_db, test_user, tmp_path, monkeypatch):
    """测 generate_all 一次生成三张图。"""
    monkeypatch.setattr(charts, "CHART_DIR", tmp_path)

    df = _make_df(temp_db, test_user)
    paths = charts.generate_all(df)

    assert len(paths) == 3
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 0


# -------- 错误路径 --------
def test_bar_monthly_empty_raises(temp_db, test_user, tmp_path):
    df = analytics.load_df(test_user)
    with pytest.raises(ValueError):
        charts.bar_monthly(df, path=tmp_path / "x.png")


def test_pie_category_no_expense_raises(temp_db, test_user, tmp_path):
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    df = analytics.load_df(test_user)
    with pytest.raises(ValueError):
        charts.pie_categories(df, "expense", path=tmp_path / "x.png")


def test_generate_all_skips_on_empty(temp_db, test_user, tmp_path, monkeypatch):
    monkeypatch.setattr(charts, "CHART_DIR", tmp_path)
    df = analytics.load_df(test_user)
    paths = charts.generate_all(df)
    assert paths == []
