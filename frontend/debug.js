import puppeteer from 'puppeteer';
import fs from 'fs';

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.toString()));
  
  console.log('Navigating to http://127.0.0.1:8000 ...');
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0' });
  
  console.log('Taking screenshot before login...');
  await page.screenshot({ path: 'screenshot_before.png' });
  
  const content = await page.content();
  console.log('HTML Length:', content.length);
  
  // Try to type user and password
  try {
    await page.type('input[type="text"]', 'admin');
    await page.type('input[type="password"]', 'admin');
    console.log('Clicking login...');
    await page.click('button[type="submit"]');
    
    // Wait for network
    await new Promise(r => setTimeout(r, 2000));
    console.log('Taking screenshot after login...');
    await page.screenshot({ path: 'screenshot_after.png' });
    
    const afterHtml = await page.content();
    fs.writeFileSync('dom_after.html', afterHtml);
    console.log('DOM after login written to dom_after.html');
  } catch (e) {
    console.error('Error during login script:', e);
  }

  await browser.close();
})();
