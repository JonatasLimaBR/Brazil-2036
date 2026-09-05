import { expect, test } from "@playwright/test";

test("card renders the debt value from the API with a source link", async ({ page }) => {
  await page.goto("/");

  const value = page.getByTestId("value");
  await expect(value).toBeVisible({ timeout: 20_000 });
  await expect(value).toContainText("R$");

  const source = page.getByTestId("source");
  await expect(source).toHaveAttribute("href", /tesourotransparente\.gov\.br|dados\.gov\.br/);

  await expect(page.locator("#card .data-class--observed")).toBeVisible();
});

test("INSS module renders without crashing for each of the 3 metrics", async ({ page }) => {
  // The historical backfill for INSS_BENEFICIOS has not run yet (BUILD_REPORT
  // blocker), so Gold may have no rows for these metric_ids -- the API then
  // returns 404 and the module renders "Indisponível", not a value. This test
  // asserts the module wires up and degrades gracefully either way; it is not
  // yet the strict "value must render" assertion the debt card test makes
  // above, because there is no real data to assert on until the backfill runs.
  await page.goto("/");

  await expect(page.getByText("Previdência & INSS")).toBeVisible();

  for (const id of [
    "inss_beneficios_emitidos",
    "inss_beneficios_mantidos",
    "inss_beneficios_indeferidos",
  ]) {
    const article = page.getByTestId(`inss-${id}`);
    await expect(article).toBeVisible({ timeout: 20_000 });
    const hasValue = await page.getByTestId(`inss-${id}-value`).count();
    const hasError = await article.locator(".error").count();
    expect(hasValue + hasError, `${id} must render a value or an error, not neither`).toBe(1);
  }
});

test("Fiscal module renders without crashing for each of the 3 metrics", async ({ page }) => {
  // No real backfill has run yet for fiscal_receita/fiscal_despesa/
  // fiscal_primario, so the API may 404 and the module renders
  // "Indisponível" -- same graceful-degradation contract as the INSS module
  // above, not yet the strict "value must render" assertion.
  await page.goto("/");

  await expect(page.getByText("Fiscal & DebtLab")).toBeVisible();

  for (const id of ["fiscal_receita", "fiscal_despesa", "fiscal_primario"]) {
    const article = page.getByTestId(`fiscal-${id}`);
    await expect(article).toBeVisible({ timeout: 20_000 });
    const hasValue = await page.getByTestId(`fiscal-${id}-value`).count();
    const hasError = await article.locator(".error").count();
    expect(hasValue + hasError, `${id} must render a value or an error, not neither`).toBe(1);
  }
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
