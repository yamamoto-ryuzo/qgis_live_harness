import { test, expect, chromium } from "@playwright/test";

// L2: 実際のQGIS内で動いているUIに対する検証。
// 前提:
//   1. scripts\deploy-plugin.ps1 でプラグインを配置し、QGIS側で一度有効化する
//   2. scripts\verify-in-qgis.ps1 で QTWEBENGINE_REMOTE_DEBUGGING=9222 付き起動
//   3. プラグインダイアログを開いた状態にする
// 実行: npm run test:live

const CDP_URL = process.env.QGIS_CDP_URL || "http://localhost:9222";

test.describe("QGIS実機(CDP接続)", () => {
  test.skip(!process.env.QGIS_LIVE, "QGIS_LIVE=1 を設定して実行");

  test("実QGIS内のプラグインUIが操作できる", async () => {
    const browser = await chromium.connectOverCDP(CDP_URL);
    const contexts = browser.contexts();
    expect(contexts.length).toBeGreaterThan(0);

    // プラグインのWebEngineページを探す
    const pages = contexts.flatMap((c) => c.pages());
    const page = pages.find((p) => p.url().includes("index.html"));
    expect(page, "プラグインUIのページが見つからない(ダイアログは開いているか)").toBeTruthy();

    await page!.getByTestId("btn-refresh").click();
    // モックではなく実データが返る: qgis-version が mock-* 以外
    await expect(page!.getByTestId("qgis-version")).not.toContainText("mock-");
    await page!.screenshot({ path: "test-results/qgis-live.png" });
  });
});
