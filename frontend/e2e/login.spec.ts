import { test, expect } from '@playwright/test';

test('admin login and topology view', async ({ page }) => {
  // Go to the login page
  await page.goto('/');

  // Check that the login form is visible
  await expect(page.locator('input[type="text"]')).toBeVisible();
  
  // Fill in the login credentials
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'admin');
  
  // Submit the form
  await page.click('button[type="submit"]');

  // Verify that we are logged in and see the Topology view
  await expect(page.locator('.view-title')).toHaveText(/TOPOLOGY/i);
  
  // Verify that the WAR ROOM button is visible for admin
  const warRoomBtn = page.locator('button', { hasText: 'WAR ROOM' });
  await expect(warRoomBtn).toBeVisible();
});
