import { chromium } from 'playwright';

(async () => {
  console.log('🔍 检查图表渲染错误...\n');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // 捕获所有console消息，特别是错误
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    
    if (type === 'error') {
      console.log(`❌ [ERROR] ${text}`);
    } else if (type === 'warning') {
      console.log(`⚠️  [WARN] ${text}`);
    } else if (text.includes('Chart') || text.includes('chart')) {
      console.log(`[Console] ${text}`);
    }
  });
  
  // 监听未捕获的异常
  page.on('pageerror', error => {
    console.log(`🔴 [Page Error] ${error}`);
  });
  
  // 监听请求失败
  page.on('requestfailed', request => {
    console.log(`❌ [Request Failed] ${request.url()} - ${request.failure().errorText}`);
  });
  
  await page.goto('http://localhost:3003/monitor');
  
  console.log('⏳ 等待页面完全加载...');
  await page.waitForTimeout(10000);
  
  // 检查图表DOM结构
  const chartInfo = await page.evaluate(() => {
    const chartContainer = document.querySelector('.recharts-wrapper');
    const areas = document.querySelectorAll('.recharts-area');
    const xAxis = document.querySelectorAll('.recharts-xAxis');
    const yAxis = document.querySelectorAll('.recharts-yAxis');
    
    return {
      hasChartContainer: !!chartContainer,
      areaCount: areas.length,
      xAxisCount: xAxis.length,
      yAxisCount: yAxis.length,
      chartContainerHTML: chartContainer ? chartContainer.innerHTML.substring(0, 500) : null,
    };
  });
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 图表DOM检查');
  console.log('='.repeat(60));
  console.log(`图表容器存在: ${chartInfo.hasChartContainer ? '✅ 是' : '❌ 否'}`);
  console.log(`Area元素数量: ${chartInfo.areaCount}`);
  console.log(`X轴元素数量: ${chartInfo.xAxisCount}`);
  console.log(`Y轴元素数量: ${chartInfo.yAxisCount}`);
  
  if (chartInfo.chartContainerHTML) {
    console.log('\n图表HTML预览:');
    console.log(chartInfo.chartContainerHTML.substring(0, 300));
  }
  
  await page.screenshot({ path: '/tmp/chart-debug.png' });
  console.log('\n📸 截图: /tmp/chart-debug.png');
  
  console.log('\n⏸️  浏览器保持打开10秒供检查...');
  await page.waitForTimeout(10000);
  
  await browser.close();
})();
