# Modelo académico de Oracle LAMB — curso, docente y estudiante

> Perfilado en vivo contra la base de producción el **21-ago-2026**, sobre el semestre
> `2026-2`. Todas las cifras de este documento se midieron; ninguna es estimada.
> Base: Oracle 11g, esquemas `DAVID` (académico) y `MOISES1` (personas).

## Para qué sirve esto

Tres consumidores distintos leen el mismo modelo:

| Consumidor | Qué necesita |
|---|---|
| **Indico** (horario del estudiante) | qué curso, quién lo dicta, quién está matriculado, cuándo se reúne |
| **DW / dw-olap** | granos, dimensiones conformadas y claves de negocio estables |
| **SGC / calidad** | indicadores de carga docente, tamaño de grupo, cobertura de programación |

Lo que sigue describe el modelo una sola vez, con la calidad de cada campo medida, para
que los tres partan de la misma verdad.

## La cadena central

```
VW_ACAD_CARGA_ACADEMICA          la "carga": un curso ofertado en un semestre
  │  ID_CARGA_CURSO  (clave de negocio)
  │
  ├──< ACAD_CARGA_CURSO_DOCENTE   quién lo dicta — una fila por grupo de docencia
  │      │  ID_CARGA_CURSO_DOCENTE
  │      │  ID_PERSONA ──> MOISES1.PERSONA
  │      │  ID_AMBIENTE ──> ACAD_AMBIENTE   (aula, solo 13,6% poblado)
  │      │  HORARIO                          (bitmap de franjas, ver abajo)
  │      │
  │      └──< ACAD_CURSO_DOCENTE_HORARIO     una fila POR SESIÓN DE CLASE
  │             FECHA_CLASE, FECHA_HORA_INICIO, FECHA_HORA_FIN
  │             ID_HORARIO_DETALLE ──> ACAD_HORARIO_DETALLE (catálogo de periodos)
  │
  └──< ACAD_CURSO_ALUMNO           quién está matriculado
         ID_PERSONA ──> MOISES1.PERSONA
         ID_HORARIO_PRACTICA ──> ACAD_CARGA_CURSO_DOCENTE  (a qué grupo pertenece)
         ESTADO                    ← filtrar SIEMPRE por '1'
```

**`ID_CARGA_CURSO` es la clave de negocio del modelo.** No es "el curso" del catálogo: es
*este curso, este semestre, este grupo, esta sede*. Es la granularidad a la que se matricula
un estudiante y a la que se asigna un docente.

## Volúmenes del semestre 2026-2

| | |
|---|---|
| Cargas (cursos ofertados) | 4 267 |
| Matrículas activas | 109 894 |
| Estudiantes distintos | 17 034 |
| Asignaciones docente-carga | 6 855 |
| Docentes distintos | 1 389 |
| Sesiones de clase programadas | 276 503 |

## Cardinalidades reales

**Una carga puede tener muchos docentes.** No es 1:1 y suponerlo produce duplicados:

| Docentes por carga | Cargas |
|---|---|
| 1 | 3 030 (71%) |
| 2 | 538 |
| 3 | 240 |
| 4–10 | 220 |
| 11–27 | 40 |
| 54 y 68 | 2 |

Los extremos son cursos de tesis: un asesor por estudiante, todos colgando de la misma
carga. Cualquier hecho que cuente "docentes" sin declarar el grano los cuenta mal.

**Un docente puede llevar dos grupos de la misma carga** — comprobado en *Investigación I*
(carga 211339: De Borba lleva los grupos 218832 y 214593). Por eso la clave de la asignación
es `ID_CARGA_CURSO_DOCENTE`, nunca el par (carga, persona).

## Calidad de los campos — lo medido

### Campos fiables

| Campo | Cobertura | Nota |
|---|---|---|
| `CICLO` | **100%** | el ciclo del plan al que pertenece la carga |
| `CUPO` | **100%** | plazas ofertadas; contrastable con el aforo del aula |
| `CREDITO`, `HT`, `HP` | 100% (valor cero incluido) | HT≠0 en 83%, HP≠0 en 66% de las cargas de Lima |
| `NOM_ESCUELA`, `NOM_FACULTAD` | 100% | jerarquía académica |
| `ID_SEDE` | 100% | 1=Lima, 2=Juliaca, 3=Tarapoto |
| `ID_MODALIDAD_ESTUDIO` | 100% | 1=presencial; 2, 11 y 13 son otras modalidades |
| `ID_NIVEL_ENSENANZA` | 100% | 1=pregrado; 2, 5, 9 son posgrado y otros |

