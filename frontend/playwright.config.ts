import { defineConfig, devices } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const envPath = resolve(import.meta.dirname, '..', '.env');
if (existsSync(envPath)) {
  for (const raw of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const split = line.indexOf('=');
    const key = line.slice(0, split);
    if (!process.env[key]) process.env[key] = line.slice(split + 1);
  }
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'line',
  use: {
    baseURL: process.env.NETRUNNER_BASE_URL || 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
  ],
  webServer: process.env.NETRUNNER_E2E_MANAGE_SERVER === '1' ? {
    command: 'cd .. && ./start.sh',
    url: process.env.NETRUNNER_BASE_URL || 'http://127.0.0.1:8000/api/ready',
    reuseExistingServer: true,
    timeout: 240000,
  } : undefined,
});
