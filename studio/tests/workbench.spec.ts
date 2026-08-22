import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const bbox = { x0: 120, y0: 180, x1: 620, y1: 230, space: "normalized" };
const page = {
  page_number: 7,
  strata: ["密集公式"],
  rationale: "test formula annotation",
  verified_aspects: [],
  image_artifact_id: "a".repeat(64),
  blocks: [],
  reading_order: [],
};
const selectedPages = [1, 7, 12, 30, 50, 70, 90, 110, 130, 150, 170, 207];
const snapshot = {
  dataset: {
    schema: "mathlens.golden-dataset.v3",
    dataset_id: "studio-browser-test",
    source: { filename: "sample.pdf", sha256: "b".repeat(64) },
    source_page_count: 207,
    render_dpi: 300,
    pages: selectedPages.map((pageNumber) => ({ ...page, page_number: pageNumber })),
  },
  revision: "c".repeat(64),
  prediction_pages: {
    "7": {
      engine: "mineru",
      engine_version: "3.4.5",
      configuration_hash: "e".repeat(64),
      blocks: [{
        id: "p7-b0",
        type: "formula",
        bbox,
        candidates: [{
          content: "x^2+1",
          engine: "mineru",
          engine_version: "3.4.5",
          confidence: null,
        }],
        selected_candidate: 0,
      }],
    },
  },
  image_urls: Object.fromEntries(selectedPages.map((pageNumber) => [
    String(pageNumber),
    `/api/images/${pageNumber}`,
  ])),
  thumbnail_urls: Object.fromEntries(selectedPages.map((pageNumber) => [
    String(pageNumber),
    `/api/thumbnails/${pageNumber}`,
  ])),
};

async function mockWorkbench(
  browserPage: Page,
  onSave: (page: Record<string, unknown>) => void = () => undefined,
) {
  await browserPage.route("**/api/workspace", (route) => route.fulfill({ json: snapshot }));
  await browserPage.route("**/api/images/*", (route) => route.fulfill({
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1100"><rect width="100%" height="100%" fill="white"/></svg>',
  }));
  await browserPage.route("**/api/thumbnails/*", (route) => route.fulfill({
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="110"><rect width="100%" height="100%" fill="white"/></svg>',
  }));
  await browserPage.route("**/api/pages/7", async (route) => {
    const body = route.request().postDataJSON() as { page: Record<string, unknown> };
    onSave(body.page);
    await route.fulfill({ json: { page: body.page, revision: "d".repeat(64) } });
  });
}

test("accepts a parser suggestion and saves human truth", async ({ page: browserPage }) => {
  let savedPage: Record<string, unknown> | null = null;
  await mockWorkbench(browserPage, (page) => { savedPage = page; });

  await browserPage.goto("/");
  await expect(browserPage.getByText("Golden Workbench")).toBeVisible();
  await expect(browserPage.locator(".bbox.prediction")).toHaveCount(1);

  await browserPage.locator(".bbox.prediction").click({ force: true });
  await browserPage.getByRole("button", { name: "接受为人工真值" }).click();
  await browserPage.getByLabel("LaTeX").fill(String.raw`x^2+1`);

  await expect(browserPage.locator(".bbox.golden")).toHaveCount(1);
  await expect(browserPage.locator(".order-list li")).toHaveCount(1);
  await expect(browserPage.getByRole("img", { name: "所选块的原始扫描裁剪" })).toBeVisible();
  await expect(browserPage.locator(".formula-preview")).toContainText("x2+1");
  await browserPage.getByRole("button", { name: "确认公式 LaTeX并前往下一项" }).click();
  await expect.poll(() => savedPage).not.toBeNull();
  expect(savedPage).toMatchObject({
    verified_aspects: [],
    reading_order: ["p7-b0"],
    blocks: [{
      id: "p7-b0",
      latex: "x^2+1",
      verified_aspects: ["formula"],
      suggested_by: {
        engine: "mineru",
        engine_version: "3.4.5",
        configuration_hash: "e".repeat(64),
        block_id: "p7-b0",
      },
    }],
  });
});

for (const viewport of [
  { name: "landscape", width: 1024, height: 640 },
  { name: "portrait", width: 768, height: 1024 },
  { name: "phone", width: 390, height: 844 },
]) {
  test(`keeps the review flow accessible in ${viewport.name}`, async ({ page: browserPage }) => {
    await browserPage.setViewportSize(viewport);
    await mockWorkbench(browserPage);
    await browserPage.goto("/");
    await browserPage.locator(".bbox.prediction").click({ force: true });
    await browserPage.getByRole("button", { name: "接受为人工真值" }).click();

    const confirm = browserPage.getByRole("button", { name: "确认公式 LaTeX并前往下一项" });
    await confirm.scrollIntoViewIfNeeded();

    await expect(confirm).toBeInViewport();
    await expect(browserPage.getByRole("img", { name: "所选块的原始扫描裁剪" })).toBeVisible();
    const overflow = await browserPage.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
    if (viewport.name === "landscape") {
      const pageListScroll = await browserPage.locator(".page-list").evaluate((element) => {
        element.scrollTop = element.scrollHeight;
        return { top: element.scrollTop, maximum: element.scrollHeight - element.clientHeight };
      });
      expect(pageListScroll.maximum).toBeGreaterThan(0);
      expect(pageListScroll.top).toBeGreaterThan(0);
      const canvasOverflow = await browserPage.locator(".canvas-scroll").evaluate((element) => ({
        horizontal: element.scrollWidth - element.clientWidth,
        vertical: element.scrollHeight - element.clientHeight,
      }));
      expect(canvasOverflow.horizontal).toBeLessThanOrEqual(1);
      expect(canvasOverflow.vertical).toBeLessThanOrEqual(1);
    }
  });
}
