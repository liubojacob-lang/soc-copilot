# Week 1 浏览器测试 - 快速参考卡

**状态**: ✅ 后端测试完成 | ⏳ 等待浏览器验证

---

## 🚀 30秒快速开始

### 方式 1: 使用测试页面 (推荐)
1. 已打开: `WEEK1_BROWSER_TEST.html`
2. 点击页面上的按钮发送测试告警
3. 观察结果

### 方式 2: 手动测试
```bash
# 终端 1: 启动前端
cd frontend
npm run dev -- -p 3003

# 浏览器访问
http://localhost:3003

# 登录
用户名: admin
密码: admin123
```

---

## ✅ 测试检查清单

### 核心功能 (必须全部通过)
- [ ] 页面加载无错误
- [ ] WebSocket 自动连接成功
- [ ] 连接状态显示为绿色 (已连接)
- [ ] 统计卡片显示正确数字
- [ ] 实时告警接收并显示
- [ ] 告警按严重级别着色

### 交互功能
- [ ] 过滤按钮工作正常
- [ ] 清空按钮清空告警列表
- [ ] 导出按钮下载 CSV
- [ ] 告警点击显示详情

### 数据完整性
- [ ] 告警 ID 显示
- [ ] 时间戳正确
- [ ] 规则信息完整
- [ ] Agent 信息显示
- [ ] MITRE ATT&CK 战术显示
- [ ] IOC 列表显示

---

## 🧪 浏览器控制台测试

打开浏览器控制台 (F12 → Console)，复制粘贴:

```javascript
// 发送 High 级别测试告警
fetch('/api/v1/wazuh/stream/test-alert', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    agent_id: '001',
    severity: 'high',
    event_type: 'ssh_login',
    count: 5
  })
}).then(r => r.json()).then(console.log);

// 检查 WebSocket 状态
console.log('WebSocket:', window.wsConnected ? '✅ 已连接' : '❌ 未连接');
```

---

## 📊 预期结果

发送告警后应该看到:
1. ✅ 告警立即出现在列表中
2. ✅ 统计数字自动更新
3. ✅ High 级别告警显示为橙色
4. ✅ Critical 级别显示为红色
5. ✅ MITRE 战术标签显示
6. ✅ IOC 信息以列表形式显示

---

## 🐛 常见问题

### Q: 看不到告警?
**A**: 检查:
1. 浏览器控制台是否有错误
2. WebSocket 连接状态 (应该是绿色)
3. 网络标签中 WebSocket 消息

### Q: 连接断开?
**A**: 刷新页面，系统会自动重连

### Q: 统计数字不更新?
**A**: 这是正常的数据延迟，等待 1-2 秒

---

## 📝 完成测试后

如果所有核心功能都通过，Week 1 即完成！

**下一步**:
- 开始 Week 2: 告警关联分析引擎
- 或继续优化 Week 1 功能

---

**测试人员签名**: ________________
**完成日期**: ________________
**测试结果**: □ 全部通过  □ 部分通过  □ 未通过

---

## 📞 需要帮助?

参考文档:
- `WEEK_1_FINAL_REPORT.md` - 完整测试报告
- `TEST_GUIDE_WEEK1.md` - 详细测试指南
- `WAZUH_DEEP_INTEGRATION_PLAN.md` - 实施计划
