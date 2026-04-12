# Wazuh 集成完成总结

**状态**: ✅ **准备就绪**  
**日期**: 2026-02-26  
**版本**: v1.0.0

---

## 📋 已创建的文件

### Docker Compose 配置

✅ `docker-compose.wazuh.yml` - Wazuh 完整栈配置

- Wazuh Manager (端口 55000)
- Wazuh Indexer/OpenSearch (端口 9200)
- Wazuh Dashboard (端口 5601)
- PostgreSQL 数据库 (端口 5432)

### 环境变量

✅ `.env.wazuh.example` - 环境变量模板

- 所有默认密码和配置
- 可复制为 `.env.wazuh` 使用

### 安装和集成脚本

✅ `setup_wazuh.sh` - 一键安装脚本

- 自动检查 Docker 和 Docker Compose
- 生成所有必要的配置文件
- 启动 Wazuh 栈
- 等待服务健康检查
- 显示访问凭据

✅ `integrate_wazuh.sh` - SOC Copilot 集成脚本

- 配置 backend/.env
- 测试 Wazuh API 连接
- 可选安装 Wazuh Agent
- 重启后端服务

### 测试脚本

✅ `test_wazuh_stream.sh` - 测试脚本（已存在）

- 启动流服务
- 检查状态
- 发送测试告警

### 文档

✅ `docs/WAZUH_INSTALLATION.md` - 完整安装指南

- 先决条件检查
- 分步安装说明
- 集成步骤
- 验证方法
- 故障排除
- 维护指南

✅ `WAZUH_STREAM_TROUBLESHOOT.md` - 故障排除指南（已存在）

- 常见问题诊断
- 解决方案
- 调试步骤

---

## 🚀 快速开始

### 步骤 1: 安装 Wazuh

```bash
# 1. 编辑环境变量（可选）
cp .env.wazuh.example .env.wazuh
nano .env.wazuh  # 更新密码

# 2. 运行安装脚本
./setup_wazuh.sh

# 3. 等待服务启动（大约 2-3 分钟）
```

**安装完成后，您可以访问：**

- Wazuh Dashboard: https://localhost:5601 (admin / ChangeThisPassword123!)
- Wazuh API: https://localhost:55000 (wazuh-wui / wazuh-wui-password)
- OpenSearch: https://localhost:9200

### 步骤 2: 集成到 SOC Copilot

```bash
# 运行集成脚本
./integrate_wazuh.sh

# 脚本会自动配置 backend/.env
```

### 步骤 3: 测试连接

```bash
# 方法 1: 使用测试脚本
./test_wazuh_stream.sh

# 方法 2: 手动测试
# 1. 登录前端获取 JWT Token
# 2. 启动流服务
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 发送测试告警
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"agent_id": "001", "severity": "high", "count": 3}'
```

### 步骤 4: 验证前端

1. 打开浏览器访问 `http://localhost:3003/zh/wazuh`
2. 应该看到 "✅ 已连接到 Wazuh 实时流"
3. 测试告警应该会实时显示在页面上

---

## 📁 文件结构

```
sec/
├── docker-compose.wazuh.yml          # Wazuh Docker Compose 配置
├── .env.wazuh.example                # 环境变量模板
├── setup_wazuh.sh                    # 安装脚本 ⭐
├── integrate_wazuh.sh                # 集成脚本 ⭐
├── test_wazuh_stream.sh              # 测试脚本
├── WAZUH_STREAM_TROUBLESHOOT.md      # 故障排除
├── WAZUH_INTEGRATION_COMPLETE.md     # 本文件
├── config/
│   ├── wazuh-indexer/
│   │   └── opensearch.yml           # OpenSearch 配置（自动生成）
│   ├── wazuh-manager/
│   │   ├── ossec.conf               # Wazuh 管理器配置（自动生成）
│   │   └── api.yaml                 # API 配置（自动生成）
│   └── wazuh-dashboard/
│       ├── opensearch_dashboards.yml # Dashboard 配置（自动生成）
│       └── wazuh.yml                 # Wazuh UI 配置（自动生成）
├── backend/
│   └── .env                         # 后端配置（自动更新）
└── docs/
    ├── WAZUH_INSTALLATION.md         # 完整安装指南
    ├── WAZUH_QUICKREF.md            # 快速参考（已存在）
    └── wazuh_integration.md         # 集成说明
```

