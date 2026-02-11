# SOC Copilot v0.6.1 - Playbook Execution Engine 测试文档

本文档提供完整的测试步骤，用于验证 SOC Copilot v0.6.1 Playbook Execution Engine 的所有功能。

## 前置条件

### 1. 启动后端服务

```bash
cd F:\AIproject\sec\backend
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 2. 验证服务健康状态

```bash
curl http://localhost:8000/api/health
```

预期响应：
```json
{"status":"healthy","service":"soc-copilot"}
```

---

## 测试案例 1: 列出可用的 Playbook

**目的**: 验证系统已正确加载所有 Playbook 模板

```bash
curl -X GET http://localhost:8000/api/playbook/playbooks
```

**预期结果**:
```json
{
  "playbooks": [
    {
      "name": "phishing_triage",
      "display_name": "钓鱼邮件分析",
      "description": "分析钓鱼邮件并提取IOC、威胁情报和资产信息",
      "version": "1.0.0",
      "estimated_duration_seconds": 30
    },
    {
      "name": "endpoint_malware_triage",
      "display_name": "终端恶意软件分析",
      "description": "分析终端恶意软件事件并进行完整调查流程",
      "version": "1.0.0",
      "estimated_duration_seconds": 45
    },
    {
      "name": "suspicious_login_triage",
      "display_name": "可疑登录分析",
      "description": "分析可疑登录事件并评估账户安全风险",
      "version": "1.0.0",
      "estimated_duration_seconds": 25
    }
  ]
}
```

---

## 测试案例 2: Phishing Triage - 空数据（基础功能）

**目的**: 测试基本的 Playbook 执行流程

### 2.1 执行 Playbook

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Test Alert"
      }
    }
  }'
```

**预期结果**:
- HTTP 状态码: 200
- 返回 `run_id`
- `status`: "success"
- 所有 5 个步骤都成功执行

### 2.2 验证结果

保存返回的 `run_id`，然后查询运行状态：

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}
```

**验证点**:
- [ ] 状态为 "success"
- [ ] `started_at` 和 `finished_at` 时间戳已设置
- [ ] `output_json.steps` 包含所有步骤输出

### 2.3 查询步骤详情

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}/steps
```

**验证点**:
- [ ] 返回 5 个步骤
- [ ] 每个步骤都有: id, step_id, step_name, status, duration_ms
- [ ] 所有步骤状态为 "success"

---

## 测试案例 3: Phishing Triage - 包含 IOC 数据

**目的**: 测试 IOC 提取功能

### 3.1 执行 Playbook（包含 IP 和域名）

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Urgent: Verify payment to 192.168.1.100 or evil.com",
        "sender": "attacker@malicious.com"
      },
      "source_text": "Click here http://evil.com/phishing to verify",
      "body": "File hash: 5d41402abc4b2a76b9719d911017c592"
      }
    }'
```

**验证点**:
- [ ] IOC 提取步骤成功
- [ ] 提取到 IP: `192.168.1.100`
- [ ] 提取到域名: `evil.com`
- [ ] 提取到 URL: `http://evil.com/phishing`
- [ ] 提取到哈希: `5d41402abc4b2a76b9719d911017c592`
- [ ] 提取到邮箱: `attacker@malicious.com`

### 3.2 验证步骤输出

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}/steps | jq '.steps[0].output_json.result'
```

**预期输出示例**:
```json
{
  "iocs": {
    "ips": ["192.168.1.100"],
    "domains": ["evil.com"],
    "urls": ["http://evil.com/phishing"],
    "hashes": ["5d41402abc4b2a76b9719d911017c592"],
    "emails": ["attacker@malicious.com"]
  },
  "count": 5,
  "source_fields": ["subject", "sender", "source_text", "body"]
}
```

---

## 测试案例 4: Apply 模式测试

**目的**: 测试 Apply 模式的执行（某些步骤可能跳过）

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "apply",
    "input_json": {
      "alert_data": {
        "subject": "Test Apply Mode"
      }
    }
  }'
```

