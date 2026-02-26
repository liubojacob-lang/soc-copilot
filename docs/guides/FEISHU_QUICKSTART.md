# 📱 飞书通知配置快速指南

## 🚀 三种配置方式

### 方式 1: 交互式配置向导 (推荐) ⭐

**最简单的方式，逐步引导您完成配置**

```bash
cd /Users/levent/Desktop/sec
python configure_feishu.py
```

**功能**:
- ✅ 逐步引导配置
- ✅ 自动验证 URL 格式
- ✅ 自动保存到 .env 文件
- ✅ 发送测试消息验证
- ✅ 显示后续步骤

---

### 方式 2: 快速测试脚本

**已经有 Webhook URL？直接测试**

```bash
cd /Users/levent/Desktop/sec
python test_feishu_quick.py https://your-webhook-url-here
```

**自定义消息**:
```bash
python test_feishu_quick.py \
  https://your-webhook-url-here \
  "自定义标题" \
  "自定义消息内容" \
  "info"
```

---

### 方式 3: 手动配置

**步骤 1: 获取飞书 Webhook URL**

1. 打开飞书群聊
2. 点击: 群设置 → 群机器人 → 添加机器人
3. 选择"自定义机器人"
4. 复制 Webhook URL

**步骤 2: 配置环境变量**

```bash
# 方式 A: 导出到当前会话
export FEISHU_WEBHOOK_URL=https://your-webhook-url

# 方式 B: 添加到 .env 文件
echo "FEISHU_WEBHOOK_URL=https://your-webhook-url" >> .env
```

**步骤 3: 测试通知**

```bash
python test_feishu_quick.py $FEISHU_WEBHOOK_URL
```

---

## 📋 配置检查清单

### 准备工作

- [ ] 有飞书账号
- [ ] 有一个群聊 (或创建新的)

### 获取 Webhook URL

- [ ] 打开群聊设置
- [ ] 添加自定义机器人
- [ ] 设置机器人名称 (建议: SOC Copilot)
- [ ] 复制 Webhook URL

### 配置系统

- [ ] 运行配置向导或手动配置
- [ ] 验证 URL 格式
- [ ] 发送测试消息
- [ ] 确认收到消息

---

## 🎯 完整配置示例

### 使用配置向导 (推荐)

```bash
# 1. 运行配置向导
cd /Users/levent/Desktop/sec
python configure_feishu.py

# 2. 按提示操作:
#    - 粘贴 Webhook URL
#    - 选择保存配置
#    - 确认发送测试消息

# 3. 检查飞书群聊收到测试消息

# 4. 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

### 使用快速测试

```bash
# 1. 获取 Webhook URL (从飞书群聊)

# 2. 快速测试
python test_feishu_quick.py https://your-webhook-url

# 3. 如果测试成功，保存到 .env
echo "FEISHU_WEBHOOK_URL=https://your-webhook-url" >> .env
```

---

## 🧪 验证配置

### 方法 1: 使用快速测试脚本

```bash
python test_feishu_quick.py $FEISHU_WEBHOOK_URL
```

### 方法 2: 使用 curl

```bash
curl -X POST $FEISHU_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "✅ 飞书通知测试成功！"
    }
  }'
```

### 方法 3: 启动服务后测试

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 发送测试通知
curl -X POST http://localhost:8000/api/v1/notifications/test
```

---

## 🐛 常见问题

### Q1: 没有收到测试消息

**检查清单**:
1. Webhook URL 是否完整复制
2. 机器人是否在群聊中
3. 网络连接是否正常
4. URL 格式是否正确 (应该以 https:// 开头)

**解决方法**:
```bash
# 重新获取 Webhook URL
python configure_feishu.py
```

### Q2: 提示 URL 格式错误

**正确格式**:
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**错误格式**:
```
❌ https://open.feishu.cn/...
❌ http://open.feishu.cn/...
❌ 缺少部分 URL
```

### Q3: 配置保存后无法加载

**检查**:
```bash
# 查看环境变量
echo $FEISHU_WEBHOOK_URL

# 查看 .env 文件
cat .env | grep FEISHU
```

**解决**:
```bash
# 手动导出环境变量
export FEISHU_WEBHOOK_URL=$(grep FEISHU_WEBHOOK_URL .env | cut -d'=' -f2)
```

---

## 📚 相关文档

- **[FEISHU_SETUP_GUIDE.md](./docs/FEISHU_SETUP_GUIDE.md)** - 完整配置指南
- **[QUICKSTART_NOTIFICATIONS.md](./QUICKSTART_NOTIFICATIONS.md)** - 快速开始
- **[IMPLEMENTATION_REPORT.md](./IMPLEMENTATION_REPORT.md)** - 实施报告

---

## 🎉 配置完成后

配置成功后，您将能够：

✅ **接收实时告警**
- 安全事件实时推送
- 格式化的告警卡片
- 可点击的详情链接

✅ **多渠道支持**
- 飞书群聊
- Slack (可选)
- Email (可选)

✅ **高可靠性**
- 消息持久化
- 自动重试
- 优先级处理

---

## 💡 提示

1. **建议配置多个渠道**: 飞书 + Email 作为备用
2. **定期测试**: 每月测试一次通知是否正常
3. **查看日志**: Worker 日志可以排查发送问题
4. **备份配置**: 保存 Webhook URL 到安全的地方

---

**配置支持**: 查看文档或运行 `python configure_feishu.py`
