// Schlichte Strich-Icons (24×24, Farbe = Textfarbe). Statt Emojis.
//   Ikonen.svg("wagen")          -> <svg> für dynamisch gebaute Knöpfe
//   <span data-ikon="wagen"></span> in HTML wird beim Laden ersetzt
(function (global) {
  "use strict";
  const PFADE = {
    logo: ["M3 3h18v18H3z", "M7.5 16.5l4.5-8 4.5 8"],
    wagen: ["M3 4h2l2.4 11.2a1 1 0 0 0 1 .8h8.9a1 1 0 0 0 1-.8L20 8H6.2", "M9.5 20.5h.01", "M17 20.5h.01"],
    suche: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M20 20l-4-4"],
    merken: ["M6 3.5h12v17l-6-4.5-6 4.5z"],
    regler: ["M4 7h10", "M18 7h2", "M4 17h4", "M12 17h8", "M16 5v4", "M10 15v4"],
    auto: ["M3 4.5h18v12H3z", "M8 20.5h8", "M12 16.5v4"],
    hell: ["M12 16.5a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9z", "M12 2.5v2", "M12 19.5v2", "M2.5 12h2", "M19.5 12h2",
      "M5.3 5.3l1.4 1.4", "M17.3 17.3l1.4 1.4", "M5.3 18.7l1.4-1.4", "M17.3 6.7l1.4-1.4"],
    dunkel: ["M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"],
    x: ["M6 6l12 12", "M18 6L6 18"],
    kopieren: ["M8.5 8.5h11v11h-11z", "M15.5 8.5v-4h-11v11h4"],
    teilen: ["M12 15V3.5", "M7.5 8L12 3.5 16.5 8", "M5 12.5V20h14v-7.5"],
    plus: ["M12 5v14", "M5 12h14"],
    pfeil: ["M14 4h6v6", "M20 4l-9 9", "M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"],
  };
  const NS = "http://www.w3.org/2000/svg";

  function svg(name, groesse = 18) {
    const s = document.createElementNS(NS, "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("width", groesse);
    s.setAttribute("height", groesse);
    s.setAttribute("aria-hidden", "true");
    s.setAttribute("class", `ikon ikon--${name}`);
    for (const d of PFADE[name] || []) {
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", d);
      s.append(p);
    }
    return s;
  }

  function einsetzen(wurzel = document) {
    wurzel.querySelectorAll("[data-ikon]").forEach((el) => {
      el.replaceWith(svg(el.dataset.ikon, Number(el.dataset.groesse) || 18));
    });
  }

  global.Ikonen = { svg, einsetzen };
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => einsetzen());
    else einsetzen();
  }
})(typeof window !== "undefined" ? window : globalThis);
