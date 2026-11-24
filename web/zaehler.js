// Besucherzählung mit GoatCounter (https://www.goatcounter.com): keine Cookies, kein lokaler Speicher, keine
// gespeicherten IP-Adressen. Details: datenschutz.html, Abschnitt "Reichweitenmessung".
// Nur auf der veröffentlichten Website – lokal (Doppelklick, Tests) wird nicht gezählt.
// Eigene Besuche ausschließen: einmal https://lp0072007.github.io/AktionenFitness/#toggle-goatcounter öffnen.
(function () {
  "use strict";
  if (location.hostname !== "lp0072007.github.io") return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.dataset.goatcounter = "https://fabianfrouz.goatcounter.com/count";
  document.head.append(s);
})();
