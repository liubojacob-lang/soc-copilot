import { chromium } from 'playwright';

(async () => {
  console.log('🔍 Previewing Optimized Monitor Page...\n');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  await page.goto('http://localhost:3003/monitor');
  
  console.log('⏳ Waiting 8 seconds for page to load...');
  await page.waitForTimeout(8000);
  
  await page.screenshot({ path: '/tmp/monitor-unified.png', fullPage: true });
  console.log('📸 Screenshot saved: /tmp/monitor-unified.png\n');
  
  console.log('✅ Browser is open with optimized navigation!');
  console.log('👀 Check the unified navigation bar at the top\n');
  
  await page.waitForTimeout(30000);
  await browser.close();
})();
