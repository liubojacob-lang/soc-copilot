# SOC Copilot v0.6.1 - 手动测试文档

本文档提供完整的手动测试步骤，用于验证 SOC Copilot v0.6.1 的所有功能。

---

## 目录

1. [环境准备](#环境准备)
2. [健康检查测试](#健康检查测试)
3. [Playbook 列表测试](#playbook-列表测试)
4. [钓鱼邮件分析测试](#钓鱼邮件分析测试)
5. [终端恶意软件分析测试](#终端恶意软件分析测试)
6. [可疑登录分析测试](#可疑登录分析测试)
7. [运行历史查询测试](#运行历史查询测试)
8. [步骤详情查询测试](#步骤详情查询测试)
9. [Apply 模式测试](#apply-模式测试)
10. [错误处理测试](#错误处理测试)
11. [数据库验证](#数据库验证)
12. [测试检查清单](#测试检查清单)

---

## 环境准备

### 1. 启动后端服务

```bash
cd F:\AIproject\sec\backend
python main.py
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 2. 验证服务状态

```bash
curl http://localhost:8000/api/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "service": "soc-copilot"
}
```

### 3. 打开测试工具

在浏览器中打开：
```
file:///F:/AIproject/sec/frontend/public/playbook-test.html
```

---

## 健康检查测试

### 测试目标
验证后端服务正常运行

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET 请求到 `/api/health` | 返回 HTTP 200 |
| 2 | 检查响应内容 | `status: "healthy"` |

### cURL 命令

```bash
curl -i http://localhost:8000/api/health
```

### 预期响应

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "status": "healthy",
  "service": "soc-copilot"
}
```

### 测试结果

- [x] 通过
- [ ] 失败

---

## Playbook 列表测试

### 测试目标
验证系统能正确返回所有可用的 Playbook 模板

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET 请求到 `/api/playbook/playbooks` | 返回 HTTP 200 |
| 2 | 检查返回的 playbook 数量 | 应该有 3 个 playbook |
| 3 | 验证每个 playbook 的字段 | 包含 name, display_name, description, version |

### cURL 命令

```bash
curl http://localhost:8000/api/playbook/playbooks
```

### 预期响应

```json
{
  "playbooks": [
    {
      "name": "phishing_triage",
      "display_name": "钓鱼邮件分析",
      "description": "分析钓鱼邮件并提取IOC、威胁情报和资产信息",
      "version": "1.0.0",
      "estimated_duration_seconds": 30,
      "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "action_plan"]
    },
    {
      "name": "endpoint_malware_triage",
      "display_name": "终端恶意软件分析",
      "description": "分析终端恶意软件事件并进行完整调查流程",
      "version": "1.0.0",
      "estimated_duration_seconds": 45,
      "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "action_plan"]
    },
    {
      "name": "suspicious_login_triage",
      "display_name": "可疑登录分析",
      "description": "分析可疑登录事件并评估账户安全风险",
      "version": "1.0.0",
      "estimated_duration_seconds": 25,
      "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "action_plan"]
    }
  ]
}
```

### 测试结果

- [x] 通过
- [ ] 失败

---

## 钓鱼邮件分析测试

### 测试用例 1: 基础测试（空数据）

#### 测试目标
验证最基本的 Playbook 执行流程

#### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "测试钓鱼邮件"
      }
    }
  }'
```

#### 预期响应

```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "playbook_name": "phishing_triage",
  "status": "success",
  "mode": "dry_run",
  "started_at": "2024-01-15T10:00:00Z",
  "finished_at": "2024-01-15T10:00:05Z",
  "input_json": {
    "alert_data": {
      "subject": "测试钓鱼邮件"
    }
  }
}
```

#### 验证点

- [ ] HTTP 状态码为 200
- [ ] 返回有效的 `run_id` (UUID格式)
- [ ] `status` 为 "success"
- [ ] `started_at` 和 `finished_at` 时间戳存在
- [ ] `finished_at` 晚于 `started_at`

#### 保存 run_id 以便后续测试

```
run_id = ___04ba1a97-a608-4f05-b218-9c1e2e0d27f5_________________________
```

---

### 测试用例 2: IOC 提取测试

#### 测试目标
验证系统能正确提取各种类型的 IOC

#### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "紧急: 请付款到 192.168.1.100 或访问 evil.com",
        "sender": "attacker@malicious.com"
      },
      "source_text": "点击链接 http://evil.com/phishing-page 验证账户",
      "body": "文件哈希: 5d41402abc4b2a76b9719d911017c592",
      "network": "检测到连接 203.0.113.5"
    }
  }'
```

#### 验证点

- [ ] 提取到 IP 地址: `192.168.1.100`, `203.0.113.5`
- [ ] 提取到域名: `evil.com`
- [ ] 提取到 URL: `http://evil.com/phishing-page`
- [ ] 提取到哈希: `5d41402abc4b2a76b9719d911017c592`
- [ ] 提取到邮箱: `attacker@malicious.com`

#### 查询步骤详情验证 IOC 提取

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}/steps
```

在响应中找到 `step_id: "ioc_extract"` 的步骤，检查 `output_json.result.iocs`。

#### 预期的 IOC 结构

```json
{
  "iocs": {
    "ips": ["192.168.1.100", "203.0.113.5"],
    "domains": ["evil.com"],
    "urls": ["http://evil.com/phishing-page"],
    "hashes": ["5d41402abc4b2a76b9719d911017c592"],
    "emails": ["attacker@malicious.com"]
  },
  "count": 6
}
```

#### 测试结果

- [x] 通过
- [ ] 失败

---

### 测试用例 3: 完整钓鱼邮件场景

#### 测试目标
模拟真实的钓鱼邮件分析场景

#### 测试数据

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "Urgent: Your account will be suspended",
        "sender": "security-alert@not-real-microsoft.com",
        "recipient": "user@company.com",
        "timestamp": "2024-01-15T09:30:00Z"
      },
      "source_text": "Click https://microsoft-security-alert.com/login to verify your account immediately",
      "body": "This email contains malicious attachment with hash 44d296d419a7cd3a6c6578b0e1f3e1f4",
      "headers": {
        "X-Originating-IP": "185.220.101.1",
        "Reply-To": "phisher@temp-mail.com"
      }
    }
  }'
```

#### 验证点

| 步骤 | 验证内容 |
|------|----------|
| IOC 提取 | 提取到域名、URL、IP、邮箱、哈希 |
| 威胁情报查询 | 调用 OTX API 查询 IOC |
| 资产丰富 | 关联到邮箱域名和主机信息 |
| 风险评分 | 计算综合风险分数 |
| 行动计划 | 生成处置建议 |

#### 测试结果

- [x] 通过
- [ ] 失败

---

## 终端恶意软件分析测试

### 测试目标
验证终端恶意软件分析 Playbook 的完整功能

### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "endpoint_malware_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "恶意软件检测: workstation-001",
        "hostname": "PC-FINANCE-001",
        "username": "john.doe",
        "file_path": "C:\\Users\\john\\Downloads\\invoice.exe",
        "file_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        "detection_time": "2024-01-15T14:25:00Z",
        "detection_source": "EDR"
      },
      "process_info": {
        "pid": 4567,
        "command_line": "invoice.exe /silent /install",
        "parent_process": "explorer.exe"
      }
    }
  }'
```

### 验证点

| 步骤 | 验证内容 |
|------|----------|
| IOC 提取 | 提取到文件哈希、主机名、用户名 |
| 威胁情报查询 | 查询文件哈希的威胁情报 |
| 资产丰富 | 关联主机信息 (PC-FINANCE-001) |
| 风险评分 | 评估恶意软件风险等级 |
| 行动计划 | 生成隔离主机、调查用户等行动建议 |

### 测试结果

- [x] 通过
- [ ] 失败

---

## 可疑登录分析测试

### 测试目标
验证可疑登录分析 Playbook 的完整功能

### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "suspicious_login_triage",
    "mode": "dry_run",
    "input_json": {
      "alert_data": {
        "subject": "异常登录检测: 从未知位置登录",
        "username": "john.doe@company.com",
        "source_ip": "203.0.113.50",
        "login_time": "2024-01-15T03:25:00Z",
        "location": "Unknown Location, Russia",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "login_method": "password",
        "authentication_result": "success"
      },
      "user_context": {
        "usual_locations": ["New York, USA", "London, UK"],
        "usual_ip_ranges": ["192.168.1.0/24"],
        "last_login": "2024-01-14T18:00:00Z",
        "last_location": "New York, USA"
      }
    }
  }'
```

### 验证点

| 步骤 | 验证内容 |
|------|----------|
| IOC 提取 | 提取到源 IP、用户名 |
| 威胁情报查询 | 查询 IP 的威胁情报 |
| 资产丰富 | 关联用户账户信息 |
| 风险评分 | 考虑地理位置异常、时间异常 |
| 行动计划 | 生成重置密码、通知用户等行动建议 |

### 测试结果

- [ ] 通过
- [ ] 失败

---

## 运行历史查询测试

### 测试用例 1: 列出所有运行

#### cURL 命令

```bash
curl http://localhost:8000/api/playbook/runs
```

#### 预期响应

```json
{
  "total": 5,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "id": "xxx",
      "playbook_name": "phishing_triage",
      "status": "success",
      "mode": "dry_run",
      "started_at": "2024-01-15T10:00:00Z",
      "finished_at": "2024-01-15T10:00:05Z"
    }
  ]
}
```

#### 验证点

- [ ] `total` 字段显示总运行数
- [ ] `items` 数组包含所有运行记录
- [ ] 每条记录包含 id, playbook_name, status, 时间戳

---

### 测试用例 2: 分页查询

#### cURL 命令

```bash
curl "http://localhost:8000/api/playbook/runs?page=1&page_size=2"
```

#### 验证点

- [ ] 只返回 2 条记录
- [ ] `page` 字段正确

---

### 测试用例 3: 按状态筛选

#### cURL 命令

```bash
curl "http://localhost:8000/api/playbook/runs?status=success"
curl "http://localhost:8000/api/playbook/runs?status=failed"
```

#### 验证点

- [ ] 只返回指定状态的运行

---

### 测试用例 4: 按 Playbook 筛选

#### cURL 命令

```bash
curl "http://localhost:8000/api/playbook/runs?playbook_name=phishing_triage"
```

#### 验证点

- [ ] 只返回 phishing_triage 的运行记录

---

### 测试结果

- [x] 通过
- [ ] 失败

---

## 步骤详情查询测试

### 测试目标
验证能正确获取单个运行的所有步骤详情

### cURL 命令

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}/steps
```

### 预期响应

```json
{
  "run_id": "xxx",
  "steps": [
    {
      "id": "step-1",
      "run_id": "xxx",
      "step_index": 0,
      "step_id": "ioc_extract",
      "step_name": "IOC Extraction",
      "step_type": "extraction",
      "status": "success",
      "started_at": "2024-01-15T10:00:00Z",
      "finished_at": "2024-01-15T10:00:01Z",
      "duration_ms": 150,
      "input_json": {},
      "output_json": {
        "result": {
          "iocs": {...},
          "count": 5
        }
      }
    },
    {
      "id": "step-2",
      "step_index": 1,
      "step_id": "ti_lookup_otx",
      "step_name": "Threat Intelligence Lookup (OTX)",
      "status": "success",
      "duration_ms": 250
    },
    {
      "id": "step-3",
      "step_index": 2,
      "step_id": "asset_enrich",
      "step_name": "Asset Enrichment",
      "status": "success",
      "duration_ms": 100
    },
    {
      "id": "step-4",
      "step_index": 3,
      "step_id": "risk_score",
      "step_name": "Risk Scoring",
      "status": "success",
      "duration_ms": 80
    },
    {
      "id": "step-5",
      "step_index": 4,
      "step_id": "action_plan",
      "step_name": "Action Plan Generation",
      "status": "success",
      "duration_ms": 120
    }
  ]
}
```

### 验证点

- [ ] 返回 5 个步骤
- [ ] 每个步骤有正确的 step_index (0-4)
- [ ] 所有步骤状态为 "success"
- [ ] duration_ms 有合理值
- [ ] finished_at 晚于 started_at

### 测试结果

- [ ] 通过
- [ ] 失败

---

## Apply 模式测试

### 测试目标
验证 apply 模式的执行（某些步骤可能跳过）

### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "mode": "apply",
    "input_json": {
      "alert_data": {
        "subject": "Apply Mode Test"
      }
    }
  }'
```

### 验证点

| 验证项 | 说明 |
|--------|------|
| status | 应为 "success" |
| mode | 应为 "apply" |
| 跳过的步骤 | 检查是否有步骤 status 为 "skipped" |
| skipped_reason | 跳过的步骤应有原因说明 |

### 查询步骤详情

```bash
curl http://localhost:8000/api/playbook/runs/{run_id}/steps
```

### 测试结果

- [ ] 通过
- [ ] 失败

---

## 错误处理测试

### 测试用例 1: 无效的 Playbook 名称

#### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "invalid_playbook_name",
    "mode": "dry_run",
    "input_json": {}
  }'
```

#### 预期结果

- HTTP 状态码: 400 或 500
- 错误消息包含 "Unknown playbook" 或类似内容

#### 验证点

- [ ] 返回错误状态码
- [ ] 错误消息清晰

---

### 测试用例 2: 缺少必填字段

#### cURL 命令

```bash
curl -X POST http://localhost:8000/api/playbook/run \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage"
  }'
