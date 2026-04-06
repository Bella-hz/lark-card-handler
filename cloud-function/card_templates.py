#!/usr/bin/env python3
"""
飞书交互卡片 JSON 模板生成器
"""

from typing import List, Dict, Any, Optional
from datetime import date


def build_overview_card(today: date, overview: Dict, message_id: str = "") -> Dict:
    """
    构建概览卡片（主卡片）
    overview 格式:
    {
        "dev_in_progress": 12,
        "dev_completed": 3,
        "dev_overdue": 2,
        "test_in_progress": 8,
        "test_completed": 1,
        "test_overdue": 1,
        "defect_pending": 5,
        "defect_processing": 3,
        "defect_closed": 1,
    }
    Note: message_id 保留用于未来功能（如消息编辑/删除），当前未使用。
    """
    # 使用 .get() 并设置默认值，避免 KeyError
    dev_in_progress = overview.get("dev_in_progress", 0)
    dev_completed = overview.get("dev_completed", 0)
    dev_overdue = overview.get("dev_overdue", 0)
    test_in_progress = overview.get("test_in_progress", 0)
    test_completed = overview.get("test_completed", 0)
    test_overdue = overview.get("test_overdue", 0)
    defect_pending = overview.get("defect_pending", 0)
    defect_processing = overview.get("defect_processing", 0)
    defect_closed = overview.get("defect_closed", 0)

    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📋 研发日报 {today.strftime('%Y-%m-%d')}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**📊 概览**"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"- 开发任务：进行中 {dev_in_progress} "
                            f"| 今日完成 {dev_completed} "
                            f"| 逾期 {dev_overdue}\n"
                            f"- 测试任务：进行中 {test_in_progress} "
                            f"| 今日完成 {test_completed} "
                            f"| 逾期 {test_overdue}\n"
                            f"- 缺陷问题：待处理 {defect_pending} "
                            f"| 处理中 {defect_processing} "
                            f"| 今日关闭 {defect_closed}"
                        )
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"🔴 逾期 ({dev_overdue + test_overdue})"
                            },
                            "type": "primary",
                            "value": {"action": "show_overdue"},
                            "confirm": {
                                "title": {"tag": "plain_text", "content": "查看逾期任务"},
                                "text": {"tag": "plain_text", "content": "即将加载逾期任务列表..."}
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"✅ 今日完成 ({dev_completed + test_completed})"
                            },
                            "type": "primary",
                            "value": {"action": "show_completed"},
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"🔄 进行中 ({dev_in_progress + test_in_progress})"
                            },
                            "type": "primary",
                            "value": {"action": "show_in_progress"},
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"🐛 缺陷 ({defect_pending + defect_processing})"
                            },
                            "type": "primary",
                            "value": {"action": "show_defects"},
                        },
                    ]
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"本卡片由机器人自动生成 | 最后更新: {today.strftime('%H:%M')}"
                        }
                    ]
                }
            ]
        }
    }


def build_task_list_card(today: date, category: str, tasks: List[Dict]) -> Dict:
    """
    构建任务列表卡片
    tasks 格式: [{"record_id": "...", "table_id": "...", "name": "...", "user": "...", "plan_date": "...", "status": "...", "extra": "..."}]
    """
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📋 研发日报 - {category}** ({today.strftime('%Y-%m-%d')})"
            }
        },
        {"tag": "hr"}
    ]

    # 空任务列表处理
    if not tasks:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "暂无任务"
            }
        })
    else:
        for task in tasks:
            # 使用 .get() 并设置默认值，避免 KeyError
            task_name = task.get("name", "未命名任务")
            task_user = task.get("user", "未分配")
            task_record_id = task.get("record_id", "")
            task_table_id = task.get("table_id", "")

            # 任务行
            plan_str = task.get("plan_date", "未计划")
            extra = task.get("extra", "")
            extra_str = f"\n   {extra}" if extra else ""

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**{task_name}**\n"
                        f"👤 {task_user} | 📅 计划: {plan_str}{extra_str}"
                    )
                }
            })

        # 操作按钮
        actions = [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "✓ 完成"},
                "type": "primary",
                "value": {
                    "action": "complete",
                    "record_id": task_record_id,
                    "table_id": task_table_id
                }
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📅 改时间"},
                "type": "default",
                "value": {
                    "action": "edit_date",
                    "record_id": task_record_id,
                    "table_id": task_table_id
                }
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📝 备注"},
                "type": "default",
                "value": {
                    "action": "edit_remark",
                    "record_id": task_record_id,
                    "table_id": task_table_id
                }
            }
        ]

        elements.append({
            "tag": "action",
            "actions": actions
        })
        elements.append({"tag": "hr"})
    # 返回按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "← 返回概览"},
                "type": "default",
                "value": {"action": "show_overview"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 刷新"},
                "type": "default",
                "value": {"action": "refresh"}
            }
        ]
    })

    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📋 研发日报 - {category}"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }


