import { test, expect } from '@playwright/test';
import { deploymentPassword, isServerDeployment } from './credentials';

test('@release student role UI restrictions and redirect logic', async ({ page }) => {
  // 1. Go to the login page
  await page.goto('/');

  // 2. Log in as a student
  await page.fill('input[type="text"]', 'student');
  await page.fill('input[type="password"]', deploymentPassword('student'));
  await page.click('button[type="submit"]');

  // Verify we are logged in and see the taskbar
  await expect(page.locator('.start-btn')).toBeVisible();

  // 3. Open the start menu
  await page.click('.start-btn');
  await expect(page.locator('.start-menu')).toBeVisible();

  // 4. Verify restricted links/sections are NOT present for student
  await expect(page.locator('button', { hasText: 'AI Playbooks' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Subnet Scan' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Network Controller' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Database Control' })).not.toBeVisible();
  await expect(page.locator('h3', { hasText: 'RED TEAM' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Cyberdeck Codex' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Threat Hunting' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Analytics Center' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Wireless IDS' })).not.toBeVisible();
  await expect(page.locator('button', { hasText: 'Intelligence & TTP' })).not.toBeVisible();

  // 5. Try navigating to restricted routes (e.g. /playbooks) and verify redirect to /dashboard
  await page.goto('/playbooks');
  await page.waitForURL('**/dashboard');
  await expect(page.locator('.dashboard-container')).toBeVisible();

  await page.goto('/attack');
  await page.waitForURL('**/dashboard');
  await expect(page.locator('.dashboard-container')).toBeVisible();

  // 6. Log out
  await page.click('.start-btn');
  await page.click('.btn-logout');
  await expect(page.locator('input[type="text"]')).toBeVisible();
});

test('@release admin role standard UI access', async ({ page }) => {
  test.skip(!isServerDeployment(), 'Privileged accounts are disabled in student deployments');
  // 1. Go to the login page
  await page.goto('/');

  // 2. Log in as admin
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', deploymentPassword('admin'));
  await page.click('button[type="submit"]');

  // Verify we are logged in and see the taskbar
  await expect(page.locator('.start-btn')).toBeVisible();

  // 3. Open the start menu
  await page.click('.start-btn');
  await expect(page.locator('.start-menu')).toBeVisible();

  // 4. Verify standard/admin links/sections ARE present
  await expect(page.locator('button', { hasText: 'AI Playbooks' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Subnet Scan' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Network Controller' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Database Control' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'RED TEAM' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Cyberdeck Codex' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Threat Hunting' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Analytics Center' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Wireless IDS' })).toBeVisible();
  await expect(page.locator('button', { hasText: 'Intelligence & TTP' })).toBeVisible();
});
