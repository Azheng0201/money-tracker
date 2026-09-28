"""io_csv.py 的单元测试。"""
import io_csv

def test_export_import_roundtrip(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000, "9月")
    temp_db.add_transaction(test_user, "2026-09-11", "expense", "餐饮", 38.5, "午饭")

    content = io_csv.export_rows(test_user)
    assert content.startswith("\ufeff")
    assert "工资" in content

    for r in temp_db.list_all(test_user):
        temp_db.delete_transaction(test_user, r["id"])
    assert temp_db.list_all(test_user) == []

    report = io_csv.import_csv(test_user, content)
    assert report["imported"] == 2
    assert report["errors"] == []
    assert len(temp_db.list_all(test_user)) == 2

def test_import_skips_duplicates(temp_db, test_user):
    temp_db.add_transaction(test_user, "2026-09-10", "income", "工资", 8000, "9月")
    content = io_csv.export_rows(test_user)

    reported = io_csv.import_csv(test_user, content, skip_duplicates=True)
    assert reported["imported"] == 0    
    assert reported["skipped"] == 1    

def test_import_bad_rows_collected(temp_db, test_user):
    content = (
        "date,type,category,amount,note\n"
        "2026-09-10,income,工资,8000.00,好数据\n"
        "2026/09/10,expense,餐饮,50,日期格式错\n"
        "2026-09-12,wrong,交通,10,类型错\n"
        "2026-09-13,expense,购物,abc,金额错\n"
    )
    report = io_csv.import_csv(test_user, content)
    assert report["imported"] == 1
    assert len(report["errors"]) == 3
    assert len(temp_db.list_all(test_user)) == 1

def test_import_strips_bom(temp_db, test_user):
    content = "\ufeffdate,type,category,amount,note\n" \
              "2026-09-10,income,工资,8000,9月\n"
    reported = io_csv.import_csv(test_user, content)
    assert reported["imported"] == 1
    assert len(temp_db.list_all(test_user)) == 1

def test_import_empty_note_ok(temp_db, test_user):
    content = "date,type,category,amount,note\n" \
              "2026-09-10,expense,餐饮,50,\n"
    reported = io_csv.import_csv(test_user, content)
    assert reported["imported"] == 1
    row = temp_db.list_all(test_user)[0]
    assert row["note"] == ""