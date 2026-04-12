#!/bin/bash
# 最终验证脚本

echo "================================"
echo "SOC Copilot 集成验证"
echo "================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 测试计数
PASSED=0
FAILED=0

# 测试函数
test_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    response=$(curl -s "$url" 2>&1)
    
    if echo "$response" | grep -q "$expected"; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "   Expected: $expected"
        echo "   Got: $response"
        ((FAILED++))
        return 1
    fi
}

# 运行测试
echo "=== 服务健康检查 ==="
test_service "Grafana" "http://localhost:3001/api/health" "ok"
test_service "Loki" "http://localhost:3100/ready" "ready"
echo ""

echo "=== Docker 容器检查 ==="
if docker compose -f docker-compose.grafana.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Grafana 栈运行正常${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Grafana 栈未运行${NC}"
    ((FAILED++))
fi
echo ""

echo "=== Backend 集成检查 ==="
if [ -f "backend/services/loki_alert_sender.py" ]; then
    echo -e "${GREEN}✅ Loki 发送器已安装${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Loki 发送器未找到${NC}"
    ((FAILED++))
fi

if [ -f "backend/routers/alerts_to_loki.py" ]; then
    echo -e "${GREEN}✅ 告警路由已安装${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ 告警路由未找到${NC}"
    ((FAILED++))
fi
echo ""

echo "=== 配置文件检查 ==="
if [ -f "grafana-soc-dashboard.json" ]; then
    echo -e "${GREEN}✅ Grafana 仪表板配置存在${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ 仪表板配置未找到${NC}"
    ((FAILED++))
fi

if [ -f "docker-compose.grafana.yml" ]; then
    echo -e "${GREEN}✅ Docker Compose 配置存在${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Docker Compose 配置未找到${NC}"
    ((FAILED++))
fi
echo ""

# 测试告警发送
echo "=== 告警发送测试 ==="
echo -n "发送测试告警到 Loki... "
if python3 test_loki_integration.py 2>&1 | grep -q "✅"; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi
echo ""

# 总结
echo "================================"
echo "测试结果"
echo "================================"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！集成完成！${NC}"
    echo ""
    echo "接下来可以："
    echo "  1. 访问 Grafana: http://localhost:3001"
    echo "  2. 配置 Loki 数据源"
    echo "  3. 导入仪表板: grafana-soc-dashboard.json"
    echo "  4. 查看测试告警"
    exit 0
else
    echo -e "${YELLOW}⚠️  部分测试失败，请检查上述错误${NC}"
    exit 1
fi
