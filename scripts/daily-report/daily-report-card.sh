#!/usr/bin/env bash
set -euo pipefail

# 加载配置 - 使用 ../daily_report/ 路径（因为 config 在 daily_report 目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../daily_report/config.sh"

# 腾讯云函数 API 地址（部署后在腾讯云控制台获取）
SCF_API_URL="${SCF_API_URL:-}"

# 生成概览卡片并推送
main() {
    echo "=== 推送交互式日报卡片 ==="

    # 检查云函数 API 地址
    if [ -z "${SCF_API_URL}" ]; then
        echo "Error: SCF_API_URL not set. Please configure your Tencent Cloud Function URL."
        exit 1
    fi

    # 调用云函数 API 获取概览卡片
    echo "Fetching card from cloud function..."
    local card_json
    card_json=$(curl -s -X POST "${SCF_API_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"action\":{\"action_type\":\"get_overview\"}}")

    if [ -z "$card_json" ]; then
        echo "Error: Failed to fetch card from cloud function"
        exit 1
    fi

    echo "Card fetched, sending to chat..."

    # 发送到群聊
    if [ -n "${CHAT_ID}" ]; then
        echo "Sending interactive card to group chat..."
        lark-cli im +messages-send \
            --chat-id "${CHAT_ID}" \
            --content "${card_json}" \
            --msg-type interactive 2>&1
    fi

    # 发送到管理员私聊
    if [ -n "${ADMIN_ID}" ]; then
        echo "Sending interactive card to admin..."
        lark-cli im +messages-send \
            --user-id "${ADMIN_ID}" \
            --content "${card_json}" \
            --msg-type interactive 2>&1 || true
    fi

    echo "=== 完成 ==="
}

main "$@"