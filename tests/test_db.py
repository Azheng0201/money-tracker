"""db.py 的单元测试。"""
import pytest

# ---------- CRUD ----------
def test_add_and_get(temp_db):
    tid = temp_db.add_transaction("2026-09-10", "income", "工资", 8000, "9月")
    assert tid > 0
    row = temp_db.get_by_id(tid)
    assert row["amount"] == 8000
    assert row["type"] == "income"
    assert row["category"] == "工资"
    assert row["note"] == "9月"

def test_get_nonexistent(temp_db):
    assert temp_db.get_by_id(9999) is None

def test_list_all_order_desc(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-12", "expense", "交通", 10)
    dates = [r["date"] for r in temp_db.list_all()]
    assert dates == ["2026-09-12", "2026-09-11", "2026-09-10"]

def test_update_partial_fields(temp_db):
    tid = temp_db.add_transaction("2026-09-10", "income", "工资", 8000, "原备注")
    ok = temp_db.update_transaction(tid, amount=9000)
    assert ok is True
    row = temp_db.get_by_id(tid)
    assert row["amount"] == 9000
    assert row["note"] == "原备注"

def test_update_nonexistent(temp_db):
    assert temp_db.update_transaction(9999, amount=1) is False

def test_update_no_valid_fields(temp_db):
    tid = temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    # 传了不认识的字段，全部被过滤掉
    assert temp_db.update_transaction(tid, whatever=1) is False

def test_delete_existing(temp_db):
    tid = temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    assert temp_db.delete_transaction(tid) is True
    assert temp_db.get_by_id(tid) is None

def test_delete_nonexistent(temp_db):
    assert temp_db.delete_transaction(9999) is False

# ---------- 筛选 ----------
def test_query_by_month(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-10-01", "expense", "餐饮", 30)
    assert len(temp_db.query_by_month("2026-09")) == 2
    assert len(temp_db.query_by_month("2026-10")) == 1

@pytest.mark.parametrize("bad", ["2026-13", "abc", "2026/09", "202609"])
def test_query_by_month_invalid(temp_db, bad):
    with pytest.raises(ValueError):
        temp_db.query_by_month(bad)

def test_query_half_open_interval(temp_db):
    """[from, to) 语义：含 from，不含 to。"""
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-12", "expense", "交通", 10)
    rows = temp_db.query(date_from="2026-09-11", date_to="2026-09-12")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-09-11"

def test_query_by_type(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-12", "expense", "交通", 10)
    assert len(temp_db.query(type_="expense")) == 2
    assert len(temp_db.query(type_="income")) == 1

def test_query_by_category(temp_db):
    temp_db.add_transaction("2026-09-10", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-11", "expense", "交通", 10)
    assert len(temp_db.query(category="餐饮")) == 1

def test_query_by_keyword(temp_db):
    temp_db.add_transaction("2026-09-10", "expense", "餐饮", 50, "公司午饭")
    temp_db.add_transaction("2026-09-11", "expense", "交通", 10, "地铁")
    assert len(temp_db.query(keyword="午饭")) == 1
    assert len(temp_db.query(keyword="午")) == 1
    assert len(temp_db.query(keyword="不存在")) == 0

# ---------- 汇总 ----------
def test_summary_basic(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-11", "expense", "交通", 10)
    s = temp_db.summary()
    assert s["income"] == 8000
    assert s["expense"] == 60
    assert s["balance"] == 7940
    assert s["count"] == 3
    assert s["income_count"] == 1
    assert s["expense_count"] == 2

def test_summary_empty(temp_db):
    s = temp_db.summary()
    assert s == {"income": 0.0, "expense": 0.0, "balance": 0.0, 
                "count": 0, "income_count": 0, "expense_count": 0}

def test_summary_only_income(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    s = temp_db.summary()
    assert s["expense"] == 0.0
    assert s["balance"] == 8000.0

def test_summary_by_month(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-10-01", "income", "工资", 8000)
    rows = temp_db.summary_by_month()
    assert [r["month"] for r in rows] == ["2026-09", "2026-10"]
    assert rows[0]["balance"] == 7950
    assert rows[1]["balance"] == 8000

def test_summary_by_category_order_and_percent(temp_db):
    temp_db.add_transaction("2026-09-10", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 30)
    temp_db.add_transaction("2026-09-12", "expense", "交通", 20)
    rows = temp_db.summary_by_category("expense")
    # 按金额降序，餐饮80，交通20
    assert rows[0]["category"] == "餐饮"
    assert rows[0]["total"] == 80
    assert rows[0]["count"] == 2
    assert rows[0]["percent"] == 80.0
    assert rows[1]["percent"] == 20.0

def test_list_categories_sorted(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    temp_db.add_transaction("2026-09-12", "expense", "交通", 10)
    cats = temp_db.list_categories()
    assert cats == sorted(cats)
    assert set(cats) == {"工资", "餐饮", "交通"}

def test_list_categories_filter_type(temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)
    assert temp_db.list_categories("expense") == ["餐饮"]
    assert temp_db.list_categories("income") == ["工资"]

# ---------- 约束 ----------
def test_amount_check_constraint(temp_db):
    """amount < 0 应该被数据库拒绝。"""
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.add_transaction("2026-09-10", "expense", "餐饮", -5)

def test_type_check_constraint(temp_db):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.add_transaction("2026-09-10", "wrong", "餐饮", 5)
