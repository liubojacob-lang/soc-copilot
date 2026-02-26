import { chromium } from 'playwright';

(async () => {
  console.log('🌐 Opening browser...\n');
  
  // Launch browser in non-headless mode so user can see it
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500 // Slow down actions slightly for visibility
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  
  const page = await context.newPage();
  
  // Log all console messages
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('SSE') || text.includes('connection') || text.includes('Connected') || 
        text.includes('Monitor') || text.includes('Polling') || text.includes('Error')) {
      console.log(`[Browser Console] ${text}`);
    }
  });
  
  // Log network requests for SSE
  page.on('request', request => {
    if (request.url().includes('/api/monitor/stream')) {
      console.log('🔗 SSE Request initiated');
    }
  });
  
  page.on('response', response => {
    if (response.url().includes('/api/monitor/stream')) {
      console.log('✅ SSE Response - Status:', response.status());
      console.log('   Content-Type:', response.headers()['content-type']);
    }
  });
  
  console.log('📱 Navigating to http://localhost:3003/monitor\n');
  await page.goto('http://localhost:3003/monitor');
  
  console.log('⏳ Waiting for page to load and SSE to connect...\n');
  
  // Wait for connection to establish
  await page.waitForTimeout(8000);
  
  // Check connection status
  const connectionBadge = await page.locator('text=/SSE|Polling/').first().textContent();
  const connectedIndicators = await page.locator('.rounded-full').count();
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 MONITOR PAGE STATUS');
  console.log('='.repeat(60));
  console.log('Connection Badge:', connectionBadge);
  console.log('Status Indicators:', connectedIndicators);
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/monitor-live.png', fullPage: true });
  console.log('\n📸 Screenshot saved: /tmp/monitor-live.png');
  
  console.log('\n✅ Browser is now open at http://localhost:3003/monitor');
  console.log('👀 You can interact with the page directly');
  console.log('\nPress Ctrl+C to close the browser when done...\n');
  
  // Keep browser open - don't close it automatically
  // Wait for user to manually close or interrupt
  await new Promise(() => {}); // Keep running indefinitely
  
  // This will only run if browser is closed manually
  await browser.close();
})();
