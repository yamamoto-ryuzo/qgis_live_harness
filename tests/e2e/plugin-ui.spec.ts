import { test, expect } from "@playwright/test";

// L1: 通常ブラウザ + MockBridge で UI ロジックを検証する。
// サーブされる ui/ 静的ファイルに対して実行される。

test("初期表示でプラグイン情報とレイヤー一覧が出る", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("qgis-version")).toContainText("QGIS");
  await expect(page.getByTestId("layer-list").locator("li")).toHaveCount(3);
});

test("レイヤーをクリックするとアクティブになる", async ({ page }) => {
  await page.goto("/");
  const item = page.getByTestId("layer-list").locator("li").nth(1);
  await item.click();
  await expect(item).toHaveClass(/active/);
  await expect(page.getByTestId("status")).toContainText("active:");
});

test("アクティブレイヤー未選択でズームするとエラー表示", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("btn-zoom").click();
  await expect(page.getByTestId("status")).toContainText("no active layer");
  await expect(page.getByTestId("status")).toHaveClass(/error/);
});

test("無効レイヤーに警告マークが付く", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("layer-list")).toContainText("⚠ 欠損レイヤー");
});