**验证点**:
- [ ] 状态为 "success"
- [ ] 检查是否有步骤被标记为 "skipped"
- [ ] `skipped_reason` 字段正确说明跳过原因

---

## 测试案例 5: 列出所有 Playbook Runs

**目的**: 测试运行历史查询功能

### 5.1 列出所有运行

```bash
curl "http://localhost:8000/api/playbook/runs"
```

**验证点**:
- [ ] 返回 `items` 数组
- [ ] 每个运行包含: id, playbook_name, status, started_at, finished_at
- [ ] `total` 字段显示总数量

### 5.2 分页测试

```bash
curl "http://localhost:8000/api/playbook/runs?page_size=1&page=1"
curl "http://localhost:8000/api/playbook/runs?page_size=1&page=2"
```

**验证点**:
- [ ] 分页正确工作
- [ ] 每页返回指定的记录数

### 5.3 按状态筛选

```bash
curl "http://localhost:8000/api/playbook/runs?status=success"
curl "http://localhost:8000/api/playbook/runs?status=failed"
```

**验证点**:
- [ ] 筛选结果正确
- [ ] 只返回指定状态的运行

---

## 测试案例 6: Endpoint Malware Triage

**目的**: 测试终端恶意软件分析 Playbook

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "endpoint_malware_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Malware detected on workstation",
        "hostname": "PC-FINANCE-001",
        "file_path": "C:\\Users\\john\\Downloads\\malware.exe",
        "file_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
      }
    }
  }'
```

**验证点**:
- [ ] IOC 提取获取文件哈希
- [ ] 资产丰富步骤关联到主机名
- [ ] 风险评分反映恶意软件威胁
- [ ] 行动计划包含隔离和调查步骤

---

## 测试案例 7: Suspicious Login Triage

**目的**: 测试可疑登录分析 Playbook

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "suspicious_login_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Suspicious login from unknown location",
        "username": "john.doe",
        "source_ip": "203.0.113.5",
        "login_time": "2024-01-15T03:25:00Z",
        "location": "Unknown Location"
      }
    }
  }'
```

**验证点**:
- [ ] IOC 提取获取源 IP
- [ ] 资产丰富关联用户账户
- [ ] 风险评分考虑地理位置异常
- [ ] 行动计划包含账户安全检查

---

## 测试案例 8: 错误处理

### 8.1 无效的 Playbook 名称

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "invalid_playbook",
    "mode": "dry_run",
    "input_json": {}
  }'
```

**预期结果**:
- HTTP 状态码: 400 或 500
- 错误消息包含 "Unknown playbook"

### 8.2 缺少必填字段

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage"
  }'
```

**预期结果**:
- HTTP 状态码: 422 (Validation Error)
- 错误消息说明缺少必填字段

---

## 测试案例 9: 数据库持久化验证

**目的**: 验证数据正确保存到数据库

### 9.1 检查数据库

```bash
sqlite3 F:/AIproject/sec/data/app.db
```

进入 SQLite 后执行：

```sql
-- 查看 playbook_runs 表
SELECT id, playbook_name, status, started_at, finished_at
FROM playbook_runs
ORDER BY started_at DESC
LIMIT 5;

-- 查看 playbook_run_steps 表
SELECT run_id, step_id, step_name, status, duration_ms
FROM playbook_run_steps
ORDER BY run_id, step_index
LIMIT 10;
```

**验证点**:
- [ ] playbook_runs 表包含所有运行记录
- [ ] playbook_run_steps 表包含所有步骤记录
- [ ] 时间戳正确
- [ ] duration_ms 有合理值

### 9.2 检查外键关系

```sql
-- 检查步骤是否正确关联到运行
SELECT
  pr.id as run_id,
  pr.status as run_status,
  COUNT(prs.id) as step_count
FROM playbook_runs pr
LEFT JOIN playbook_run_steps prs ON pr.id = prs.run_id
GROUP BY pr.id;
```

**验证点**:
- [ ] 每个运行都有 5 个步骤
- [ ] 所有步骤都正确关联到运行

---

## 测试案例 10: 性能测试

### 10.1 单次执行时间

使用 `time` 命令测量执行时间：

