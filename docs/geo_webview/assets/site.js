// geo_webview docs — mermaid 図のレンダリング(CDN)
// オフライン時は mermaid コードがそのまま表示される
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
for (const code of document.querySelectorAll('pre > code.language-mermaid')) {
  const div = document.createElement('div');
  div.className = 'mermaid';
  div.textContent = code.textContent;
  code.parentElement.replaceWith(div);
}
await mermaid.run({ querySelector: '.mermaid' });
