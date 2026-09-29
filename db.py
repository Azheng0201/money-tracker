import sqlite3
from datetime import datetime as _dt
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "finance.db"

def get_conn() -> sqlite3.Connection:
    """返回一个连接， row 可以像字典一样用列名访问。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """建表(已存在则表示跳过)。"""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                note TEXT DEFAULT ''
            )
            """
        )
        # users 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                category      TEXT    NOT NULL,
                monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                UNIQUE(user_id, category)
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON transactions(type)")

    _migrate_add_user_id()

def _migrate_add_user_id() -> None:
    """
    给 transactions 表加 user_id 列。
    已有数据归给 legacy 用户。
    """
    with get_conn() as conn:
        cols = [r["name"] for r in
                conn.execute("PRAGMA table_info(transactions)").fetchall()]
        if "user_id" in cols:
            return  # 已经迁移过

        print("[migration] transactions 表增加 user_id 列...")
        conn.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER")

        # 保证 legacy 用户存在
        row = conn.execute(
            "SELECT id FROM users WHERE username = 'legacy'").fetchone()
        if row:
            legacy_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO users(username, password_hash, created_at) "
                "VALUES (?, ?, ?)",
                ("legacy", "!", _dt.now().isoformat(timespec="seconds")),
            )
            legacy_id = cur.lastrowid

        n = conn.execute(
            "UPDATE transactions SET user_id = ? WHERE user_id IS NULL",
            (legacy_id,),
        ).rowcount
        print(f"[migration] 已把 {n} 条旧数据归给 legacy 用户 (id={legacy_id})")

def migrate() -> None:
    """运行所有需要的迁移。开放在 init_db 之后调用。"""
    _migrate_add_user_id()


def month_range(ym: str) -> tuple[str, str]:
    """把 'YYYY-MM' 换成 （本月1号，下月1号）的半开区间。"""
    if len(ym) != 7 or ym[4] != "-":
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = ym.split("-")
    if not (y.isdigit() and m.isdigit() and 1 <= int(m) <= 12):
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = int(y), int(m)
    start = f"{y:04d}-{m:02d}-01"
    end = f"{y + 1:04d}-01-01" if m == 12 else f"{y:04d}-{m + 1:02d}-01"
    return start, end


def add_transaction(user_id: int, date: str, type_: str, category: str,
                    amount: float, note: str = "") -> int:
    """添加一条交易记录，返回新记录的 id。"""
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO transactions (user_id, date, type, category, amount, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, date, type_, category, float(amount), note)
        )
        return cursor.lastrowid

def _build_where(user_id, date_from=None, date_to=None, type_=None,
                 category=None, keyword=None) -> tuple[str, list]:
    """构造 WHERE 子句和参数列表。date_to 是排他边界。"""
    sql = " WHERE user_id = ?"
    params: list = [user_id]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date < ?"
        params.append(date_to)
    if type_:
        sql += " AND type =  ?"
        params.append(type_)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if keyword:
        sql += " AND (note LIKE ? OR category LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like])
    return sql, params

def list_all(user_id: int) -> list[sqlite3.Row]:
    """返回所有交易记录，按日期降序排列。"""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM transactions WHERE user_id = ? "
                              "ORDER BY date DESC, id DESC", (user_id,))
        return cursor.fetchall()

