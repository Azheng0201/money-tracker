import sqlite3
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
                amout REAL NOT NULL CHECK(amout >= 0),
                note TEXT DEFAULT ''
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON transactions(type)")

def add_transaction(date: str, type_: str, category: str, amout: float, note: str = "") -> int:
    """添加一条交易记录，返回新记录的 id。"""
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO transactions (date, type, category, amout, note) VALUES (?, ?, ?, ?, ?)",
            (date, type_, category, float(amout), note)
        )
        return cursor.lastrowid

def list_all() -> list[sqlite3.Row]:
    """返回所有交易记录，按日期降序排列。"""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
        return cursor.fetchall()

def get_by_id(tid: int) -> sqlite3.Row | None:
    """根据 id 获取交易记录，找不到返回 None。"""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM transactions WHERE id = ?", (tid,))
        return cursor.fetchone()

# ---- 冒烟测试：直接运行本文件时执行 ----
if __name__ == "__main__":
    init_db()
    print("✅数据库初始化完成。", DB_PATH)

    # 只在空库时插入示例，避免重复运行搞脏数据
    if not list_all():
        add_transaction("2026-09-10", "income", "工资", 8000, "9月工资")
        add_transaction("2026-09-11", "expense", "餐饮", 38.50, "午餐")
        add_transaction("2026-09-11", "expense", "交通", 12.00, "地铁")
        print("✅插入3条示例数据。")

    print("\n🗒️ 当前所有交易：")
    for row in list_all():
        print(f" [{row['id']}] {row['date']} {row['type']:<7} "
              f"{row['category']:<4} {row['amout']:>8.2f} {row['note']}")