### Campos con hueco

| Campo | Cobertura | Consecuencia |
|---|---|---|
| `GRUPO` | **36%** | no sirve como clave; solo como desempate |
| `ACAD_CARGA_CURSO_DOCENTE.ID_AMBIENTE` (aula) | **13,6%** | el aula real no está en Oracle |
| `ACAD_CURSO_ALUMNO.ID_HORARIO_PRACTICA` | **7,3%** | rara vez se sabe a qué grupo va el alumno |
| Código de curso | **4%** | ver abajo |

### El código universitario del estudiante: `MVW_ACAD_ALUMNO_CONTRATO`

**`DAVID.MVW_ACAD_ALUMNO_CONTRATO.CODIGO`** es la fuente del código universitario vigente
—el `202211635` que el estudiante escribe—, con cobertura del **99,7 %** del padrón activo.

Dos tablas cercanas engañan y costaron una búsqueda entera:

| Tabla | Qué guarda |
|---|---|
| `MOISES1.PERSONA.CODIGO` | **no** es el código universitario: cadenas internas de 14–20 caracteres |
| `MOISES1.PERSONA_NATURAL_ALUMNO.CODIGO` | un código por persona, pero para muchos el **antiguo** (`M20180178`) — cubre solo el 63 % |
| **`DAVID.MVW_ACAD_ALUMNO_CONTRATO.CODIGO`** | **el vigente** — 99,7 % |

Un estudiante que cambia de programa cambia de código: conviene aceptar el vigente **y**
los anteriores, para que se encuentre escriba el que escriba.

El flujo institucional es **Oracle → MidPoint → LDAP**, así que LDAP no puede traer un
código que Oracle no tenga. Si un identificador aparece en el directorio y no en la tabla
que se está consultando, la tabla es la equivocada — no al revés.

### Documentos de identidad: no todos son DNI

`schacPersonalUniqueID` trae el tipo dentro del urn
(`urn:schac:personalUniqueID:pe:PASSPORT:PE:FZ564018`). En el padrón 2026-2 conviven
**DNI (4 285), pasaporte (38) y carné de extranjería (33)**. Los de extranjero llevan
letras o guiones, así que cualquier validación de «solo dígitos» los descarta en silencio
y deja a esos estudiantes sin forma de identificarse.

### El código de curso no es usable

Existe en el catálogo — `ACAD_PLAN_CURSO.CODIGO` al 74%, `ACAD_CURSO_DETALLE.CODIGO` al
70% — pero **solo el 4% de las cargas de 2026-2 enlaza con él** por `ID_PLAN_CURSO`, y
`ACAD_CURSO.CODIGO` está vacío (1 fila de 7 060). En la práctica **el curso se identifica
por su nombre**, con lo que eso implica para el emparejamiento.

### `ESTADO` de la matrícula: filtrar por `'1'` siempre

| ESTADO | Matrículas | |
|---|---|---|
| `'1'` | 109 894 | activa — **la única que cuenta** |
| `'M'` | 3 001 | |
| `'4'` | 1 869 | |
| `'0'` | 724 | |
| `'3'` | 49 | |

El significado de `M`, `4`, `0` y `3` no está documentado en un catálogo localizable; lo
verificado es que `'1'` es el 96% y es lo que el sistema trata como matrícula vigente.
**Una consulta sin este filtro infla los conteos y mezcla retiros con activos.**

Análogamente, la carga se filtra por `ESTADO_CURSO='1' AND ESTADO_CARGA_CURSO='1'`.

## Las dos formas del horario

Oracle guarda *cuándo* se dicta cada grupo en dos sitios, y no son equivalentes:

**1. `ACAD_CURSO_DOCENTE_HORARIO` — una fila por sesión.** 276 503 filas en 2026-2, se
escribe a diario. Trae `FECHA_CLASE` y hora de inicio y fin reales. **Validada contra el
libro de horarios del campus: 772 de 793 franjas coinciden (97%).** Es la fuente utilizable.
Ojo: una clase de 07:30 a 10:10 son *tres* filas de 50 minutos; hay que unir los periodos
contiguos para reconstruir la franja.

**2. `ACAD_CARGA_CURSO_DOCENTE.HORARIO` — bitmap.** Cadena de longitud múltiplo de siete:
siete días por periodo, uno tras otro. El bit *n* es el día `n % 7` contando **domingo como
cero**, y el periodo `n // 7`, sobre las horas estándar del campus desde las 07:30. Poblado
al 99%, acierta el día de la semana el 95% de las veces. Útil para saber *qué grupo* se
reúne en una franja; no para construir un horario.

