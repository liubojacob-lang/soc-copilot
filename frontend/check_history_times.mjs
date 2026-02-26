import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // 收集所有日志
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('time range') || text.includes('points') || text.includes('timeSpan')) {
      console.log(`[Browser] ${text}`);
    }
  });
  
  await page.goto('http://localhost:3003/monitor');
  await page.waitForTimeout(8000);
  
  // 获取历史数据的实际时间信息
  const timeInfo = await page.evaluate(async () => {
    const response = await fetch('/api/monitor/history?minutes=60');
    const data = await response.json();
    
    if (data.history && data.history.length > 0) {
      const timestamps = data.history.map(h => h.timestamp);
      const now = new Date();
      
      return {
        count: data.history.length,
        now: now.toISOString(),
        latest: timestamps[0],
        oldest: timestamps[timestamps.length - 1],
        timeSpan: Math.round((now - new Date(timestamps[timestamps.length - 1])) / 60000), // minutes
        sampleFirst: timestamps[0],
        sampleLast: timestamps[timestamps.length - 1],
        sampleMid: timestamps[Math.floor(timestamps.length / 2)],
      };
    }
    
    return { error: 'No history data' };
  });
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 历史数据时间分析');
  console.log('='.repeat(60));
  console.log(`数据点数量: ${timeInfo.count}`);
  console.log(`当前时间: ${timeInfo.now}`);
  console.log(`最新数据: ${timeInfo.latest}`);
  console.log(`最旧数据: ${timeInfo.oldest}`);
  console.log(`时间跨度: ${timeInfo.timeSpan}分钟`);
  
  const ageMinutes = Math.round((new Date(timeInfo.now) - new Date(timeInfo.latest)) / 60000);
  console.log(`\n最新数据年龄: ${ageMinutes}分钟`);
  
  if (ageMinutes > 60) {
    console.log('\n⚠️  问题诊断:');
    console.log(`  最新数据是 ${ageMinutes}分钟前的`);
    console.log(`  如果选择1h范围: 只能显示最近${Math.max(0, 60-ageMinutes)}分钟的新数据`);
    console.log(`  如果没有新数据 → 图表只显示1-2个点`);
  }
  
  await browser.close();
})();
