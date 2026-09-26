"""matplotlib 图表生成。所有图存到 static/charts/。"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 必须在 import pyplot 之前， 用无 GUI 后端
import matplotlib.pyplot as plt
import pandas as pd

import analytics

CHART_DIR = Path(__file__).parent / "static" / "charts"

# 中文字体：按优先级尝试，系统装了哪个就用哪个
_CN_FONTS = ['Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB',
            'WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS',
            'Noto Sans CJK SC', 'Source Han Sans SC']

def _setup_font() -> None:
    plt.rcParams["font.sans-serif"] = _CN_FONTS + ["sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False  # 负号显示正常

_setup_font()

def _prepare_path(path: str | Path | None, default_name: str) -> Path:
    p = Path(path) if path else CHART_DIR / default_name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

# ---------- 1. 月度收支柱状图 ----------
def bar_monthly(df: pd.DataFrame,
                path: str | Path | None = None) -> Path:
    path = _prepare_path(path, "monthly_bar.png")
    m = analytics.monthly_df(df)
    if m.empty:
        raise ValueError("没有可绘制的数据")

    fig, ax = plt.subplots(figsize=(10, 5))
    xs = list(range(len(m)))
    width = 0.38

    bars_i = ax.bar([x - width / 2 for x in xs], m["income"], 
                    width, label="收入", color="#4CAF50")
    bars_e = ax.bar([x + width / 2 for x in xs], m["expense"], 
                        width, label="支出", color="#F44336")

    ax.set_xticks(xs)
    ax.set_xticklabels(m.index, rotation=0)
    ax.set_ylabel("金额（元）")
    ax.set_title("月度收支")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # 数值标签，方便一眼看出多少
    for bars in (bars_i, bars_e):
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h,
                    f"{h:.0f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path

# ----------2. 分类占比饼图 ----------
def pie_categories(df: pd.DataFrame, type_:str = "expense",
                   top_n: int = 8,
                   path: str | Path | None = None) -> Path:
    label = "支出" if type_ == "expense" else "收入"
    path = _prepare_path(path, f"pie_{type_}.png")

    top = analytics.top_categories(df, type_=type_, n=top_n)
    if top.empty:
        raise ValueError(f"没有{label}数据")

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        top["total"],
        labels=top["category"],
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title(f"{label}分类占比 (Top {len(top)})")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path

# ---------- 3. 结余趋势折线图 ----------
def line_balance(df:pd.DataFrame,
                 path: str | Path | None = None) -> Path:
    path = _prepare_path(path, "balance_line.png")
    m = analytics.monthly_df(df)
    if m.empty:
        raise ValueError("没有可绘制的数据。")

    months = list(m.index)
    balance = m["balance"].tolist()
    cumulative = m["balance"].cumsum().tolist()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(months, balance, marker="o", label="当月结余", color="#2196F3")
    ax.plot(months, cumulative, marker="s", linestyle="--",
            label="累计结余", color="#FF9800")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle=":")

    ax.set_ylabel("金额（元）")
    ax.set_title("结余趋势")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path

# ---------- 一键生成 ----------
def generate_all(df: pd.DataFrame,
                 prefix: str = "") -> list:
    """
    生成所有图表。传入的 df 一般来自 analytics.load_df(from, to)。
    返回生成的路径列表。
    """
    paths = []
    try:
        paths.append(bar_monthly(df, CHART_DIR / f"{prefix}monthly_bar.png"))
    except ValueError as e:
        print(f"  ⚠️ 跳过柱状图：{e}")
    try:
        paths.append(line_balance(df, CHART_DIR / f"{prefix}balance_line.png"))
    except ValueError as e:
        print(f"  ⚠️ 跳过折线图：{e}")
    try:
        paths.append(pie_categories(df, "expense", path= CHART_DIR / f"{prefix}pie_expense.png"))
    except ValueError as e:
        print(f"  ⚠️ 跳过饼图：{e}")
    return paths

if __name__ == "__main__":
    df = analytics.load_df()
    out = generate_all(df)
    print("生成：")
    for p in out:
        print(" ", p)