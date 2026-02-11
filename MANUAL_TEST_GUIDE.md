# SOC Copilot 手动测试指南

## 测试环境准备

### 确保服务运行中

| 服务 | 地址 | 状态检查 |
|------|------|----------|
| 后端 | http://localhost:8000 | 访问 http://localhost:8000/api/health |
| 前端 | http://localhost:3000 | 浏览器打开 |
| API文档 | http://localhost:8000/docs | Swagger UI |

---

## 测试一：健康检查

### 步骤
1. 打开浏览器或终端
2. 访问：`http://localhost:8000/api/health`
3. 检查返回结果

### 预期结果
```json
{
  "status": "ok",
  "version": "0.4.0"
}
```

---

## 测试二：告警分析 (Alert Analyzer)

### 步骤
1. 打开前端页面 http://localhost:3000
2. 切换到 **"Alert Analyzer"** 标签页
3. 输入以下安全日志：

```
[2024-02-06 10:23:45] FAILED_LOGIN - User admin from IP 192.168.1.100 failed to authenticate. Reason: invalid password
[2024-02-06 10:24:12] SUSPICIOUS_PROCESS - Process 'svchost.exe' spawned from 'C:\Temp\malware.exe' on host WS-DESKTOP-01
[2024-02-06 10:25:33] MALWARE_DETECTED - File hash SHA256: 44d88612fea8a8f36de82e1278abb02f09adac7280000f712b4141b0b7a4d2e1 detected as malicious
[2024-02-06 10:26:18] DATA_EXFILTRATION - Large data transfer to external IP 45.76.211.92 (1.2GB transferred)
[2024-02-06 10:27:05] SUSPICIOUS_URL - User accessed http://malicious-domain.xyz/download/payload.exe
```

4. 点击 **"Analyze"** 按钮
5. 等待分析结果

### 验证点
- [ ] 事件类型识别正确（至少3种类型）
- [ ] 提取到 IOC：IP地址 (192.168.1.100, 45.76.211.92)
- [ ] 提取到 IOC：域名 (malicious-domain.xyz)
- [ ] 提取到 IOC：文件哈希 (SHA256)
- [ ] 显示严重程度 (Severity)
- [ ] 显示影响分析面板 (Impact Analysis)
- [ ] 提供防御建议

### 命令行测试（可选）
```bash
curl -X POST "http://localhost:8000/api/analyze-alert" \
  -H "Content-Type: application/json" \
  -d "{\"raw_log\": \"[2024-02-06 10:23:45] FAILED_LOGIN - User admin from IP 192.168.1.100 failed to authenticate\"}"
```

---

## 测试三：时间线重建 (Timeline Builder)

### 步骤
1. 切换到 **"Timeline Builder"** 标签页
2. 输入以下事件序列：

```
2024-02-06 08:00:00 - System WS-FILESERVER-01 started normally
2024-02-06 09:15:23 - User john.doe logged in from 192.168.1.50
2024-02-06 09:30:45 - Suspicious PowerShell execution detected on WS-FILESERVER-01
2024-02-06 09:45:12 - Multiple failed authentication attempts from 45.33.32.156
2024-02-06 10:00:00 - Unusual file access pattern on \\WS-FILESERVER-01\finance
2024-02-06 10:15:33 - 2GB data transfer to external IP 103.41.124.51 detected
2024-02-06 10:30:00 - User john.doe account locked due to suspicious activity
2024-02-06 11:00:00 - Security analyst alerted and investigation initiated
```

3. 点击 **"Build Timeline"** 按钮
4. 等待结果

### 验证点
- [ ] 事件按时间顺序排列
- [ ] 标识可疑事件 (Top 5 Suspicious Events)
- [ ] 显示影响分析
- [ ] 提供调查下一步建议

---

## 测试四：报告生成 (Report Writer)

### 步骤
1. 切换到 **"Report Writer"** 标签页
2. 选择报告类型：**"Incident Report"**（事件报告）
3. 输入事件描述：

