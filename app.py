"""Flask 网页版：交易列表、统计、图表。"""
from flask import Flask, render_template

import db

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transactions")
def transactions():
    rows = db.list_all()
    return render_template("transactions.html", rows=rows)

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)