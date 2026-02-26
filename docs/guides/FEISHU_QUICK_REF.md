# 📱 飞书通知配置快速参考

## ⚡ 30秒快速配置

### 1️⃣ 获取飞书 Webhook URL

```
飞书群聊 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人 → 复制 URL
```

**URL 格式**:
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

### 2️⃣ 配置方式 A: 交互式向导 (推荐)

```bash
cd /Users/levent/Desktop/sec
python configure_feishu.py
```

然后按提示:
1. 粘贴 Webhook URL
2. 选择保存配置
3. 确认发送测试

---

### 3️⃣ 配置方式 B: 快速测试

```bash
# 直接测试
python test_feishu_quick.py https://your-webhook-url

# 保存到配置文件
echo "FEISHU_WEBHOOK_URL=https://your-webhook-url" >> .env
```

---

## 🎨 消息预览

配置成功后，您将在飞书群聊中收到:

```
┌─────────────────────────────┐
│  🚨 安全告警: SSH 登录失败   │
│                             │
│  **告警详情**                │
│  • 来源: Wazuh               │
│  • 级别: 🔴 HIGH            │
│  • IP: 192.168.1.100        │
│                             │
│  [查看详情]                 │
└─────────────────────────────┘
```

---

## ✅ 验证配置

```bash
# 方法 1: 快速测试
python test_feishu_quick.py $FEISHU_WEBHOOK_URL

# 方法 2: 使用 curl
curl -X POST $FEISHU_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'

# 方法 3: API 测试 (服务启动后)
curl -X POST http://localhost:8000/api/v1/notifications/test
```

---

## 🐛 问题排查

| 问题 | 解决方法 |
|------|---------|
| 没收到消息 | 检查 Webhook URL 是否正确 |
| URL 格式错误 | 确保以 `https://open.feishu.cn/` 开头 |
| 机器人被移除 | 重新添加机器人到群聊 |

---

## 📚 文档

- **完整指南**: [docs/FEISHU_SETUP_GUIDE.md](docs/FEISHU_SETUP_GUIDE.md)
- **快速开始**: [FEISHU_QUICKSTART.md](FEISHU_QUICKSTART.md)
- **演示脚本**: `python demo_feishu_config.py`

---

## 🚀 开始配置

```bash
cd /Users/levent/Desktop/sec

# 方式 1: 交互式配置
python configure_feishu.py

# 方式 2: 查看演示
python demo_feishu_config.py

# 方式 3: 快速测试 (替换您的 URL)
python test_feishu_quick.py https://your-webhook-url
```

---

**提示**: 配置完成后建议同时配置 Slack 或 Email 作为备用通知渠道！
