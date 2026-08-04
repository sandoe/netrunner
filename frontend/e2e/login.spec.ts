import { test, expect } from '@playwright/test';
import { deploymentPassword, isServerDeployment } from './credentials';

test('@release admin login and topology view', async ({ page }) => {
  test.skip(!isServerDeployment(), 'Privileged accounts are disabled in student deployments');
  // Go to the login page
  await page.goto('/');

  // Check that the login form is visible
  await expect(page.locator('input[type="text"]')).toBeVisible();
  
  // Fill in the login credentials
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', deploymentPassword('admin'));
  
  // Submit the form
  await page.click('button[type="submit"]');

  // Verify that the authenticated desktop is visible.
  await expect(page.locator('.start-btn')).toBeVisible();

  // Open the real topology route and assert its current user-facing controls.
  await page.goto('/topology');
  await expect(page.locator('.topology-container')).toBeVisible();
  await expect(page.getByRole('button', { name: /SELECT/ })).toBeVisible();

  // Verify that admin-only operations are available in the start menu.
  await page.locator('.start-btn').click();
  await expect(page.getByRole('heading', { name: 'RED TEAM' })).toBeVisible();
});
