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