```
On February 6, 2024, a security incident was detected involving unauthorized access to the file server WS-FILESERVER-01. The attacker IP 45.33.32.156 made multiple authentication attempts followed by data exfiltration to IP 103.41.124.51. Approximately 2GB of financial data was transferred.
```

4. 点击 **"Generate Report"** 按钮

### 验证点
- [ ] 报告格式正确
- [ ] 包含事件摘要
- [ ] 包含时间线
- [ ] 包含影响评估
- [ ] 包含建议措施

---

## 测试五：资产管理 (Assets)

### 5.1 创建资产

```bash
curl -X POST "http://localhost:8000/api/assets" \
  -H "Content-Type: application/json" \
  -d "{\"hostname\": \"WS-FILESERVER-01\", \"ip\": \"192.168.1.10\", \"owner\": \"IT Department\", \"business\": \"Finance\", \"criticality\": \"high\", \"tags\": [\"fileserver\", \"windows\"]}"
```

### 验证点
- [ ] 返回新创建的资产信息
- [ ] 包含自动生成的 ID

### 5.2 查询资产列表

```bash
curl "http://localhost:8000/api/assets"
```

### 5.3 搜索资产

```bash
curl "http://localhost:8000/api/assets?search=FILESERVER"
```

### 验证点
- [ ] 搜索结果包含 WS-FILESERVER-01

### 5.4 批量导入资产

创建文件 `assets.json`：
```json
{
  "assets": [
    {"hostname": "WS-DC-01", "ip": "192.168.1.5", "owner": "IT Ops", "business": "Infrastructure", "criticality": "critical"},
    {"hostname": "WS-DB-01", "ip": "192.168.1.20", "owner": "DBA Team", "business": "Database", "criticality": "high"},
    {"hostname": "WS-WEB-01", "ip": "192.168.1.30", "owner": "Web Team", "business": "Web Services", "criticality": "medium"}
  ]
}
```

执行导入：
```bash
curl -X POST "http://localhost:8000/api/assets/import" \
  -H "Content-Type: application/json" \
  -d @assets.json
```

---

## 测试六：威胁情报 (Threat Intelligence)

### 6.1 单个 IP 查询

```bash
curl "http://localhost:8000/api/ti/otx?ioc_type=ip&ioc_value=193.201.224.92"
```

### 验证点
- [ ] 返回 verdict (判定结果)
- [ ] 返回 score (威胁分数 0-100)
- [ ] 返回 pulse_count (威胁情报数量)
- [ ] 返回 tags (威胁标签)

### 6.2 域名查询

```bash
curl "http://localhost:8000/api/ti/otx?ioc_type=domain&ioc_value=microsoft-login-update.com"
```

### 6.3 批量查询

```bash
curl -X POST "http://localhost:8000/api/ti/otx/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"items\": [{\"ioc_type\": \"ip\", \"ioc_value\": \"193.201.224.92\"}, {\"ioc_type\": \"domain\", \"ioc_value\": \"microsoft-login-update.com\"}]}"
```

### 6.4 缓存测试

1. 首次查询某个 IOC
2. 再次查询相同 IOC
3. 验证 `cached` 字段为 `true`

---

## 测试七：IOC 命中记录 (IOC Hits)

### 7.1 手动创建 IOC 命中

```bash
curl -X POST "http://localhost:8000/api/ioc-hits/manual" \
  -H "Content-Type: application/json" \
  -d "{\"ioc_type\": \"ip\", \"ioc_value\": \"45.76.211.92\", \"confidence\": 85, \"source\": \"analyst\", \"notes\": \"Confirmed C2 server\"}"
```

### 7.2 查询所有 IOC 命中

```bash
curl "http://localhost:8000/api/ioc-hits"
```

### 7.3 按 IOC 值查询

```bash
curl "http://localhost:8000/api/ioc-hits?ioc_value=45.76.211.92"
```

---

## 测试八：历史记录 (History)

### 8.1 查看历史记录

```bash
curl "http://localhost:8000/api/history"
```

### 验证点
- [ ] 显示之前的分析记录
- [ ] 包含时间戳
- [ ] 可以按类型筛选

