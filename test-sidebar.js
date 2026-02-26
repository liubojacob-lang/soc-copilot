const puppeteer = require('puppeteer');

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  // Navigate to AI Assistant
  await page.goto('http://localhost:3003/en/ai-assistant');
  await sleep(2000);
  
  console.log('✓ Page loaded:', page.url());
  
  // Check if redirected to login
  if (page.url().includes('login')) {
    console.log('ℹ Redirected to login page');
    
    // Fill login form
    await page.waitForSelector('input[type="text"]', { timeout: 5000 });
    await page.type('input[type="text"]', 'admin');
    await page.type('input[type="password"]', 'admin123');
    
    // Submit
    await page.click('button[type="submit"]');
    await sleep(3000);
    
    console.log('✓ After login, URL:', page.url());
  }
  
  // Wait for AI Assistant page
  await sleep(2000);
  
  // Take initial screenshot
  await page.screenshot({ path: '/tmp/ai-assistant-initial.png', fullPage: false });
  console.log('✓ Initial screenshot saved to /tmp/ai-assistant-initial.png');
  
  // Check page content
  const content = await page.content();
  
  console.log('\n📊 Element Detection:');
  console.log(content.includes('<aside') ? '✓ Aside element found' : '✗ Aside element not found');
  console.log(content.includes('fixed left-0') ? '✓ Fixed left positioning' : '✗ Fixed positioning not found');
  console.log(content.includes('Chat History') || content.includes('历史对话') ? '✓ Chat history title' : '✗ Title not found');
  
  // Check for icons
  const hasPlus = await page.$('svg[class*="lucide-plus"]') !== null;
  const hasChevronRight = await page.$('svg[class*="lucide-chevron-right"]') !== null;
  const hasChevronLeft = await page.$('svg[class*="lucide-chevron-left"]') !== null;
  
  console.log(hasPlus ? '✓ Plus icon (New Chat)' : '✗ Plus icon');
  console.log(hasChevronRight ? '✓ ChevronRight icon (Expand)' : '✗ ChevronRight icon');
  console.log(hasChevronLeft ? '✓ ChevronLeft icon (Collapse)' : '✗ ChevronLeft icon');
  
  // Find sidebar
  const sidebar = await page.$('aside');
  if (sidebar) {
    const width = await sidebar.evaluate(el => el.offsetWidth || el.clientWidth);
    console.log(`✓ Sidebar width: ${width}px`);
    console.log(width <= 70 ? '  → Collapsed state detected' : '  → Expanded state detected');
  }
  
  // Find and click history button
  const buttons = await page.$$('button');
  console.log(`\n📊 Found ${buttons.length} buttons`);
  
  // Try to find history button
  let foundHistoryBtn = false;
  for (let i = 0; i < Math.min(buttons.length, 10); i++) {
    const title = await buttons[i].evaluate(el => el.title || el.getAttribute('aria-label') || '');
    if (title && (title.toLowerCase().includes('history') || title.includes('历史'))) {
      console.log(`✓ Clicking history button: "${title}"`);
      await buttons[i].click();
      await sleep(1000);
      foundHistoryBtn = true;
      break;
    }
  }
  
  if (foundHistoryBtn) {
    await page.screenshot({ path: '/tmp/ai-assistant-sidebar-open.png', fullPage: false });
    console.log('✓ Sidebar open screenshot saved');
  }
  
  await browser.close();
  console.log('\n✅ Test completed! Check screenshots in /tmp/');
})();
