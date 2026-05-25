import puppeteer from 'puppeteer';
import fs from 'fs';

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.toString()));
  
  console.log('Navigating to http://127.0.0.1:8000 ...');
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0' });
  
  try {
    await page.type('input[type="text"]', 'admin');
    await page.type('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');
    
    // Wait for login
    await new Promise(r => setTimeout(r, 2000));
    
    // Click War Room Tab
    console.log('Clicking War Room tab...');
    await page.click('.btn-warroom');
    await new Promise(r => setTimeout(r, 1000));
    
    console.log('Taking screenshot of War Room...');
    await page.screenshot({ path: 'screenshot_warroom.png' });
    
    // Click Engage Chaos Mode
    console.log('Engaging chaos mode...');
    const engageBtn = await page.$('.btn-engage.btn-red');
    if (engageBtn) {
      await engageBtn.click();
      await new Promise(r => setTimeout(r, 1000));
      console.log('Taking screenshot after chaos...');
      await page.screenshot({ path: 'screenshot_chaos.png' });
      fs.writeFileSync('dom_chaos.html', await page.content());
      console.log('DOM after chaos written to dom_chaos.html');
    } else {
      console.log('Engage button not found!');
    }
  } catch (e) {
    console.error('Error during script:', e);
  }

  await browser.close();
})();
