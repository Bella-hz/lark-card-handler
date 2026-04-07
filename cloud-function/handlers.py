#!/usr/bin/env python3
"""
飞书卡片回调处理函数
处理按钮点击和表单提交事件
"""

import json
import logging
import os
from typing import Dict, Tuple
from datetime import date
from bitable_client import BitableClient, STATUS_MAPPINGS
from card_updater import CardUpdater
from card_builder import CardBuilder


# 管理员用户列表（从环境变量获取，多个用逗号分隔）
ADMIN_USERS = set()
_env = os.environ.get("ADMIN_USERS", "")
if _env:
    ADMIN_USERS = set(uid.strip() for uid in _env.split(",") if uid.strip())
logging.info(f"ADMIN_USERS: {ADMIN_USERS}")


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

    # 表ID到状态字段的映射（开始时间/完成时间需要动态设置）
    TABLE_STATUS_FIELDS = {
        "tblo5L10rWTWjKf9": {"状态": "已完成", "实际完成时间": None},
        "tblpajWitnEuY3G5": {"状态": "处理完成", "实际完成时间": None},
        "tblS8qBWisBv6O9N": {"状态": "已完成", "实际完成时间": None},
        "tbl98ZxWyCcgounb": {"任务状态": "提测通过", "实际完成时间": None},
        "tblm13vKwIfwYBt0": {"任务状态": "已完成测试", "实际完成时间": None},
        "tblsJ5woCFfYgrNi": {"当前状态": "已关闭", "关闭时间": None},
    }

    # 进行中状态
    IN_PROGRESS_STATUS = {
        "tblo5L10rWTWjKf9": "进行中",
        "tblpajWitnEuY3G5": "处理中",
        "tblS8qBWisBv6O9N": "进行中",
        "tbl98ZxWyCcgounb": "待测试",
        "tblm13vKwIfwYBt0": "测试中",
    }

    # 缺陷状态流转
    DEFECT_STATUS_FIELDS = {
        "tblsJ5woCFfYgrNi": {"当前状态": "已关闭", "关闭时间": None},
    }
    DEFECT_IN_PROGRESS_STATUS = {
        "tblsJ5woCFfYgrNi": {"当前状态": "处理中"},
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

            logging.info(f"handle_click: action={action}, record_id={record_id}, table_id={table_id}")

            # 概览按钮
            if action == "show_overview":
                return self.builder.build_overview_card(), message_id

            # 任务列表按钮
            elif action == "show_completed":
                tasks = self.builder.get_completed_tasks()
                logging.info(f"show_completed: got {len(tasks)} tasks")
                return self.builder.build_task_list_card("今日完成", tasks), message_id

            elif action == "show_in_progress":
                tasks = self.builder.get_in_progress_tasks()
                logging.info(f"show_in_progress: got {len(tasks)} tasks")
                return self.builder.build_task_list_card("进行中", tasks), message_id

            elif action == "show_overdue":
                tasks = self.builder.get_overdue_tasks()
                logging.info(f"show_overdue: got {len(tasks)} tasks")
                return self.builder.build_task_list_card("逾期任务", tasks), message_id

            elif action == "show_defects":
                defects = self.builder.get_pending_defects()
                logging.info(f"show_defects: got {len(defects)} defects")
                return self.builder.build_defect_card(defects), message_id

            # 任务操作
            elif action == "start_task":
                # 开始任务 - 更新开始时间
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id
                success = self._mark_task_start(record_id, table_id)
                if success:
                    return self.builder.build_success_card("任务已开始"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "complete_task":
                # 完成任务 - 更新完成时间
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id
                success = self._mark_task_complete(record_id, table_id)
                if success:
                    return self.builder.build_success_card("任务已完成"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "complete":
                # 兼容旧按钮
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id
                success = self._mark_task_complete(record_id, table_id)
                if success:
                    return self.builder.build_success_card("任务已完成"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "edit_date":
                # 跳转到修改计划完成时间表单
                return self.builder.build_form_card("修改计划完成时间", "save_plan_end", record_id, table_id), message_id

            elif action == "edit_date_start":
                # 跳转到修改计划开始时间表单
                return self.builder.build_form_card("修改计划开始时间", "save_plan_start", record_id, table_id), message_id

            elif action == "edit_remark":
                # 跳转到备注表单
                return self.builder.build_form_card("添加备注", "save_remark", record_id, table_id), message_id

            # 缺陷操作
            elif action == "defect_accept":
                # 缺陷开始处理
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该缺陷处理人，无法操作"), message_id
                success = self._mark_defect_accept(record_id, table_id)
                if success:
                    return self.builder.build_success_card("已接受缺陷处理"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "defect_close":
                # 缺陷关闭
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该缺陷处理人，无法操作"), message_id
                success = self._mark_defect_close(record_id, table_id)
                if success:
                    return self.builder.build_success_card("缺陷已关闭"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "defect_reopen":
                # 缺陷重新打开
                if not self._check_permission(record_id, table_id, user_id):
                    return self.builder.build_error_card("您不是该缺陷处理人，无法操作"), message_id
                success = self._mark_defect_reopen(record_id, table_id)
                if success:
                    return self.builder.build_success_card("缺陷已重新打开"), message_id
                else:
                    return self.builder.build_error_card("操作失败，请重试"), message_id

            elif action == "save_plan_end":
                # 保存计划完成时间
                return self.builder.build_success_card("计划完成时间已更新"), message_id

            elif action == "save_plan_start":
                # 保存计划开始时间
                return self.builder.build_success_card("计划开始时间已更新"), message_id

            elif action == "save_remark":
                # 保存备注
                return self.builder.build_success_card("备注已更新"), message_id

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
        form_data 格式: Lark card input 提交的数据
        """
        logging.info(f"handle_form_submit: form_data={form_data}")

        record_id = form_data.get("record_id")
        table_id = form_data.get("table_id")
        message_id = form_data.get("message_id", "")
        action = form_data.get("action", "")

        # 权限检查
        if not self._check_permission(record_id, table_id, user_id):
            return self.builder.build_error_card("您不是该任务负责人，无法操作"), message_id

        # 构建更新字段
        fields = {}
        # 计划完成时间
        plan_end = form_data.get("plan_end") or form_data.get("date")
        if plan_end:
            fields["计划完成"] = plan_end
        # 计划开始时间
        plan_start = form_data.get("plan_start")
        if plan_start:
            fields["计划开始"] = plan_start
        # 备注
        remark = form_data.get("remark")
        if remark:
            fields["备注"] = remark

        if not fields:
            return self.builder.build_error_card("没有需要保存的内容"), message_id

        # 更新记录
        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"handle_form_submit: success, action={action}, fields={fields}")
            return self.builder.build_success_card("已更新"), message_id
        except Exception as e:
            logging.error(f"handle_form_submit error: {e}")
            return self.builder.build_error_card(f"更新失败: {str(e)}"), message_id

    def _check_permission(self, record_id: str, table_id: str, user_id: str) -> bool:
        """检查用户是否有权限操作该任务（管理员或负责人）"""
        # 首先检查是否是管理员
        if user_id in ADMIN_USERS:
            logging.info(f"_check_permission: user {user_id} is admin, allowed")
            return True

        if not record_id or not table_id:
            logging.warning(f"_check_permission: missing record_id or table_id")
            return False

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

        result = user_id in owner_ids
        logging.info(f"_check_permission: user_id={user_id}, owner_ids={owner_ids}, result={result}")
        return result

    def _get_owner_field(self, table_id: str) -> str:
        """根据表 ID 返回负责人字段名"""
        return self.TABLE_OWNER_FIELDS.get(table_id, "负责人")

    def _mark_task_start(self, record_id: str, table_id: str) -> bool:
        """标记任务开始"""
        today = date.today().isoformat()
        fields = {"实际开始": today}
        # 根据表 ID 设置对应的进行中状态
        if table_id == "tblo5L10rWTWjKf9":
            fields["状态"] = "进行中"
        elif table_id == "tblpajWitnEuY3G5":
            fields["状态"] = "处理中"
        elif table_id == "tblS8qBWisBv6O9N":
            fields["状态"] = "进行中"
        elif table_id == "tbl98ZxWyCcgounb":
            fields["任务状态"] = "待测试"
        elif table_id == "tblm13vKwIfwYBt0":
            fields["任务状态"] = "测试中"

        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"_mark_task_start: success, record_id={record_id}, table_id={table_id}, fields={fields}")
            return True
        except Exception as e:
            logging.warning(f"_mark_task_start: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False

    def _mark_task_complete(self, record_id: str, table_id: str) -> bool:
        """标记任务完成"""
        today = date.today().isoformat()
        fields = {"实际完成": today}

        # 根据表 ID 确定状态字段
        if table_id == "tblo5L10rWTWjKf9":
            fields["状态"] = "已完成"
        elif table_id == "tblpajWitnEuY3G5":
            fields["状态"] = "处理完成"
        elif table_id == "tblS8qBWisBv6O9N":
            fields["状态"] = "已完成"
        elif table_id == "tbl98ZxWyCcgounb":
            fields["任务状态"] = "提测通过"
        elif table_id == "tblm13vKwIfwYBt0":
            fields["任务状态"] = "已完成测试"

        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"_mark_task_complete: success, record_id={record_id}, table_id={table_id}, fields={fields}")
            return True
        except Exception as e:
            logging.warning(f"_mark_task_complete: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False

    def _mark_defect_accept(self, record_id: str, table_id: str) -> bool:
        """接受缺陷处理"""
        status_fields = self.DEFECT_IN_PROGRESS_STATUS.get(table_id, {})
        fields = dict(status_fields)

        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"_mark_defect_accept: success, record_id={record_id}, table_id={table_id}")
            return True
        except Exception as e:
            logging.warning(f"_mark_defect_accept: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False

    def _mark_defect_close(self, record_id: str, table_id: str) -> bool:
        """关闭缺陷"""
        today = date.today().isoformat()
        fields = {"当前状态": "已关闭", "关闭时间": today}

        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"_mark_defect_close: success, record_id={record_id}, table_id={table_id}")
            return True
        except Exception as e:
            logging.warning(f"_mark_defect_close: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False

    def _mark_defect_reopen(self, record_id: str, table_id: str) -> bool:
        """重新打开缺陷"""
        fields = {"当前状态": "重新打开"}

        try:
            self.bitable.update_record(table_id, record_id, fields)
            logging.info(f"_mark_defect_reopen: success, record_id={record_id}, table_id={table_id}")
            return True
        except Exception as e:
            logging.warning(f"_mark_defect_reopen: update_record failed, record_id={record_id}, table_id={table_id}, error: {e}")
            return False
