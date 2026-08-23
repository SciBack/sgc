# Validación del sistema contra las normas canónicas

**Fecha:** 2026-08-23 · **Contrastado contra fuentes primarias** de la biblioteca
(`sciback/biblioteca/sineace/`) y los portales oficiales de Sunedu.

---

## Los tres mundos, y por qué no se mezclan

La normativa peruana mantiene separadas tres cosas que en el habla diaria se
confunden:

| | Quién | Carácter | Lógica |
|---|---|---|---|
| **Licenciamiento** | Sunedu | **Obligatorio** — es el permiso para operar | Se cumple o no se cumple |
| **Acreditación de programa** | Sineace · Coneau | Voluntario | Niveles NL/L/LP → vigencia en años |
| **Acreditación institucional** | Sineace · Coneau | Voluntario | Ídem, pero otro modelo |

No es una distinción académica. El **Modelo de Acreditación Institucional del
Coneau (2026), §4.2** lo dice literalmente: sus estándares se definieron
revisando las condiciones básicas de Sunedu *«para diferenciar los niveles de
exigencia»*. Licenciamiento es el piso; acreditación, el reconocimiento por
encima de ese piso.

---

## Lo que se validó y CUADRA

### Acreditación de programas — fiel al modelo oficial

La Tabla 8 del modelo declara **10 estándares, 53 criterios, 52 evidencias y 29
indicadores**. El sistema tiene exactamente 10 / 53 / 29. ✅

### Acreditación institucional — fiel al modelo oficial

El modelo declara **9 estándares, 68 criterios, 84 evidencias y 37
indicadores**. El sistema tiene 9 / 68 / 37. ✅

### La escala de valoración — literal

Los tres niveles del sistema (`NL` no logrado · `L` logrado · `LP` logrado
plenamente) son los de la norma. ✅

### La regla de vigencia — correcta en tres de sus cuatro tramos

Tabla 9 de ambos modelos, contrastada contra `sgc/scoring.py`:

| Norma dice | Sistema hace |
|---|---|
| Uno o más estándares NL → **en proceso** | ✅ igual |
| Todos L, o combinación L/LP → **3 años** | ✅ igual |
| Todos LP → **6 años** | ✅ igual |
| Todos LP **+ puntos de excelencia** → **8 años** | ❌ **no implementado** |

---

## Lo que NO cuadra

### 1. La acreditación de 8 años es inalcanzable ⚠️

La norma la concede cuando **todos los estándares son LP** y además se acumulan
puntos de la Tabla 10 (Criterios de acreditación con excelencia). Los umbrales
**difieren entre modelos**:

- **Programas: 16 o más puntos.**
- **Institucional: 20 o más puntos.**

El sistema nunca emite ese resultado: la opción existe en el desplegable y hay
un campo `puntaje_excelencia`, pero **nada lo calcula**. Tampoco están cargados
los criterios de la Tabla 10 (porcentaje de docentes con doctorado, docentes en
Renacyt, docentes a tiempo completo, egresados titulados, etc.).

Detalle que vale la pena conocer: **el criterio 7 de esa tabla premia tener un
sistema de gestión de calidad** — 4 puntos si está implementado, **8 si está
certificado**. Este mismo sistema suma para la excelencia.

### 2. La regla de vigencia está escrita a fuego ⚠️

`Marco Normativo` tiene un campo `reglas_vigencia` pensado para que cada marco
declare las suyas, pero **nadie lo lee**. La regla vive en el código y se aplica
igual a programas y a institucional — hoy funciona porque sus tramos 1-3
coinciden, pero **sus umbrales de excelencia no** (16 frente a 20). Cuando se
implemente el tramo de 8 años, hacerlo por marco, no en el código.

### 3. Las condiciones básicas cargadas son las de la ley, no las del modelo vigente 🔴

Es el hallazgo de fondo. El marco `CBC-SUNEDU-2026` del sistema tiene **8
condiciones** con el texto del **artículo 28 de la Ley 30220** (2014). Pero
Sunedu opera con *modelos* que desarrollan esas condiciones en componentes e
indicadores, y hay más de uno:

| Instrumento | Estructura |
|---|---|
| Ley 30220, art. 28 | 8 condiciones básicas — **lo que tiene el sistema** |
| Modelo de licenciamiento para universidades nuevas (**RCD 043-2020-SUNEDU/CD**) | **6 CBC** con componentes e indicadores |
| Renovación de licencia (**RCD 091-2021-SUNEDU/CD**) | **4 CBC** |

Los modelos Coneau 2026 mapean sus estándares contra el de **6 CBC** (Sunedu,
2020), no contra las 8 de la ley. Además, la **Ley 32105 (agosto 2024)** eliminó
la renovación periódica: la licencia pasa a ser permanente *condicionada al
cumplimiento continuo*, verificado por supervisión e informes.

**Qué decidir:** con qué modelo debe diagnosticar UPeU su cumplimiento. Es una
decisión de Calidad, no técnica — y hasta tomarla, el diagnóstico se hace contra
las 8 condiciones de la ley, que siguen siendo la base legal pero no la matriz
operativa con la que supervisa Sunedu hoy.

**Brecha de biblioteca:** no tenemos ninguna resolución de licenciamiento entre
las fuentes primarias (`sciback/biblioteca/sunedu/` solo tiene grados, títulos y
Renati). Conviene incorporar la RCD 043-2020 y la RCD 091-2021.

---

## Lo que se corrigió a raíz de esta validación

Se añadió `Marco Normativo.alcance` (licenciamiento / acreditación de programa /
acreditación institucional / gestión interna), lo puebla `f17_alcance_marcos`, y
con él tres guards:

1. Una **autoevaluación rechaza un marco de licenciamiento**. Antes se podía
   abrir una con las condiciones básicas y obtener «Acreditado 6 años» — el
   agravante es que en esa escala la sigla `LP` significa *Cumple*, no *logrado
   plenamente*, y el motor solo ve la sigla.
2. Un **informe de cumplimiento rechaza un marco de acreditación** (el espejo).
3. **Coherencia de alcance**: la acreditación de programa exige programa-sede;
   la institucional no lo admite.

## Fuentes

- Modelo de Acreditación para Programas de Estudios de Educación Superior
  Universitaria del Coneau (Sineace, 2026) — Tablas 8, 9 y 10.
- Modelo de Acreditación Institucional de Universidades y Escuelas de Posgrado
  del Coneau (Sineace, 2026) — §4.2, §10.3, Tablas 9 y 10.
  Ambos en `~/proyectos/sciback/biblioteca/sineace/`.
- [Sunedu — Licenciamiento institucional para universidades nuevas](https://www.sunedu.gob.pe/licenciamiento-institucional-universidades-nuevas/) (RCD 043-2020-SUNEDU/CD).
- [Sunedu — Renovación de licencia institucional](https://www.sunedu.gob.pe/renovacion-licencia-institucional/) (RCD 091-2021-SUNEDU/CD).
- Ley 30220, Ley Universitaria, art. 28 — en `sciback/biblioteca/congreso/`.
- Ley 32105 (05-ago-2024) — licencia permanente condicionada al cumplimiento continuo.
