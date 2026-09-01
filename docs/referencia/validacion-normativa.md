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

No es una distinción académica, y conviene citarla con precisión. El **Modelo de
Licenciamiento Institucional (RCD 006-2015-SUNEDU/CD), §2.5** llama a ambos
procesos *«distintos y complementarios»* y sitúa el licenciamiento como
condición necesaria para iniciar el proceso conducente a la acreditación, que es
voluntaria. Por su parte, el **Modelo de Acreditación Institucional del Coneau
(2026), §4.2** cuenta que su propuesta de estándares consideró la revisión de las
condiciones básicas *del modelo de licenciamiento para universidades nuevas*, y
que *«esto ha permitido diferenciar los niveles de exigencia respecto a la
calidad de la gestión institucional»*.

> Nota: en una primera redacción esta cita se recortó a «para diferenciar los
> niveles de exigencia», lo que sugería un propósito de diseño que la fuente no
> afirma. El argumento de fondo —son escalones distintos— se sostiene mejor en el
> §2.5 del modelo de 2015.

Licenciamiento es el piso; acreditación, el reconocimiento por encima de ese piso.

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

### 3. Las condiciones básicas cargadas SÍ son las del modelo vigente ✅ *(corregido)*

**Esta sección afirmaba lo contrario y estaba equivocada.** Se corrige tras incorporar la
normativa de licenciamiento a la biblioteca (`sciback/biblioteca/sunedu/` y
`congreso/ley-32105-…`).

El marco `CBC-SUNEDU-2026` del sistema tiene las **8 condiciones** del **Modelo de
Licenciamiento Institucional (RCD 006-2015-SUNEDU/CD)**, con los textos del art. 28 de la
Ley 30220. La sospecha era que estuviera superado, porque los modelos Coneau 2026 mapean
sus estándares contra una matriz de **6 CBC**. No lo está: esa matriz de 6 pertenece al
modelo para **universidades nuevas** (RCD 043-2020), que a UPeU no le aplica.

Lo zanja la **Guía de orientación para la aplicación de la Ley 32105** (SUNEDU, Dirección
Técnico Normativa, 2024), que enumera los modelos uno por uno:

| Modelo | Norma | Estado | ¿Aplica a UPeU? |
|---|---|---|---|
| **Licenciamiento Institucional** | RCD 006-2015 (+ RS 054-2017) | **Vigente** | **Sí — es el suyo** |
| Licenciamiento de universidades nuevas | RCD 043-2020 (+ RS 055-2021, 065-2022) | Vigente | No — UPeU no es nueva |
| Semipresencialidad y a distancia | RCD 105-2020 | Vigente | Solo esos programas |
| Renovación de licencia | RCD 091-2021 | **Derogado** | No |
| Pregrado de Medicina | RCD 097-2019 | **Derogado** | No |

### Y el sistema encaja mejor de lo que parecía

La **Ley 32105** (El Peruano, 05-ago-2024) reescribió el artículo 13 de la Ley
Universitaria. Dice literalmente:

> **13.4.** «La autorización otorgada mediante el licenciamiento por la SUNEDU es de
> carácter permanente, **siempre y cuando las universidades demuestren el cumplimiento
> continuo de las condiciones básicas de calidad**. No obstante, las universidades estarán
> sujetas a evaluaciones periódicas inopinadas […]».

Y su **13.5** enumera las herramientas de la SUNEDU: plataforma de monitoreo y evaluación
continua, auditorías internas y externas, inspecciones periódicas, sistema de alerta
temprana, **la presentación de informes anuales de cumplimiento**, y sanciones.

**Esa última frase es la base legal del módulo M01.** El Informe de Cumplimiento —un
diagnóstico anual y recurrente del estado de las 8 condiciones— no es una práctica interna
que nos inventamos: es una herramienta que la ley nombra. Con la renovación periódica ya
derogada, demostrar cumplimiento **continuo** es precisamente lo que se supervisa, y es
para lo que sirve ese módulo.

### ¿Y las modificaciones posteriores de la Ley Universitaria?

Se revisaron **una por una** las catorce modificaciones de la Ley 30220 (todas en
`sciback/biblioteca/congreso/`, junto al texto consolidado al 13-ago-2025), para comprobar
si alguna altera lo anterior. **Ninguna lo hace.** La única posterior que toca
licenciamiento es la **Ley 31520** (2022), que suprimió la licencia renovable — y por eso
decae el modelo de Medicina. Las dos más recientes van por otro lado: la **32141** modifica
autonomía y centros de producción; la **32418** (ago-2025, la última) modifica atribuciones
de vicerrectores e incorpora el orden de sucesión rectoral — gobierno universitario, no
licenciamiento.

**Lo que sí falta incorporar** es la **RS 054-2017**, que aprueba las *consideraciones para
la presentación de los medios de verificación* del modelo de 2015 — es decir, qué evidencia
acepta SUNEDU para cada indicador. No está en la biblioteca y es directamente aplicable al
módulo de Evidencia.

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

## El SGC no solo prepara la acreditación: es evidencia de ella

*(Añadido el 2026-09-01, tras revisar los 198 elementos cargados.)*

Tres estándares de los modelos Coneau describen exactamente lo que un SGC hace. Un
sistema que los implementa **se evalúa a sí mismo**: es a la vez la herramienta con la
que se prepara el expediente y la evidencia de esos estándares.

