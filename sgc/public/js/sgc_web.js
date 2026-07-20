// SGC UPeU — mejora progresiva del login nativo de Frappe.
(function (window) {
  "use strict";

  if (window.SGCLogin && window.SGCLogin.version === 1) {
    window.SGCLogin.start();
    return;
  }

  var document = window.document;
  var estado = {
    observer: null,
    observerTimer: null,
    metricasSolicitadas: false,
  };

  function crearElemento(tag, clase, texto) {
    var elemento = document.createElement(tag);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function esLoginLocal() {
    return new URLSearchParams(window.location.search).get("login_local") === "1";
  }

  function esPaginaLogin() {
    return document.body && document.body.getAttribute("data-path") === "login";
  }

  function crearStat(nombre, etiqueta, tipo) {
    var stat = crearElemento("article", "sgc-login-stat");
    stat.setAttribute("data-metric", nombre);

    var label = crearElemento("p", "sgc-login-stat-label", etiqueta);
    var value = crearElemento("strong", "sgc-login-stat-value", "—");
    value.setAttribute("data-metric-value", "");
    var text = crearElemento("p", "sgc-login-stat-text", "Datos no disponibles");
    text.setAttribute("data-metric-text", "");
    var visual;

    if (tipo === "dots") {
      visual = crearElemento("div", "sgc-login-stat-dots");
    } else {
      visual = crearElemento("div", "sgc-login-stat-bar");
      var fill = crearElemento("span", "sgc-login-stat-bar-fill");
      fill.style.transform = "scaleX(0)";
      visual.appendChild(fill);
    }
    visual.setAttribute("aria-hidden", "true");

    stat.appendChild(label);
    stat.appendChild(value);
    stat.appendChild(text);
    stat.appendChild(visual);
    return stat;
  }

  function crearEstructura() {
    var existente = document.getElementById("sgc-login-cover");
    if (existente) return existente;

    var cover = crearElemento("div", "sgc-login-cover");
    cover.id = "sgc-login-cover";

    var video = crearElemento("video", "sgc-login-video");
    video.setAttribute("aria-hidden", "true");
    video.setAttribute("src", "/assets/sgc/media/login/oficinas-dti.mp4");
    video.setAttribute("poster", "/assets/sgc/media/login/oficinas-dti-poster.jpg");
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.setAttribute("muted", "");
    video.setAttribute("loop", "");
    video.setAttribute("playsinline", "");
    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduceMotion) video.setAttribute("autoplay", "");
    cover.appendChild(video);

    ["vertical", "horizontal", "radial"].forEach(function (tipo) {
      var veil = crearElemento("div", "sgc-login-veil sgc-login-veil--" + tipo);
      veil.setAttribute("aria-hidden", "true");
      cover.appendChild(veil);
    });

    var header = crearElemento("header", "sgc-login-header");
    var logo = crearElemento("img", "sgc-login-logo");
    logo.src = "/assets/sgc/media/login/upeu-logo-2026-white.svg";
    logo.alt = "Universidad Peruana Unión";
    var separador = crearElemento("span", "sgc-login-header-separator");
    separador.setAttribute("aria-hidden", "true");
    header.appendChild(logo);
    header.appendChild(separador);
    header.appendChild(crearElemento("span", "sgc-login-product", "SGC UPeU"));
    cover.appendChild(header);

    var layout = crearElemento("main", "sgc-login-layout");
    var hero = crearElemento("section", "sgc-login-hero");
    hero.appendChild(crearElemento("p", "sgc-login-eyebrow", "Dirección de Gestión de la Calidad"));
    hero.appendChild(crearElemento("h1", "sgc-login-title", "Calidad que se demuestra."));
    hero.appendChild(
      crearElemento(
        "p",
        "sgc-login-support",
        "Acreditación, evidencias y mejora continua — conectadas, trazables y medibles.",
      ),
    );

    var stats = crearElemento("div", "sgc-login-stats");
    stats.appendChild(crearStat("programas", "Programas académicos", "dots"));
    stats.appendChild(crearStat("autoevaluaciones", "Autoevaluaciones activas", "bar"));
    stats.appendChild(crearStat("evidencias", "Evidencias vigentes", "bar"));
    hero.appendChild(stats);
    layout.appendChild(hero);

    var cardSlot = crearElemento("section", "sgc-login-card-slot");
    cardSlot.setAttribute("aria-label", "Acceso al Sistema de Gestión de la Calidad");
    layout.appendChild(cardSlot);
    cover.appendChild(layout);

    cover.appendChild(
      crearElemento(
        "footer",
        "sgc-login-footer",
        "© 2026 SGC UPeU · Universidad Peruana Unión · Dirección de Gestión de la Calidad",
      ),
    );
    document.body.insertBefore(cover, document.body.firstChild);
    return cover;
  }

  function adaptarTarjeta(card) {
    if (!card) return false;
    var slot = document.querySelector(".sgc-login-card-slot");
    if (!slot) return false;

    card.classList.add("sgc-login-card");
    if (!card.querySelector("[data-sgc-login-intro]")) {
      var intro = crearElemento("div", "sgc-login-card-intro");
      intro.setAttribute("data-sgc-login-intro", "");
      intro.appendChild(crearElemento("p", "sgc-login-card-brand", "SGC"));
      intro.appendChild(crearElemento("h2", "sgc-login-card-title", "Bienvenido al SGC"));
      intro.appendChild(
        crearElemento(
          "p",
          "sgc-login-card-copy",
          "Accede con tu identidad institucional para continuar.",
        ),
      );
      intro.appendChild(crearElemento("span", "sgc-login-card-accent"));
      card.insertBefore(intro, card.firstChild);
    }

    var cta = card.querySelector("a.btn-keycloak");
    if (!cta) return false;
    if (cta.textContent.trim() !== "Ingresar con mi cuenta UPeU") {
      cta.textContent = "Ingresar con mi cuenta UPeU";
    }
    cta.classList.add("sgc-login-cta");
    cta.removeAttribute("role");

    if (!card.querySelector("[data-sgc-login-guide]")) {
      var guide = crearElemento("a", "sgc-login-guide", "Guía de inicio");
      guide.href = "https://sciback.github.io/sgc/manual-uso/primeros-pasos/";
      guide.setAttribute("data-sgc-login-guide", "");
      card.appendChild(guide);
    }

    if (card.parentNode !== slot) {
      var anterior = slot.querySelector(".sgc-login-card");
      if (anterior && anterior !== card) anterior.remove();
      slot.appendChild(card);
    }
    return true;
  }

  function esEnteroNoNegativo(valor) {
    return Number.isFinite(valor) && Number.isInteger(valor) && valor >= 0;
  }

  function esPorcentaje(valor) {
    return esEnteroNoNegativo(valor) && valor <= 100;
  }

  function obtenerStat(nombre) {
    return document.querySelector('[data-metric="' + nombre + '"]');
  }

  function fallbackStat(nombre, texto) {
    var stat = obtenerStat(nombre);
    if (!stat) return;
    stat.querySelector("[data-metric-value]").textContent = "—";
    stat.querySelector("[data-metric-text]").textContent = texto || "Datos no disponibles";
    var fill = stat.querySelector(".sgc-login-stat-bar-fill");
    if (fill) fill.style.transform = "scaleX(0)";
    var dots = stat.querySelector(".sgc-login-stat-dots");
    if (dots) {
      while (dots.firstChild) dots.removeChild(dots.firstChild);
    }
  }

  function activarFallback() {
    fallbackStat("programas");
    fallbackStat("autoevaluaciones");
    fallbackStat("evidencias");
  }

  function pintarProgramas(data) {
    if (!data || !esEnteroNoNegativo(data.activos) || !esEnteroNoNegativo(data.sedes)) {
      fallbackStat("programas");
      return;
    }
    var stat = obtenerStat("programas");
    stat.querySelector("[data-metric-value]").textContent = String(data.activos);
    stat.querySelector("[data-metric-text]").textContent = "en " + data.sedes + (data.sedes === 1 ? " sede" : " sedes");
    var dots = stat.querySelector(".sgc-login-stat-dots");
    while (dots.firstChild) dots.removeChild(dots.firstChild);
    for (var indice = 0; indice < Math.min(data.sedes, 6); indice += 1) {
      dots.appendChild(crearElemento("span", "sgc-login-stat-dot"));
    }
  }

  function pintarAutoevaluaciones(data) {
    if (
      !data ||
      !esEnteroNoNegativo(data.activas) ||
      !esEnteroNoNegativo(data.total) ||
      data.activas > data.total ||
      (data.total === 0 ? data.pct !== null : !esPorcentaje(data.pct))
    ) {
      fallbackStat("autoevaluaciones");
      return;
    }
    var stat = obtenerStat("autoevaluaciones");
    stat.querySelector("[data-metric-value]").textContent = String(data.activas);
    var proporcion = data.total === 0 ? 0 : data.activas / data.total;
    stat.querySelector("[data-metric-text]").textContent =
      data.total === 0
        ? "sin autoevaluaciones registradas"
        : data.activas + " de " + data.total + " activas";
    stat.querySelector(".sgc-login-stat-bar-fill").style.transform = "scaleX(" + proporcion + ")";
  }

  function pintarEvidencias(data) {
    if (
      !data ||
      !esEnteroNoNegativo(data.vigentes) ||
      !esEnteroNoNegativo(data.con_vigencia) ||
      data.vigentes > data.con_vigencia ||
      (data.pct !== null && !esPorcentaje(data.pct))
    ) {
      fallbackStat("evidencias");
      return;
    }
    var stat = obtenerStat("evidencias");
    if (data.pct === null) {
      stat.querySelector("[data-metric-value]").textContent = "—";
      stat.querySelector("[data-metric-text]").textContent = "sin control de vigencia";
      stat.querySelector(".sgc-login-stat-bar-fill").style.transform = "scaleX(0)";
      return;
    }
    stat.querySelector("[data-metric-value]").textContent = data.pct + "%";
    stat.querySelector("[data-metric-text]").textContent =
      data.vigentes + " de " + data.con_vigencia + " vigentes";
    stat.querySelector(".sgc-login-stat-bar-fill").style.transform = "scaleX(" + data.pct / 100 + ")";
  }

  function pintarMetricas(payload) {
    if (!payload || typeof payload !== "object") {
      activarFallback();
      return;
    }
    pintarProgramas(payload.programas);
    pintarAutoevaluaciones(payload.autoevaluaciones);
    pintarEvidencias(payload.evidencias);
  }

  async function cargarMetricas() {
    if (estado.metricasSolicitadas) return;
    estado.metricasSolicitadas = true;
    try {
      var signal = typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(4000) : undefined;
      var response = await window.fetch("/api/method/sgc.login_portada.metricas_portada", {
        signal: signal,
      });
      if (!response.ok) throw new Error("Respuesta de métricas no válida");
      var json = await response.json();
      pintarMetricas(json && json.message);
    } catch (error) {
      activarFallback();
    }
  }

  function aplicar() {
    if (esLoginLocal() || !esPaginaLogin()) return;
    document.body.classList.add("sgc-login");
    crearEstructura();
    adaptarTarjeta(document.querySelector(".login-content"));
  }

  function detenerObserver() {
    if (estado.observer) estado.observer.disconnect();
    if (estado.observerTimer) window.clearTimeout(estado.observerTimer);
    estado.observer = null;
    estado.observerTimer = null;
  }

  function start() {
    if (esLoginLocal() || !esPaginaLogin()) return;
    aplicar();
    cargarMetricas();
    detenerObserver();
    if (window.MutationObserver && document.body) {
      estado.observer = new window.MutationObserver(function () {
        aplicar();
      });
      estado.observer.observe(document.body, { childList: true, subtree: true });
      estado.observerTimer = window.setTimeout(detenerObserver, 5000);
    }
  }

  window.SGCLogin = {
    version: 1,
    esLoginLocal: esLoginLocal,
    crearEstructura: crearEstructura,
    adaptarTarjeta: adaptarTarjeta,
    cargarMetricas: cargarMetricas,
    pintarMetricas: pintarMetricas,
    activarFallback: activarFallback,
    start: start,
    destroy: detenerObserver,
  };

  if (document.readyState !== "loading") start();
  else document.addEventListener("DOMContentLoaded", start, { once: true });
})(window);