```bash
time curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {"subject": "Performance Test"}
    }
  }'
```

**验证点**:
- [ ] 执行时间 < 5 秒（dry_run 模式）
- [ ] 响应时间合理

### 10.2 并发测试（可选）

使用多个并发请求测试：

```bash
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/playbook/run \
    -H "Content-Type: application/json" \
    -d "{\"playbook_name\": \"phishing_triage\", \"mode\": \"dry_run\", \"input_json\": {\"alert_data\": {\"subject\": \"Test $i\"}}}" &
done
wait
```

**验证点**:
- [ ] 所有请求都成功处理
- [ ] 数据库正确保存所有记录
- [ ] 没有数据竞争问题

---

## 测试检查清单

### 功能验证
- [ ] 所有 3 个 Playbook 可用
- [ ] Phishing Triage 执行成功
- [ ] Endpoint Malware Triage 执行成功
- [ ] Suspicious Login Triage 执行成功
- [ ] IOC 提取正确识别 IP、域名、URL、哈希、邮箱
- [ ] 威胁情报查询步骤执行
- [ ] 资产丰富步骤执行
- [ ] 风险评分步骤执行
- [ ] 行动计划生成步骤执行

### 数据持久化
- [ ] 运行记录保存到 playbook_runs 表
- [ ] 步骤记录保存到 playbook_run_steps 表
- [ ] 时间戳正确记录
- [ ] 持续时间正确计算
- [ ] 外键关系正确

### 状态管理
- [ ] 步骤状态正确: pending → running → success/failed/skipped
- [ ] 运行状态正确: running → success/failed
- [ ] 错误消息正确记录

### API 响应
- [ ] 所有端点返回正确的 HTTP 状态码
- [ ] JSON 响应格式正确
- [ ] 分页功能正常工作
- [ ] 筛选功能正常工作

---

## 常见问题排查

### 问题 1: 服务无法启动

**症状**: 启动时报错 `ModuleNotFoundError`

**解决方案**:
```bash
# 检查是否在正确的目录
cd F:\AIproject\sec\backend

# 重新安装依赖
pip install -r requirements.txt
```

### 问题 2: Playbook 执行失败

**症状**: 返回 500 错误或状态为 "failed"

**排查步骤**:
1. 检查后端日志查看详细错误
2. 验证所有步骤已正确注册
3. 检查数据库连接正常

### 问题 3: 数据未保存

**症状**: API 返回成功但数据库为空

**排查步骤**:
1. 检查 `get_session` 函数中的 commit 逻辑
2. 验证数据库文件权限
3. 检查是否有数据库锁定

---

## 附录: 快速测试脚本

创建一个快速测试脚本 `test_playbook.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== SOC Copilot v0.6.1 测试 ==="
echo ""

echo "1. 测试健康检查"
curl -s $BASE_URL/api/health
echo -e "\n"

echo "2. 列出可用 Playbook"
curl -s $BASE_URL/api/playbook/playbooks | jq '.'
echo -e "\n"

echo "3. 执行 Phishing Triage"
RESPONSE=$(curl -s -X POST $BASE_URL/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Test with IP 192.168.1.1"
      }
    }
  }')

echo $RESPONSE | jq '.'
RUN_ID=$(echo $RESPONSE | jq -r '.id')
echo "Run ID: $RUN_ID"
echo -e "\n"

echo "4. 查询运行状态"
curl -s $BASE_URL/api/playbook/runs/$RUN_ID | jq '.status, .started_at, .finished_at'
echo -e "\n"

echo "5. 查询步骤详情"
curl -s $BASE_URL/api/playbook/runs/$RUN_ID/steps | jq '.steps[] | {step_id, step_name, status, duration_ms}'
echo -e "\n"

echo "6. 列出所有运行"
curl -s $BASE_URL/api/playbook/runs | jq '.total, .items | length'
echo -e "\n"

echo "=== 测试完成 ==="
```

运行测试脚本:
```bash
bash test_playbook.sh
```

---

## 版本信息

- SOC Copilot 版本: v0.6.1
- 文档版本: 1.0
- 最后更新: 2025-02-07
