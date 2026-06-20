#!/bin/bash
###############################################################################
# 飞书通知快速配置脚本
#
# 用法: ./scripts/setup-feishu.sh
###############################################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║          飞书通知配置向导                              ║"
echo "║          SOC Copilot v0.9.0                           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# 步骤 1: 引导用户创建飞书机器人
echo -e "${BLUE}步骤 1: 获取飞书 Webhook URL${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""
echo "1. 打开飞书客户端"
echo "2. 进入要接收告警的群聊"
echo "3. 点击群设置 → 群机器人 → 添加机器人"
echo "4. 选择「自定义机器人」"
echo "5. 设置机器人名称: SOC Copilot"
echo "6. 复制生成的 Webhook URL"
echo ""
echo -e "${YELLOW}Webhook URL 格式: ${NC}"
echo "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
echo ""
echo -e "${CYAN}按 Enter 继续下一步...${NC}"
read

# 步骤 2: 输入 Webhook URL
echo ""
echo -e "${BLUE}步骤 2: 输入 Webhook URL${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""
read -p "请粘贴您的飞书 Webhook URL: " WEBHOOK_URL

# 验证 URL 格式
if [[ ! $WEBHOOK_URL =~ ^https://open\.feishu\.cn/open-apis/bot/v2/hook/ ]]; then
    echo -e "${RED}❌ 错误: Webhook URL 格式不正确${NC}"
    echo "   URL 应该以 https://open.feishu.cn/open-apis/bot/v2/hook/ 开头"
    echo ""
    echo "请检查后重试"
    exit 1
fi

echo -e "${GREEN}✅ URL 格式验证通过${NC}"
echo ""

# 步骤 3: 选择配置方式
echo -e "${BLUE}步骤 3: 选择配置方式${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""
echo "请选择配置方式:"
echo "  1. 更新 .env 文件 (推荐)"
echo "  2. 仅测试不保存"
echo "  3. 退出"
echo ""
read -p "请选择 (1-3): " CHOICE

case $CHOICE in
    1)
        # 更新 .env 文件
        ENV_FILE="$PWD/.env"

        echo ""
        echo -e "${BLUE}正在更新配置文件...${NC}"

        # 如果 .env 不存在，从模板创建
        if [ ! -f "$ENV_FILE" ]; then
            if [ -f ".env.example" ]; then
                cp .env.example "$ENV_FILE"
                echo -e "${GREEN}✅ 已从模板创建 .env 文件${NC}"
            else
                touch "$ENV_FILE"
            fi
        fi

        # 添加或更新 FEISHU_WEBHOOK_URL
        if grep -q "^FEISHU_WEBHOOK_URL=" "$ENV_FILE" 2>/dev/null; then
            # 更新现有配置
            sed -i.bak "s|^FEISHU_WEBHOOK_URL=.*|FEISHU_WEBHOOK_URL=$WEBHOOK_URL|" "$ENV_FILE"
            echo -e "${GREEN}✅ 已更新现有配置${NC}"
        else
            # 添加新配置
            echo "" >> "$ENV_FILE"
            echo "# 飞书通知配置" >> "$ENV_FILE"
            echo "FEISHU_WEBHOOK_URL=$WEBHOOK_URL" >> "$ENV_FILE"
            echo -e "${GREEN}✅ 已添加新配置${NC}"
        fi

        echo ""
        echo -e "${GREEN}配置已保存到: $ENV_FILE${NC}"
        ;;
    2)
        echo ""
        echo -e "${YELLOW}⚠️  跳过保存，仅进行测试${NC}"
        ;;
    3)
        echo ""
        echo "退出配置"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}步骤 4: 测试飞书通知${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""
echo -e "${CYAN}正在发送测试消息...${NC}"
echo ""

# 构造测试消息
TEST_MESSAGE='{
  "msg_type": "interactive",
  "card": {
    "config": {
      "wide_screen_mode": true
    },
    "header": {
      "title": {
        "content": "✅ 飞书通知配置成功！",
        "tag": "plain_text"
      },
      "template": "green"
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "content": "**SOC Copilot 安全告警系统**\n\n恭喜！您已成功配置飞书通知。\n\n当系统检测到安全威胁时，您将在此群聊中收到实时告警通知。",
          "tag": "lark_md"
        }
      },
      {
        "tag": "hr"
      },
      {
        "tag": "div",
        "text": {
          "content": "📅 测试时间: '$(date '+%Y-%m-%d %H:%M:%S')'\n🤖 SOC Copilot v0.9.0",
          "tag": "plain_text"
        }
      }
    ]
  }
}'

# 发送测试消息
if curl -s -X POST "$WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "$TEST_MESSAGE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 测试消息发送成功！${NC}"
    echo ""
    echo "请检查您的飞书群聊，应该已收到一条测试消息。"
else
    echo -e "${RED}❌ 测试消息发送失败${NC}"
    echo ""
    echo "可能的原因:"
    echo "  1. Webhook URL 不正确"
    echo "  2. 网络连接问题"
    echo "  3. 机器人已被移除"
    echo ""
    echo "请检查后重试"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 5: 配置完成${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}🎉 飞书通知配置完成！${NC}"
echo ""
echo "下一步:"
echo "  1. ${CYAN}启动 SOC Copilot 服务${NC}"
echo "     docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "  2. ${CYAN}发送告警测试${NC}"
echo "     curl -X POST http://localhost:8000/api/v1/security-alerts/ingest \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"source\":\"test\",\"event_id\":\"test-001\",\"event_type\":\"test\",\"severity\":\"high\",\"title\":\"测试告警\",\"description\":\"这是一条测试告警\",\"timestamp\":\"2026-02-24T12:00:00Z\"}'"
echo ""
echo "  3. ${CYAN}查看通知文档${NC}"
echo "     docs/FEISHU_SETUP_GUIDE.md"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo "  - 配置更多通知渠道可提高可靠性"
echo "  - 建议同时配置 Slack 和 Email 作为备用"
echo ""
