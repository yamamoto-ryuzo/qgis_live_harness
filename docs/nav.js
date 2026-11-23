// QGIS Live Harness ドキュメント共通ナビゲーション
// 使い方: <script src="nav.js" defer></script>
// - 左サイドバーにサイト内リンクを生成
// - 現在ページを自動ハイライト
// - JS が無効でも本文は通常表示される（サイドバーだけ出ない）
(function () {
  // ナビ構造
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
      section: 'コンポーネント',
      items: [
        { href: 'driver.html', text: 'QGIS Live Driver' },
        { href: 'harness.html', text: 'QGIS Live Harness' },
      ]
    },
    {
      section: 'ガイド',
      items: [
        { href: 'distribution.html', text: 'プラグイン配布' },
        { href: 'internals.html', text: 'Harnessのプラグイン化' },
        { href: 'plugins.html', text: 'プラグイン一覧' },
        { href: 'geosuite.html', text: 'GeoSuite' },
      ]
    },
    {
      section: 'プラグイン',
      items: [
        { href: 'https://github.com/yamamoto-ryuzo/qgis_live_harness/tree/master/qgis-plugin', text: 'プラグイン docs(GitHub)', ext: true },
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
