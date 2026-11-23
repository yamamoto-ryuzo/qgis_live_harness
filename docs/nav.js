// QGIS Live Harness ドキュメント共通ナビゲーション
// 使い方: <script src="nav.js" defer></script>
// - 左サイドバーにサイト内リンクを生成
// - 現在ページを自動ハイライト
// - JS が無効でも本文は通常表示される（サイドバーだけ出ない）
(function () {
  // ナビ構造 = 2本柱: QGISプラグイン群 × KASUGAIシリーズ
  //   連携は geo_webview + KASUGAI Canvas が主経路、AI 操作面は geo_driver
  //   と各プラグイン bridge が担う（index.html「基本構成」参照）
  const GROUPS = [
    {
      section: 'はじめに',
      items: [
        { href: 'index.html', text: '概要' },
        { href: 'usage.html', text: '使い方・セットアップ' },
        { href: 'security.html', text: 'セキュリティ' },
      ]
    },
    {
      // QGIS側プラグイン群 — geo_* 全9本。GeoSuite ワークフロー順＋制御ハブ
      section: 'QGISプラグイン',
      items: [
        { href: 'plugins.html', text: 'プラグイン一覧（全9件）' },
        { href: 'geosuite.html', text: 'GeoSuite — ワークフロー' },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_userfunc', text: 'geo_userfunc', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_import', text: 'geo_import', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_search', text: 'geo_search', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_webview', text: 'geo_webview', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_report', text: 'geo_report', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_excel', text: 'geo_excel', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_legend', text: 'geo_legend', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin/geo_launcher', text: 'geo_launcher', ext: true },
        { href: 'driver.html', text: 'geo_driver — 制御ハブ' },
        { href: 'distribution.html', text: 'プラグイン配布' },
      ]
    },
    {
      // KASUGAIシリーズ — 連携の主経路は geo_webview + KASUGAI Canvas
      section: 'KASUGAIシリーズ',
      items: [
        { href: 'https://github.com/yamamoto-ryuzo/kasugai_canvas', text: 'KASUGAI Canvas', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/kasugai_canvas/tree/main/docs', text: 'Canvas ドキュメント', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/kasugai_qgis', text: 'kasugai_qgis ランチャー', ext: true },
        { href: 'https://github.com/yamamoto-ryuzo/kasugai-canvas-web', text: 'kasugai-canvas-web（CDN版）', ext: true },
      ]
    },
    {
      section: '開発基盤',
      items: [
        { href: 'harness.html', text: 'QGIS Live Harness' },
        { href: 'internals.html', text: 'Harnessのプラグイン化' },
      ]
    },
    {
      section: 'リンク',
      items: [
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness', text: 'GitHub リポジトリ', ext: true },
      ]
    },
  ];

  const here = location.pathname.split('/').pop() || 'index.html';

  let html = '<div class="site"><span class="logo">Q</span>QGIS Live Harness</div>';
  html += '<div class="links">';
  for (const g of GROUPS) {
    html += `<div class="group">${g.section}</div>`;
    for (const it of g.items) {
      const cls = ['navlink'];
      if (it.ext) cls.push('ext');
      if (it.href === here) cls.push('active');
      html += `<a class="${cls.join(' ')}" href="${it.href}">${it.text}</a>`;
    }
  }
  html += '</div>';

  const nav = document.createElement('nav');
  nav.className = 'sidebar';
  nav.innerHTML = html;
  document.body.prepend(nav);

  // サイドバーのスクロール位置をページ遷移間で保持（タブ単位）
  const SCROLL_KEY = 'qgis-live-harness-docs-nav-scroll';
  try {
    const savedTop = sessionStorage.getItem(SCROLL_KEY);
    if (savedTop) nav.scrollTop = parseInt(savedTop, 10) || 0;
    let scrollTimer = null;
    nav.addEventListener('scroll', () => {
      if (scrollTimer) clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => {
        try { sessionStorage.setItem(SCROLL_KEY, String(nav.scrollTop)); } catch (e) { /* 無視 */ }
      }, 80);
    });
  } catch (e) { /* sessionStorage 不可時は位置保持なし */ }
})();