```

#### 预期结果

- HTTP 状态码: 422 (Validation Error)
- 错误消息说明缺少必填字段

#### 验证点

- [ ] 返回 422 状态码
- [ ] 错误消息指明缺少 mode 或 input_json

---

### 测试用例 3: 无效的 run_id

#### cURL 命令

```bash
curl http://localhost:8000/api/playbook/runs/invalid-uuid
```

#### 预期结果

- HTTP 状态码: 404
- 错误消息: "Run not found"

#### 验证点

- [x] 返回 404 状态码

---

### 测试结果

- [ ] 通过
- [ ] 失败

---

## 数据库验证

### 测试目标
验证数据正确持久化到数据库

### 步骤 1: 打开数据库

```bash
sqlite3 F:/AIproject/sec/data/app.db
```

### 步骤 2: 查看 playbook_runs 表

```sql
SELECT id, playbook_name, status, mode, started_at, finished_at
FROM playbook_runs
ORDER BY started_at DESC
LIMIT 10;
```

#### 预期结果

```
id                                   | playbook_name              | status  | mode   | started_at          | finished_at
-------------------------------------|----------------------------|---------|--------|---------------------|---------------------
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | phishing_triage            | success | dry_run| 2024-01-15 10:00:00 | 2024-01-15 10:00:05
...
```

#### 验证点

- [ ] 所有运行都已保存
- [ ] 时间戳正确
- [ ] status 正确

---

### 步骤 3: 查看 playbook_run_steps 表

```sql
SELECT run_id, step_index, step_id, step_name, status, duration_ms
FROM playbook_run_steps
ORDER BY run_id, step_index
LIMIT 20;
```

#### 预期结果

```
run_id                              | step_index | step_id       | step_name                    | status  | duration_ms
------------------------------------|-----------|---------------|------------------------------|---------|------------
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | 0          | ioc_extract   | IOC Extraction               | success | 150
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | 1          | ti_lookup_otx | Threat Intelligence Lookup   | success | 250
...
```

#### 验证点

- [ ] 每个运行有 5 个步骤
- [ ] step_index 从 0 到 4
- [ ] 所有步骤状态正确
- [ ] duration_ms 有值

---

### 步骤 4: 检查外键关系

```sql
SELECT
  pr.id as run_id,
  pr.playbook_name,
  pr.status as run_status,
  COUNT(prs.id) as step_count
