"""Flask 层的集成测试。"""

# ---------- 基础页面 ----------
def test_index_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "MoneyTracker" in r.get_data(as_text=True)

def test_index_empty_db(client):
    """空数据库首页不能崩。"""
    r = client.get("/")
    assert r.status_code == 200

def test_transactions_200_empty(client):
    r = client.get("/transactions")
    assert r.status_code == 200
    assert "还没有任何交易" in r.get_data(as_text=True) \
        or "还没有任何记录" in r.get_data(as_text=True) \
        or "没有符合" in r.get_data(as_text=True)

# ---------- /add ----------
def test_add_get_shows_form(client):
    r = client.get("/add")
    assert r.status_code == 200
    assert "添加交易" in r.get_data(as_text=True)

def test_add_post_success(client, temp_db):
    r = client.post("/add", data={
        "date": "2026-09-10", "type": "income",
        "category": "工资", "amount": "8000", "note": "9月",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert "已添加交易" in r.get_data(as_text=True)
    rows = temp_db.list_all()
    assert len(rows) == 1
    assert rows[0]["amount"] == 8000

def test_add_post_invalid_amount(client, temp_db):
    r = client.post("/add", data={
            "date": "2026-09-10", "type": "income",
            "category": "工资", "amount": "abc", "note": "",
    })
    assert r.status_code == 200
    assert "金额必须是数字" in r.get_data(as_text=True)
    assert len(temp_db.list_all()) == 0

def test_add_post_empty_category(client, temp_db):
    r = client.post("/add", data={
            "date": "2026-09-10", "type": "income",
            "category": "", "amount": "100",
    })
    assert "分类不能为空" in r.get_data(as_text=True)
    assert len(temp_db.list_all()) == 0

def test_add_post_invalid_date(client, temp_db):
    r = client.post("/add", data={
            "date": "2026/09/10", "type": "income",
            "category": "工资", "amount": "100",
    })
    assert "日期格式" in r.get_data(as_text=True)
    assert len(temp_db.list_all()) == 0

def test_add_post_invalid_type(client, temp_db):
    r = client.post("/add", data={
            "date": "2026-09-10", "type": "wrong",
            "category": "工资", "amount": "100",
    })
    assert "类型必须是收入或支出" in r.get_data(as_text=True)
    assert len(temp_db.list_all()) == 0

def test_add_form_keeps_input_on_error(client):
    """校验失败时，用户之前填的内容要回填。"""
    r = client.post("/add", data={
        "date": "2026-09-10", "type": "income",
        "category": "工资", "amount": "abc", "note": "备注不回丢",
    })
    body = r.get_data(as_text=True)
    assert "工资" in body
    assert "备注不回丢" in body

# ---------- /edit ----------
def _add_one(temp_db, **kw) -> int:
    defaults = dict(date="2026-09-10", type_="income",
                    category="工资", amount=8000, note="测试")
    defaults.update(kw)
    return temp_db.add_transaction(
        defaults["date"], defaults["type_"],
        defaults["category"], defaults["amount"], defaults["note"]
    )

def test_edit_get_prefills(client, temp_db):
    tid = _add_one(temp_db)
    r = client.get(f"/edit/{tid}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "编辑交易" in body
    assert "工资" in body
    assert "8000" in body

def test_edit_nonexistent_redirects(client):
    r = client.get("/edit/9999")
    assert r.status_code == 302
    assert "/transactions" in r.headers["Location"]

def test_edit_post_updates(client, temp_db):
    tid = _add_one(temp_db)
    r = client.post(f"/edit/{tid}", data={
        "date": "2026-09-11", "type": "expense",
        "category": "购物", "amount": "129.9", "note": "键盘",
    }, follow_redirects=True)
    assert "已更新" in r.get_data(as_text=True)
    row = temp_db.get_by_id(tid)
    assert row["amount"] == 129.9
    assert row["category"] == "购物"
    assert row["type"] == "expense"

def test_eidt_post_invalid_keeps_changes_uncommitted(client, temp_db):
    tid = _add_one(temp_db)
    client.post(f"/edit/{tid}", data={
        "date": "2026-09-11", "type": "expense",
        "category": "购物", "amount": "abc",
    })
    row = temp_db.get_by_id(tid)
    assert row["amount"] == 8000
    assert row["category"] == "工资"

# ---------- /delete ----------
def test_delete_post_removes(client, temp_db):
    tid = _add_one(temp_db)
    r = client.post(f"/delete/{tid}", follow_redirects=True)
    assert "已删除" in r.get_data(as_text=True)
    assert temp_db.get_by_id(tid) is None

def test_delete_get_method_not_allowed(client, temp_db):
    """GET /delete/<id> 必须是 405。"""
    tid = _add_one(temp_db)
    r = client.get(f"/delete/{tid}")
    assert r.status_code == 405
    assert temp_db.get_by_id(tid) is not None

def test_delete_nonexistent(client):
    r = client.post("/delete/99999", follow_redirects=True)
    assert "没有" in r.get_data(as_text=True)

# ---------- 筛选 / 分页 ----------
def test_transactions_filter_by_type(client, temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-09-11", "expense", "餐饮", 50)

    r = client.get("/transactions?type=expense")
    body = r.get_data(as_text=True)
    assert "餐饮" in body
    assert "<td>工资</td>" not in body

def test_transactions_filter_by_month(client, temp_db):
    temp_db.add_transaction("2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction("2026-10-10", "income", "工资", 8000)

    r = client.get("/transactions?month=2026-09")
    body = r.get_data(as_text=True)
    assert "2026-09-10" in body
    assert "2026-10-10" not in body

def test_transactions_pagination(client, temp_db):
    for i in range(25):
        temp_db.add_transaction(f"2026-09-{i+1:02d}",
                                "expense", "餐饮", 10)
    r1 = client.get("/transactions?page=1")
    r2 = client.get("/transactions?page=2")
    assert "第 1 / 2 页" in r1.get_data(as_text=True)
    assert "第 2 / 2 页" in r2.get_data(as_text=True)

def test_transactions_page_out_of_range(client, temp_db):
    temp_db.add_transaction("2026-09-10", "expense", "餐饮", 10)
    r = client.get("/transactions?page=999")
    assert r.status_code == 200
    assert "第 1 / 1 页" in r.get_data(as_text=True) \
        or "共 1" in r.get_data(as_text=True) \
        or "没有符合" in r.get_data(as_text=True)

def test_transactions_filter_keeps_filter_on_page_2(client, temp_db):
    """翻页时筛选条件不丢。"""
    for i in range(25):
        temp_db.add_transaction(f"2026-09-{i+1:02d}",
                                "expense", "餐饮", 10)

    r = client.get("/transactions?type=expense&page=2")
    body = r.get_data(as_text=True)
    assert "type=expense" in body