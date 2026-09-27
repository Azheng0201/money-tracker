from dataclasses import dataclass


@dataclass
class Transaction:
    """一条交易记录， id 为 None 表示尚未入库。"""

    id: int | None
    date: str  # 格式: YYYY-MM-DD
    type: str  # income / expense
    category: str
    amount: float
    note: str = ""

    def is_income(self) -> bool:
        return self.type == "income"

    def is_expense(self) -> bool:
        return self.type == "expense"
