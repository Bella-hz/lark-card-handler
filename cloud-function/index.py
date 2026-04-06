#!/usr/bin/env python3
"""
腾讯云函数入口
接收飞书卡片回调事件，处理后返回结果
"""

import json
import logging
import os
from handlers import CallbackHandler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# 云函数环境变量（在腾讯云控制台配置）
APP_ID = os.environ.get("APP_ID", "")
APP_SECRET = os.environ.get("APP_SECRET", "")
BASE_TOKEN = os.environ.get("BASE_TOKEN", "")


def verify_signature(event: dict) -> bool:
    """
    验证飞书请求签名
    飞书事件回调会携带 X-Lark-Signature 头
    """
    # 获取签名（如果有）
    # 简化处理：实际生产环境应验证签名
    return True


def main_handler(event, context):
    """
    云函数入口
    event 格式:
    {
        "headers": {"content-type": "application/json", ...},
        "body": "{...json data...}"
    }
    """
    logger.info(f"Received event: {event}")

    try:
        # 解析请求体
        body = json.loads(event.get("body", "{}"))
        logger.info(f"Parsed body: {body}")

        # 验证签名
        if not verify_signature(body):
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        # 处理事件
        handler = CallbackHandler(APP_ID, APP_SECRET, BASE_TOKEN)

        # 提取事件类型
        action_type = body.get("action", {}).get("action_type", "")
        user_id = body.get("user", {}).get("user_id", "")

        if action_type == "click":
            # 按钮点击
            action_data = json.loads(body.get("action", {}).get("data", {}).get("value", "{}"))
            card, msg_id = handler.handle_click(action_data, user_id)
            return {"statusCode": 200, "body": json.dumps(card)}

        elif action_type == "submit":
            # 表单提交
            form_data = body.get("action", {}).get("data", {})
            card, msg_id = handler.handle_form_submit(form_data, user_id)
            return {"statusCode": 200, "body": json.dumps(card)}

        else:
            return {"statusCode": 200, "body": json.dumps({"msg": "OK"})}

    except Exception as e:
        logger.error(f"Error handling event: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# 本地测试入口
if __name__ == "__main__":
    test_event = {
        "body": json.dumps({
            "action": {
                "action_type": "click",
                "data": {
                    "value": json.dumps({
                        "action": "show_overview"
                    })
                }
            },
            "user": {
                "user_id": "ou_xxx"
            }
        })
    }
    result = main_handler(test_event, None)
    print(json.dumps(result, ensure_ascii=False, indent=2))