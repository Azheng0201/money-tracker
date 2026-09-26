"""数据隔离测试。alice 看不到也动不了 bob 的数据。"""
from werkzeug.security import generate_password_hash

def _make_user(temp_db, username: str) -> int:
    return temp_db.create_user(username, generate_password_hash("pass1234"))

def test_alice_cannot_see_bobs_transactions(raw_client, temp_db):
    uid_a = _make_user(temp_db, "alice") 
    uid_b = _make_user(temp_db, "bob")
    temp_db.add_transaction(uid_a, "2026-09-10", "income", "工资", 8000)
    temp_db.add_transaction(uid_b, "2026-09-11", "expense", "餐饮", 50)

    # 以 alice 身份登录
    raw_client.post("/login", data={"username": "alice", "password": "pass1234"})
    body = raw_client.get("/transactions").get_data(as_text=True)
    assert "工资" in body
    assert "餐饮" not in body

def test_alice_cannot_edit_bobs(raw_client, temp_db):
    uid_a = _make_user(temp_db, "alice") 
    uid_b = _make_user(temp_db, "bob")
    bob_tx = temp_db.add_transaction(uid_b, "2026-09-11", "expense", "餐饮", 50)

    raw_client.post("/login", data={"username": "alice", "password": "pass1234"})
    r = raw_client.get(f"/edit/{bob_tx}")
    assert r.status_code == 302
    row = temp_db.get_by_id(uid_b, bob_tx)
    assert row is not None

def test_alice_cannot_delete_bobs(raw_client, temp_db):
    uid_a = _make_user(temp_db, "alice") 
    uid_b = _make_user(temp_db, "bob")
    bob_tx = temp_db.add_transaction(uid_b, "2026-09-11", "expense", "餐饮", 50)
    
    raw_client.post("/login", data={"username": "alice", "password": "pass1234"})
    raw_client.post(f"/delete/{bob_tx}")
    assert temp_db.get_by_id(uid_b, bob_tx) is not None

def test_anonymous_redirected_to_login(raw_client):
    r = raw_client.get("/transactions")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]

def test_login_then_redirect_to_next(raw_client, temp_db):
    _make_user(temp_db, "alice")
    r = raw_client.post("/login?next=/transactions", 
                        data={"username": "alice", "password": "pass1234"})
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/transactions")