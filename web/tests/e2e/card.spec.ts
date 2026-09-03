import { expect, test } from "@playwright/test";

test("card renders the debt value from the API with a source link", async ({ page }) => {
  await page.goto("/");

  const value = page.getByTestId("value");
  await expect(value).toBeVisible({ timeout: 20_000 });
  await expect(value).toContainText("R$");

  const source = page.getByTestId("source");
  await expect(source).toHaveAttribute("href", /tesourotransparente\.gov\.br|dados\.gov\.br/);

  await expect(page.locator(".data-class--observed")).toBeVisible();
});

test("no debt figure is hardcoded in the served bundle", async ({ request }) => {
  const html = await (await request.get("/")).text();
  const scriptMatch = html.match(/src="([^"]*assets\/[^"]+\.js)"/);
  expect(scriptMatch, "expected a bundled module script").not.toBeNull();

  const bundle = await (await request.get(scriptMatch![1]!)).text();
  // the real 2022 SP figure and its rounded forms must not appear literally
  expect(bundle).not.toMatch(/332[.,]?70[0-9]/);
  expect(bundle).not.toContain("divida_consolidada_liquida");
});
