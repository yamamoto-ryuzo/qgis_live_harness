// README.md を章ごとの複数ページHTMLに変換して docs/ に出力する。
//   npm run docs:build
// GitHub Pages は Settings → Pages → Deploy from a branch → master /docs を指定。
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'docs');
const REPO = 'https://github.com/yamamoto-ryuzo/qgis_live_harness';
const BRANCH = 'master';

// README の `## ` 見出しをページへ割り当てる。先にマッチしたページが優先。
// どれにもマッチしない章は index へ流す(構成/環境要件/注意)。
const PAGES = [
  { slug: 'index', title: '概要', match: null },
  { slug: 'driver', title: 'QGIS Live Driver', match: /^1\. / },
  { slug: 'harness', title: 'QGIS Live Harness', match: /^2\. / },
  { slug: 'usage', title: '構成・セットアップ・使い方', match: /^(ディレクトリ構成|セットアップ|使い方)/ },
  { slug: 'distribution', title: 'プラグイン配布', match: /^プラグイン配布/ },
  { slug: 'internals', title: 'Harnessのプラグイン化', match: /^Harness自体のプラグイン化/ },
];

const md = readFileSync(join(ROOT, 'README.md'), 'utf8');
const [preamble, ...sectionMds] = md.split(/(?=^## )/m);
const sections = sectionMds.map((s) => ({
  heading: s.match(/^## (.*)/)[1],
  md: s,
}));

const assigned = new Map(PAGES.map((p) => [p.slug, p.slug === 'index' ? [preamble] : []]));
for (const sec of sections) {
  const page = PAGES.find((p) => p.match && p.match.test(sec.heading)) ?? PAGES[0];
  assigned.get(page.slug).push(sec.md);
}

// 相対リンク(.md含む)はGitHub上のblob/tree URLへ書き換える。
// #アンカー・外部URLはそのまま。
marked.use({
  renderer: {
    link(token) {
      let { href } = token;
      if (!/^(https?:|mailto:|#)/.test(href)) {
        const clean = href.replace(/^\.\//, '');
        const kind = clean.endsWith('/') ? 'tree' : 'blob';
        href = `${REPO}/${kind}/${BRANCH}/${clean}`;
      }
      const text = this.parser.parseInline(token.tokens);
      const title = token.title ? ` title="${token.title}"` : '';
      return `<a href="${href}"${title}>${text}</a>`;
    },
  },
});

const CSS = `
  :root { --nav-w: 240px; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", "Noto Sans JP", sans-serif;
         color: #1f2328; display: flex; min-height: 100vh; }
  nav { width: var(--nav-w); flex-shrink: 0; border-right: 1px solid #d1d9e0;
        padding: 24px 16px; position: sticky; top: 0; height: 100vh; overflow: auto; }
  nav .site { font-weight: 700; font-size: 15px; margin-bottom: 16px; }
  nav a { display: block; padding: 6px 8px; border-radius: 6px; color: #0969da;
          text-decoration: none; font-size: 14px; }
  nav a.active { background: #ddf4ff; font-weight: 600; }
  nav a:hover { background: #f6f8fa; }
  main { flex: 1; max-width: 980px; padding: 32px 48px 80px; overflow-wrap: break-word; }
  h1 { border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; }
  h2 { border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; margin-top: 32px; }
  h3 { margin-top: 24px; }
  code, pre { font-family: ui-monospace, Consolas, monospace; }
  code { background: #eff1f3; padding: .2em .4em; border-radius: 6px; font-size: 85%; }
  pre { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; display: block; overflow: auto; }
  th, td { border: 1px solid #d1d9e0; padding: 6px 13px; }
  tr:nth-child(2n) { background: #f6f8fa; }
  blockquote { border-left: .25em solid #d1d9e0; color: #59636e;
               margin: 0; padding: 0 1em; }
  a { color: #0969da; }
  .mermaid { margin: 16px 0; }
  @media (max-width: 800px) {
    body { flex-direction: column; }
    nav { width: auto; height: auto; position: static; border-right: none;
          border-bottom: 1px solid #d1d9e0; }
    main { padding: 16px 20px 60px; }
  }
`;

const MERMAID = `<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
document.querySelectorAll('pre > code.language-mermaid').forEach((el) => {
  const div = document.createElement('div');
  div.className = 'mermaid';
  div.textContent = el.textContent;
  el.parentElement.replaceWith(div);
});
mermaid.initialize({ startOnLoad: false });
await mermaid.run({ querySelector: '.mermaid' });
</script>`;

function pageHtml(page, bodyHtml) {
  const nav = PAGES.map((p) =>
    `<a href="${p.slug}.html"${p.slug === page.slug ? ' class="active"' : ''}>${p.title}</a>`
  ).join('\n      ');
  return `<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${page.title} | QGIS Live Harness</title>
<style>${CSS}</style>
</head>
<body>
  <nav>
    <div class="site">QGIS Live Harness</div>
    ${nav}
    <a href="${REPO}">GitHub リポジトリ</a>
  </nav>
  <main>
${bodyHtml}
  </main>
${MERMAID}
</body>
</html>
`;
}

mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, '.nojekyll'), '');
for (const page of PAGES) {
  const body = marked(assigned.get(page.slug).join('\n'));
  writeFileSync(join(OUT, `${page.slug}.html`), pageHtml(page, body), 'utf8');
  console.log(`docs/${page.slug}.html (${assigned.get(page.slug).length} sections)`);
}