FROM playbook_runs pr
LEFT JOIN playbook_run_steps prs ON pr.id = prs.run_id
GROUP BY pr.id
ORDER BY pr.started_at DESC
LIMIT 10;
```

#### 预期结果

```
run_id  | playbook_name     | run_status | step_count
--------|-------------------|------------|-----------
xxx     | phishing_triage   | success    | 5
xxx     | malware_triage    | success    | 5
```

#### 验证点

- [x] 每个运行都有 5 个步骤
- [x] 外键关系正确

---

### 步骤 5: 统计数据

```sql
-- 按状态统计
SELECT status, COUNT(*) as count
FROM playbook_runs
GROUP BY status;

-- 按 playbook 统计
SELECT playbook_name, COUNT(*) as count
FROM playbook_runs
GROUP BY playbook_name;

-- 平均执行时间
SELECT
  playbook_name,
  AVG((julianday(finished_at) - julianday(started_at)) * 86400) as avg_duration_seconds
FROM playbook_runs
WHERE status = 'success'
GROUP BY playbook_name;
```

---

### 测试结果

- [x] 通过
- [ ] 失败

---

## 测试检查清单

### 功能测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 健康检查 | ☐ | |
| 列出可用 Playbook | ☐ | 应该有 3 个 |
| 钓鱼邮件 - 基础测试 | ☐ | |
| 钓鱼邮件 - IOC 提取 | ☐ | |
| 钓鱼邮件 - 完整场景 | ☐ | |
| 终端恶意软件分析 | ☐ | |
| 可疑登录分析 | ☐ | |
| Dry_run 模式 | ☐ | |
| Apply 模式 | ☐ | |
| 列出运行历史 | ☐ | |
| 分页查询 | ☐ | |
| 状态筛选 | ☐ | |
| 步骤详情查询 | ☐ | |

### 错误处理测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 无效 Playbook 名称 | ☐ | |
| 缺少必填字段 | ☐ | |
| 无效 run_id | ☐ | |
| 无效 JSON 格式 | ☐ | |

### 数据持久化测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| playbook_runs 表数据正确 | ☐ | |
| playbook_run_steps 表数据正确 | ☐ | |
| 时间戳正确 | ☐ | |
| 持续时间计算正确 | ☐ | |
| 外键关系正确 | ☐ | |
| 历史记录累积正确 | ☐ | |

### 步骤执行验证

| 步骤 | 验证内容 | 状态 |
|------|----------|------|
| Step 1 - IOC 提取 | 正确提取 IP、域名、URL、哈希、邮箱 | ☐ |
| Step 2 - 威胁情报 | 调用 OTX API 查询 | ☐ |
| Step 3 - 资产丰富 | 关联资产信息 | ☐ |
| Step 4 - 风险评分 | 计算风险分数 | ☐ |
| Step 5 - 行动计划 | 生成处置建议 | ☐ |

### API 响应验证

| 验证项 | 状态 | 备注 |
|--------|------|------|
| HTTP 状态码正确 | ☐ | 200/400/404/422/500 |
| JSON 格式正确 | ☐ | |
| 必填字段存在 | ☐ | id, status, 时间戳等 |
| 时间格式为 ISO 8601 | ☐ | |
| 分页参数生效 | ☐ | |

---

## 快速测试脚本 (PowerShell)

```powershell
# SOC Copilot v0.6.1 快速测试脚本

