"""Flask 网页版：交易列表、统计、图表。"""
from flask import (Flask, render_template, request,
                   redirect, url_for, flash)

import db

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # flash 需要，上线必须换成随机值

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
        # 1. 拿表单数据（都做 strip，防止用户输入多余空格）
        date     = request.form.get("date", "").strip()
        type_    = request.form.get("type", "").strip()
        category = request.form.get("category", "").strip()
        amount_s = request.form.get("amount", "").strip()
        note     = request.form.get("note", "").strip()

        # 2. 校验
        errors = []
        if not date:
            errors.append("日期不能为空")
        else:
            try:
                from datetime import datetime as _dt
                _dt.strptime(date, "%Y-%m-%d")
            except ValueError:
                errors.append("日期格式应为 YYYY-MM-DD")

        if type_ not in ("income", "expense"):
            errors.append("交易类型必须是收入或支出")

        if not category:
            errors.append("分类不能为空")

        amount = None
        try:
            amount = float(amount_s)
            if amount < 0:
                errors.append("金额不能为负")
        except ValueError:
            errors.append("金额必须是数字")

        # 3. 有错 → 回表单页 + 把已填的字段带回去
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "add.html",
                form={"date": date, "type": type_, 
                      "category": category, "amount": amount_s,
                      "note": note},
            )

        # 4. 写库 + 提示 + 跳回列表
        new_id = db.add_transaction(date, type_, category, amount, note)
        flash(f"✅ 已添加交易，id = {new_id}", "success")
        return redirect(url_for("transactions"))

    # GET 请求：空表单，日期默认今天
    from datetime import date as _date
    return render_template(
        "add.html",
        form={"date": _date.today().isoformat(),
              "type": "expense", "category": "", "amount": "", "note": ""},
    )

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)