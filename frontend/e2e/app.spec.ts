import { test, expect } from '@playwright/test'

test.describe('PLM Application', () => {
  test('should display the home page', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/PLM/)
  })

  test('should navigate to parts list', async ({ page }) => {
    await page.goto('/')

    // Click on Parts link in navigation
    await page.getByRole('link', { name: /parts/i }).click()

    // Should be on parts page
    await expect(page).toHaveURL(/.*parts/)
  })

  test('should navigate to documents list', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: /documents/i }).click()

    await expect(page).toHaveURL(/.*documents/)
  })

  test('should navigate to projects list', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: /projects/i }).click()

    await expect(page).toHaveURL(/.*projects/)
  })
})

test.describe('Login Flow', () => {
  test('should show login form', async ({ page }) => {
    await page.goto('/login')

    // Should have email and password fields
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('should show validation errors for empty form', async ({ page }) => {
    await page.goto('/login')

    // Try to submit empty form
    await page.getByRole('button', { name: /sign in/i }).click()

    // Browser validation should prevent submission
    const emailInput = page.getByLabel(/email/i)
    await expect(emailInput).toHaveAttribute('required')
  })
})
