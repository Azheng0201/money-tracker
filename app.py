"""Flask 网页版：交易列表、统计、图表。"""
from flask import (Flask, render_template, request,
                   redirect, url_for, flash)
from datetime import datetime, date as _date

import db

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # flash 需要，上线必须换成随机值

def _validate_tx_form(form) -> tuple[list[str], dict]:
    """
    校验交易表单。返回 (errors, cleaned)。
    cleaned 里的 amount 是 float (校验通过时) 或 None (非法时) ;
    同时保留 amount_s 原字符串供回填。
    """
    date_s   = form.get("date", "").strip()
    type_    = form.get("type", "").strip()
    category = form.get("category", "").strip()
    amount_s = form.get("amount", "").strip()
    note     = form.get("note", "").strip()

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
        "date": date_s, "type": type_, "category": category,
        "amount": amount, "amount_s": amount_s, "note": note,
    }
    return errors, cleaned

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transactions")
def transactions():
    rows = db.list_all()
    return render_template("transactions.html", rows=rows)

@app.route("/add", methods=["GET", "POST"])
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
        
        new_id = db.add_transaction(c["date"], c["type"], c["category"], c["amount"], c["note"])
        flash(f"✅ 已添加交易，id = {new_id}", "success")
        return redirect(url_for("transactions"))

    return render_template(
        "form.html",
        form={"date": _date.today().isoformat(),
              "type": "expense", "category": "", "amount_s": "", "note": ""},
        form_title="添加交易",
        form_action=url_for("add"),
        submit_label="保存",
    )

@app.route("/edit/<int:tid>", methods=["GET", "POST"])
def edit(tid):
    row = db.get_by_id(tid)
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
            tid, date=c["date"], type=c["type"], category=c["category"],
            amount=c["amount"], note=c["note"]
        )
        if ok:
            flash(f"✅ 已更新 id = {tid}", "success")
        else:
            flash(f"⚠️ 更新失败", "error")
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
def delete(tid):
    ok = db.delete_transaction(tid)
    if ok:
        flash(f"🗑️ 已删除 id = {tid}", "success")
    else:
        flash(f"⚠️ 没有 id = {tid} 的记录", "error")
    return redirect(url_for("transactions"))

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)