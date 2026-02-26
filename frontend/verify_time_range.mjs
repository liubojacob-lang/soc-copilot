import { chromium } from 'playwright';

(async () => {
  console.log('🧪 验证时间范围修复...\n');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('Point:') || text.includes('Filtered result')) {
      console.log(`[Console] ${text}`);
    }
  });
  
  await page.goto('http://localhost:3003/monitor');
  await page.waitForTimeout(10000);
  
  // 测试不同时间范围
  const ranges = ['1h', '6h', '24h'];
  
  for (const range of ranges) {
    console.log(`\n🔍 测试 ${range} 时间范围...`);
    
    const result = await page.evaluate(async (testRange) => {
      // 找到并点击对应的按钮
      const buttons = Array.from(document.querySelectorAll('button'));
      const targetBtn = buttons.find(b => b.textContent.trim() === testRange);
      
      if (targetBtn) {
        targetBtn.click();
        
        // 等待重新渲染
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // 检查过滤后的结果
        const logs = [];
        const originalLog = console.log;
        console.log = (...args) => logs.push(args.join(' '));
        
        // 触发重新渲染来获取日志
        window.dispatchEvent(new Event('test'));
        
        console.log = originalLog;
        
        return {
          clicked: true,
          logs: logs.filter(l => l.includes('Filtered result'))
        };
      }
      
      return { clicked: false };
    }, range);
    
    console.log(`  按钮${result.clicked ? '✅ 点击成功' : '❌ 点击失败'}`);
  }
  
  await page.screenshot({ path: '/tmp/time-range-verify.png' });
  console.log('\n📸 截图: /tmp/time-range-verify.png');
  
  console.log('\n⏸️  浏览器保持打开20秒供手动检查...');
  await page.waitForTimeout(20000);
  
  await browser.close();
})();