**No es una declaración de cumplimiento.** El sistema aporta el soporte; la evidencia la
produce la institución al usarlo. Sin datos reales cargados, ninguno de estos criterios
se cumple por el mero hecho de que el software exista.

### Programas, estándar 8 — GESTIÓN DE LA INFORMACIÓN (6 criterios)

*«Se recoge y analiza información de la gestión y resultados del programa.»*

| Criterio | Qué exige | Qué lo soporta |
|---|---|---|
| 8.1 | Mecanismos que garanticen **disponibilidad, integridad y confidencialidad** | Permisos por rol y ámbito, respaldo con restauración probada, registro de cambios |
| 8.2 | Información de empleadores, egresados, docentes y estudiantes | `Grupo Interes`, `Instrumento`, `Aplicacion Instrumento`, `Resultado Instrumento` |
| 8.3 | Indicadores de desempeño docente (ID2, ID19) | `Indicador` + `Ficha Indicador` + `Valor Indicador` |
| 8.4 | Indicadores de evaluación del aprendizaje (ID4, ID10) | ídem, alimentado por conector |
| 8.5 | Indicadores de graduación y titulación (ID25, ID28, ID29) | ídem |
| 8.6 | Información **accesible al personal directivo** para decidir | Tablero y listas filtradas por rol |

Los criterios 8.3 a 8.5 **nombran indicadores concretos del propio modelo**, así que la
trazabilidad indicador → criterio no es interpretación: está en la norma.

### Programas, estándar 10 — GESTIÓN DE LA CALIDAD (4 criterios)

| Criterio | Qué exige | Qué lo soporta |
|---|---|---|
| 10.1 | Diseño del SGC: política de calidad e instancias de decisión | `Politica Calidad`, `Comite`, `Reunion`, `Acuerdo` |
| 10.2 | Procesos mínimos del SGC | `Proceso` + `Ficha Caracterizacion Proceso` |
| 10.3 | **Registro histórico** de los cambios del SGC | Versionado de `Documento Controlado` y `track_changes` |
| 10.4 | Evaluación periódica y acciones de mejora | `Revision Direccion`, `Plan Mejora`, `Accion Mejora` |

### Institucional, estándar 9 — GESTIÓN DE LA CALIDAD (5 criterios)

| Criterio | Qué exige | Qué lo soporta |
|---|---|---|
| 9.1 | Política institucional de calidad y documentos del SGC | `Politica Calidad`, `Objetivo Calidad`, `Documento Controlado` |
| 9.2 | Alcance del SGC a **todos** los procesos | Árbol de procesos completo del mapa institucional |
| 9.3 | Custodia y gestión documental bajo unidad responsable | `Documento Controlado` con flujo de aprobación y propietario |
| 9.4 | Revisión periódica del SGC con base en evidencias | `Revision Direccion` |
| 9.5 | Evaluación de resultados e implementación de mejoras | Indicadores de proceso + `Plan Mejora` |

### Dos consecuencias prácticas

1. **En licenciamiento este argumento no aplica.** Ninguna de las condiciones básicas de
   Sunedu menciona gestión de la información ni sistemas: se comprobó por búsqueda sobre
   el texto oficial de sus criterios cargados. El argumento vale solo para acreditación.
2. **La Tabla 10 lo refuerza.** Su criterio 7 otorga puntos de excelencia por tener un
   SGC: cuatro puntos implementado, ocho certificado. Un mismo sistema suma por tres vías
   distintas — soporta el estándar 8, evidencia los estándares de gestión de la calidad, y
   puntúa para la vigencia extendida.

Relacionado: el estándar 9 de programas (*Supervisión y revisión del programa de
estudios*) pide en su criterio 9.2 el registro histórico de cambios curriculares, con el
mismo mecanismo documental.

## Fuentes

- Modelo de Acreditación para Programas de Estudios de Educación Superior
  Universitaria del Coneau (Sineace, 2026) — Tablas 8, 9 y 10.
- Modelo de Acreditación Institucional de Universidades y Escuelas de Posgrado
  del Coneau (Sineace, 2026) — §4.2, §10.3, Tablas 9 y 10.
  Ambos en `~/proyectos/sciback/biblioteca/sineace/`.
- [Sunedu — Licenciamiento institucional para universidades nuevas](https://www.sunedu.gob.pe/licenciamiento-institucional-universidades-nuevas/) (RCD 043-2020-SUNEDU/CD).
- [Sunedu — Renovación de licencia institucional](https://www.sunedu.gob.pe/renovacion-licencia-institucional/) (RCD 091-2021-SUNEDU/CD).
- **Ley 30220, Ley Universitaria — texto consolidado** (82 pp., al 13-ago-2025) y las
  catorce modificaciones, en `sciback/biblioteca/congreso/`.
- **Ley 32105** (El Peruano, 05-ago-2024) — art. 13.4 (licencia permanente condicionada al
  cumplimiento continuo) y 13.5 (herramientas de SUNEDU, incluidos los **informes anuales
  de cumplimiento**).
- **Guía de orientación para la aplicación de la Ley 32105** (SUNEDU, Dirección Técnico
  Normativa, 2024) y los modelos de licenciamiento **RCD 006-2015**, **RCD 043-2020** (con
  su matriz de CBC) y **RCD 091-2021** (derogado), todos en `sciback/biblioteca/sunedu/`.
