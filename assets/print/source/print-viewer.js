/* global React, ReactDOM */
// Screen viewer mount — no JSX. Same artifacts as print-entry.js.
(function () {
  const e = React.createElement;

  function makeSection({ id, label, label2, render }) {
    const wrap = document.createElement("section");
    wrap.id = id;
    wrap.dataset.screenLabel = label2 || label;
    wrap.style.display = "flex";
    wrap.style.flexDirection = "column";
    wrap.style.alignItems = "center";
    wrap.style.gap = "6px";

    const tag = document.createElement("div");
    tag.className = "page-label";
    tag.textContent = label;
    wrap.appendChild(tag);

    const sized = document.createElement("div");
    sized.className = "page-host";
    const inner = document.createElement("div");
    inner.className = "page-wrap";
    inner.style.width = "1700px";
    inner.style.height = "2200px";
    sized.appendChild(inner);
    wrap.appendChild(sized);

    document.getElementById("pages").appendChild(wrap);
    ReactDOM.createRoot(inner).render(render());
    return sized;
  }

  const hosts = [];
  hosts.push(makeSection({
    id: "sec-board", label: "Campfire Board · 1 of 8", label2: "01 Board",
    render: () => e(window.SovBoardA),
  }));
  hosts.push(makeSection({
    id: "sec-mat", label: "Player Mat · 2 of 8", label2: "02 Player Mat",
    render: () => e(window.SovPlayerMat),
  }));
  hosts.push(makeSection({
    id: "sec-qr", label: "Quick Reference · 3 of 8", label2: "03 Quick Ref",
    render: () => e(window.SovQuickRef),
  }));
  hosts.push(makeSection({
    id: "sec-treaty", label: "Treaty Quick-Reference · 4 of 8", label2: "04 Treaty Ref",
    render: () => e(window.SovTreatyQuickRef),
  }));
  hosts.push(makeSection({
    id: "sec-market", label: "Market Board · 5 of 8", label2: "05 Market",
    render: () => e(window.SovMarketBoard),
  }));

  function multiSection(id, label2, builderFn, baseLabel) {
    const arr = builderFn();
    arr.forEach((pageEl, i) => {
      const tag = arr.length > 1 ? `${baseLabel} · sheet ${i + 1}/${arr.length}` : baseLabel;
      hosts.push(makeSection({
        id: i === 0 ? id : `${id}-${i}`,
        label: tag,
        label2: arr.length > 1 ? `${label2} ${i + 1}` : label2,
        render: () => pageEl,
      }));
    });
  }
  multiSection("sec-events", "06 Events", window.SovEventPages, "Event Cards");
  multiSection("sec-deals", "07 Deals", window.SovDealPages, "Deal Cards");
  multiSection("sec-vouchers", "08 Vouchers", window.SovVoucherPages, "Voucher Cards");

  function fit() {
    const target = Math.min((window.innerWidth - 80) / 1700, 0.55);
    document.querySelectorAll(".page-host").forEach((h) => {
      h.style.width = `${1700 * target}px`;
      h.style.height = `${2200 * target}px`;
      const wrap = h.querySelector(".page-wrap");
      if (wrap) wrap.style.transform = `scale(${target})`;
    });
  }
  window.addEventListener("resize", fit);
  requestAnimationFrame(fit);

  const links = document.querySelectorAll("#toc a[data-target]");
  function updateActive() {
    const y = window.scrollY + 120;
    let activeId = null;
    document.querySelectorAll("#pages > section").forEach((sec) => {
      const top = sec.offsetTop;
      if (top <= y) {
        const base = sec.id.split("-").slice(0, 2).join("-");
        activeId = base;
      }
    });
    links.forEach((a) => a.classList.toggle("active", a.dataset.target === activeId));
  }
  window.addEventListener("scroll", updateActive, { passive: true });
  updateActive();
})();
