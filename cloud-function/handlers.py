#!/usr/bin/env python3
"""
飞书卡片回调处理函数
处理按钮点击和表单提交事件
"""

import json
import logging
from typing import Dict, Tuple
from datetime import date
from bitable_client import BitableClient, STATUS_MAPPINGS
from card_updater import CardUpdater
from card_builder import CardBuilder


class CallbackHandler:
    """卡片回调处理器"""

    # 表ID到负责人字段名的映射
    TABLE_OWNER_FIELDS = {
        "tblo5L10rWTWjKf9": "开发负责人",
        "tblpajWitnEuY3G5": "负责人",
        "tblS8qBWisBv6O9N": "负责人",
        "tbl98ZxWyCcgounb": "任务负责人",
        "tblm13vKwIfwYBt0": "测试人员",
        "tblsJ5woCFfYgrNi": "处理人",
    }

    # 表ID到状态字段的映射（关闭时间需要动态设置）
    TABLE_STATUS_FIELDS = {
        "tblo5L10rWTWjKf9": {"状态": "已完成"},
        "tblpajWitnEuY3G5": {"状态": "处理完成"},
        "tblS8qBWisBv6O9N": {"状态": "已完成"},
        "tbl98ZxWyCcgounb": {"任务状态": "提测通过"},
        "tblm13vKwIfwYBt0": {"任务状态": "已完成测试"},
        "tblsJ5woCFfYgrNi": {"当前状态": "已关闭"},  # 关闭时间需要动态设置
    }

    def __init__(self, app_id: str, app_secret: str, base_token: str):
        self.bitable = BitableClient(app_id, app_secret, base_token)
        self.updater = CardUpdater(app_id, app_secret)
        self.base_token = base_token
        self.builder = CardBuilder(base_token, app_id, app_secret)

    def handle_click(self, action_data: Dict, user_id: str) -> Tuple[Dict, str]:
        """
        处理按钮点击
        返回: (response_card, message_id)
        """
        try:
            action = action_data.get("action")
            record_id = action_data.get("record_id")
            table_id = action_data.get("table_id")
            message_id = action_data.get("message_id", "")

            if action == "show_overview":
                return self.builder.build_overview_card(), message_id

            elif action == "show_completed":
                tasks = self.builder.get_completed_tasks()
                return self.builder.build_task_list_card("今日完成", tasks), message_id

            elif action == "show_in_progress":
                tasks = self.builder.get_in_progress_tasks()
                return self.builder.build_task_list_card("进行中", tasks), message_id

            elif action == "show_overdue":
                tasks = self.builder.get_overdue_tasks()
                return self.builder.build_task_list_card("逾期任务", tasks), message_id

            elif action == "show_defects":
                defects = self.builder.get_pending_defects()
                return self.builder.build_defect_card(defects), message_id

            elif action == "complete":
                # 权限检查
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id

                # 执行状态变更
                success = self._mark_complete(record_id, table_id)
                if success:
                    return self.builder.build_success_card("任务已标记完成"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "refresh":
                return self.builder.build_overview_card(), message_id

            elif action == "cancel":
                return self.builder.build_overview_card(), message_id

            else:
                return self.builder.build_error_card(f"未知操作: {action}"), message_id
        except Exception as e:
            logging.error(f"handle_click error: {action_data}, error: {e}", exc_info=True)
            message_id = action_data.get("message_id", "")
            return self.builder.build_error_card(f"处理失败: {str(e)}"), message_id

    def handle_form_submit(self, form_data: Dict, user_id: str) -> Tuple[Dict, str]:
        """
        处理表单提交
        form_data 格式: {"record_id": "...", "table_id": "...", "date": "...", "remark": "..."}
        """
        record_id = form_data.get("record_id")
        table_id = form_data.get("table_id")
        message_id = form_data.get("message_id", "")

        # 权限检查
        if not self._check_permission(record_id, table_id, user_id):
            return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id

        # 构建更新字段
        fields = {}
        if form_data.get("date"):
            fields["期望完成时间"] = form_data["date"]  # 统一写期望时间字段
        if form_data.get("remark"):
            fields["备注"] = form_data["remark"]

        if not fields:
            return self.builder.build_error_card("没有需要保存的内容"), message_id

        # 更新记录
        try:
            self.bitable.update_record(table_id, record_id, fields)
            return self.builder.build_success_card("排期信息已更新"), message_id
        except Exception as e:
            return self.builder.build_error_card(f"更新失败: {str(e)}"), message_id

    def _check_permission(self, record_id: str, table_id: str, user_id: str) -> bool:
        """检查用户是否有权限操作该任务"""
        # 获取记录信息
        try:
            record = self.bitable.get_record(table_id, record_id)
            fields = record.get("data", {}).get("record", {}).get("fields", {})
        except Exception as e:
            logging.warning(f"_check_permission: get_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False

        # 根据表类型检查负责人字段
        owner_field = self.TABLE_OWNER_FIELDS.get(table_id, "负责人")
        owner = fields.get(owner_field, [])

        # owner 可能是列表
        if isinstance(owner, list):
            owner_ids = [o.get("id", "") for o in owner if isinstance(o, dict)]
        elif isinstance(owner, dict):
            owner_ids = [owner.get("id", "")]
        else:
            owner_ids = []

        return user_id in owner_ids

    def _get_owner_field(self, table_id: str) -> str:
        """根据表 ID 返回负责人字段名"""
        return self.TABLE_OWNER_FIELDS.get(table_id, "负责人")

    def _mark_complete(self, record_id: str, table_id: str) -> bool:
        """标记任务完成"""
        today = date.today().isoformat()
        fields = {"实际完成时间": today}

        # 根据表 ID 确定状态字段 - 使用类常量
        base_status = self.TABLE_STATUS_FIELDS.get(table_id, {})
        if base_status:
            # 特殊处理：tblsJ5woCFfYgrNi 需要动态设置关闭时间
            if table_id == "tblsJ5woCFfYgrNi":
                fields.update(base_status)
                fields["关闭时间"] = today
            else:
                fields.update(base_status)

        try:
            self.bitable.update_record(table_id, record_id, fields)
            return True
        except Exception as e:
            logging.warning(f"_mark_complete: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False
