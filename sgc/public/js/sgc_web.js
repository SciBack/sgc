// SGC-UPeU — ajustes de la página de login (textos en español + botón SSO limpio).
// El login.js de Frappe re-renderiza las vistas, así que se reaplica ante cambios del DOM.
(function () {
  function apply() {
    var card = document.querySelector(".login-content");
    if (!card) return;
    document.body.classList.add("sgc-login");

    document.querySelectorAll(".page-card-head-text h4").forEach(function (h) {
      if (h.textContent !== "Sistema de Gestión de la Calidad") {
        h.textContent = "Sistema de Gestión de la Calidad";
      }
    });
    document.querySelectorAll(".page-card-subtitle").forEach(function (s) {
      var t = "Inicia sesión con tu cuenta institucional UPeU";
      if (s.textContent !== t) s.textContent = t;
    });
    document.querySelectorAll("a.btn-keycloak").forEach(function (b) {
      var img = b.querySelector("img");
      if (img) img.remove();
      if (b.textContent.trim() !== "Iniciar sesión con UPeU") {
        b.textContent = "Iniciar sesión con UPeU";
      }
    });
  }

  function start() {
    apply();
    // reaplica ante los re-render de la login page
    var target = document.querySelector(".page-content") || document.body;
    if (window.MutationObserver && target) {
      var obs = new MutationObserver(function () { apply(); });
      obs.observe(target, { childList: true, subtree: true });
      // desconecta tras unos segundos: la login page ya no cambia sola después
      setTimeout(function () { obs.disconnect(); }, 5000);
    }
  }

  if (document.readyState !== "loading") start();
  else document.addEventListener("DOMContentLoaded", start);
})();
