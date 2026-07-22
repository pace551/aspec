// STK-NEXT-08: the T3+ Playwright smoke — boot the built app, render the key page,
// perform one real interaction end to end.
import { expect, test } from "@playwright/test";

test("home page renders and accepts a signature", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Guestbook" })).toBeVisible();

  await page.getByLabel("Name").fill("Playwright");
  await page.getByRole("button", { name: "Sign" }).click();

  await expect(
    page.getByRole("listitem").filter({ hasText: "Playwright" }),
  ).toBeVisible();
});
