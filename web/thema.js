// Hell / Dunkel / Automatisch (nach Systemeinstellung). Wird im <head> geladen, damit beim Öffnen nichts aufblitzt.
(function () {
  "use strict";
  const SCHLUESSEL = "aktionenfitness.thema";
  const STUFEN = ["auto", "hell", "dunkel"];
  const ANZEIGE = { auto: ["auto", "Automatisch (wie das System)"], hell: ["hell", "Hell"], dunkel: ["dunkel", "Dunkel"] };
  // Icon aus ikonen.js (wird vor thema.js geladen); ohne ikonen.js: Text
  const symbol = (t) => (window.Ikonen ? window.Ikonen.svg(ANZEIGE[t][0]) : ANZEIGE[t][1]);
  const root = document.documentElement;

  function lesen() {
    try { const t = localStorage.getItem(SCHLUESSEL); return STUFEN.includes(t) ? t : "auto"; } catch { return "auto"; }
  }
  function anwenden(thema) {
    if (thema === "hell") root.dataset.theme = "light";
    else if (thema === "dunkel") root.dataset.theme = "dark";
    else delete root.dataset.theme;
    const dunkel = thema === "dunkel" || (thema === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dunkel ? "#111318" : "#ffffff");
  }
  let thema = lesen();
  anwenden(thema);

  // Umschalter in die Kopfzeile jeder Seite
  document.addEventListener("DOMContentLoaded", () => {
    const kopf = document.querySelector(".kopf__inhalt");
    if (!kopf) return;
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "thema-knopf";
    const zeigen = () => {
      const text = ANZEIGE[thema][1];
      knopf.replaceChildren(symbol(thema));
      knopf.title = `Darstellung: ${text} – tippen zum Wechseln`;
      knopf.setAttribute("aria-label", knopf.title);
    };
    knopf.addEventListener("click", () => {
      thema = STUFEN[(STUFEN.indexOf(thema) + 1) % STUFEN.length];
      try { localStorage.setItem(SCHLUESSEL, thema); } catch { /* privater Modus */ }
      anwenden(thema);
      zeigen();
    });
    zeigen();
    kopf.insertBefore(knopf, kopf.lastElementChild);
    matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => anwenden(thema));
  });
  // Andere Tabs/Seiten übernehmen die Wahl sofort
  window.addEventListener("storage", (e) => {
    if (e.key !== SCHLUESSEL) return;
    thema = lesen();
    anwenden(thema);
    const k = document.querySelector(".thema-knopf");
    if (k) k.replaceChildren(symbol(thema));
  });
})();
