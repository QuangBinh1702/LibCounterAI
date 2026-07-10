import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from 'playwright';

const baseURL = 'http://127.0.0.1:4174';
const jsonHeaders = { 'content-type': 'application/json' };
const browserRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const viteBin = resolve(browserRoot, 'node_modules/vite/bin/vite.js');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function waitForServer(url, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Server is still starting.
    }
    await delay(500);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function addApiRoutes(page) {
  await page.route('http://localhost:8000/api/health', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify({
        status: 'healthy',
        services: { database: 'configured at localhost', cache: 'configured at localhost' },
      }),
    });
  });

  await page.route('http://localhost:8000/api/cameras', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify([
        { id: 1, name: 'Demo Gate', source_url: 'rtsp://demo.local/library', status: 'OFFLINE' },
      ]),
    });
  });

  await page.route('http://localhost:8000/api/persons', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify([
        { id: 1, full_name: 'Nguyen Van A', member_code: 'SV123456', role: 'STUDENT', status: 'ACTIVE' },
      ]),
    });
  });

  await page.route('http://localhost:8000/api/sessions**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify([
        {
          id: 101,
          person_name: 'UNKNOWN_20260706_0001',
          member_code: null,
          identity_type: 'UNKNOWN',
          entry_at: '2026-07-06T08:00:00',
          exit_at: '2026-07-06T08:15:00',
          duration_seconds: 900,
          status: 'CLOSED',
        },
      ]),
    });
  });

  await page.route('http://localhost:8000/api/stats/occupancy**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify({
        current_occupancy: 1,
        total_entries_today: 2,
        total_exits_today: 1,
        known_visitors_today: 1,
        unknown_visitors_today: 1,
        total_sessions_today: 2,
      }),
    });
  });

  await page.route('http://localhost:8000/api/stats/hourly**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: jsonHeaders,
      body: JSON.stringify([
        { hour: 8, entry: 2, exit: 1 },
        { hour: 9, entry: 0, exit: 0 },
      ]),
    });
  });
}

async function runSmoke() {
  const server = spawn(
    process.execPath,
    [viteBin, '--host', '127.0.0.1', '--port', '4174'],
    { cwd: browserRoot, stdio: 'pipe' },
  );

  let browser;
  try {
    server.stdout.on('data', (chunk) => process.stdout.write(chunk));
    server.stderr.on('data', (chunk) => process.stderr.write(chunk));

    await waitForServer(baseURL);

    browser = await chromium.launch();
    const page = await browser.newPage();
    await addApiRoutes(page);

    await page.goto(baseURL);
    await page.getByTestId('view-monitor').waitFor({ state: 'visible' });
    await page.getByTestId('video-screen').waitFor({ state: 'visible' });

    const backendDotClass = await page.locator('[data-testid="backend-status"] .dot').getAttribute('class');
    assert(backendDotClass && !backendDotClass.includes('offline'), 'Backend status did not become online.');

    await page.getByTestId('nav-registry').click();
    await page.getByTestId('view-registry').waitFor({ state: 'visible' });
    const personsText = await page.getByTestId('persons-table').innerText();
    assert(personsText.includes('Nguyen Van A'), 'Registry did not render the mocked person name.');
    assert(personsText.includes('SV123456'), 'Registry did not render the mocked member code.');

    await page.getByTestId('nav-history').click();
    await page.getByTestId('view-history').waitFor({ state: 'visible' });
    const sessionsText = await page.getByTestId('sessions-table').innerText();
    assert(sessionsText.includes('UNKNOWN_20260706_0001'), 'History did not render the mocked unknown session.');

    const downloadPromise = page.waitForEvent('download');
    await page.getByTestId('export-menu').click();
    await page.getByTestId('export-csv').click();
    const download = await downloadPromise;
    assert(
      /^libcounterai_sessions_\d{4}-\d{2}-\d{2}(?:_\d{4}-\d{2}-\d{2})?\.csv$/.test(download.suggestedFilename()),
      `Unexpected CSV filename: ${download.suggestedFilename()}`,
    );

    await page.getByTestId('nav-analytics').click();
    await page.getByTestId('view-analytics').waitFor({ state: 'visible' });
    await page.getByTestId('period-filter').waitFor({ state: 'visible' });
    await page.getByTestId('traffic-chart').waitFor({ state: 'visible' });
    const analyticsText = await page.getByTestId('analytics-cards').innerText();
    assert(analyticsText.includes('1'), 'Analytics did not render current occupancy.');
    assert(analyticsText.includes('2'), 'Analytics did not render entry count.');

    console.log('Dashboard E2E smoke PASSED.');
  } finally {
    if (browser) await browser.close();
    if (!server.killed) {
      server.kill();
    }
  }
}

runSmoke().catch((error) => {
  console.error('Dashboard E2E smoke FAILED.');
  console.error(error);
  process.exit(1);
});