$baseUrl = "http://localhost:8000"

Write-Host "=== SOC Copilot v0.6.1 快速测试 ===" -ForegroundColor Green
Write-Host ""

# 1. 健康检查
Write-Host "[1/6] 健康检查..." -ForegroundColor Yellow
$response = curl -s $baseUrl/api/health
Write-Host $response
Write-Host ""

# 2. 列出 Playbook
Write-Host "[2/6] 列出可用 Playbook..." -ForegroundColor Yellow
$response = curl -s $baseUrl/api/playbook/playbooks
Write-Host $response
Write-Host ""

# 3. 执行钓鱼邮件分析
Write-Host "[3/6] 执行钓鱼邮件分析..." -ForegroundColor Yellow
$body = @{
    playbook_name = "phishing_triage"
    mode = "dry_run"
    input_json = @{
        alert_data = @{
            subject = "测试: IP 192.168.1.1 域名 evil.com"
            sender = "test@malicious.com"
        }
        source_text = "访问 http://evil.com/phishing"
        body = "文件哈希: 5d41402abc4b2a76b9719d911017c592"
    }
} | ConvertTo-Json -Depth 3

$response = curl -s -X POST $baseUrl/api/playbook/run `
    -H "Content-Type: application/json" `
    -d $body

Write-Host $response
$runId = ($response | ConvertFrom-Json).id
Write-Host "Run ID: $runId"
Write-Host ""

