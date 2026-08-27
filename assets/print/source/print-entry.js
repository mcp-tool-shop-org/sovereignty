/* global React, ReactDOM */
// Production print mount — no JSX. ARTIFACTS registry + settle-after-paint.
(function () {
  const e = React.createElement;
  const ARTIFACTS = [
    { id: "board", render: () => [e(window.SovBoardA)] },
    { id: "mat", render: () => [e(window.SovPlayerMat)] },
    { id: "quickref", render: () => [e(window.SovQuickRef)] },
    { id: "treaty", render: () => [e(window.SovTreatyQuickRef)] },
    { id: "events", render: () => window.SovEventPages() },
    { id: "deals", render: () => window.SovDealPages() },
    { id: "vouchers", render: () => window.SovVoucherPages() },
    { id: "market", render: () => [e(window.SovMarketBoard)] },
  ];

  const params = new URLSearchParams(window.location.search);
  const only = params.get("only");
  const allow = only
    ? new Set(only.split(",").map((s) => s.trim()).filter(Boolean))
    : null;
  const sequence = allow ? ARTIFACTS.filter((a) => allow.has(a.id)) : ARTIFACTS;

  const pages = document.getElementById("pages");
  for (const art of sequence) {
    const elements = art.render();
    elements.forEach((el, i) => {
      const wrap = document.createElement("div");
      wrap.className = "sov-page";
      wrap.dataset.artifact = art.id;
      wrap.dataset.pageIndex = String(i);
      pages.appendChild(wrap);
      ReactDOM.createRoot(wrap).render(el);
    });
  }

  const FACE_SPECS = [
    '400 24px "Cormorant Garamond"',
    '500 24px "Cormorant Garamond"',
    '600 44px "Cormorant Garamond"',
    '700 24px "Cormorant Garamond"',
    'italic 400 16px "Cormorant Garamond"',
    'italic 500 16px "Cormorant Garamond"',
    'italic 600 16px "Cormorant Garamond"',
    '16px "IM Fell English"',
    'italic 16px "IM Fell English"',
    '400 14px "JetBrains Mono"',
    '500 14px "JetBrains Mono"',
  ];

  function nextPaint() {
    return new Promise((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(resolve));
    });
  }

  async function settle() {
    // React 18 createRoot paints asynchronously. Load faces AFTER that paint
    // so Chrome subsets the glyphs actually used (Type0), not a pre-paint empty set.
    await nextPaint();
    if (document.fonts && document.fonts.load) {
      await Promise.all(FACE_SPECS.map((s) => document.fonts.load(s)));
      if (document.fonts.ready) await document.fonts.ready;
    }
    await nextPaint();
    document.body.classList.remove("is-loading");
    document.body.dataset.ready = "true";
  }

  settle();
})();
