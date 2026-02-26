#!/bin/bash
# Grafana 集成设置脚本

echo "=== SOC Copilot → Grafana 集成设置 ==="
echo ""

echo "✅ Grafana 服务状态:"
docker compose -f docker-compose.grafana.yml ps
echo ""

echo "📊 仪表板配置文件已创建:"
echo "   - grafana-soc-dashboard.json"
echo "   - grafana-alert-rules.json"
echo ""

echo "🚀 快速开始:"
echo ""
echo "1. 访问 Grafana: http://localhost:3001"
echo "   用户名: admin"
echo "   密码: admin"
echo ""
echo "2. 添加 Loki 数据源:"
echo "   → Configuration → Data sources → Add data source"
echo "   → 选择: Loki"
echo "   → URL: http://loki:3100"
echo "   → Save & Test"
echo ""
echo "3. 导入仪表板:"
echo "   → Dashboard → Import"
echo "   → 上传: grafana-soc-dashboard.json"
echo "   → 选择 Loki 数据源"
echo ""
echo "4. 查看告警:"
echo "   → Explore → Loki"
echo "   → 查询: {job=\"soc-copilot\"}"
echo "   → Run query"
echo ""

echo "📝 发送测试告警:"
echo "   python3 test_loki_integration.py"
echo ""
