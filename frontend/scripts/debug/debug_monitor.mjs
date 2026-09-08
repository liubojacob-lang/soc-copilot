import { chromium } from 'playwright';

(async () => {
  console.log('🔍 Debugging Monitor Page...\n');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Capture ALL console messages
  page.on('console', msg => {
    console.log(`[${msg.type()}] ${msg.text()}`);
  });
  
  // Capture all network errors
  page.on('response', response => {
    if (response.status() >= 400) {
      console.log(`[HTTP ${response.status()}] ${response.url()}`);
    }
  });
  
  // Capture all requests
  page.on('request', request => {
    const url = request.url();
    if (url.includes('monitor') || url.includes('stream')) {
      console.log(`[REQUEST] ${request.method()} ${url}`);
    }
  });
  
  await page.goto('http://localhost:3003/monitor');
  
  console.log('\n⏳ Waiting 10 seconds for SSE connection...\n');
  await page.waitForTimeout(10000);
  
  // Check state
  const connected = await page.locator('text=/Connected|Disconnected/').first().textContent();
  console.log(`\n📊 Connection Status: ${connected}`);
  
  await page.screenshot({ path: '/tmp/monitor-debug.png' });
  console.log('\n📸 Screenshot: /tmp/monitor-debug.png');
  
  console.log('\n⏸️  Browser will stay open for 30 seconds. Check it now!');
  await page.waitForTimeout(30000);
  
  await browser.close();
})();
