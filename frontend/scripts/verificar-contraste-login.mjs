#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import postcss from "postcss";

const rutas = {
  core: fileURLToPath(
    new URL("../../sgc/public/css/sciback_core.css", import.meta.url),
  ),
  tema: fileURLToPath(
    new URL("../../sgc/public/css/themes/upeu.css", import.meta.url),
  ),
  login: fileURLToPath(
    new URL("../../sgc/public/css/sgc_web.css", import.meta.url),
  ),
};

const leerCss = (archivo) => {
  try {
    return readFileSync(archivo, "utf8");
  } catch (error) {
    console.error(`✗ No se pudo leer ${archivo}: ${error.message}`);
    process.exit(2);
  }
};

const tokens = new Map();
for (const archivo of [rutas.core, rutas.tema]) {
  let raiz;
  try {
    raiz = postcss.parse(leerCss(archivo), { from: archivo });
  } catch (error) {
    console.error(`✗ No se pudo analizar ${archivo}: ${error.message}`);
    process.exit(2);
  }
  raiz.walkRules(":root", (regla) => {
    regla.walkDecls(/^--color-/, (decl) =>
      tokens.set(decl.prop, decl.value.trim()),
    );
  });
}

const normalizarHex = (valor) => {
  const hex = valor.toLowerCase();
  if (/^#[0-9a-f]{6}$/.test(hex)) return hex;
  if (/^#[0-9a-f]{3}$/.test(hex)) {
    return `#${[...hex.slice(1)].map((canal) => canal + canal).join("")}`;
  }
  return null;
};
const sinImportant = (valor) => valor.replace(/\s*!important\s*$/i, "").trim();
const resolver = (valor, visitados = new Set()) => {
  const limpio = sinImportant(valor);
  const hex = normalizarHex(limpio);
  if (hex) return hex;
  const referencia = limpio.match(/^var\(\s*(--color-[\w-]+)\s*\)$/);
  if (!referencia || visitados.has(referencia[1]) || !tokens.has(referencia[1]))
    return null;
  visitados.add(referencia[1]);
  return resolver(tokens.get(referencia[1]), visitados);
};
const extraerColor = (decl) => {
  if (!decl) return null;
  const valor = sinImportant(decl.value);
  const directo = resolver(valor);
  if (directo) return directo;
  const color = valor.match(
    /(var\(\s*--color-[\w-]+\s*\)|#[0-9a-fA-F]{3,6})\s*$/,
  )?.[1];
  return color ? resolver(color) : null;
};
const luminancia = (hex) => {
  const rgb = [1, 3, 5].map(
    (inicio) => Number.parseInt(hex.slice(inicio, inicio + 2), 16) / 255,
  );
  const lineal = (canal) =>
    canal <= 0.04045 ? canal / 12.92 : ((canal + 0.055) / 1.055) ** 2.4;
  return (
    0.2126 * lineal(rgb[0]) + 0.7152 * lineal(rgb[1]) + 0.0722 * lineal(rgb[2])
  );
};
const contraste = (a, b) => {
  const [alta, baja] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (alta + 0.05) / (baja + 0.05);
};

const selectoresAuditados = new Set([
  ".sgc-login-cta",
  ".sgc-login-card .btn-keycloak",
  ".sgc-login-cta:hover",
  ".sgc-login-card .btn-keycloak:hover",
  ".sgc-login-cta:focus-visible",
  ".sgc-login-card .btn-keycloak:focus-visible",
  ".sgc-login-guide",
  ".sgc-login-guide:hover",
  ".sgc-login-guide:focus-visible",
]);
const propiedadesCromaticas = new Set([
  "background",
  "background-color",
  "border",
  "color",
  "outline",
]);

const auditar = (css, { emitir = true } = {}) => {
  let raiz;
  try {
    raiz = postcss.parse(css, { from: rutas.login });
  } catch (error) {
    return { fallos: 1, mensajes: [`CSS inválido: ${error.message}`] };
  }

  let fallos = 0;
  const mensajes = [];
  const reportar = (ok, mensaje) => {
    if (!ok) fallos += 1;
    mensajes.push(`${ok ? "✓" : "✗"} ${mensaje}`);
  };
  const declaracionExacta = (nombre, propiedad) => {
    const encontradas = [];
    raiz.walkRules((regla) => {
      if (!regla.selectors?.includes(nombre)) return;
      for (const nodo of regla.nodes ?? []) {
        if (nodo.type === "decl" && nodo.prop === propiedad)
          encontradas.push(nodo);
      }
    });
    if (encontradas.length !== 1) {
      reportar(
        false,
        `${nombre} debe declarar ${propiedad} exactamente una vez; se encontraron ${encontradas.length}.`,
      );
      return null;
    }
    return encontradas[0];
  };
  const exigirValor = (selector, propiedad, esperado, etiqueta) => {
    const decl = declaracionExacta(selector, propiedad);
    const actual = decl ? sinImportant(decl.value).toLowerCase() : null;
    reportar(
      actual === esperado,
      `${etiqueta}: ${actual ?? "declaración ausente"}; esperado ${esperado}.`,
    );
    return decl;
  };

  raiz.walkRules((regla) => {
    const afectaColor = (regla.nodes ?? []).some(
      (nodo) => nodo.type === "decl" && propiedadesCromaticas.has(nodo.prop),
    );
    if (!afectaColor) return;
    for (const nombre of regla.selectors ?? []) {
      const afectaControl = [
        ".sgc-login-cta",
        ".btn-keycloak",
        ".sgc-login-guide",
      ].some((objetivo) => nombre.includes(objetivo));
      if (afectaControl && !selectoresAuditados.has(nombre)) {
        reportar(false, `Override cromático no auditado para ${nombre}.`);
      }
    }
  });

  const fondoTarjeta = exigirValor(
    ".sgc-login-card",
    "background",
    "#ffffff",
    "Superficie de tarjeta",
  );
  const bordeTarjeta = exigirValor(
    ".sgc-login-card",
    "border",
    "1px solid var(--color-marca-primaria-400)",
    "Borde de tarjeta",
  );
  const titulo = exigirValor(
    ".sgc-login-card-title",
    "color",
    "#17253a",
    "Título de tarjeta",
  );
  const copia = exigirValor(
    ".sgc-login-card-copy",
    "color",
    "#53657b",
    "Copy de tarjeta",
  );

  const fondosCta = [];
  const textosCta = [];
  for (const selector of [".sgc-login-cta", ".sgc-login-card .btn-keycloak"]) {
    fondosCta.push(
      exigirValor(
        selector,
        "background",
        "var(--color-marca-primaria-700)",
        `Fondo base ${selector}`,
      ),
    );
    textosCta.push(
      exigirValor(
        selector,
        "color",
        "var(--color-sobre-marca-primaria)",
        `Texto base ${selector}`,
      ),
    );
  }

  const fondosHover = [];
  const textosHover = [];
  for (const selector of [
    ".sgc-login-cta:hover",
    ".sgc-login-card .btn-keycloak:hover",
  ]) {
    fondosHover.push(
      exigirValor(
        selector,
        "background",
        "var(--color-marca-primaria-600)",
        `Fondo hover ${selector}`,
      ),
    );
    textosHover.push(
      exigirValor(
        selector,
        "color",
        "var(--color-sobre-marca-primaria)",
        `Texto hover ${selector}`,
      ),
    );
  }

  const guia = exigirValor(
    ".sgc-login-guide",
    "color",
    "var(--color-marca-primaria-700)",
    "Texto base de guía",
  );
  const guiaHover = exigirValor(
    ".sgc-login-guide:hover",
    "color",
    "var(--color-marca-primaria-600)",
    "Texto hover de guía",
  );

  const outlines = [];
  for (const selector of [
    ".sgc-login-cta:focus-visible",
    ".sgc-login-card .btn-keycloak:focus-visible",
    ".sgc-login-guide:focus-visible",
  ]) {
    outlines.push(
      exigirValor(
        selector,
        "outline",
        "3px solid var(--color-marca-primaria-700)",
        `Focus ${selector}`,
      ),
    );
  }

  const esperadosSobreFotografia = [
    [".sgc-login-header", "color", "var(--color-sobre-marca-primaria)"],
    [".sgc-login-eyebrow", "color", "var(--color-sobre-marca-primaria)"],
    [".sgc-login-title", "color", "var(--color-sobre-marca-primaria)"],
    [".sgc-login-support", "color", "rgba(255, 255, 255, 0.9)"],
    [".sgc-login-stat", "background", "rgba(0, 42, 84, 0.58)"],
    [".sgc-login-stat-label", "color", "rgba(255, 255, 255, 0.82)"],
    [".sgc-login-stat-text", "color", "rgba(255, 255, 255, 0.82)"],
    [".sgc-login-stat-value", "color", "var(--color-sobre-marca-primaria)"],
    [".sgc-login-footer", "color", "rgba(255, 255, 255, 0.78)"],
  ];
  for (const [selector, propiedad, esperado] of esperadosSobreFotografia) {
    exigirValor(
      selector,
      propiedad,
      esperado,
      `Contrato translúcido ${selector}`,
    );
  }

  const fondo = extraerColor(fondoTarjeta);
  const pruebas = [
    ["título de tarjeta", extraerColor(titulo), fondo, 4.5],
    ["copy de tarjeta", extraerColor(copia), fondo, 4.5],
    ["borde de tarjeta", extraerColor(bordeTarjeta), fondo, 3],
    ...fondosCta.map((decl, indice) => [
      `CTA base ${indice + 1}`,
      extraerColor(textosCta[indice]),
      extraerColor(decl),
      4.5,
    ]),
    ...fondosHover.map((decl, indice) => [
      `CTA hover ${indice + 1}`,
      extraerColor(textosHover[indice]),
      extraerColor(decl),
      4.5,
    ]),
    ["guía base", extraerColor(guia), fondo, 4.5],
    ["guía hover", extraerColor(guiaHover), fondo, 4.5],
    ...outlines.map((decl, indice) => [
      `focus ${indice + 1}`,
      extraerColor(decl),
      fondo,
      3,
    ]),
  ];
  for (const [nombre, frente, fondoPrueba, minimo] of pruebas) {
    if (!frente || !fondoPrueba) {
      reportar(
        false,
        `${nombre}: no se pudieron resolver los colores aplicados.`,
      );
      continue;
    }
    const ratio = contraste(frente, fondoPrueba);
    reportar(
      ratio >= minimo,
      `${nombre}: ${frente} / ${fondoPrueba} = ${ratio.toFixed(2)}:1 (mínimo ${minimo}:1).`,
    );
  }

  const dorados = new Set(
    [...tokens.entries()]
      .filter(([token]) => token.startsWith("--color-marca-secundaria-"))
      .map(([, valor]) => resolver(valor)),
  );
  raiz.walkDecls("color", (decl) => {
    if (
      decl.value.includes("--color-marca-secundaria-") ||
      dorados.has(resolver(decl.value))
    ) {
      reportar(
        false,
        `${rutas.login}:${decl.source?.start?.line ?? 1} usa dorado como tinta normal.`,
      );
    }
  });

  if (emitir) mensajes.forEach((mensaje) => console.log(mensaje));
  return { fallos, mensajes };
};

const cssLogin = leerCss(rutas.login);
const resultado = auditar(cssLogin);
if (resultado.fallos) process.exit(1);

const canarios = [
  [
    "hover de bajo contraste",
    cssLogin.replace(
      "background: var(--color-marca-primaria-600) !important;",
      "background: var(--color-marca-primaria-50) !important;",
    ),
  ],
  [
    "override más específico del CTA",
    `${cssLogin}\nbody.sgc-login .sgc-login-cta { color: #ffffff; }\n`,
  ],
  [
    "focus sin contraste de componente",
    cssLogin.replace(
      "outline: 3px solid var(--color-marca-primaria-700);",
      "outline: 3px solid var(--color-marca-secundaria-400);",
    ),
  ],
];
for (const [nombre, cssInvalido] of canarios) {
  if (
    cssInvalido === cssLogin ||
    auditar(cssInvalido, { emitir: false }).fallos === 0
  ) {
    console.error(`✗ Canary inválido: ${nombre} no fue rechazado.`);
    process.exit(1);
  }
}

console.log(
  "✓ Pares auditables de tarjeta, CTA, guía y foco cumplen WCAG; canarios negativos rechazados.",
);
console.log(
  "ℹ Header, hero, métricas y footer conservan sus valores blancos/translúcidos esperados, pero su contraste sobre video, póster y velos no puede certificarse estáticamente; queda para la validación visual de Task6.",
);
