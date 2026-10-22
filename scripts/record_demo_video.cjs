const path = require('path');
const fs = require('fs');
const puppeteer = require(path.join(__dirname, '..', 'frontend', 'node_modules', 'puppeteer'));

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function record() {
  const demoDir = path.join(__dirname, '..', 'docs', 'demo');
  const framesDir = path.join(demoDir, 'frames');

  if (fs.existsSync(framesDir)) {
    fs.rmSync(framesDir, { recursive: true, force: true });
  }
  fs.mkdirSync(framesDir, { recursive: true });

  console.log('Launching browser to record live application interaction...');
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,720'],
    defaultViewport: { width: 1280, height: 720 },
  });

  const page = await browser.newPage();
  let frameIndex = 0;
  let isRecording = true;

  // Frame capture loop in background at ~6 fps
  const captureLoop = async () => {
    while (isRecording) {
      try {
        const framePath = path.join(
          framesDir,
          `frame_${String(frameIndex).padStart(5, '0')}.png`
        );
        await page.screenshot({ path: framePath });
        frameIndex++;
      } catch (e) {
        // Page might be navigating or closing
      }
      await sleep(150); // ~6.6 FPS
    }
  };

  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });

  // Start background frame capture
  const recordPromise = captureLoop();

  // Scene 1: Welcome Screen (2.5 seconds)
  console.log('Recording Scene 1: Welcome Screen...');
  await sleep(2500);

  // Scene 2: Open Upload Modal & Upload CSV (3.5 seconds)
  console.log('Recording Scene 2: Upload CSV...');
  const uploadBtn = await page.$('button.btn-primary');
  if (uploadBtn) {
    await uploadBtn.click();
    await sleep(800);

    const sampleCsv = path.join(__dirname, '..', 'backend', 'data', 'sample_sales.csv');
    const fileInput = await page.$('input[type="file"]');
    if (fileInput) {
      await fileInput.uploadFile(sampleCsv);
      await sleep(1000);

      const submitBtn = await page.$('.modal-body button.btn-primary');
      if (submitBtn) {
        await submitBtn.click();
        await sleep(2000);
      }
    }
  }

  // Scene 3: Inspect Data Preview & Schema (3 seconds)
  console.log('Recording Scene 3: Data Preview & Schema...');
  await sleep(3000);

  // Scene 4: Click suggested question "Which region generated highest revenue?" (5 seconds)
  console.log('Recording Scene 4: Question & Chart generation...');
  const suggestions = await page.$$('.suggestion-card');
  if (suggestions.length > 0) {
    await suggestions[0].click();
    await sleep(4000); // Wait for calculation and chart rendering
  }

  // Scene 5: Anomaly Detection Question (5 seconds)
  console.log('Recording Scene 5: Anomaly detection...');
  const chatInput = await page.$('textarea.chat-input');
  const sendBtn = await page.$('button.send-btn');
  if (chatInput && sendBtn) {
    await chatInput.type('Detect anomalies in the dataset', { delay: 40 });
    await sleep(400);
    await sendBtn.click();
    await sleep(4500); // Wait for anomaly cards
  }

  // Scene 6: Switch to Automated Insights Dashboard (3 seconds)
  console.log('Recording Scene 6: Insights & KPIs Dashboard...');
  const tabs = await page.$$('.panel-tab');
  if (tabs.length > 1) {
    await tabs[1].click();
    await sleep(3500); // Review KPIs, top performers, monthly trends
  }

  // Stop recording
  isRecording = false;
  await recordPromise;
  await browser.close();

  console.log(`Finished capturing ${frameIndex} frames!`);
}

record().catch((err) => {
  console.error('Recording failed:', err);
  process.exit(1);
});