### 8.2 获取单条记录

```bash
# 先获取列表，找到某个 record_id
curl "http://localhost:8000/api/history/{record_id}"
```

### 8.3 删除记录

```bash
curl -X DELETE "http://localhost:8000/api/history/{record_id}"
```

---

## 测试九：综合场景测试

### 场景：模拟一次完整的入侵事件调查

#### 步骤 1：准备资产数据
```bash
curl -X POST "http://localhost:8000/api/assets" \
  -H "Content-Type: application/json" \
  -d "{\"hostname\": \"WS-CEO-PC\", \"ip\": \"192.168.1.100\", \"owner\": \"CEO Office\", \"business\": \"Executive\", \"criticality\": \"critical\"}"
```

#### 步骤 2：分析入侵日志
在 Alert Analyzer 中输入：
```
[2024-02-06 14:00:00] SUSPICIOUS_LOGIN - Successful login for user ceo_admin from external IP 103.41.124.51 (unusual location)
[2024-02-06 14:05:23] STRANGE_PROCESS - PowerShell.exe spawned with encoded command on WS-CEO-PC
[2024-02-06 14:10:45] DATA_ACCESS - Sensitive files accessed in \\WS-CEO-PC\C$\Confidential
[2024-02-06 14:15:00] NETWORK_CONNECTION - Outbound connection to 193.201.224.92:443 established
[2024-02-06 14:20:33] FILE_TRANSFER - Large file (500MB) transferred to external IP
```

#### 步骤 3：查看威胁情报
```bash
curl "http://localhost:8000/api/ti/otx?ioc_type=ip&ioc_value=103.41.124.51"
```

#### 步骤 4：生成事件报告
使用 Timeline Builder 或 Report Writer 创建完整报告

---

## 测试结果记录表

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 健康检查 | ☐ 通过 ☐ 失败 | |
| 告警分析 | ☐ 通过 ☐ 失败 | |
| IOC 提取 | ☐ 通过 ☐ 失败 | |
| 时间线重建 | ☐ 通过 ☐ 失败 | |
| 报告生成 | ☐ 通过 ☐ 失败 | |
| 资产创建 | ☐ 通过 ☐ 失败 | |
| 资产搜索 | ☐ 通过 ☐ 失败 | |
| 威胁情报查询 | ☐ 通过 ☐ 失败 | |
| 批量查询 | ☐ 通过 ☐ 失败 | |
| IOC 命中记录 | ☐ 通过 ☐ 失败 | |
| 历史记录查询 | ☐ 通过 ☐ 失败 | |
| 综合场景测试 | ☐ 通过 ☐ 失败 | |

---

## 常见问题排查

### 问题 1：后端无法启动
**检查**：
- Python 虚拟环境是否激活
- 依赖是否安装完整：`pip install -r requirements.txt`
- .env 文件是否存在

### 问题 2：威胁情报查询失败
**检查**：
- `ALLOW_EXTERNAL_TI=true` 是否设置
- OTX API Key 是否有效
- 网络连接是否正常

### 问题 3：前端无法连接后端
**检查**：
- 后端是否在 8000 端口运行
- 浏览器控制台是否有 CORS 错误

---

## 测试数据参考

### 已知恶意 IOCs（用于测试）

| 类型 | 值 | 说明 |
|------|-----|------|
| IP | 193.201.224.92 | 已知恶意 IP |
| IP | 103.41.124.51 | 可疑 IP |
| Domain | microsoft-login-update.com | 钓鱼域名示例 |
| Hash | 44d88612fea8a8f36de82e1278abb02f | EICAR 测试文件 (MD5) |
| Hash | 275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f | EICAR (SHA256) |

### 安全 IOCs（用于测试负例）

| 类型 | 值 | 说明 |
|------|-----|------|
| IP | 8.8.8.8 | Google DNS |
| IP | 1.1.1.1 | Cloudflare DNS |
| Domain | google.com | 合法域名 |

---

**测试完成后，请填写测试结果记录表并报告任何发现的问题。**
