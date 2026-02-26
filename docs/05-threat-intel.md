# 威胁情报集成

## 适用对象

安全分析师（使用威胁情报功能）、开发人员（扩展情报源）。

## 目标

理解 OTX 集成方式、缓存策略、合规过滤规则。

## AlienVault OTX 介绍

| 项目 | 说明 |
|------|------|
| 全称 | AlienVault Open Threat Exchange |
| 用途 | 全球威胁情报共享社区 |
| API | https://otx.alienvault.com/api/v1 |
| 费用 | 免费（公开数据） |

## OTX 对接方式

### 1. 获取 API Key

1. 访问 https://otx.alienvault.com
2. 注册账号
3. Settings → API → Create API Key
4. 复制 Key 到 `.env`

```env
OTX_API_KEY=your-otx-api-key-here
```

### 2. API 调用

```python
# 查询 IP 威胁情报
GET https://otx.alienvault.com/api/v1/indicators/IPv4/203.0.113.50/general

# 响应
{
  "pulse_info": {
    "count": 5,
    "pulses": [
      {
        "name": "APT29 Campaign",
        "tags": ["apt", "russia"]
      }
    ]
  }
}
```

### 3. 速率限制

| 级别 | 限制 |
|------|------|
| 免费版 | 10 次/分钟 |
| 付费版 | 无限制 |

## 合规过滤策略

以下 IOC 不会查询 OTX：

```python
PRIVATE_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8"
]

def should_query_otx(ioc: str, ioc_type: str) -> bool:
    # 跳过私有 IP
    if ioc_type == "ip":
        for range in PRIVATE_IP_RANGES:
            if is_in_range(ioc, range):
                return False
    return True
```

## 本地缓存策略

### TTL 配置

| IOC 类型 | TTL | 说明 |
|----------|-----|------|
| IP | 7 天 | IP 归属变化较慢 |
| Domain | 3 天 | 域名解析可能变化 |
| Hash | 30 天 | 样本特征稳定 |

### 缓存表结构

```sql
CREATE TABLE threat_intel_cache (
    id INTEGER PRIMARY KEY,
    ioc TEXT NOT NULL,
    ioc_type TEXT NOT NULL,
    result JSON,
    provider TEXT DEFAULT 'otx',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    UNIQUE(ioc, ioc_type)
);
```

## 失败降级策略

```python
async def lookup_intel(ioc: str, ioc_type: str) -> Dict:
    # 1. 检查本地缓存
    cached = await get_cache(ioc, ioc_type)
    if cached:
        return cached
    
    # 2. 检查是否需要跳过
    if not should_query_otx(ioc, ioc_type):
        return {"verdict": "unknown", "source": "skip_private"}
    
    # 3. 调用 OTX
    try:
        result = await otx_lookup(ioc, ioc_type)
        await save_cache(ioc, ioc_type, result)
        return result
    except Exception as e:
        logger.warning(f"OTX lookup failed: {e}")
        return {"verdict": "unknown", "error": str(e)}
```
