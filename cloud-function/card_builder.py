#!/usr/bin/env python3
"""
卡片内容构建器
从多维表格读取数据，构建卡片内容
"""

import json
import urllib.request
from datetime import date, datetime
from typing import Dict, List
from card_templates import (
    build_overview_card,
    build_task_list_card,
    build_defect_card,
    build_success_card,
    build_error_card,
)


class CardBuilder:
    """卡片内容构建器"""

    def __init__(self, base_token: str, app_id: str = None, app_secret: str = None):
        self.base_token = base_token
        self.access_token = None
        # Pre-compute sets for efficient category membership checks
        self._dev_table_ids = set(cfg["id"] for cfg in self.TABLE_CONFIGS["dev"])
        self._test_table_ids = set(cfg["id"] for cfg in self.TABLE_CONFIGS["test"])
        if app_id and app_secret:
            self._authenticate(app_id, app_secret)

    def _authenticate(self, app_id: str, app_secret: str):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                self.access_token = result.get("tenant_access_token")
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}") from e

    def _fetch_records(self, table_id: str) -> List[Dict]:
        """获取表的所有记录"""
        if self.access_token is None:
            raise RuntimeError("access_token is not available. Please provide app_id and app_secret for authentication.")

        all_records = []
        page_token = None
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_token}/tables/{table_id}/records?page_size=100"

        while True:
            # Add page_token to URL if it exists
            fetch_url = url
            if page_token:
                fetch_url = f"{url}&page_token={page_token}"

            headers = {"Authorization": f"Bearer {self.access_token}"}
            req = urllib.request.Request(fetch_url, headers=headers)
            try:
                with urllib.request.urlopen(req) as resp:
                    result = json.loads(resp.read())
                    items = result.get("data", {}).get("items", [])
                    all_records.extend(items)

                    # Check for pagination
                    page_token = result.get("data", {}).get("page_token")
                    if not page_token:
                        break
            except Exception as e:
                raise RuntimeError(f"Failed to fetch records: {e}") from e

        return all_records

    def _get_today(self) -> date:
        return date.today()

    # 表配置
    TABLE_CONFIGS = {
        "dev": [
            {"id": "tblo5L10rWTWjKf9", "name": "开发任务", "name_field": "任务标题",
             "user_field": "开发负责人", "status_field": "状态", "plan_field": "计划完成时间", "actual_field": "实际完成时间"},
            {"id": "tblpajWitnEuY3G5", "name": "硬件组任务", "name_field": "任务名称",
             "user_field": "负责人", "status_field": "状态", "plan_field": "期望完成时间", "actual_field": "实际完成时间"},
            {"id": "tblS8qBWisBv6O9N", "name": "神盾开发", "name_field": "详细任务名称",
             "user_field": "负责人", "status_field": "任务状态", "plan_field": "计划完成时间", "actual_field": "实际完成时间"},
        ],
        "test": [
            {"id": "tbl98ZxWyCcgounb", "name": "提测任务", "name_field": "提测任务标题",
             "user_field": "任务负责人", "status_field": "任务状态", "plan_field": "预期提测时间", "actual_field": "实际完成时间"},
            {"id": "tblm13vKwIfwYBt0", "name": "测试任务", "name_field": "任务描述",
             "user_field": "测试人员", "status_field": "任务状态", "plan_field": "计划完成时间", "actual_field": "实际完成时间"},
        ],
        "defect": [
            {"id": "tblsJ5woCFfYgrNi", "name": "缺陷管理", "name_field": "问题简述",
             "user_field": "处理人", "status_field": "当前状态", "plan_field": "计划完成时间", "actual_field": "关闭时间"},
        ]
    }

    COMPLETED_STATUSES = ["已完成", "处理完成", "已完成测试", "提测通过", "已关闭"]

    def _extract_user_name(self, user_field) -> str:
        """从用户字段提取姓名"""
        if not user_field:
            return "未分配"
        if isinstance(user_field, list) and len(user_field) > 0:
            return user_field[0].get("name", "未分配")
        if isinstance(user_field, dict):
            return user_field.get("name", "未分配")
        return str(user_field)

    def _parse_date(self, date_str) -> str:
        """解析日期为 MM-DD 格式"""
        if not date_str:
            return "未计划"
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(date_str)[:10], fmt).strftime("%m-%d")
            except ValueError:
                continue
        return str(date_str)[:10]

    def _is_completed(self, status: str) -> bool:
        return status in self.COMPLETED_STATUSES if status else False

    def get_overview_stats(self) -> Dict:
        """获取概览统计数据"""
        stats = {
            "dev_in_progress": 0, "dev_completed": 0, "dev_overdue": 0,
            "test_in_progress": 0, "test_completed": 0, "test_overdue": 0,
            "defect_pending": 0, "defect_processing": 0, "defect_closed": 0
        }

        today = self._get_today()

        for cfg in self.TABLE_CONFIGS["dev"] + self.TABLE_CONFIGS["test"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                if not name:
                    continue
                status = str(fields.get(cfg["status_field"], ""))
                plan_str = fields.get(cfg["plan_field"], "")
                plan_date = self._parse_date(plan_str) if plan_str else None
                actual = fields.get(cfg["actual_field"], "")

                if actual and self._parse_date(actual) == today.strftime("%m-%d"):
                    if cfg["id"] in self._dev_table_ids:
                        stats["dev_completed"] += 1
                    else:
                        stats["test_completed"] += 1
                elif plan_date and not self._is_completed(status):
                    try:
                        plan_month_day = datetime.strptime(plan_date, "%m-%d")
                        today_md = datetime.strptime(today.strftime("%m-%d"), "%m-%d")
                        if plan_month_day < today_md:
                            if cfg["id"] in self._dev_table_ids:
                                stats["dev_overdue"] += 1
                            else:
                                stats["test_overdue"] += 1
                        else:
                            if cfg["id"] in self._dev_table_ids:
                                stats["dev_in_progress"] += 1
                            else:
                                stats["test_in_progress"] += 1
                    except ValueError:
                        if cfg["id"] in self._dev_table_ids:
                            stats["dev_in_progress"] += 1
                        else:
                            stats["test_in_progress"] += 1
                elif not self._is_completed(status):
                    if cfg["id"] in self._dev_table_ids:
                        stats["dev_in_progress"] += 1
                    else:
                        stats["test_in_progress"] += 1

        # 缺陷统计
        for cfg in self.TABLE_CONFIGS["defect"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                if not name:
                    continue
                status = str(fields.get(cfg["status_field"], ""))

                if status in ("待处理", "新建", "重新打开"):
                    stats["defect_pending"] += 1
                elif status in ("处理中", "已确认", "修复中"):
                    stats["defect_processing"] += 1

        return stats

    def get_overview_card(self) -> Dict:
        today = self._get_today()
        stats = self.get_overview_stats()
        return build_overview_card(today, stats)

    def get_completed_tasks(self) -> List[Dict]:
        """获取今日完成任务"""
        tasks = []
        today = self._get_today()
        today_str = today.strftime("%m-%d")

        for cfg in self.TABLE_CONFIGS["dev"] + self.TABLE_CONFIGS["test"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                if not name:
                    continue
                actual = fields.get(cfg["actual_field"], "")
                if actual and self._parse_date(actual) == today_str:
                    tasks.append({
                        "record_id": rec.get("record_id", ""),
                        "table_id": cfg["id"],
                        "name": name,
                        "user": self._extract_user_name(fields.get(cfg["user_field"])),
                        "plan_date": self._parse_date(fields.get(cfg["plan_field"], "")),
                        "status": fields.get(cfg["status_field"], ""),
                    })

        return tasks

    def get_in_progress_tasks(self) -> List[Dict]:
        tasks = []
        for cfg in self.TABLE_CONFIGS["dev"] + self.TABLE_CONFIGS["test"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                status = fields.get(cfg["status_field"], "")
                if name and not self._is_completed(status):
                    tasks.append({
                        "record_id": rec.get("record_id", ""),
                        "table_id": cfg["id"],
                        "name": name,
                        "user": self._extract_user_name(fields.get(cfg["user_field"])),
                        "plan_date": self._parse_date(fields.get(cfg["plan_field"], "")),
                        "status": status,
                    })
        return tasks[:20]  # 限制 20 条

    def get_overdue_tasks(self) -> List[Dict]:
        tasks = []
        today = self._get_today()
        for cfg in self.TABLE_CONFIGS["dev"] + self.TABLE_CONFIGS["test"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                status = fields.get(cfg["status_field"], "")
                plan_str = fields.get(cfg["plan_field"], "")
                if name and plan_str and not self._is_completed(status):
                    plan_date_str = self._parse_date(plan_str)
                    try:
                        plan_date = datetime.strptime(plan_date_str, "%m-%d")
                        today_md = datetime.strptime(today.strftime("%m-%d"), "%m-%d")
                        if plan_date < today_md:
                            tasks.append({
                                "record_id": rec.get("record_id", ""),
                                "table_id": cfg["id"],
                                "name": name,
                                "user": self._extract_user_name(fields.get(cfg["user_field"])),
                                "plan_date": plan_date_str,
                                "status": status,
                            })
                    except ValueError:
                        continue
        return sorted(tasks, key=lambda x: x["plan_date"])[:5]

    def get_pending_defects(self) -> List[Dict]:
        defects = []
        for cfg in self.TABLE_CONFIGS["defect"]:
            records = self._fetch_records(cfg["id"])
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get(cfg["name_field"], "")
                status = fields.get(cfg["status_field"], "")
                if name and status in ("待处理", "处理中", "已确认", "修复中"):
                    defects.append({
                        "record_id": rec.get("record_id", ""),
                        "table_id": cfg["id"],
                        "name": name,
                        "user": self._extract_user_name(fields.get(cfg["user_field"])),
                        "priority": fields.get("优先级", ""),
                        "status": status,
                    })
        return defects

    def build_overview_card(self) -> Dict:
        """构建概览卡片"""
        today = self._get_today()
        overview = self.get_overview_stats()
        return build_overview_card(today, overview)

    def build_task_list_card(self, category: str, tasks: List[Dict]) -> Dict:
        today = self._get_today()
        return build_task_list_card(today, category, tasks)

    def build_defect_card(self, defects: List[Dict]) -> Dict:
        today = self._get_today()
        return build_defect_card(today, defects)

    def build_success_card(self, message: str) -> Dict:
        return build_success_card(message)

    def build_error_card(self, message: str) -> Dict:
        return build_error_card(message)