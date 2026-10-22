const path = require('path');
const puppeteer = require(path.join(__dirname, '..', 'frontend', 'node_modules', 'puppeteer'));
const fs = require('fs');

async function main() {
  const screenshotDir = path.join(__dirname, '..', 'docs', 'screenshots');
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1366,820'],
    defaultViewport: { width: 1366, height: 820 },
  });

  const page = await browser.newPage();
  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });

  // 1. Capture welcome screen
  console.log('Capturing app_welcome.png...');
  await page.screenshot({ path: path.join(screenshotDir, 'app_welcome.png') });

  // 2. Click upload button
  console.log('Opening upload modal...');
  const uploadBtn = await page.$('button.btn-primary');
  if (uploadBtn) {
    await uploadBtn.click();
    await new Promise((r) => setTimeout(r, 600));

    // Upload file
    const samplePath = path.join(__dirname, '..', 'backend', 'data', 'sample_sales.csv');
    console.log('Uploading sample CSV:', samplePath);
    const fileInput = await page.$('input[type="file"]');
    if (fileInput) {
      await fileInput.uploadFile(samplePath);
      await new Promise((r) => setTimeout(r, 600));

      // Click upload confirmation button
      const submitBtn = await page.$('.modal-body button.btn-primary');
      if (submitBtn) {
        await submitBtn.click();
        console.log('Waiting for upload to complete...');
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
  }

  // 3. Capture dashboard with data preview
  console.log('Capturing app_dashboard.png...');
  await page.screenshot({ path: path.join(screenshotDir, 'app_dashboard.png') });

  // 4. Click a suggested question e.g. "Which region generated the highest revenue?"
  console.log('Clicking suggested question...');
  const suggestions = await page.$$('.suggestion-card');
  if (suggestions.length > 0) {
    await suggestions[0].click();
    console.log('Waiting for analysis...');
    await new Promise((r) => setTimeout(r, 2500));
  }

  // 5. Ask anomaly question via input
  console.log('Asking anomaly question...');
  const chatInput = await page.$('textarea.chat-input');
  const sendBtn = await page.$('button.send-btn');
  if (chatInput && sendBtn) {
    await chatInput.type('Detect anomalies in the dataset');
    await sendBtn.click();
    console.log('Waiting for anomaly analysis...');
    await new Promise((r) => setTimeout(r, 3000));
  }

  // 6. Capture full chat analysis with charts and code
  console.log('Capturing app_chat_analysis.png...');
  await page.screenshot({ path: path.join(screenshotDir, 'app_chat_analysis.png') });

  // 7. Click Insights tab on right panel
  console.log('Clicking Insights panel...');
  const tabs = await page.$$('.panel-tab');
  if (tabs.length > 1) {
    await tabs[1].click();
    await new Promise((r) => setTimeout(r, 1500));
    console.log('Capturing app_insights.png...');
    await page.screenshot({ path: path.join(screenshotDir, 'app_insights.png') });
  }

  await browser.close();
  console.log('All screenshots captured successfully!');
}

main().catch((err) => {
  console.error('Error taking screenshots:', err);
  process.exit(1);
});
