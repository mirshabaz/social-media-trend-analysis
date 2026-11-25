import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  reporter: [['list']],
  use: {
	baseURL: 'http://127.0.0.1:5173',
	trace: 'retain-on-failure',
	screenshot: 'only-on-failure',
  },
  projects: [
	{ name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
	{ name: 'tablet-chromium', use: { browserName: 'chromium', viewport: { width: 768, height: 1024 }, isMobile: false } },
	{ name: 'mobile-chromium', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
	command: 'npm run dev -- --host 127.0.0.1',
	url: 'http://127.0.0.1:5173',
	reuseExistingServer: true,
  },
})