def build_form_card(title: str, form_type: str, record_id: str, table_id: str, fields: List[Dict]) -> Dict:
    """
    构建表单卡片（用于修改时间和备注）
    fields 格式: [{"label": "...", "name": "...", "type": "date|text", "value": "..."}]
    """
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{title}**"
            }
        }
    ]

    for field in fields:
        # 使用 .get() 并设置默认值，避免 KeyError
        field_label = field.get("label", "")
        field_name = field.get("name", "")
        field_type = field.get("type", "text")

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": field_label
            }
        })

        if field_type == "date":
            elements.append({
                "tag": "input",
                "name": field_name,
                "label": {"tag": "plain_text", "content": field_label}
            })
        else:
            elements.append({
                "tag": "textarea",
                "name": field_name,
                "placeholder": {"tag": "plain_text", "content": field.get("placeholder", "")}
            })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "取消"},
                "type": "default",
                "value": {"action": "cancel"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "保存"},
                "type": "primary",
                "value": {
                    "action": form_type,
                    "record_id": record_id,
                    "table_id": table_id
                }
            }
        ]
    })

    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": elements
        }
    }


def build_success_card(message: str) -> Dict:
    """构建成功提示卡片"""
    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "✅ 操作成功"},
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": message
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "← 返回概览"},
                            "type": "default",
                            "value": {"action": "show_overview"}
                        }
                    ]
                }
            ]
        }
    }


def build_error_card(message: str) -> Dict:
    """构建错误提示卡片"""
    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "❌ 操作失败"},
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": message
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "← 返回"},
                            "type": "default",
                            "value": {"action": "show_overview"}
                        }
                    ]
                }
            ]
        }
    }


def build_defect_card(today: date, defects: List[Dict]) -> Dict:
    """
    构建缺陷卡片
    defects 格式: [{"record_id": "...", "table_id": "...", "name": "...", "user": "...", "priority": "...", "status": "..."}]
    """
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🐛 研发日报 - 缺陷列表** ({today.strftime('%Y-%m-%d')})"
            }
        },
        {"tag": "hr"}
    ]

    if not defects:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "暂无待处理缺陷"
            }
        })
    else:
        for defect in defects:
            priority = defect.get("priority", "")
            status = defect.get("status", "")

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{defect.get('name', '未命名')}**\n👤 {defect.get('user', '未分配')} | {priority} | {status}"
                }
            })

            # 操作按钮
            actions = [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✓ 关闭"},
                    "type": "primary",
                    "value": {
                        "action": "close_defect",
                        "record_id": defect.get("record_id", ""),
                        "table_id": defect.get("table_id", "")
                    }
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📝 备注"},
                    "type": "default",
                    "value": {
                        "action": "edit_defect_remark",
                        "record_id": defect.get("record_id", ""),
                        "table_id": defect.get("table_id", "")
                    }
                }
            ]

            elements.append({
                "tag": "action",
                "actions": actions
            })
            elements.append({"tag": "hr"})

    # 返回按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "← 返回概览"},
                "type": "default",
                "value": {"action": "show_overview"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 刷新"},
                "type": "default",
                "value": {"action": "refresh"}
            }
        ]
    })

    return {
        "schema": "2.0",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🐛 缺陷列表"
                },
                "template": "orange"
            },
            "elements": elements
        }
    }
