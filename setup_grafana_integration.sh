#!/bin/bash
# Grafana 集成设置脚本

echo "=== SOC Copilot → Grafana 集成设置 ==="
echo ""

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}步骤 1: 确认 Grafana 服务状态${NC}"
docker compose -f docker-compose.grafana.yml ps
echo ""

echo -e "${YELLOW}步骤 2: 导入 SOC Copilot 仪表板${NC}"
echo "请按以下步骤操作:"
echo "  1. 浏览器访问: http://localhost:3001"
echo "  2. 登录 (admin/admin)"
echo "  3. Dashboard → Import"
echo "  4. 上传文件: grafana-soc-dashboard.json"
echo "  5. 选择 Loki 数据源"
echo ""

echo -e "${YELLOW}步骤 3: 配置 Loki 数据源${NC}"
echo "如果还没配置:"
echo "  1. Configuration → Data sources → Add data source"
echo "  2. 选择: Loki"
echo "  3. URL: http://loki:3100"
echo "  4. Save & Test"
echo ""

echo -e "${YELLOW}步骤 4: 测试告警发送${NC}"
echo "运行测试脚本:"
echo "  python3 test_loki_integration.py"
echo ""

echo -e "${YELLOW}步骤 5: 在 Grafana 查看告警${NC}"
echo "  1. 进入 Explore"
echo "  2. 选择 Loki 数据源"
echo "  3. 查询: {job=\"soc-copilot\"}"
echo "  4. 点击 Run query"
echo ""

echo -e "${GREEN}✅ 设置完成！${NC}"
echo ""
echo "接下来您可以:"
echo "  - 自定义仪表板"
echo "  - 配置告警规则"
echo "  - 设置通知渠道"
echo ""

# 询问是否发送测试告警
read -p "是否现在发送测试告警到 Loki？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "发送测试告警..."
    python3 test_loki_integration.py
fi
