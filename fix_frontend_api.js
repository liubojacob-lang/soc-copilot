// 临时修复：直接访问后端 API
// 在浏览器控制台中运行此代码

// 配置
const API_BASE = 'http://localhost:8000';

// 从 localStorage 获取 token
const token = localStorage.getItem('token');

if (!token) {
  console.error('❌ 未找到 token，请先登录');
} else {
  console.log('✅ Token 已找到');

  // 发送测试告警
  fetch(`${API_BASE}/api/v1/wazuh/stream/test-alert`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      agent_id: '001',
      severity: 'high',
      event_type: 'ssh_login',
      count: 5
    })
  })
  .then(response => response.json())
  .then(data => {
    console.log('✅ 测试告警发送成功:', data);
  })
  .catch(error => {
    console.error('❌ 发送失败:', error);
  });

  // 获取历史告警
  fetch(`${API_BASE}/api/v1/wazuh/stream/history?limit=10`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  .then(response => response.json())
  .then(data => {
    console.log('✅ 历史告警:', data);
  })
  .catch(error => {
    console.error('❌ 获取失败:', error);
  });
}
