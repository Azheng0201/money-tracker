"""CSV 导入导出。用标准库 csv, 不依赖 pandas。"""
import csv
import io
from datetime import datetime

import db

EXPORT_HEADER = ["date", "type", "category", "amount", "note"]

def export_rows(user_id: int) -> str:
    """
    导出当前用户的全部交易为 CSV 字符串。
    UTF-8 + BOM, 方便 Excel 双击不乱码。
    """
    rows = db.list_all(user_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_HEADER)
    for r in rows:
        writer.writerow([
            r["date"], r["type"], r["category"], 
            f"{r["amount"]:.2f}", r["note"] or "",
        ])
    return "\ufeff" + buf.getvalue()

def import_csv(user_id: int, file_content: str,
               skip_duplicates: bool = False) -> dict:
    """
    从 CSV 文本导入。返回报告：
    {
        "imported": 成功条数,
        "skipped":  跳过条数（去重时才有）,
        "errors":   [(行号，原因), ...]
    }
    """
    # 去掉 BOM
    if file_content.startswith("\ufeff"):
        file_content = file_content[1:]

    reader = csv.DictReader(io.StringIO(file_content))
    report = {"imported": 0, "skipped": 0, "errors": []}

    # 预取现有数据用于去重
    existing = set()
    if skip_duplicates:
        for r in db.list_all(user_id):
            existing.add(_dedup_key(
                r["date"], r["type"], r["category"], r["amount"], r["note"] or ""
            ))

    for lineno, row in enumerate(reader, start=2): # 第一行是表头
        err = _validate_row(row)
        if err:
            report["errors"].append((lineno, err))
            continue

        date_s = row["date"].strip()
        type_ = row["type"].strip()
        category = row["category"].strip()
        amount = round(float(row["amount"]), 2)
        note = (row.get("note") or "").strip()

        if skip_duplicates:
            key = _dedup_key(date_s, type_, category, amount, note)
            if key in existing:
                report["skipped"] += 1
                continue

        db.add_transaction(user_id, date_s, type_, category, amount, note)
        report["imported"] += 1
        if skip_duplicates:
            existing.add(_dedup_key(date_s, type_, category, amount, note))

    return report

def _dedup_key(date_s, type_, category, amount, note):
    """去重键：完全相同才算重复。"""
    return (date_s, type_, category, round(float(amount), 2), note)

def _validate_row(row: dict) -> str | None:
    """校验一行，返回错误信息，没错误返回 None。"""
    required = ["date", "type", "category", "amount"]
    for k in required:
        if k not in row or row[k] is None or not str(row[k]).strip():
            return f"缺少字段 {k}"

    try:
        datetime.strptime(row["date"].strip(), "%Y-%m-%d")
    except ValueError:
        return f"日期格式错误：{row['date']}"

    if row["type"].strip() not in ("income", "expense"):
        return f"类型必须是 income/expense: {row['type']}"

    try:
        amt = float(row["amount"])
        if amt < 0:
            return f"金额不能为负：{row['amount']}"
    except ValueError:
        return f"金额不是数字：{row['amount']}"

    return None