def list_months(user_id: int) -> list[str]:
    """返回有数据的月份， 倒序。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(date, 1, 7) as m "
            "FROM transactions WHERE user_id = ? ORDER BY m DESC", (user_id,),
        ).fetchall()
    return [r["m"] for r in rows]

def recent_transactions(user_id: int, limit: int = 5) -> list[sqlite3.Row]:
    """最近 N 条交易，按日期倒序。limit 必须为正整数。"""
    if limit <= 0:
        return []
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

def get_by_id(user_id: int, tid: int) -> sqlite3.Row | None:
    """根据 id 获取交易记录，找不到返回 None。"""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?",
                              (tid, user_id),)
        return cursor.fetchone()

def query(user_id, date_from=None, date_to=None, type_=None,
          category=None, keyword=None):
    where, params = _build_where(user_id, date_from, date_to, type_, category, keyword)
    sql = ("SELECT * FROM transactions" + where +
           " ORDER BY date DESC, id DESC")

    with get_conn() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

def query_paged(user_id, page=1, per_page=20, date_from=None, date_to=None,
                type_=None, category=None, keyword=None):
    """
    分页查询。返回（rows, total_count）。
    page 从 1 开始。conditions 同 query()。
    """
    page = max(1, int(page))
    per_page = max(1, int(per_page))
    offset = (page - 1) * per_page

    where, params = _build_where(user_id, date_from, date_to, type_, category, keyword)

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM transactions{where}", params
        ).fetchone()["n"]

        rows = conn.execute(
            f"SELECT * FROM transactions{where} "
            f"ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()
    return rows, int(total)

def query_by_month(user_id, ym: str) -> list[sqlite3.Row]:
    """
    按月份查询，ym 格式: YYYY-MM
    返回该月所有交易记录，用 [本月1号, 下月1号)的区间。
    """
    if len(ym) != 7 or ym[4] != "-":
        raise ValueError("月份格式应为 YYYY-MM")

    year, month = ym.split("-")
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        raise ValueError("月份格式应为 YYYY-MM")

    y, m = int(year), int(month)
    start = f"{y:04d}-{m:02d}-01"
    if m == 12:
        end = f"{y+1:04d}-01-01"
    else:
        end = f"{y:04d}-{m+1:02d}-01"

    sql = ("SELECT * FROM transactions WHERE user_id = ? AND date >= ? AND date < ? "
           "ORDER BY date DESC, id DESC")
    with get_conn() as conn:
        cursor = conn.execute(sql, (user_id, start, end))
        return cursor.fetchall()

def list_categories(user_id: int, type_: str | None = None) -> list[str]:
    """
    返回所有分类，按字母升序排列。
    如果 type_ 为 "income" 或 "expense"，则只返回该类型的分类。
    """
    sql = "SELECT DISTINCT category FROM transactions WHERE user_id = ?"
    params: list = [user_id]
    if type_:
        sql += " AND type = ?"
        params.append(type_)
    sql += " ORDER BY category"

    with get_conn() as conn:
        return [r["category"] for r in conn.execute(sql, params)]

def summary(user_id: int, date_from=None, date_to=None) -> dict:
    """
    返回一个区间内的汇总。
    - date_from / date_to 格式: YYYY-MM-DD，半开区间[date_from, date_to)
    {
        "income": 收入合计,
        "expense": 支出合计,
        "balance": 结余 = income - expense,
        "count": 总笔数,
        "income_count": 收入笔数,
        "expense_count": 支出笔数,
    }
    没有匹配记录时各项为0
    """
    where, params = _build_where(user_id, date_from, date_to)
    sql = f"""
        SELECT 
            COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense,
            COUNT(*) as count,
            SUM(CASE WHEN type='income' THEN 1 ELSE 0 END) AS income_count,
            SUM(CASE WHEN type='expense' THEN 1 ELSE 0 END) AS expense_count
        FROM transactions{where}
    """

    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()

    income = float(row['income'] or 0)
    expense = float(row['expense'] or 0)
    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "count": int(row["count"] or 0),
        "income_count": int(row["income_count"] or 0),
        "expense_count": int(row["expense_count"] or 0),
    }

def summary_by_month(user_id: int, date_from: str | None = None,
            date_to: str | None = None) -> list[dict]:
    """
    按月汇总，返回列表（按月份升序）：
    [{"month": "2026-09", "income": .., "expense": .., "balance": .., "count": ..,}, ...]
    - date_from / date_to 格式: YYYY-MM-DD，半开区间[date_from, date_to)
    """
    where, params = _build_where(user_id, date_from, date_to)
    sql = f"""
        SELECT 
            substr(date, 1, 7) AS month,
            COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense,
            COUNT(*) as count 
        FROM transactions{where}
    """

    sql += " GROUP BY month ORDER BY month"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            "month": r["month"],
            "income": float(r["income"] or 0),
            "expense": float(r["expense"] or 0),
            "balance": float((r["income"] or 0) - (r["expense"] or 0)),
            "count": int(r["count"] or 0),
        }
        for r in rows
    ]

def summary_by_category(user_id: int, type_: str | None = None,
                        date_from: str | None = None,
                        date_to: str | None = None) -> list[dict]:
    """
    按分类汇总，默认统计支出。
    返回列表（按金额降序）：
    [{"category": "餐饮", "total": 123.4, "count": 5, "percent": 32.1}, ...]
    percent 是占该 type_ 总额的比例（0-100，保留1位小数）
    - date_from / date_to 格式: YYYY-MM-DD，半开区间[date_from, date_to)
    """
    where, params = _build_where(user_id, date_from, date_to, type_)
    sql = f"""
        SELECT category,
               SUM(amount) AS total,
               COUNT(*) AS count
        FROM transactions{where}
    """
    sql += " GROUP BY category ORDER BY total DESC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    grand = sum(float(r["total"] or 0) for r in rows) or 1.0
    return [
        {
            "category": r["category"],
            "total": float(r["total"] or 0),
            "count": float(r["count"] or 0),
            "percent": round(float(r["total"] or 0) / grand * 100, 1),
        }
        for r in rows
    ]

def update_transaction(user_id: int, tid: int, **fields) -> bool:
    """
    按 id 更新交易。支持的字段：date, type, category, amout, note。
    返回 True 表示更新成功，False 表示找不到该 id 或没有字段可更新。
    """
    allowed = {"date", "type", "category", "amount", "note"}
    updates = {k: v for k, v in fields.items() if k in allowed}

    if not updates:
        return False
    if not get_by_id(user_id, tid):
        return False

    # amount 强制转 float，防止上层传递 str
    if "amount" in updates:
        updates["amount"] = float(updates["amount"])

    # 构建更新语句
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [tid, user_id]

    with get_conn() as conn:
        conn.execute(f"UPDATE transactions SET {set_clause} "
                     f"WHERE id = ? AND user_id = ?", values,)
    return True

def delete_transaction(user_id: int, tid: int) -> bool:
    """按 id 删除交易，返回 True 表示删除成功，False 表示找不到该 id。"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?",
                           (tid, user_id))
        return cur.rowcount > 0

