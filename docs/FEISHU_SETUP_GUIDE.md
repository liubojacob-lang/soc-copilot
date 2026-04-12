# 📱 飞书通知配置指南

## 🎯 配置步骤

### 步骤 1: 创建飞书群聊

1. **打开飞书客户端**
   - 电脑端或移动端都可以

2. **创建群聊** (如果没有专门的告警群)
   - 点击 "+ 新建群聊"
   - 选择"创建新群"
   - 设置群名称，例如："安全告警通知群"
   - 邀请需要接收告警的成员加入

### 步骤 2: 添加自定义机器人

1. **打开群聊设置**
   - 点击群聊右上角的 "..." 或群设置图标
   - 选择 "群机器人"
   - 点击 "添加机器人"

2. **选择"自定义机器人"**
   - 在机器人列表中选择"自定义机器人"
   - 点击"添加"

3. **配置机器人**
   - **机器人名称**: SOC Copilot (或您喜欢的名称)
   - **描述**: 安全告警通知机器人 (可选)
   - **头像**: 上传机器人头像 (可选)

4. **获取 Webhook URL**
   - 点击"添加"后，系统会生成 Webhook URL
   - URL 格式类似:
     ```
     https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
     ```
   - **复制这个 URL** - 后面配置会用到！

5. **安全设置 (可选但推荐)**
   - **IP 白名单**: 添加您的服务器 IP (如果固定)
   - **签名验证**: 启用后需要在请求中添加签名
   - **加密密钥**: 启用后需要配置验证

### 步骤 3: 配置 SOC Copilot

#### 方法 A: 使用环境变量 (推荐)

1. **编辑 `.env` 文件**

   ```bash
   cd /Users/levent/Desktop/sec
   nano .env
   ```

2. **添加飞书配置**

   ```bash
   # 飞书通知配置
   FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

3. **保存文件** (Ctrl+O, Enter, Ctrl+X)

#### 方法 B: 直接导出环境变量

```bash
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

#### 方法 C: 使用测试配置文件

```bash
# 复制测试配置模板
cp .env.test .env.local

# 编辑配置
nano .env.local

# 添加您的 Webhook URL
```

### 步骤 4: 测试飞书通知

#### 方法 1: 使用本地测试脚本

```bash
cd /Users/levent/Desktop/sec

# 配置环境变量
export FEISHU_WEBHOOK_URL=your-webhook-url-here

# 运行测试
python test_notification_local.py
```

#### 方法 2: 使用 curl 直接测试

```bash
# 替换 YOUR_WEBHOOK_URL 为实际的 Webhook URL
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "✅ 飞书通知配置成功！\n\n这是一条测试消息，来自 SOC Copilot 安全告警系统。"
    }
  }'
```

#### 方法 3: 使用 Docker 部署后测试

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 发送测试通知
curl -X POST http://localhost:8000/api/v1/notifications/test
```

---

## 🔐 高级配置 (可选)

### 启用签名验证

如果您启用了飞书的签名验证，需要：

1. **获取签名密钥** - 从飞书机器人设置中获取

2. **修改通知服务** - 添加签名验证支持

```python
# 在 notification_service.py 中添加签名计算
import hmac
import hashlib
import base64
import time

def generate_sign(secret: str) -> str:
    """生成飞书签名"""
    timestamp = str(int(time.time()))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return f"{timestamp}.{sign}"
```

### 自定义卡片样式

飞书支持丰富的卡片样式，您可以自定义：

- 颜色模板 (red, orange, yellow, green, blue, gray)
- 按钮链接
- 图片插入
- Markdown 格式

---

## 🎨 飞书卡片样式示例

### 基础文本消息

```json
{
  "msg_type": "text",
  "content": {
    "text": "这是一条文本消息"
  }
}
```

### 富文本卡片 (SOC Copilot 使用)

```json
{
  "msg_type": "interactive",
  "card": {
    "config": {
      "wide_screen_mode": true
    },
    "header": {
      "title": {
        "content": "🚨 安全告警",
        "tag": "plain_text"
      },
      "template": "red"
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "content": "**告警详情**\n- 来源: Wazuh\n- 级别: High\n- 时间: 2026-02-24 12:00:00",
          "tag": "lark_md"
        }
      },
      {
        "tag": "hr"
      },
      {
        "tag": "action",
        "actions": [
          {
            "tag": "button",
            "text": {
              "content": "查看详情",
              "tag": "plain_text"
            },
            "type": "primary",
            "url": "https://your-domain.com/alerts/123"
          }
        ]
      }
    ]
  }
}
```

---

## 🐛 故障排查

### 问题 1: 没有收到消息

**可能原因**:

1. Webhook URL 配置错误
2. 网络连接问题
3. 机器人已被移除

**解决方法**:

```bash
# 1. 验证 Webhook URL 格式
echo $FEISHU_WEBHOOK_URL
# 应该以 https://open.feishu.cn/open-apis/bot/v2/hook/ 开头

# 2. 使用 curl 直接测试
curl -X POST $FEISHU_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'

# 3. 检查飞书群聊
# - 确认机器人在群聊中
# - 查看群聊设置 -> 群机器人 -> 状态是否正常
```

### 问题 2: 收到错误消息

**常见错误**:

| 错误信息              | 原因         | 解决方法              |
| --------------------- | ------------ | --------------------- |
| `webhook url invalid` | URL 错误     | 检查 URL 是否完整复制 |
| `sign verify fail`    | 签名验证失败 | 检查签名密钥配置      |
| `rate limit`          | 发送频率过高 | 降低发送频率          |

### 问题 3: Docker 环境无法发送

**检查步骤**:

```bash
# 1. 检查环境变量是否传递到容器
docker exec -it soc-copilot-alert-worker env | grep FEISHU

# 2. 查看 Worker 日志
docker logs soc-copilot-alert-worker-prod -f

# 3. 测试容器网络连接
docker exec -it soc-copilot-alert-worker \
  curl -I https://open.feishu.cn
```

---

## 📋 配置检查清单

- [ ] 已创建飞书群聊
- [ ] 已添加自定义机器人
- [ ] 已复制 Webhook URL
- [ ] 已配置环境变量
- [ ] 已测试 Webhook URL (curl 测试)
- [ ] 已运行通知测试脚本
- [ ] 已收到测试消息
- [ ] 已检查消息格式正确

---

## 🎉 完成配置后

配置完成后，您将能够：

✅ 接收实时安全告警
✅ 查看格式化的告警卡片
✅ 点击链接快速查看告警详情
✅ 在群聊中讨论和响应告警

---

## 📚 参考资料

- [飞书开放平台 - 机器人](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)
- [飞书卡牌消息格式](https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjL2YDM14iN2ATN)
- [飞书消息类型](https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjL2YDM14iN2ATN)

---

**需要帮助?**

如果您在配置过程中遇到问题：

1. 检查 Webhook URL 是否正确
2. 使用 curl 测试 URL 有效性
3. 查看日志输出了解详细错误
4. 参考飞书官方文档

---

_配置指南最后更新: 2026-02-24_
