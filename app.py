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

    if request.method == "OPTIONS":
        return "", 204

    # 只解析一次 body
    body = request.get_json(force=True) or {}

    if challenge:
        logger.info(f"Feishu URL verification: challenge={challenge}")
        return jsonify({"challenge": challenge})

    try:
        logger.info(f"Received event: {body}")

        # 导入处理模块
        from handlers import CallbackHandler

        handler = CallbackHandler(APP_ID, APP_SECRET, BASE_TOKEN)

        # 提取事件数据 - 飞书事件在 event 字段中
        event = body.get("event", {})
        action = event.get("action", {})
        operator = event.get("operator", {})

        action_type = action.get("tag", "")  # button, input, etc.
        action_value = action.get("value", {})
        user_id = operator.get("open_id", "")

        logger.info(f"Parsed: action_type={action_type}, action_value={action_value}, user_id={user_id}")

        if action_type == "button":
            # 按钮点击
            action_name = action_value.get("action", "")
            logger.info(f"Button clicked: {action_name}")

            # 简单返回确认
            return jsonify({"msg": "ok"})

        elif action_type == "input":
            # 表单提交
            return jsonify({"msg": "ok"})

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
