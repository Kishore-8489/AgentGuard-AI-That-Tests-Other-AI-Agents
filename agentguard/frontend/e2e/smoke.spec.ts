import { test, expect } from '@playwright/test';

test('end-to-end demo catches failures and verifies the fixed agent', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Agent reliability, explained.' })).toBeVisible();
  const vulnerable = page.getByRole('button', { name: /Run vulnerable agent/i });
  const hardened = page.getByRole('button', { name: /Run hardened agent/i });
  await expect(vulnerable).toBeEnabled();
  await vulnerable.click();
  await expect(page.getByText('v1.0 / vulnerable')).toBeVisible();
  await expect(page.getByText('FAILED').first()).toBeVisible();
  await hardened.click();
  await expect(page.getByText('v1.1 / hardened')).toBeVisible();
  await expect(page.getByText('PASSED').first()).toBeVisible();
  await page.getByRole('button', { name: /Compare versions/i }).click();
  await expect(page.getByText('FIXED FAILURES')).toBeVisible();
});
