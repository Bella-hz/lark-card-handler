#!/usr/bin/env python3
"""
飞书消息卡片更新器
用于更新已发送的卡片内容
"""

import json
import urllib.request
from typing import Dict


class CardUpdater:
    """飞书卡片更新客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self._authenticate()

    def _authenticate(self):
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                self.access_token = result.get("tenant_access_token")
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}") from e

    def update_card(self, message_id: str, card_content: Dict) -> Dict:
        """
        更新消息卡片内容
        message_id: 原始消息 ID
        card_content: 新的卡片 JSON
        """
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # 构建更新请求体
        body = {
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=headers,
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                # 检查 API 返回码
                if result.get("code") and result.get("code") != 0:
                    raise RuntimeError(f"API error: code={result.get('code')}, msg={result.get('msg')}")
                return result
        except Exception as e:
            raise RuntimeError(f"Failed to update card: {e}") from e

    def reply_card(self, message_id: str, card_content: Dict, chat_id: str = None) -> Dict:
        """
        在原卡片下回复新卡片（替换内容）
        message_id: 原消息 ID
        card_content: 新的卡片 JSON
        chat_id: 聊天 ID（如果已知道可以直接传入）
        """
        # 如果没有传入 chat_id，尝试从 message_id 获取
        if not chat_id:
            url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req) as resp:
                    msg_info = json.loads(resp.read())
                    chat_id = msg_info.get("data", {}).get("chat_id")
                    if not chat_id:
                        raise ValueError("chat_id not found in message info")
            except ValueError:
                raise
            except Exception as e:
                raise RuntimeError(f"Failed to get message info: {e}") from e

        # 发送新卡片
        new_body = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        send_req = urllib.request.Request(
            send_url,
            data=json.dumps(new_body).encode(),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(send_req) as resp:
                result = json.loads(resp.read())
                if result.get("code") and result.get("code") != 0:
                    raise RuntimeError(f"API error: code={result.get('code')}, msg={result.get('msg')}")
                return result
        except Exception as e:
            raise RuntimeError(f"Failed to send reply card: {e}") from e
