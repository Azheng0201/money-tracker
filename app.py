"""Flask 网页版：交易列表、统计、图表。"""

from datetime import date as _date
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import analytics
import charts
import db

app = Flask(__name__)


@app.before_request
def load_logged_in_user():
    """每次请求前把当前用户挂到 g.user 上，模板和视图都能直接用。"""
    user_id = session.get("user_id")
    g.user = db.get_user_by_id(user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("请先登录", "error")
            # 把当前的 URL 记录下来，登录后跳回去
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


CHART_DIR = Path(__file__).parent / "static" / "charts"
CHART_FILES = ["monthly_bar.png", "pie_expense.png", "balance_line.png"]


def _ensure_charts() -> None:
    """首次访问或数据缺失时生成图表。已存在就跳过"""
    prefix = f"u{g.user['id']}_"
    names = [prefix + n for n in ("monthly_bar.png", "pie_expense.png", "balance_line.png")]
    if all((CHART_DIR / n).exists() for n in names):
        return
    df = analytics.load_df(g.user["id"])
    if df.empty:
        return
    try:
        charts.generate_all(df, prefix=prefix)
    except Exception as e:
        # 生成失败不影响页面其他部分渲染
        app.logger.warning("生成图表失败：%s", e)


def _chart_version() -> str:
    """用最新的图表文件 mtime 作为版本号，防浏览器缓存旧图。"""
    prefix = f"u{g.user['id']}_"
    if not CHART_DIR.exists():
        return "0"
    files = list(CHART_DIR.glob(f"{prefix}*.png"))
    if not files:
        return "0"
    return str(int(max(f.stat().st_mtime for f in files)))


@app.template_filter("money")
def money_filter(v):
    """￥格式，保留 2 位。"""
    return f"￥{float(v):,.2f}"


app.secret_key = "dev-secret-change-me"  # flash 需要，上线必须换成随机值


def _validate_tx_form(form) -> tuple[list[str], dict]:
    """
    校验交易表单。返回 (errors, cleaned)。
    cleaned 里的 amount 是 float (校验通过时) 或 None (非法时) ;
    同时保留 amount_s 原字符串供回填。
    """
    date_s = form.get("date", "").strip()
    type_ = form.get("type", "").strip()
    category = form.get("category", "").strip()
    amount_s = form.get("amount", "").strip()
    note = form.get("note", "").strip()

    errors: list[str] = []

    if not date_s:
        errors.append("日期不能为空")
    else:
        try:
            datetime.strptime(date_s, "%Y-%m-%d")
        except ValueError:
            errors.append("日期格式应为 YYYY-MM-DD")

    if type_ not in ("income", "expense"):
        errors.append("类型必须是收入或支出")

    if not category:
        errors.append("分类不能为空")

    amount: float | None = None
    try:
        amount = float(amount_s)
        if amount < 0:
            errors.append("金额不能为负")
    except ValueError:
        errors.append("金额必须是数字")

    cleaned = {
        "date": date_s,
        "type": type_,
        "category": category,
        "amount": amount,
        "amount_s": amount_s,
        "note": note,
    }
    return errors, cleaned


@app.route("/")
@login_required
def index():
    _ensure_charts()
    s = db.summary(g.user["id"])
    recent = db.recent_transactions(g.user["id"], 5)
    return render_template(
        "dashboard.html",
        summary=s,
        recent=recent,
        chart_version=_chart_version(),
        has_charts=all((CHART_DIR / n).exists() for n in CHART_FILES),
    )


PER_PAGE = 20


def _month_range(ym: str) -> tuple[str, str]:
    """'YYYY-MM' → （本月1号，下月1号）。"""
    if len(ym) != 7 or ym[4] != "-":
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = ym.split("-")
    if not (y.isdigit() and m.isdigit() and 1 <= int(m) <= 12):
        raise ValueError("月份格式应为 YYYY-MM")
    y, m = int(y), int(m)
    start = f"{y:04d}-{m:02d}-01"
    end = f"{y + 1:04d}-01-01" if m == 12 else f"{y:04d}-{m + 1:02d}-01"
    return start, end


@app.route("/transactions")
@login_required
def transactions():
    # 1. 读查询参数
    month = request.args.get("month", "").strip() or None
    type_ = request.args.get("type", "").strip() or None
    category = request.args.get("category", "").strip() or None
    keyword = request.args.get("keyword", "").strip() or None
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    # 2. 月份 → 日期区间
    date_from = date_to = None
    if month:
        try:
            date_from, date_to = _month_range(month)
        except ValueError:
            flash(f"⚠️ 月份格式错误：{month}", "error")
            month = None

    # 3. 查询
    rows, total = db.query_paged(
        g.user["id"],
        page=page,
        per_page=PER_PAGE,
        date_from=date_from,
        date_to=date_to,
        type_=type_,
        category=category,
        keyword=keyword,
    )

    # 4. 边界保护：page 超出范围就跳转最后一页
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    if page > total_pages:
        page = total_pages
        rows, total = db.query_paged(
            g.user["id"],
            page=page,
            per_page=PER_PAGE,
            date_from=date_from,
            date_to=date_to,
            type_=type_,
            category=category,
            keyword=keyword,
        )

    # 5. 保留筛选条件的 URL 生成器 （给模板翻页用）
    def url_with(**overrides):
        args = {k: v for k, v in request.args.items()}
        for k, v in overrides.items():
            if v is None or v == "":
                args.pop(k, None)
            else:
                args[k] = v
        return url_for("transactions", **args)

    return render_template(
        "transactions.html",
        rows=rows,
        total=total,
        page=page,
        per_page=PER_PAGE,
        total_pages=total_pages,
        filters={"month": month, "type": type_, "category": category, "keyword": keyword},
        months=db.list_months(g.user["id"]),
        categories=db.list_categories(g.user["id"]),
        url_with=url_with,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if len(username) < 3:
            errors.append("用户名至少 3 个字符")
        if len(password) < 6:
            errors.append("密码至少 6 位")
        if password != confirm:
            errors.append("两次密码不一致")
        if db.get_user_by_username(username):
            errors.append("用户名已被占用")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form={"username": username})

        uid = db.create_user(username, generate_password_hash(password))
        session["user_id"] = uid
        flash(f"✅ 注册成功，欢迎 {username}", "success")
        return redirect(url_for("index"))

    return render_template("register.html", form={"username": ""})


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.get_user_by_username(username)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("用户名或密码错误", "error")
            return render_template("login.html", form={"username": username})

        session.clear()
        session["user_id"] = user["id"]
        flash(f"✅ 欢迎回来，{username}", "success")

        # 登录成功后跳回原来想访问的页面
        next_url = request.args.get("next") or url_for("index")
        # 防止 open redirect: next 必须是站内相对路径
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("index")
        return redirect(next_url)

    return render_template("login.html", form={"username": ""})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("👋 已退出登录", "success")
    return redirect(url_for("login"))


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        errors, c = _validate_tx_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "form.html",
                form=c,
                form_title="添加交易",
                form_action=url_for("add"),
                submit_label="保存",
            )

        new_id = db.add_transaction(
            g.user["id"], c["date"], c["type"], c["category"], c["amount"], c["note"]
        )
        flash(f"✅ 已添加交易，id = {new_id}", "success")
        return redirect(url_for("transactions"))

    return render_template(
        "form.html",
        form={
            "date": _date.today().isoformat(),
            "type": "expense",
            "category": "",
            "amount_s": "",
            "note": "",
        },
        form_title="添加交易",
        form_action=url_for("add"),
        submit_label="保存",
    )


