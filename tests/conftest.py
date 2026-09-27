"""pytest 公共 fixture: 每个测试一个独立的临时数据库。"""

import sys
from pathlib import Path

import pytest

# 让测试能导入项目根目录里的 db / analytics
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """
    每个测试拿到一个全新的空数据库。
    monkeypatch 把 db.DB_PATH 指向 tmp_path 下的 test.db,
    测试结束自动清理，不会污染 data/finance.db。
    """
    import db as db_module

    test_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_path)
    db_module.init_db()
    yield db_module


@pytest.fixture
def raw_client(temp_db, monkeypatch):
    """
    未登录的原始 client。
    每个测试拿到一个 Flask 测试客户端，指向临时数据库。
    同时禁用 _ensure_charts, 避免每次请求都跑 matplotlib。
    """
    import app as app_module

    monkeypatch.setattr(app_module, "_ensure_charts", lambda: None)
    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def client(raw_client):
    """默认已登录的 client"""
    raw_client.post(
        "/register",
        data={
            "username": "tester",
            "password": "pass1234",
            "confirm": "pass1234",
        },
    )
    return raw_client


@pytest.fixture
def test_user(temp_db):
    """创建一个测试用户，返回其 id。所有交易相关测试直接用它。"""
    return temp_db.create_user("testuser", "fake_hash_for_test")


@pytest.fixture
def tester_id(temp_db, client):
    """获取 client fixture 自动登录的 tester 用户的 id。"""
    u = temp_db.get_user_by_username("tester")
    return u["id"]
