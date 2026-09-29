"""预算功能测试。"""
import pytest

def test_set_budget_insert(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 500)
    rows = temp_db.list_budgets(test_user)
    assert len(rows) == 1
    assert rows[0]["category"] == "餐饮"
    assert rows[0]["monthly_limit"] == 500

def test_set_budget_upsert(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 500)
    temp_db.set_budget(test_user, "餐饮", 800)
    rows = temp_db.list_budgets(test_user)
    assert len(rows) == 1
    assert rows[0]["monthly_limit"] == 800

def test_delete_budget(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 500)
    assert temp_db.delete_budget(test_user, "餐饮") is True
    assert temp_db.delete_budget(test_user, "餐饮") is False
    assert temp_db.list_budgets(test_user) == []

def test_check_budgets_ok(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 1000)
    temp_db.add_transaction(test_user, "2026-09-10", "expense", "餐饮", 300)
    checks = temp_db.check_budgets(test_user, "2026-09")
    assert len(checks) == 1
    c = checks[0]
    assert c["spent"] == 300
    assert c["remaining"] == 700
    assert c["percent"] == 30.0
    assert c["status"] == "ok"

def test_check_budgets_warning(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 1000)
    temp_db.add_transaction(test_user, "2026-09-10", "expense", "餐饮", 850)
    c = temp_db.check_budgets(test_user, "2026-09")[0]
    assert c["status"] == "warning"

def test_check_budgets_over(temp_db, test_user):
    temp_db.set_budget(test_user, "餐饮", 1000)
    temp_db.add_transaction(test_user, "2026-09-10", "expense", "餐饮", 1200)
    c = temp_db.check_budgets(test_user, "2026-09")[0]
    assert c["status"] == "over"
    assert c["remaining"] == -200

def test_check_budgets_no_spending(temp_db, test_user):
    """有预算但是没花钱，spent=0，percent=0。"""
    temp_db.set_budget(test_user, "宠物", 200)
    c = temp_db.check_budgets(test_user, "2026-09")[0]
    assert c["spent"] == 0
    assert c["percent"] == 0.0
    assert c["status"] == "ok"

def test_check_budgets_only_expense(temp_db, test_user):
    """收入不影响预算"""
    temp_db.set_budget(test_user, "工资", 1000)
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000)
    c = temp_db.check_budgets(test_user, "2026-09")[0]
    assert c["spent"] == 0

def test_check_budgets_month_isolation(temp_db, test_user):
    """9 月的支出不影响 10 月的预算执行。"""
    temp_db.set_budget(test_user, "餐饮", 1000)
    temp_db.add_transaction(test_user, "2026-09-15", "expense", "餐饮", 500)
    c9 = temp_db.check_budgets(test_user, "2026-09")[0]
    c10 = temp_db.check_budgets(test_user, "2026-10")[0]
    assert c9["spent"] == 500
    assert c10["spent"] == 0

def test_month_range_valid():
    import db
    assert db.month_range("2026-09") == ("2026-09-01", "2026-10-01")
    assert db.month_range("2026-12") == ("2026-12-01", "2027-01-01")

@pytest.mark.parametrize("bad", ["2026-13", "abc", "2026/09", "202609", ""])
def test_month_range_invalid(bad):
    import db
    with pytest.raises(ValueError):
        db.month_range(bad)