---

## 🔑 默认凭据

### Wazuh Dashboard

- **URL**: https://localhost:5601
- **用户名**: admin
- **密码**: ChangeThisPassword123!

### Wazuh API

- **URL**: https://localhost:55000
- **用户名**: wazuh-wui
- **密码**: wazuh-wui-password

### OpenSearch

- **URL**: https://localhost:9200
- **用户名**: admin
- **密码**: ChangeThisPassword123!

⚠️ **重要**: 生产环境中请修改这些默认密码！

---

## 🛠️ 常用命令

### 查看 Wazuh 服务状态

```bash
docker compose -f docker-compose.wazuh.yml ps
```

### 查看 Wazuh 日志

```bash
# 所有服务
docker compose -f docker-compose.wazuh.yml logs -f

# 特定服务
docker compose -f docker-compose.wazuh.yml logs -f wazuh.manager
docker compose -f docker-compose.wazuh.yml logs -f wazuh.dashboard
```

### 停止 Wazuh

```bash
docker compose -f docker-compose.wazuh.yml down
```

### 重启 Wazuh

```bash
docker compose -f docker-compose.wazuh.yml restart
```

### 检查 Wazuh API 健康状态

```bash
curl -k https://localhost:55000/healthcheck
```

---

## 🔧 故障排除

### 问题 1: 前端显示 "未连接到 Wazuh 实时流"

**解决方案**：

```bash
# 1. 检查 Wazuh 是否运行
docker compose -f docker-compose.wazuh.yml ps

# 2. 检查后端配置
grep WAZUH_ENABLED backend/.env

# 3. 启动流服务
TOKEN="your_jwt_token"
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"

# 4. 查看详细故障排除指南
cat WAZUH_STREAM_TROUBLESHOOT.md
```

### 问题 2: Wazuh 服务未启动

**解决方案**：

```bash
# 查看日志
docker compose -f docker-compose.wazuh.yml logs -f

# 常见问题：
# - 端口冲突：检查 5601, 55000, 9200 是否被占用
# - 内存不足：确保至少 4GB RAM 可用
# - 权限问题：确保 Docker 有足够权限
```

### 问题 3: 无法访问 Wazuh Dashboard

**解决方案**：

```bash
# 1. 确认服务健康
docker compose -f docker-compose.wazuh.yml ps wazuh.dashboard

# 2. 等待服务启动（最多 2 分钟）
docker compose -f docker-compose.wazuh.yml logs -f wazuh.dashboard

# 3. 浏览器接受 SSL 警告（自签名证书）
# 或使用: http://localhost:5601 (如果配置了 HTTP)
```

---

## 📚 相关文档

1. **完整安装指南**: `docs/WAZUH_INSTALLATION.md`
2. **快速参考**: `docs/WAZUH_QUICKREF.md`
3. **故障排除**: `WAZUH_STREAM_TROUBLESHOOT.md`
4. **WebSocket 功能指南**: `docs/websocket_guide.md`
5. **性能优化指南**: `docs/performance_guide.md`

---

## ✅ 集成检查清单

- [ ] Docker 和 Docker Compose 已安装
- [ ] 端口 5601, 55000, 9200, 5432 可用
- [ ] `.env.wazuh` 已创建并配置
- [ ] Wazuh 栈已启动 (`./setup_wazuh.sh`)
- [ ] Wazuh Dashboard 可访问
- [ ] 后端 `.env` 已更新 (`./integrate_wazuh.sh`)
- [ ] 后端服务已重启
- [ ] Wazuh 流服务已启动
- [ ] 前端显示 "已连接"
- [ ] 测试告警可接收

---

## 🎉 集成完成！

如果您已完成以上所有步骤，Wazuh 现在应该已经完全集成到 SOC Copilot 中了！

**下一步**：

1. 登录 Wazuh Dashboard 探索功能
2. 在 SOC Copilot 中配置告警规则
3. 安装 Wazuh Agents 到受监控的主机
4. 开始实时监控安全事件！

---

**需要帮助？**

- 查看完整文档: `docs/WAZUH_INSTALLATION.md`
- 查看故障排除: `WAZUH_STREAM_TROUBLESHOOT.md`
- 查看服务日志: `docker compose -f docker-compose.wazuh.yml logs -f`

---

**生成时间**: 2026-02-26  
**文档版本**: v1.0.0
