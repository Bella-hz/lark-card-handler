#!/usr/bin/env python3
"""
Railway Web 服务入口
使用 Flask 运行云函数逻辑
"""

import os
import sys
import json
import logging

# 添加 cloud-function 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cloud-function"))

from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

app = Flask(__name__)

# 环境变量
APP_ID = os.environ.get("APP_ID", "")
APP_SECRET = os.environ.get("APP_SECRET", "")
BASE_TOKEN = os.environ.get("BASE_TOKEN", "")


@app.route("/", methods=["GET", "POST", "OPTIONS"])
def index():
    """处理所有请求"""
    # 飞书 URL 验证请求 - 支持 GET 和 POST
    challenge = request.args.get("challenge", "")
    if not challenge:
        # POST 请求中可能有 challenge 在 body 中
        try:
            body = request.get_json(silent=True) or {}
            challenge = body.get("challenge", "")
        except:
            challenge = ""

    if challenge:
        logger.info(f"Feishu URL verification: challenge={challenge}")
        return jsonify({"challenge": challenge})

    if request.method == "OPTIONS":
        return "", 204

    try:
        body = request.get_json() or {}
        logger.info(f"Received event: {body}")

        # 导入处理模块
        from handlers import CallbackHandler

        handler = CallbackHandler(APP_ID, APP_SECRET, BASE_TOKEN)

        # 提取事件类型
        action_type = body.get("action", {}).get("action_type", "")
        user_id = body.get("user", {}).get("user_id", "")

        if action_type == "click":
            action_data = json.loads(body.get("action", {}).get("data", {}).get("value", "{}"))
            card, msg_id = handler.handle_click(action_data, user_id)
            return jsonify(card)

        elif action_type == "submit":
            form_data = body.get("action", {}).get("data", {})
            card, msg_id = handler.handle_form_submit(form_data, user_id)
            return jsonify(card)

        elif action_type == "get_overview":
            # 获取概览卡片
            card = handler.builder.get_overview_card()
            return jsonify(card)

        else:
            return jsonify({"msg": "OK"})

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "env": {
            "APP_ID": "***" if APP_ID else "EMPTY",
            "APP_SECRET": "***" if APP_SECRET else "EMPTY",
            "BASE_TOKEN": "***" if BASE_TOKEN else "EMPTY"
        }
    })

@app.route("/test", methods=["GET", "POST"])
def test():
    """测试端点 - 不调用飞书 API"""
    from datetime import date
    from card_templates import build_overview_card
    today = date.today()
    overview = {
        "dev_in_progress": 5,
        "dev_completed": 2,
        "dev_overdue": 1,
        "test_in_progress": 3,
        "test_completed": 1,
        "test_overdue": 0,
        "defect_pending": 2,
        "defect_processing": 1,
        "defect_closed": 0,
    }
    card = build_overview_card(today, overview)
    return jsonify(card)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