# 4. 查询运行状态
Write-Host "[4/6] 查询运行状态..." -ForegroundColor Yellow
Start-Sleep -Seconds 1
$response = curl -s "$baseUrl/api/playbook/runs/$runId"
Write-Host $response
Write-Host ""

# 5. 查询步骤详情
Write-Host "[5/6] 查询步骤详情..." -ForegroundColor Yellow
$response = curl -s "$baseUrl/api/playbook/runs/$runId/steps"
$response | ConvertFrom-Json | Select-Object -ExpandProperty steps | ForEach-Object {
    Write-Host "  Step $($_.step_index): $($_.step_name) - $($_.status) ($($_.duration_ms)ms)"
}
Write-Host ""

# 6. 列出运行历史
Write-Host "[6/6] 列出运行历史..." -ForegroundColor Yellow
$response = curl -s "$baseUrl/api/playbook/runs?limit=5"
$response | ConvertFrom-Json | Select-Object -ExpandProperty items | ForEach-Object {
    Write-Host "  $($_.id): $($_.playbook_name) - $($_.status)"
}
Write-Host ""

Write-Host "=== 测试完成 ===" -ForegroundColor Green
```

### 使用方法

1. 将脚本保存为 `quick-test.ps1`
2. 在 PowerShell 中运行: `.\quick-test.ps1`

---

## 常见问题排查

### 问题 1: CORS 错误

**症状**: 浏览器控制台显示 CORS 相关错误

**解决方案**:
1. 确认后端已更新 CORS 配置
2. 重启后端服务
3. 清除浏览器缓存

---

### 问题 2: Run not found

**症状**: 查询运行时返回 "Run not found"

**排查步骤**:
1. 检查 `run_id` 是否正确复制
2. 检查数据库中是否存在该记录
3. 检查后端日志是否有错误

---

### 问题 3: 步骤执行失败

**症状**: 运行状态为 "failed"

**排查步骤**:
1. 查询步骤详情找到失败的步骤
2. 检查 `error_text` 字段
3. 查看后端日志获取详细错误

---

### 问题 4: 数据库锁定

**症状**: `database is locked` 错误

**解决方案**:
1. 确保只有一个后端实例在运行
2. 关闭所有数据库连接
3. 重启后端服务

---

## 版本信息

- **SOC Copilot 版本**: v0.6.1
- **文档版本**: 1.0
- **最后更新**: 2025-02-07
- **作者**: Claude Code

---

## 测试记录表

| 日期 | 测试人 | 测试项 | 结果 | 备注 |
|------|--------|--------|------|------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
