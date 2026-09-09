import { expect, test } from "@playwright/test";

const TAB_IDS = ["home", "dados", "modulos-portais", "arquitetura-roadmap", "sobre"];

test("Home is the default active tab with no hash", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("#tab-home")).toBeVisible();
  await expect(page.locator("#tab-btn-home")).toHaveAttribute("aria-selected", "true");
  for (const id of TAB_IDS.filter((t) => t !== "home")) {
    await expect(page.locator(`#tab-${id}`)).toBeHidden();
  }
});

test("clicking each tab shows only its panel and hides the rest", async ({ page }) => {
  await page.goto("/");

  for (const id of TAB_IDS) {
    await page.locator(`#tab-btn-${id}`).click();
    await expect(page.locator(`#tab-${id}`)).toBeVisible();
    await expect(page.locator(`#tab-btn-${id}`)).toHaveAttribute("aria-selected", "true");
    for (const other of TAB_IDS.filter((t) => t !== id)) {
      await expect(page.locator(`#tab-${other}`)).toBeHidden();
      await expect(page.locator(`#tab-btn-${other}`)).toHaveAttribute("aria-selected", "false");
    }
  }
});

test("a deep-link hash opens the matching tab on load", async ({ page }) => {
  await page.goto("/#modulos-portais");

  await expect(page.locator("#tab-modulos-portais")).toBeVisible();
  await expect(page.locator("#tab-btn-modulos-portais")).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#tab-home")).toBeHidden();
});

test("Home tab shows the fiscal snapshot cards with a non-pipeline source label", async ({
  page,
}) => {
  await page.goto("/");

  // getByText("Brasil hoje") is ambiguous: LandingEvolution's "Versão 1" description also
  // contains the substring "Brasil Hoje" -- scope to the heading role.
  await expect(page.getByRole("heading", { name: /Brasil hoje/i })).toBeVisible();
  const cards = page.locator(".fiscal-card");
  await expect(cards).toHaveCount(7);

  for (const card of await cards.all()) {
    const source = await card.locator(".fiscal-card__source").innerText();
    expect(source).toMatch(/Boletim Macrofiscal|Prisma Fiscal/);
  }
});
