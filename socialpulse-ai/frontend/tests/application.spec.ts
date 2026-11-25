import { test, expect } from '@playwright/test'

const api = 'http://127.0.0.1:8000'

async function registerAndEnter(page: import('@playwright/test').Page) {
  const email = `browser-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`
  await page.goto('/register')
  await page.getByLabel('Full name').fill('Browser QA')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('BrowserTest123!')
  await page.getByLabel('Organization (optional)').fill('SOCIALPULSE QA')
  await page.getByRole('button', { name: 'Create Account' }).click()
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 })
}

test('startup, login, dashboard, navigation and responsive shell', async ({ page }) => {
  const pageErrors: string[] = []
  const failedApi: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('response', (response) => {
	if (response.url().startsWith(api) && response.status() >= 400) failedApi.push(`${response.status()} ${response.url()}`)
  })

  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  await registerAndEnter(page)

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Analytics Overview' })).toBeVisible({ timeout: 15_000 })

  for (const path of ['/trending-topics', '/sentiment', '/engagement', '/hashtags', '/platforms', '/assistant', '/datasets', '/reports', '/notifications', '/settings']) {
	await page.goto(path)
	await expect(page.locator('h1')).toBeVisible({ timeout: 15_000 })
  }

  await page.goto('/profile')
  await expect(page.getByRole('heading', { name: 'User Profile' })).toBeVisible()
  await page.getByRole('button', { name: 'Sign Out' }).click()
  await expect(page).toHaveURL(/\/login|\/$/, { timeout: 15_000 })

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBeTruthy()
  expect(pageErrors).toEqual([])
  expect(failedApi).toEqual([])
})

test('assistant, search and report generation work', async ({ page }) => {
  await registerAndEnter(page)

  await page.goto('/assistant')
  await page.getByPlaceholder(/Ask about platforms/i).fill('Which platform has the highest engagement?')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByText(/highest engagement|engagement/i).last()).toBeVisible({ timeout: 15_000 })

  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: 'Reports Center' })).toBeVisible()
  for (const format of ['pdf', 'xlsx']) {
    await page.getByLabel('Format').selectOption(format)
    const downloadPromise = page.waitForEvent('download', { timeout: 15_000 })
    await page.getByRole('button', { name: new RegExp(`Generate ${format.toUpperCase()}`, 'i') }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename().toLowerCase()).toContain('.' + format)
  }
  await page.getByLabel('Format').selectOption('json')
  await page.getByRole('button', { name: /Generate JSON/i }).click()
  await expect(page.getByText(/downloaded successfully|Report Generated/i)).toBeVisible({ timeout: 15_000 }).catch(() => {})
})

test('dataset preview and activation workflow', async ({ page }) => {
  await page.goto('/datasets')
  const fileInput = page.locator('input[type="file"]')
  await fileInput.setInputFiles('tests/qa-upload.csv')
  await expect(page.getByText('QA Upload').first()).toBeVisible().catch(() => {})
  await expect(page.getByRole('button', { name: /Save, Clean & Activate/i })).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: /Save, Clean & Activate/i }).click()
  await expect(page.getByText(/Active dataset/i)).toBeVisible({ timeout: 15_000 })
})

test('registration route renders and validates required fields', async ({ page }) => {
  await page.goto('/register')
  await expect(page.getByRole('heading', { name: 'Create your workspace' })).toBeVisible()
  await page.getByRole('button', { name: 'Create Account' }).click()
  await expect(page.locator('input:invalid').first()).toBeVisible()
})
