#!/usr/bin/env python3
"""
飞书交互卡片 JSON 模板生成器
"""

from typing import List, Dict, Any, Optional
from datetime import date


def build_overview_card(today: date, overview: Dict, message_id: str = "") -> Dict:
    """
    构建概览卡片（主卡片）
    """
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


def build_task_list_card(today: date, category: str, tasks: List[Dict]) -> Dict:
    """
    构建任务列表卡片
    tasks 格式: [{"record_id": "...", "table_id": "...", "name": "...", "user": "...", "plan_date": "...", "status": "..."}]
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
            task_name = task.get("name", "未命名任务")
            task_user = task.get("user", "未分配")
            task_record_id = task.get("record_id", "")
            task_table_id = task.get("table_id", "")
            plan_str = task.get("plan_date", "未计划")
            status = task.get("status", "")

            # 任务行
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**{task_name}**\n"
                        f"👤 {task_user} | 📅 计划: {plan_str} | 状态: {status}"
                    )
                }
            })

            # 根据类别显示不同按钮
            if category == "进行中":
                # 进行中任务：显示开始/结束按钮
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "▶️ 开始"},
                        "type": "primary",
                        "value": {
                            "action": "start_task",
                            "record_id": task_record_id,
                            "table_id": task_table_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🏁 结束"},
                        "type": "danger",
                        "value": {
                            "action": "complete_task",
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
                ]
            elif category == "今日完成" or category == "逾期任务":
                # 已完成/逾期任务：显示结束和备注按钮
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🏁 结束"},
                        "type": "danger",
                        "value": {
                            "action": "complete_task",
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
                    },
                ]
            else:
                # 默认按钮
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✓ 完成"},
                        "type": "primary",
                        "value": {
                            "action": "complete_task",
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
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"📋 {category}"
            },
            "template": "blue"
        },
        "elements": elements
    }


def build_form_card(title: str, form_type: str, record_id: str, table_id: str, fields: List[Dict] = None) -> Dict:
    """
    构建表单卡片（用于修改时间和备注）
    """
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{title}**"
            }
        },
        {"tag": "hr"}
    ]

    if form_type == "save_date":
        # 日期输入
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "计划完成日期"
            }
        })
        elements.append({
            "tag": "input",
            "name": "date",
            "label": {"tag": "plain_text", "content": "选择日期"}
        })
    else:
        # 备注输入
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "备注内容"
            }
        })
        elements.append({
            "tag": "textarea",
            "name": "remark",
            "placeholder": {"tag": "plain_text", "content": "请输入备注..."}
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
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue"
        },
        "elements": elements
    }


def build_success_card(message: str) -> Dict:
    """构建成功提示卡片"""
    return {
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


def build_error_card(message: str) -> Dict:
    """构建错误提示卡片"""
    return {
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
            name = defect.get("name", "未命名")
            user = defect.get("user", "未分配")
            record_id = defect.get("record_id", "")
            table_id = defect.get("table_id", "")

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{name}**\n👤 {user} | {priority} | 状态: {status}"
                }
            })

            # 根据状态显示不同按钮
            if status in ("待处理", "新建", "重新打开"):
                # 待处理状态：可以接受
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✓ 接受"},
                        "type": "primary",
                        "value": {
                            "action": "defect_accept",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 备注"},
                        "type": "default",
                        "value": {
                            "action": "edit_remark",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    }
                ]
            elif status in ("处理中", "已确认", "修复中"):
                # 处理中状态：可以关闭
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🏁 关闭"},
                        "type": "danger",
                        "value": {
                            "action": "defect_close",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "↩️ 重新打开"},
                        "type": "default",
                        "value": {
                            "action": "defect_reopen",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 备注"},
                        "type": "default",
                        "value": {
                            "action": "edit_remark",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    }
                ]
            else:
                # 其他状态：可以重新打开
                actions = [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "↩️ 重新打开"},
                        "type": "default",
                        "value": {
                            "action": "defect_reopen",
                            "record_id": record_id,
                            "table_id": table_id
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 备注"},
                        "type": "default",
                        "value": {
                            "action": "edit_remark",
                            "record_id": record_id,
                            "table_id": table_id
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
                "value": {"action": "show_defects"}
            }
        ]
    })

    return {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "🐛 缺陷列表"
            },
            "template": "orange"
        },
        "elements": elements
    }
