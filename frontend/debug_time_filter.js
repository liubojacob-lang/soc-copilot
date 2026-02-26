// 模拟时间过滤逻辑
const history = [
  { timestamp: '2026-02-16T08:00:00' },
  { timestamp: '2026-02-16T08:30:00' },
  { timestamp: '2026-02-16T09:00:00' },
  { timestamp: '2026-02-16T09:30:00' },
  { timestamp: '2026-02-16T10:00:00' },
];

const now = new Date('2026-02-16T10:30:00'); // 假设当前是10:30

console.log('当前时间:', now.toISOString());
console.log('\n当前过滤逻辑（使用历史最新时间）:');

const latestTimestamp = Math.max(...history.map(p => new Date(p.timestamp).getTime()));
console.log('历史最新时间:', new Date(latestTimestamp).toISOString());

const ranges = {
  '1h': 60 * 60 * 1000,
  '6h': 6 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
};

Object.entries(ranges).forEach(([range, rangeMs]) => {
  const filtered = history.filter((point) => {
    const pointTime = new Date(point.timestamp).getTime();
    return (latestTimestamp - pointTime) <= rangeMs;
  });
  
  console.log(`${range}: ${filtered.length}个点`);
  filtered.forEach(p => {
    console.log(`  - ${p.timestamp}`);
  });
});

console.log('\n问题：如果历史最新时间是10:00，现在是10:30');
console.log('那么1小时内(10:00往前)只有10:00这一个点！');