@app.route("/edit/<int:tid>", methods=["GET", "POST"])
@login_required
def edit(tid):
    row = db.get_by_id(g.user["id"], tid)
    if row is None:
        flash(f"⚠️ 没有 id = {tid} 的记录", "error")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        errors, c = _validate_tx_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            # 出错时也要把用户输入回填
            return render_template(
                "form.html",
                form=c,
                form_title=f"编辑交易 #{tid}",
                form_action=url_for("edit", tid=tid),
                submit_label="保存修改",
            )

        ok = db.update_transaction(
            g.user["id"],
            tid,
            date=c["date"],
            type=c["type"],
            category=c["category"],
            amount=c["amount"],
            note=c["note"],
        )
        if ok:
            flash(f"✅ 已更新 id = {tid}", "success")
        else:
            flash("⚠️ 更新失败", "error")
        return redirect(url_for("transactions"))

    # GET：把 Row 转成 dict 再传入模板
    form = {
        "date": row["date"],
        "type": row["type"],
        "category": row["category"],
        "amount": row["amount"],
        "note": row["note"],
    }
    return render_template(
        "form.html",
        form=form,
        form_title=f"编辑交易 #{tid}",
        form_action=url_for("edit", tid=tid),
        submit_label="保存修改",
    )


@app.route("/delete/<int:tid>", methods=["POST"])
@login_required
def delete(tid):
    ok = db.delete_transaction(g.user["id"], tid)
    if ok:
        flash(f"🗑️ 已删除 id = {tid}", "success")
    else:
        flash(f"⚠️ 没有 id = {tid} 的记录", "error")
    return redirect(url_for("transactions"))


@app.route("/charts/refresh", methods=["POST"])
@login_required
def refresh_charts():
    df = analytics.load_df(g.user["id"])
    if df.empty:
        flash("⚠️ 没有数据可以绘图", "error")
        return redirect(url_for("index"))
    prefix = f"u{g.user['id']}_"
    try:
        paths = charts.generate_all(df, prefix=prefix)
    except Exception as e:
        flash(f"❌ 图表生成失败： {e}", "error")
        return redirect(url_for("index"))
    flash(f"✅ 已生成 {len(paths)} 张图表", "success")
    return redirect(url_for("index"))


@app.route("/api/monthly")
@login_required
def api_monthly():
    df = analytics.load_df()
    m = analytics.monthly_df(df)
    return jsonify(
        {
            "months": list(m.index),
            "income": m["income"].tolist(),
            "expense": m["expense"].tolist(),
        }
    )


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
