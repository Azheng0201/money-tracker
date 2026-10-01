"""生产环境启动脚本。本地调试用这个或 waitress-serve 命令都行。"""
import os
from waitress import serve

import app as app_module
import db

if __name__ == "__main__":
    db.init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 启动生产服务器 http:// {host}:{port}")
    serve(app_module.app, host=host, port=port, threads=4)