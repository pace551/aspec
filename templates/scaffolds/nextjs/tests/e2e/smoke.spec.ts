// STK-NEXT-08: the T3+ smoke — boot the built app and prove the key page serves.
// Grow this into one real interaction as soon as the page has one.
import { expect, test } from "@playwright/test";

test("home page serves", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
