import { expect, test } from "@playwright/test";

test("register, create group, add participant, add expense, logout", async ({ page }) => {
  const suffix = Date.now();
  const email = `e2e_${suffix}@example.com`;
  const groupName = `E2E Group ${suffix}`;

  await page.goto("/register");
  await page.getByLabel("Display name").fill("E2E Owner");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Password123!");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/groups$/);
  await page.getByLabel("New group name").fill(groupName);
  await page.getByRole("button", { name: "Create group" }).click();

  const groupCardLink = page.getByRole("link", { name: new RegExp(groupName) });
  await expect(groupCardLink).toBeVisible();
  await groupCardLink.click();

  await expect(page).toHaveURL(/\/groups\/.+/);

  await page.getByPlaceholder("Rahul").fill("Rahul");
  await page.getByRole("button", { name: "Add participant" }).click();
  await expect(page.locator(".participant-row strong", { hasText: "Rahul" })).toBeVisible();

  await page.getByLabel("Amount").fill("120.00");
  await page.getByLabel("Description").fill("E2E Dinner");
  await page.getByLabel("Category").fill("Food");
  await page.getByLabel("Payer").selectOption({ label: "E2E Owner" });

  await page
    .locator("label.checkbox-card", { hasText: "E2E Owner" })
    .locator("input[type='checkbox']")
    .check();
  await page
    .locator("label.checkbox-card", { hasText: "Rahul" })
    .locator("input[type='checkbox']")
    .check();

  await page.getByRole("button", { name: "Add expense" }).click();
  await expect(page.getByText("E2E Dinner")).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
});
