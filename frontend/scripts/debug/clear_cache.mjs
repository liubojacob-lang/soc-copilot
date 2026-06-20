import { chromium } from 'playwright';

(async () => {
  console.log('🧹 清空前端缓存...\n');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 访问 Monitor 页面
  await page.goto('http://localhost:3003/monitor');
  console.log('⏳ 等待页面加载...');
  await page.waitForTimeout(3000);

  // 清空 localStorage
  const cleared = await page.evaluate(() => {
    const before = localStorage.length;
    localStorage.clear();
    return {
      cleared: before,
      message: `已清空 ${before} 个 localStorage 项`
    };
  });

  console.log('\n✅ 前端缓存已清空:');
  console.log(`  清空项数: ${cleared.cleared}`);
  console.log(`  ${cleared.message}`);

  // 刷新页面
  console.log('\n🔄 刷新页面...');
  await page.reload();
  await page.waitForTimeout(5000);

  // 检查历史数据
  const historyInfo = await page.evaluate(async () => {
    const response = await fetch('/api/monitor/history?minutes=60');
    const data = await response.json();

    return {
      count: data.history?.length || 0,
      hasCachedData: localStorage.getItem('monitor_history') !== null,
    };
  });

  console.log('\n📊 当前状态:');
  console.log(`  历史数据点: ${historyInfo.count}`);
  console.log(`  是否有缓存: ${historyInfo.hasCachedData ? '❌ 还有缓存' : '✅ 已清空'}`);

  await page.screenshot({ path: '/tmp/cleared-cache.png' });
  console.log('\n📸 截图: /tmp/cleared-cache.png');

  console.log('\n⏸️  浏览器保持打开10秒...');
  await page.waitForTimeout(10000);

  await browser.close();
  console.log('\n✅ 清空完成！数据已从零开始记录！');
})();
