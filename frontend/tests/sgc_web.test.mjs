import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { JSDOM } from "jsdom";

const source = await readFile(new URL("../../sgc/public/js/sgc_web.js", import.meta.url), "utf8");
const oauthHref = "https://keyid.upeu.edu.pe/realms/upeu/protocol/openid-connect/auth?state=ORIGINAL";

const fixture = `<!doctype html>
<html><body data-path="login"><main class="page-content"><section class="login-content">
  <div class="alert alert-danger" role="alert">No se pudo completar el acceso.</div>
  <a class="btn-keycloak" href="${oauthHref}">Ingresar con cuenta institucional</a>
</section></main></body></html>`;

function createMediaQuery(initialMatches = false) {
  let listener = null;
  return {
    matches: initialMatches,
    media: "(prefers-reduced-motion: reduce)",
    addEventListener(type, callback) {
      if (type === "change") listener = callback;
    },
    removeEventListener(type, callback) {
      if (type === "change" && listener === callback) listener = null;
    },
    addListener(callback) {
      listener = callback;
    },
    removeListener(callback) {
      if (listener === callback) listener = null;
    },
    emit(matches) {
      this.matches = matches;
      listener?.({ matches, media: this.media });
    },
  };
}

function createPage({ query = "", fetchImpl, reducedMotion = false, mediaQuery } = {}) {
  const dom = new JSDOM(fixture, {
    url: `https://calidad.upeu.edu.pe/login${query}`,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  dom.window.fetch = fetchImpl ?? (() => Promise.reject(new Error("API no disponible")));
  dom.window.matchMedia = () => mediaQuery ?? createMediaQuery(reducedMotion);
  dom.window.HTMLMediaElement.prototype.play = () => Promise.resolve();
  dom.window.HTMLMediaElement.prototype.pause = () => {};
  dom.window.HTMLMediaElement.prototype.load = () => {};
  return dom;
}

function closePage(dom) {
  dom.window.SGCLogin?.destroy();
  dom.window.close();
}

async function settle() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

test("el montaje es idempotente y conserva los nodos nativos", async (t) => {
  const dom = createPage();
  t.after(() => closePage(dom));
  const cta = dom.window.document.querySelector("a.btn-keycloak");
  const alert = dom.window.document.querySelector('[role="alert"]');

  dom.window.eval(source);
  dom.window.SGCLogin.start();
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const main = dom.window.document.querySelector("main");
  const cover = dom.window.document.querySelector("#sgc-login-cover");
  assert.equal(dom.window.document.querySelectorAll("#sgc-login-cover").length, 1);
  assert.equal(dom.window.document.querySelectorAll("main").length, 1);
  assert.equal(main.contains(cover), true);
  assert.equal(main.contains(cta), true);
  assert.deepEqual(
    [...dom.window.document.querySelectorAll(".sgc-login-stat")].map((node) => node.tagName),
    ["DIV", "DIV", "DIV"],
  );
  assert.strictEqual(dom.window.document.querySelector("a.btn-keycloak"), cta);
  assert.equal(cta.href, oauthHref);
  assert.match(cta.href, /state=ORIGINAL$/);
  assert.equal(cta.textContent.trim(), "Ingresar con mi cuenta UPeU");
  assert.notEqual(cta.getAttribute("role"), "alert");
  assert.strictEqual(dom.window.document.querySelector('[role="alert"]'), alert);
  assert.equal(alert.textContent.trim(), "No se pudo completar el acceso.");
});

test("sin CTA conserva el login nativo y monta cuando Frappe publica el enlace", async (t) => {
  const dom = createPage();
  t.after(() => closePage(dom));
  const document = dom.window.document;
  const card = document.querySelector(".login-content");
  document.querySelector("a.btn-keycloak").remove();

  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  assert.equal(document.querySelector("#sgc-login-cover"), null);
  assert.equal(document.body.classList.contains("sgc-login"), false);
  assert.equal(document.querySelectorAll("main").length, 1);
  assert.strictEqual(document.querySelector("main .login-content"), card);

  const cta = document.createElement("a");
  cta.className = "btn-keycloak";
  cta.href = oauthHref;
  cta.textContent = "Ingresar con cuenta institucional";
  card.appendChild(cta);
  await settle();

  assert.equal(document.querySelectorAll("#sgc-login-cover").length, 1);
  assert.equal(document.body.classList.contains("sgc-login"), true);
  assert.equal(document.querySelectorAll("main").length, 1);
  assert.equal(document.querySelector("main").contains(document.querySelector("#sgc-login-cover")), true);
  assert.equal(document.querySelector("main").contains(card), true);
  assert.strictEqual(document.querySelector(".sgc-login-card-slot a.btn-keycloak"), cta);
  assert.equal(cta.href, oauthHref);
});

test("un re-render de Frappe reemplaza la tarjeta presentada con los nodos nuevos", async (t) => {
  const dom = createPage();
  t.after(() => closePage(dom));
  const document = dom.window.document;
  const oldCta = document.querySelector("a.btn-keycloak");

  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const nuevaTarjeta = document.createElement("section");
  nuevaTarjeta.className = "login-content";
  const nuevaAlerta = document.createElement("div");
  nuevaAlerta.className = "alert alert-danger";
  nuevaAlerta.setAttribute("role", "alert");
  nuevaAlerta.textContent = "La sesión institucional expiró.";
  const nuevoCta = document.createElement("a");
  nuevoCta.className = "btn-keycloak";
  nuevoCta.href = oauthHref.replace("state=ORIGINAL", "state=NEW");
  nuevoCta.textContent = "Reintentar acceso institucional";
  nuevaTarjeta.append(nuevaAlerta, nuevoCta);
  document.querySelector(".page-content").replaceChildren(nuevaTarjeta);
  await settle();

  const slot = document.querySelector(".sgc-login-card-slot");
  const main = document.querySelector("main");
  const cover = document.querySelector("#sgc-login-cover");
  assert.equal(document.querySelectorAll("#sgc-login-cover").length, 1);
  assert.equal(document.querySelectorAll("main").length, 1);
  assert.equal(main.contains(cover), true);
  assert.equal(main.contains(nuevaTarjeta), true);
  assert.strictEqual(slot.querySelector("a.btn-keycloak"), nuevoCta);
  assert.equal(main.contains(nuevoCta), true);
  assert.equal(nuevoCta.href, oauthHref.replace("state=ORIGINAL", "state=NEW"));
  assert.match(nuevoCta.href, /state=NEW$/);
  assert.strictEqual(slot.querySelector('[role="alert"]'), nuevaAlerta);
  assert.equal(nuevaAlerta.textContent, "La sesión institucional expiró.");
  assert.equal(slot.contains(oldCta), false);
  assert.equal(oldCta.isConnected, false);
});

test("un re-render conserva cover, video, metricas y una sola carga API", async (t) => {
  const payload = {
    programas: { activos: 22, sedes: 3 },
    autoevaluaciones: { activas: 6, total: 10, pct: 60 },
    evidencias: { vigentes: 8, con_vigencia: 10, pct: 80 },
  };
  let fetchCalls = 0;
  const dom = createPage({
    fetchImpl: async () => {
      fetchCalls += 1;
      return { ok: true, json: async () => ({ message: payload }) };
    },
  });
  t.after(() => closePage(dom));
  const document = dom.window.document;

  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const cover = document.querySelector("#sgc-login-cover");
  const video = cover.querySelector("video.sgc-login-video");
  assert.deepEqual(
    [...cover.querySelectorAll("[data-metric-value]")].map((node) => node.textContent),
    ["22", "6", "80%"],
  );

  const nuevaTarjeta = document.createElement("section");
  nuevaTarjeta.className = "login-content";
  const nuevaAlerta = document.createElement("div");
  nuevaAlerta.setAttribute("role", "alert");
  nuevaAlerta.textContent = "Se requiere un nuevo acceso.";
  const nuevoCta = document.createElement("a");
  nuevoCta.className = "btn-keycloak";
  nuevoCta.href = oauthHref.replace("state=ORIGINAL", "state=NEW");
  nuevaTarjeta.append(nuevaAlerta, nuevoCta);
  document.querySelector(".page-content").replaceChildren(nuevaTarjeta);
  await settle();

  const main = document.querySelector("main");
  assert.equal(document.querySelectorAll("#sgc-login-cover").length, 1);
  assert.strictEqual(document.querySelector("#sgc-login-cover"), cover);
  assert.strictEqual(cover.querySelector("video.sgc-login-video"), video);
  assert.equal(main.contains(cover), true);
  assert.equal(main.contains(nuevaTarjeta), true);
  assert.strictEqual(cover.querySelector("a.btn-keycloak"), nuevoCta);
  assert.equal(nuevoCta.href, oauthHref.replace("state=ORIGINAL", "state=NEW"));
  assert.strictEqual(cover.querySelector('[role="alert"]'), nuevaAlerta);
  assert.deepEqual(
    [...cover.querySelectorAll("[data-metric-value]")].map((node) => node.textContent),
    ["22", "6", "80%"],
  );
  assert.equal(fetchCalls, 1);
});

test("login_local deja intacto el login de emergencia", async (t) => {
  const dom = createPage({ query: "?login_local=1" });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  assert.equal(dom.window.document.querySelector("#sgc-login-cover"), null);
  assert.equal(dom.window.document.body.classList.contains("sgc-login"), false);
});

test("un fallo de red conserva SSO visible y metricas fallback", async (t) => {
  const dom = createPage({ fetchImpl: () => Promise.reject(new Error("offline")) });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const cta = dom.window.document.querySelector("a.btn-keycloak");
  assert.ok(cta);
  assert.notEqual(cta.hidden, true);
  assert.deepEqual(
    [...dom.window.document.querySelectorAll("[data-metric-value]")].map((node) => node.textContent),
    ["—", "—", "—"],
  );
});

test("una respuesta valida pinta las tres metricas", async (t) => {
  const payload = {
    programas: { activos: 22, sedes: 7 },
    autoevaluaciones: { activas: 6, total: 10, pct: 60 },
    evidencias: { vigentes: 8, con_vigencia: 10, pct: 80 },
  };
  const dom = createPage({
    fetchImpl: async () => ({ ok: true, json: async () => ({ message: payload }) }),
  });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  assert.deepEqual(
    [...dom.window.document.querySelectorAll("[data-metric-value]")].map((node) => node.textContent),
    ["22", "6", "80%"],
  );
  assert.equal(dom.window.document.querySelectorAll('[data-metric="programas"] .sgc-login-stat-dot').length, 6);
  assert.match(dom.window.document.querySelector('[data-metric="programas"] [data-metric-text]').textContent, /7 sedes/);
});

test("evidencias sin control no generan NaN ni una barra invalida", async (t) => {
  const payload = {
    programas: { activos: 1, sedes: 1 },
    autoevaluaciones: { activas: 0, total: 0, pct: null },
    evidencias: { vigentes: 0, con_vigencia: 0, pct: null },
  };
  const dom = createPage({
    fetchImpl: async () => ({ ok: true, json: async () => ({ message: payload }) }),
  });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const evidencia = dom.window.document.querySelector('[data-metric="evidencias"]');
  assert.equal(evidencia.querySelector("[data-metric-value]").textContent, "—");
  assert.equal(evidencia.querySelector("[data-metric-text]").textContent, "sin control de vigencia");
  assert.equal(evidencia.querySelector(".sgc-login-stat-bar-fill").style.transform, "scaleX(0)");
  assert.doesNotMatch(dom.window.document.body.textContent, /NaN|undefined/);
  assert.equal(
    dom.window.document.querySelector('[data-metric="autoevaluaciones"] [data-metric-text]').textContent,
    "sin autoevaluaciones registradas",
  );
});

test("evidencias contradictorias no presentan porcentaje incoherente", async (t) => {
  const payload = {
    programas: { activos: 1, sedes: 1 },
    autoevaluaciones: { activas: 1, total: 2, pct: 50 },
    evidencias: { vigentes: 8, con_vigencia: 10, pct: 20 },
  };
  const dom = createPage({
    fetchImpl: async () => ({ ok: true, json: async () => ({ message: payload }) }),
  });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const evidencia = dom.window.document.querySelector('[data-metric="evidencias"]');
  assert.equal(evidencia.querySelector("[data-metric-value]").textContent, "—");
  assert.equal(evidencia.querySelector("[data-metric-text]").textContent, "Datos no disponibles");
  assert.equal(evidencia.querySelector(".sgc-login-stat-bar-fill").style.transform, "scaleX(0)");
  assert.doesNotMatch(evidencia.textContent, /20%|80%/);
});

test("reduced motion no activa autoplay", async (t) => {
  const dom = createPage({ reducedMotion: true });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const video = dom.window.document.querySelector("video.sgc-login-video");
  assert.ok(video);
  assert.equal(video.hasAttribute("autoplay"), false);
  assert.equal(video.hasAttribute("src"), false);
  assert.equal(
    video.getAttribute("poster"),
    "/assets/sgc/media/login/oficinas-dti-poster.jpg",
  );
});

test("un cambio dinamico de movimiento detiene y restaura el video", async (t) => {
  const mediaQuery = createMediaQuery(false);
  const dom = createPage({ mediaQuery });
  t.after(() => closePage(dom));
  let playCalls = 0;
  let pauseCalls = 0;
  let loadCalls = 0;
  dom.window.HTMLMediaElement.prototype.play = () => {
    playCalls += 1;
    return Promise.resolve();
  };
  dom.window.HTMLMediaElement.prototype.pause = () => {
    pauseCalls += 1;
  };
  dom.window.HTMLMediaElement.prototype.load = () => {
    loadCalls += 1;
  };

  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const video = dom.window.document.querySelector("video.sgc-login-video");
  assert.equal(video.getAttribute("src"), "/assets/sgc/media/login/oficinas-dti.mp4");
  assert.equal(video.hasAttribute("autoplay"), true);
  assert.equal(playCalls, 1);

  mediaQuery.emit(true);
  await settle();
  assert.equal(video.hasAttribute("src"), false);
  assert.equal(video.hasAttribute("autoplay"), false);
  assert.equal(pauseCalls, 1);
  assert.equal(loadCalls, 1);

  mediaQuery.emit(false);
  await settle();
  assert.equal(video.getAttribute("src"), "/assets/sgc/media/login/oficinas-dti.mp4");
  assert.equal(video.hasAttribute("autoplay"), true);
  assert.equal(playCalls, 2);
});

test("datos malformados usan fallback sin inyectar HTML ni bloquear SSO", async (t) => {
  const payload = {
    programas: { activos: "<img src=x onerror=alert(1)>", sedes: -2 },
    autoevaluaciones: { activas: 1, total: 4, pct: 400 },
    evidencias: { vigentes: {}, con_vigencia: 1, pct: "80" },
  };
  const dom = createPage({
    fetchImpl: async () => ({ ok: true, json: async () => ({ message: payload }) }),
  });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  assert.ok(dom.window.document.querySelector("a.btn-keycloak"));
  assert.equal(dom.window.document.querySelector("img[src=x]"), null);
  assert.doesNotMatch(dom.window.document.body.textContent, /NaN|undefined|<img/);
  assert.deepEqual(
    [...dom.window.document.querySelectorAll("[data-metric-value]")].map((node) => node.textContent),
    ["—", "—", "—"],
  );
});
