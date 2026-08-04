import { test, expect } from '@playwright/test';
import { deploymentPassword, isServerDeployment } from './credentials';

test('@release navigate to report generator and verify elements', async ({ page }) => {
  test.skip(!isServerDeployment(), 'Privileged accounts are disabled in student deployments');
  // Go to the main page to log in
  await page.goto('/');

  // Wait for the login form to be visible and login
  await expect(page.locator('input[type="text"]')).toBeVisible();
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', deploymentPassword('admin'));
  await page.click('button[type="submit"]');

  // Wait for login to complete by checking a dashboard/topology element
  // App.vue adds .app class when logged in
  await expect(page.locator('.app')).toBeVisible();

  // Navigate to Report Generator
  await page.goto('/reports');

  await expect(page.getByRole('heading', { name: 'REPORT BUILDER' })).toBeVisible();
  await page.getByPlaceholder('e.g. ASO').fill('E2E');
  await page.getByRole('checkbox', { name: 'Min-PC', exact: true }).check();
  await page.getByRole('checkbox', { name: 'IP Addresses (Network)' }).check();
  await page.getByRole('button', { name: 'GENERATE & VIEW REPORT' }).click();

  // Verify a report was actually generated.
  const classifiedStamp = page.locator('.stamp-classified').first();
  await expect(classifiedStamp).toHaveText(/TOP SECRET \/\/ CLASSIFIED/);

  // Verify the report header is visible
  const reportHeader = page.locator('.report-header h1');
  await expect(reportHeader).toHaveText(/SECURITY ASSESSMENT REPORT/);

  // Check that PDF export creates a real browser download.
  const downloadBtn = page.locator('button.btn-pdf');
  await expect(downloadBtn.filter({ hasText: '[ EXPORT PDF ]' })).toBeEnabled();
  const downloadPromise = page.waitForEvent('download', { timeout: 20_000 });
  await downloadBtn.filter({ hasText: '[ EXPORT PDF ]' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
});