**Ninguna de las dos trae el aula.** Esa vive en `ID_AMBIENTE`, poblado al 13,6%, o fuera de
Oracle — en el libro de horarios que mantiene el área de aulas.

`ACAD_AMBIENTE` es el catálogo de espacios: 402 filas con `NOMBRE`, `CAPACIDAD`, `NIVEL`,
`ID_SEDE` y hasta `LATITUD`/`LONGITUD`. Los nombres con prefijo `JUL -` son de Juliaca;
`TPP -` es del campus Lima.

## Notas para el Data Warehouse

**Grano recomendado de los hechos:**

| Hecho | Grano | Fuente |
|---|---|---|
| Matrícula | una fila por (estudiante, carga) | `ACAD_CURSO_ALUMNO` con `ESTADO='1'` |
| Asignación docente | una fila por `ID_CARGA_CURSO_DOCENTE` | `ACAD_CARGA_CURSO_DOCENTE` |
| Sesión de clase | una fila por sesión y grupo | `ACAD_CURSO_DOCENTE_HORARIO` |
| Oferta académica | una fila por `ID_CARGA_CURSO` | `VW_ACAD_CARGA_ACADEMICA` |

**Dimensiones conformadas candidatas:** Persona (`MOISES1.PERSONA`, sirve a estudiante y
docente), Curso, Programa/Escuela/Facultad, Semestre, Sede, Ambiente, Modalidad.

**Advertencias de modelado:**

- La carga **no** es el curso. Un mismo curso genera decenas de cargas por semestre, sede,
  programa y grupo. Conformar la dimensión Curso exige subir un nivel — y el código de curso
  no está disponible para hacerlo, así que hoy solo queda el nombre.
- `VW_ACAD_CARGA_ACADEMICA` es una **vista**, no una tabla: no confiar en su estabilidad
  estructural entre versiones del sistema académico.
- El histórico está en las mismas tablas, discriminado por `SEMESTRE`. No hay tablas de
  archivo separadas, así que todo hecho debe llevar la clave de semestre.
- Un docente aparece dos veces en la misma carga cuando lleva dos grupos: contar docentes
  distintos exige `COUNT(DISTINCT ID_PERSONA)`, no `COUNT(*)`.

## Indicadores para el SGC (área de calidad)

Todos calculables directamente sobre estas tablas:

| Indicador | Cómo se obtiene |
|---|---|
| **Carga docente** | horas semanales por docente = suma de `HT+HP` de sus asignaciones |
| **Tamaño medio de grupo** | matrículas activas ÷ cargas, por escuela y ciclo |
| **Ocupación de la oferta** | matrículas activas ÷ `CUPO` — detecta cursos sobre o infrautilizados |
| **Cobertura de programación** | cargas con sesiones en `ACAD_CURSO_DOCENTE_HORARIO` ÷ cargas totales |
| **Cobertura de aula** | asignaciones con `ID_AMBIENTE` ÷ total — hoy **13,6%**, un hallazgo de calidad en sí mismo |
| **Trazabilidad del grupo** | matrículas con `ID_HORARIO_PRACTICA` ÷ total — hoy **7,3%** |
| **Integridad del catálogo** | cargas que enlazan a un código de curso — hoy **4%** |
| **Deserción intra-semestre** | matrículas con `ESTADO` distinto de `'1'` sobre el total |

Los tres últimos no son indicadores académicos sino **de calidad del dato**, y son los que
hoy limitan lo que cualquier sistema aguas abajo puede construir. Conviene medirlos y
reportarlos como tales.

## Trampas comprobadas

1. **Sin filtrar `ESTADO`** se mezclan retiros con activos (13% de filas de más).
2. **`FETCH FIRST n ROWS`** no existe en Oracle 11g; usar `ROWNUM`.
3. **Listas `IN` de más de 1 000 elementos** fallan con ORA-01795; trocear.
4. **`TO_CHAR(fecha,'D')`** devuelve 1=domingo con la configuración por defecto de esta
   base; para ISO (1=lunes) convertir con `int(d)-1 or 7`.
5. **`VW_HORARIO_DOCENTE`** tiene día y hora poblados y **no son fiables**; no confundirla
   con `ACAD_CURSO_DOCENTE_HORARIO`, que sí lo es.
6. **Los nombres de persona** vienen partidos (`NOMBRE`, `PATERNO`, `MATERNO`) y en el orden
   contrario al de los documentos del campus; comparar por conjunto de tokens, no por
   cadena.
