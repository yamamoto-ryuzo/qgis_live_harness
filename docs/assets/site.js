// QGIS Live Harness docs — shared behavior
// (mermaid rendering / heading anchors / on-this-page toc / code copy)

// ---- code blocks: wrap <pre> with language label + copy button ----
for (const pre of document.querySelectorAll('main pre')) {
  const code = pre.querySelector('code');
  const m = code && [...code.classList].find((c) => c.startsWith('language-'));
  const lang = m ? m.slice('language-'.length) : '';
  if (lang === 'mermaid') continue;
  const wrap = document.createElement('div');
  wrap.className = 'codeblock';
  pre.parentElement.insertBefore(wrap, pre);
  wrap.appendChild(pre);
  if (lang) {
    const tag = document.createElement('span');
    tag.className = 'lang';
    tag.textContent = lang;
    wrap.appendChild(tag);
  }
  const btn = document.createElement('button');
  btn.className = 'copy';
  btn.type = 'button';
  btn.textContent = 'コピー';
  btn.addEventListener('click', async () => {
    await navigator.clipboard.writeText(pre.textContent.replace(/\n$/, ''));
    btn.textContent = '✓ コピー済';
    setTimeout(() => (btn.textContent = 'コピー'), 1500);
  });
  wrap.appendChild(btn);
}

// ---- tables: horizontal-scroll wrapper ----
for (const table of document.querySelectorAll('main table')) {
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  table.parentElement.insertBefore(wrap, table);
  wrap.appendChild(table);
}

// ---- heading ids + anchors + on-this-page toc ----
const headings = [...document.querySelectorAll('main h2, main h3')];
const used = new Set();
for (const h of headings) {
  if (!h.id) {
    let id = h.textContent.trim().replace(/\s+/g, '-').replace(/[#?&"'<>]/g, '');
    while (used.has(id)) id += '-';
    used.add(id);
    h.id = id;
  }
  const a = document.createElement('a');
  a.className = 'anchor';
  a.href = `#${h.id}`;
  a.textContent = '#';
  h.appendChild(a);
}
const tocEl = document.querySelector('aside.toc');
if (tocEl && headings.length >= 2) {
  const title = document.createElement('div');
  title.className = 'toc-title';
  title.textContent = 'このページの内容';
  tocEl.appendChild(title);
  const links = new Map();
  for (const h of headings) {
    const a = document.createElement('a');
    a.href = `#${h.id}`;
    a.textContent = h.textContent.replace(/#$/, '');
    if (h.tagName === 'H3') a.className = 'lv3';
    tocEl.appendChild(a);
    links.set(h.id, a);
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          links.forEach((a) => a.classList.remove('current'));
          links.get(e.target.id)?.classList.add('current');
        }
      }
    },
    { rootMargin: '0px 0px -75% 0px' },
  );
  headings.forEach((h) => observer.observe(h));
}

// ---- mermaid ----
const mermaidBlocks = document.querySelectorAll('pre > code.language-mermaid');
if (mermaidBlocks.length) {
  const { default: mermaid } = await import(
    'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'
  );
  for (const el of mermaidBlocks) {
    const div = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = el.textContent;
    el.parentElement.replaceWith(div);
  }
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral' });
  await mermaid.run({ querySelector: '.mermaid' });
}