# ---- 冒烟测试：直接运行本文件时执行 ----
# if __name__ == "__main__":
#     init_db()
#     print("✅数据库初始化完成。", DB_PATH)

#     # 只在空库时插入示例，避免重复运行搞脏数据
#     if not list_all():
#         add_transaction("2026-09-10", "income", "工资", 8000, "9月工资")
#         add_transaction("2026-09-11", "expense", "餐饮", 38.50, "午餐")
#         add_transaction("2026-09-11", "expense", "交通", 12.00, "地铁")
#         print("✅插入3条示例数据。")

#     print("\n🗒️ 当前所有交易：")
#     for row in list_all():
#         print(f" [{row['id']}] {row['date']} {row['type']:<7} "
#               f"{row['category']:<4} {row['amount']:>8.2f} {row['note']}")

#     # 临时测试 update / delete
#     print("\n 🔧 测试 update_transaction: ")
#     ok = update_transaction(2, amount=45.00, note="午饭涨价了")
#     print("  更新 id=2:", "成功" if ok else "失败")
#     print("  当前 id=2:", dict(get_by_id(2)))

#     print("\n 🗑️ 测试 delete_transaction: ")
#     ok = delete_transaction(3)
#     print("  删除 id=3:", "成功" if ok else "失败")
#     print("  剩余条数：", len(list_all()))

def create_user(username: str, password_hash: str) -> int:
    """
    注册新用户。用户名重复会抛出 sqlite3.IntegrityError。
    返回新用户 id。
    """
    now = _dt.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, created_at) "
            "VALUES (?, ?, ?)",
            (username, password_hash, now)
        )
        return cur.lastrowid

def get_user_by_username(username: str):
    """按用户名查询用户，不存在则返回 None。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

def get_user_by_id(user_id: int):
    """按 id 查询用户，不存在则返回 None。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()

def set_budget(user_id: int, category: str, monthly_limit: float) -> None:
    """
    设置或更新预算。同一用户同一分类唯一。
    用 ON CONFLICT 做 upsert——一条 SQL 搞定"有则更新、无则插入"。
    """
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO budgets(user_id, category, monthly_limit)
            VALUES (?, ?, ?) 
            ON CONFLICT(user_id, category) 
            DO UPDATE SET monthly_limit = excluded.monthly_limit
        """, (user_id, category, float(monthly_limit)))

def delete_budget(user_id: int, category: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM budgets WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        return cur.rowcount > 0

def list_budgets(user_id: int) -> list[sqlite3.Row]:
    """按分类名排序返回所有预算。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM budgets WHERE user_id = ? ORDER BY category",
            (user_id,),
        ).fetchall()

def check_budgets(user_id: int, ym: str) -> list[dict]:
    """
    检查指定月份的预算执行情况。
    只统计 expense。没有预算的分类不返回。
    返回：
    [
        {"category": "餐饮", "limit": 500, "spent": 380, "remaining": 120,
         "percent": 76.0, "status": "ok" | "warning" | "over"},
        ...
    ]
    """
    start, end = month_range(ym)

    # 一次 SQL 拿到"每个分类的预算 + 该月的实际支出"
    sql = """
        SELECT b.category,
               b.monthly_limit AS limit_amt,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t
          ON t.category = b.category
         AND t.user_id = b.user_id
         AND t.type = 'expense'
         AND t.date >= ? AND t.date < ? 
        WHERE b.user_id = ? 
        GROUP BY b.category, b.monthly_limit 
        ORDER BY b.category
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (start, end, user_id)).fetchall()

    result = []
    for r in rows:
        limit_amt = float(r["limit_amt"])
        spent = float(r["spent"] or 0)
        remaining = limit_amt - spent
        percent = round(spent / limit_amt * 100, 1) if limit_amt > 0 else 0.0

        if limit_amt <= 0:
            status = "ok"
        elif percent >= 100:
            status = "over"
        elif percent >= 80:
            status = "warning"
        else:
            status = "ok"

        result.append({
            "category": r["category"],
            "limit": limit_amt,
            "spent": spent,
            "remaining": remaining,
            "percent": percent,
            "status": status,
        })
    return result