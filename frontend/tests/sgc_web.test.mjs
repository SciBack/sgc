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

function createPage({ query = "", fetchImpl, reducedMotion = false } = {}) {
  const dom = new JSDOM(fixture, {
    url: `https://calidad.upeu.edu.pe/login${query}`,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  dom.window.fetch = fetchImpl ?? (() => Promise.reject(new Error("API no disponible")));
  dom.window.matchMedia = () => ({
    matches: reducedMotion,
    media: "(prefers-reduced-motion: reduce)",
    addEventListener() {},
    removeEventListener() {},
  });
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

  assert.equal(dom.window.document.querySelectorAll("#sgc-login-cover").length, 1);
  assert.strictEqual(dom.window.document.querySelector("a.btn-keycloak"), cta);
  assert.equal(cta.href, oauthHref);
  assert.match(cta.href, /state=ORIGINAL$/);
  assert.equal(cta.textContent.trim(), "Ingresar con mi cuenta UPeU");
  assert.notEqual(cta.getAttribute("role"), "alert");
  assert.strictEqual(dom.window.document.querySelector('[role="alert"]'), alert);
  assert.equal(alert.textContent.trim(), "No se pudo completar el acceso.");
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

test("reduced motion no activa autoplay", async (t) => {
  const dom = createPage({ reducedMotion: true });
  t.after(() => closePage(dom));
  dom.window.eval(source);
  dom.window.SGCLogin.start();
  await settle();

  const video = dom.window.document.querySelector("video.sgc-login-video");
  assert.ok(video);
  assert.equal(video.hasAttribute("autoplay"), false);
  assert.equal(video.muted, true);
  assert.equal(video.loop, true);
  assert.equal(video.playsInline, true);
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
