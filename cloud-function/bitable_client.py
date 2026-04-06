#!/usr/bin/env python3
"""
腾讯云函数中使用的飞书多维表格客户端
通过飞书 Open API 读写多维表格数据
"""

import json
import urllib.error
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional
from datetime import date, datetime


class BitableClient:
    """飞书多维表格 API 客户端"""

    def __init__(self, app_id: str, app_secret: str, app_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
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
                if "tenant_access_token" not in result:
                    raise RuntimeError(f"Authentication failed: {result.get('msg', 'Unknown error')}")
                self.access_token = result["tenant_access_token"]
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to authenticate: {e}") from e

    def _request(self, method: str, path: str, data: Dict = None) -> Dict:
        """发送 API 请求"""
        url = f"https://open.feishu.cn/open-apis{path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"API request failed: {e}") from e

    def batch_get_records(
        self,
        table_id: str,
        filter_formula: str = None,
        page_size: int = 100,
        page_token: str = None
    ) -> List[Dict]:
        """
        批量获取记录
        返回: [{"record_id": "...", "fields": {...}}, ...]
        """
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        params = [("page_size", page_size)]
        if filter_formula:
            params.append(("filter_formula", filter_formula))
        if page_token:
            params.append(("page_token", page_token))

        url = f"{path}?{urllib.parse.urlencode(params)}"
        result = self._request("GET", url)
        records = result.get("data", {}).get("items", [])

        # 处理分页
        while result.get("data", {}).get("has_more"):
            page_token = result["data"]["page_token"]
            params = [("page_size", page_size), ("page_token", page_token)]
            if filter_formula:
                params.append(("filter_formula", filter_formula))
            url = f"{path}?{urllib.parse.urlencode(params)}"
            result = self._request("GET", url)
            records.extend(result.get("data", {}).get("items", []))

        return records

    def update_record(self, table_id: str, record_id: str, fields: Dict) -> Dict:
        """
        更新记录字段
        fields: {"状态": "已完成", "实际完成时间": "2026-04-05"}
        """
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        return self._request("PUT", path, {"fields": fields})

    def get_record(self, table_id: str, record_id: str) -> Dict:
        """获取单条记录"""
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        return self._request("GET", path)

    def list_fields(self, table_id: str) -> List[Dict]:
        """获取表字段列表"""
        path = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields"
        result = self._request("GET", path)
        return result.get("data", {}).get("items", [])


# 状态映射：按钮操作 -> 目标状态和字段
STATUS_MAPPINGS = {
    "complete": {
        "dev": {"状态": "已完成", "实际完成时间": None},  # None 表示自动填当天
        "dev_硬件": {"状态": "处理完成", "实际完成时间": None},
        "dev_神盾": {"状态": "已完成", "实际完成时间": None},
        "test": {"任务状态": "已完成测试", "实际完成时间": None},
        "defect": {"当前状态": "已关闭", "关闭时间": None},
    },
    "reopen": {
        "dev": {"状态": "进行中"},
        "test": {"任务状态": "待测试"},
        "defect": {"当前状态": "重新打开"},
    }
}


def parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串"""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str[:10], fmt).date()
        except ValueError:
            continue
    return None
