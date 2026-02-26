// 检查history数据的时间范围
const now = new Date();
const oneHourAgo = new Date(now - 60 * 60 * 1000);

console.log('当前时间:', now.toISOString());
console.log('1小时前:', oneHourAgo.toISOString());

// 模拟history数据的时间
const historyPoints = [
  { timestamp: '2026-02-16T08:09:37' },
  { timestamp: '2026-02-16T08:53:20' }
];

historyPoints.forEach(point => {
  const pointTime = new Date(point.timestamp);
  const diff = now - pointTime;
  const diffMinutes = diff / 1000 / 60;
  const isInRange = diff <= 60 * 60 * 1000;
  
  console.log(`\n${point.timestamp}:`);
  console.log(`  距现在: ${diffMinutes.toFixed(0)}分钟`);
  console.log(`  在1小时内? ${isInRange ? '是' : '否'}`);
});
