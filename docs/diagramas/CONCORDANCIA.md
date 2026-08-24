# Concordancia entre los diagramas BPMN y el sistema real

**Fecha:** 2026-08-24 · **Versión en producción:** `sgc-frappe:v106`
**Los quince flujos están recorridos contra producción.**

Contrastación de los 15 `.bpmn` contra el comportamiento comprobado en
producción, recorriendo los flujos punta a punta con usuarios reales por rol.

> **Cómo se contrasta, tras haberlo hecho mal una vez:** hay que LEER el `.bpmn`.
> El workflow de Frappe no es el diagrama: el generador añade además los pasos
> que el sistema ejecuta solo (temporizadores y mensajes, en el carril «Sistema»),
> que no son transiciones de workflow y no aparecen si uno solo mira
> `Workflow.transitions`. Deducir el contenido del diagrama desde el workflow
> produjo la discordancia falsa que abre la lista de abajo.

---

## Lo que concuerda

**Estados, transiciones y roles: los 15, sin excepción.** No es casualidad ni
mérito: los diagramas se *generan* de los mismos specs que crean los workflows
en Frappe, así que no pueden divergir por construcción. Un diagrama que
contradijera al motor sería un fallo del generador, no del proceso.

Lo que sí se comprobó ejecutando —y podría haber fallado— es que el motor
respeta lo dibujado:

- **Segregación de funciones real.** El rol equivocado recibe `Not a valid
  Workflow Action`; quien crea un documento no puede aprobarlo (`Self approval
  is not allowed`) en las transiciones marcadas de control.
- **Los carriles se cumplen.** Cada tarea está en el carril de su rol y solo ese
  rol la ejecuta: la Autoridad Aprobadora presenta a SUNEDU y la DPGC no; el
  Rectorado cierra la Revisión por la Dirección y la DPGC no puede, ni estando
  en «Realizada».
- **Las devoluciones existen y funcionan** (Observar, Devolver a planificada,
  Verificar no eficaz), incluidas las tres que se añadieron al detectar que un
  documento observado quedaba atascado.

---

## Lo que NO concuerda

### 1. ~~«Vencida» no está en el diagrama~~ — ERA FALSO ✅ *(corregido)*

**Esta discordancia no existía; el error era del informe.** Se deja escrita en
lugar de borrarla, porque el fallo de método es más instructivo que el hallazgo.

Lo que se hizo mal: comparar los estados del `Select` con los del **workflow de
Frappe**, ver que `Vencida` faltaba en el segundo, y concluir «no está en el
diagrama» **sin abrir el diagrama**. Justo en el documento cuyo propósito es
contrastar el diagrama con el sistema.

`02-evidencia.bpmn` sí dibuja `Vencida`, y con el elemento que le corresponde:
**dos eventos de temporizador** (`intermediateCatchEvent` con `timerEventDefinition`),
uno desde `Pendiente` y otro desde `Valida`, etiquetados «Vence la vigencia», que
desembocan en un evento de fin `Vencida`. Todo dentro del carril **«Sistema
(automático)»**. Está así desde el commit `c7c2454` (13-ago-2026), *«BPMN:
dibujar también lo que el sistema hace solo»* — diez días antes de que se
escribiera este informe. El generador lo declara en `bpmn.py`
(`TRANSICIONES_AUTOMATICAS`) junto con el otro paso automático del sistema, la
obsolescencia del documento reemplazado.

El informe llegaba incluso a proponer como arreglo «una transición temporizada
(evento de temporizador BPMN)», que es literalmente lo que ya había.

**Lo que sí es cierto, y no es un defecto:** `Vencida` no es un estado del
workflow, así que desde ahí no hay ninguna acción disponible — verificado en
producción. Pero el diagrama lo modela como **evento de fin**, de modo que
sistema y diagrama dicen lo mismo: una evidencia vencida es un final del camino.

**Lo único abierto es una decisión de negocio, no un fallo:** si Calidad quiere
que una evidencia caducada pueda *renovarse* (nueva vigencia y vuelta a la cola
de validación) en vez de reemplazarse por otra, eso cambia el proceso —y con él
el diagrama—, no corrige nada roto.

### 2. 42 reglas gobiernan el flujo y ninguna aparece ⚠️

Los diagramas muestran *que* existe una flecha, no *cuándo* está disponible. Hay
**42 validaciones** en los controladores que bloquean transiciones dibujadas
como si fueran libres. Por proceso: Revisión por la Dirección 7, Auditoría 6,
Documento Controlado 6, No Conformidad 6, Aplicación de Instrumento 5, Informe
de Cumplimiento 4, Evidencia 3, Programa de Auditoría 2, Hallazgo de Auditoría
2, Riesgo 1.

Ejemplos comprobados en vivo, todos invisibles en el diagrama:

| Proceso | La flecha está dibujada… | …pero antes exige |
|---|---|---|
| Informe de Cumplimiento | Presentar a SUNEDU | ninguna CBC sin evaluar (y antes, ya al **guardar**, justificación en cada CBC que no cumpla plenamente) |
| Revisión por la Dirección | Cerrar revisión | las 3 salidas §9.3.3 con responsable **y** el acta en PDF |
| Aplicación de Instrumento | Cerrar aplicación | fecha de fin de campo registrada |
| Auditoría | Iniciar ejecución | equipo auditor con al menos un miembro independiente |
| Hallazgo de Auditoría | Escalar a NC | que la no conformidad exista |

**Qué significa:** Calidad puede leer el diagrama, planificar un paso y
encontrarse con que el sistema no la deja. La regla es correcta; lo que falta es
que esté dicha.

**Cómo se arreglaría:** BPMN tiene con qué — condiciones en el flujo de salida
del gateway, o anotaciones de texto. El generador tendría que leerlas del
controlador, que hoy no hace.

### 3. Los diagramas estaban aislados; el sistema los encadena ⚠️ *(3 de 5 cerradas)*

Cada `.bpmn` era un proceso cerrado en su propio pool. Pero el sistema **salta de
un proceso a otro**, y esos saltos no se dibujaban. El generador ya dibuja tres:

| Cuando… | el sistema… | y el diagrama |
|---|---|---|
| un riesgo se materializa | crea una **No Conformidad** | ✅ *message flow* al pool caja negra (13) |
| se escala un hallazgo de auditoría | crea una **No Conformidad** | ✅ *message flow* al pool caja negra (08) |
| se cierra una aplicación de instrumento | publica **Valor Indicador** | ✅ `serviceTask` en el carril Sistema (04) |
| se valida una evidencia | sincroniza **Trazabilidad** | ⚠️ no lo muestra |
| se cierra una autoevaluación | promueve la **vigencia oficial** | ⚠️ no lo muestra |

**Cómo se dibujan ahora, y por qué de dos maneras distintas.** No son la misma
cosa y BPMN las distingue:

- **Un efecto que se queda dentro** (publicar los valores de indicador al cerrar
  la aplicación) es trabajo del propio proceso, así que va como `serviceTask` en
  el carril «Sistema (automático)», **interpuesto entre la acción y el estado** —
  que es cuando ocurre de verdad. Se declara en `EFECTOS_AL_ENTRAR`.
- **Un salto que cruza a otro proceso** (escalar a no conformidad) es un mensaje
  a alguien más, así que va como `messageFlow` hacia un **participante sin
  `processRef`** — la caja negra de BPMN: se nombra el destinatario sin abrirlo,
  porque su interior está dibujado en su propio fichero. Se declara en
  `SALTOS_ENTRE_PROCESOS`.

**Regla de admisión, para que esto no se llene de flechas decorativas:** solo se
dibuja lo que existe en el código. Cada entrada declara su `origen` (ruta al
método real) y un test lo importa: si alguien renombra o borra el método, el test
cae. Es el mismo candado que ya tenía `TRANSICIONES_AUTOMATICAS`.

**Lo que sigue abierto:** las dos filas de arriba con ⚠️. La trazabilidad y la
vigencia oficial no se dibujan porque no son ni un efecto puntual al entrar en un
estado ni un mensaje a otro proceso: son sincronizaciones de datos. Meterlas con
la notación equivocada diría algo falso; queda pendiente decidir cuál les toca.

### 4. 18 estados existen en el sistema y no están dibujados ⚠️

El generador dibuja un `exclusiveGateway` con el nombre del estado **solo cuando
ese estado tiene más de una salida** — es donde se decide algo. Un estado con una
sola salida no se dibuja: la tarea anterior encadena directamente con la
siguiente. Está documentado en `bpmn.py` y es defendible en BPMN: un punto por el
que solo se puede seguir de una manera no es una decisión, y un gateway de una
sola salida es ruido.

El coste es que **18 estados no aparecen en ningún sitio**, y no son estados de
paso: son donde el documento se queda esperando, a veces meses.

| Proceso | Estados que no se ven |
|---|---|
| Documento Controlado | Observado ⚠ · Publicado ⚠ |
| Autoevaluación | En curso ⚠ · Consolidada |
| Auditoría | En ejecucion |
| Programa de Auditoría | En ejecucion ⚠ |
| Hallazgo de Auditoría | Escalado a NC ⚠ · Cerrado |
| Hallazgo | En tratamiento ⚠ |
| No Conformidad | En analisis · En tratamiento ⚠ |
| Plan/Acción de Mejora | En ejecucion ⚠ · Verificada no eficaz |
| Riesgo | Evaluado · En tratamiento · Materializado |
| Tratamiento de Riesgo | En ejecucion ⚠ |
| Revisión por la Dirección | Cerrada ⚠ |

⚠ = **al cruzar ese estado cambia el carril**: entra un rol y sale otro. Son 10
de los 18, y ahí es donde más duele, porque el diagrama muestra una flecha de un
carril a otro sin nada en medio — como si el traspaso fuera instantáneo. En el
06, «Iniciar ejecución» la hace el Auditor y «Cerrar programa» la DPGC: entre las
dos está «En ejecucion», que es donde ocurren TODAS las auditorías del año.

**Qué significa:** quien mire el diagrama para saber dónde está parado su
documento no encontrará el estado. La lista de estados vive en el `Select` y en
el workflow, no en el dibujo.

**Cómo se arreglaría:** no con un gateway —seguiría siendo falso, no hay
decisión— sino dibujando el estado como lo que es: un `intermediateThrowEvent`
o, mejor, una anotación de texto sobre el flujo. Cambia el generador, no el
proceso.

---

## Lo que se cerró en esta tanda: la base normativa ya viaja dentro

Hasta ahora los diagramas decían quién hace qué y en qué orden, pero no contra
qué norma responde el proceso. Quien auditara uno no tenía con qué contrastarlo,
y quien quisiera cambiarlo no sabía qué margen tenía: un paso exigido por norma y
un paso que es criterio de la casa se veían exactamente igual.

**14 de los 15 llevan ya su `<bpmn:documentation>`**, generado desde el mapa
`DOCUMENTACION_NORMATIVA` de `sgc/bpmn.py` — no escrito a mano en el XML. Va lo
primero dentro de `bpmn:process`, que es donde el esquema de la OMG lo exige, y
cualquier modelador lo muestra al seleccionar el proceso. La tabla completa de
qué norma respalda cada uno está en
[`bpmn/README.md`](bpmn/README.md#de-qué-norma-nace-cada-proceso).

Lo que esa documentación **no** hace, para que no se le pida de más:

- **No es la regla ejecutable.** Sigue siendo texto para quien lee; las 42
  validaciones del punto 2 continúan sin representarse. Que el 05 cite el
  artículo 13.5 de la Ley Universitaria no le dice a nadie que «Presentar a SUNEDU» exige
  antes todas las condiciones evaluadas y justificadas.
- **No cubre los 15.** `Aplicación de Instrumento` se queda sin documentación a
  propósito: ninguna norma verificada exige aplicar encuestas. Los indicadores
  del modelo del Coneau sí están normados; que se midan por encuesta es decisión
  de la casa. El hueco dice eso, y es preferible a rellenarlo con una cita que no
  se sostenga.
- **Queda un flanco por verificar en la evidencia (02).** El texto cita cuántas
  evidencias enumeran los modelos del Coneau (52 en programas, 84 en
  institucional), pero para el licenciamiento **qué medio de verificación admite
  la Sunedu por indicador no está contrastado contra fuente primaria** — falta
  conseguir la RS 054-2017 y las consideraciones sobre medios de verificación del
  modelo de 2015. El diagrama lo dice explícitamente en vez de callarlo.

Las tres discordancias de arriba siguen vigentes tal cual: la documentación
normativa no toca ninguna de ellas.

## Cuando el diagrama tenía razón y el código no: la independencia del auditor

El `<bpmn:documentation>` del 07 dice, desde que se generó, que «la independencia
del equipo auditor —nadie audita su propio trabajo— es la razón de que el inicio
de la ejecución esté condicionado». Recorriendo el flujo el 2026-08-23 resultó
que la condición existía pero no comprobaba eso: exigía que **algún miembro
tuviera marcada la casilla** `independiente_del_area`. Una casilla que marca el
propio interesado.

Lo comprobado en producción: el responsable de un proceso creó la auditoría a
ESE proceso, se puso a sí mismo de auditor líder, marcó su propia casilla, y el
sistema le dejó iniciar la ejecución. Exactamente lo que ISO 9001 §9.2.2 c) y
ISO 19011 cl. 5.5.2 prohíben.

Es la discordancia al revés de las tres de arriba: no era el diagrama el que se
quedaba corto, era el código el que no cumplía lo que el diagrama prometía. Y
solo se ve recorriendo, porque leyendo el controlador la validación *parece* la
correcta — se llama «evidencia de independencia» y cita la cláusula.

**Arreglado** (`Auditoria._validar_independencia_real`): quien figura como
`responsable` del proceso auditado no puede estar en el equipo que lo audita. No
cubre todo —el sistema no sabe a qué área pertenece cada persona, y `Unidad
Organica` no tiene responsable— pero convierte en comprobable el único caso que
tiene dato. Lo que no se puede comprobar sigue declarándose con la casilla; la
diferencia es que ahora la casilla no es lo *único*.

**Ojo al leerlo hoy:** `Proceso.responsable` está vacío en producción, así que la
regla todavía no bloquea a nadie. Empezará a morder cuando se pueble — que es
justamente cuando importa.

## El generador también se equivoca: de dónde sale un mensaje

Al añadir los `messageFlow` (commit `0198f98`) el origen se resolvía con
`entrada_a`, la misma función que usan las flechas internas. Parecía coherente y
era sutilmente falso: cuando el estado tiene **una sola salida no se dibuja**
(discordancia 4), y entonces `entrada_a` devuelve la tarea **siguiente**. El 08
acabó diciendo «al cerrar un hallazgo ya escalado, avisa a No Conformidad»
cuando el aviso ocurre un paso antes, al escalarlo.

Corregido: el mensaje sale de la **acción que lleva al estado**, con un test que
lo fija contra las transiciones del spec. Se detectó leyendo el diagrama para
recorrerlo, no revisando el código — que es el mismo motivo por el que existe
este documento.

## Decisión abierta: qué pasa después de «no eficaz»

No es una discordancia —diagrama y sistema dicen lo mismo— sino una pregunta de
proceso que el recorrido del 09 dejó a la vista, y que Calidad tiene que
responder porque hay dos lecturas defendibles.

Tres documentos registran que un tratamiento **no funcionó**, y no se comportan
igual:

| Documento | Estado | ¿Y después? |
|---|---|---|
| Acción de Mejora | Verificada no eficaz | **Reabrir** → vuelve a «En ejecucion» |
| Hallazgo | Cerrado no eficaz | nada: es final |
| No Conformidad | Cerrada no eficaz | nada: es final |

Las dos lecturas: (a) ISO 9001 §10.2.1 obliga a seguir reaccionando, así que un
documento que dice «no funcionó» y no admite nada más deja el problema
registrado como irresuelto y sin ruta; (b) «cerrado no eficaz» cierra *ese
intento* y la continuación es un documento nuevo, lo que además conserva la
traza de que hubo un intento fallido.

Ninguna es obviamente correcta, así que no se ha tocado. Lo que sí conviene es
que las tres se comporten igual: hoy la diferencia parece más un descuido que
una decisión.

Comprobado en producción el 2026-08-23: «Cerrada no eficaz» de la NC no admite
ninguna acción —ni reabrir ni volver a analizar—, tal como el diagrama la dibuja
(evento de fin). Sistema y diagrama concuerdan; la pregunta es de proceso.

## Los cinco últimos recorridos (11 a 15), hechos en paralelo el 2026-08-23

Los quince quedan recorridos. **Estructuralmente los cinco concuerdan**: estados,
transiciones, carriles y metadatos de autoaprobación coinciden con los workflows
vivos, y ninguna transición dibujada resultó imposible. Lo que apareció fueron
**huecos del controlador**: el diagrama prometía y el código no cumplía.

### 11 · Plan de Mejora

`Cerrado` es terminal, tal como se dibuja. La separación redactor/aprobador la
impone el **RBAC** (la DPGC no tiene permiso de creación), no el
`allow_self_approval`, que al comparar `owner` nunca llega a morder.

Tres huecos: (a) aprobar y cerrar no dejaban firma — añadidos `aprobado_por`,
`fecha_aprobacion`, `cerrado_por`, `fecha_cierre`, sellados por el sistema (ISO
9001 §10.2.2); (b) se ponía «En ejecucion» un plan **sin acciones y sin
responsable**, que quedaba en avance 0 % y semáforo Verde (§10.2.1 b); (c) el
cierre no miraba el contenido — se cerró un plan con las acciones sin empezar, y
otro cuya **única acción estaba «Verificada no eficaz»** salió al **100 % y en
Verde**: el sistema daba por buena justo la acción que acababan de declarar
inútil. El cierre exige ahora que todas estén verificadas eficaces, porque
§10.2.1 d) pide revisar la eficacia, no solo ejecutar.

### 12 · Acción de Mejora

**Su reapertura sí funciona de verdad** —`Verificada no eficaz → Reabrir → En
ejecucion`, recorrida entera—, a diferencia de la del 08.

Cuatro huecos: (a) no existía registro de quién verifica la eficacia — añadido
`verificada_por`, sellado al entrar en cualquiera de las dos verificaciones y
**borrado al reabrir**, para que nadie lea «verificada por X» en una acción sin
verificar (§10.2.1 e); (b) se cerraba como eficaz **sin evidencia** (§10.2.2);
(c) se recorría el flujo entero sin responsable ni plazo, y eso tiene efecto
comprobable: el semáforo del plan solo mira acciones con fecha, así que una
acción sin plazo **nunca** pone el plan en rojo, y el aviso de vencimiento se
dirige al responsable, así que sin él no se avisa a nadie; (d) el avance quedaba
en 100 tras «no eficaz» y tras reabrir, de modo que el plan anunciaba 100 %
mientras su acción se rehacía por haber fallado.

### 13 · Riesgo — el peor de los cinco

**El `messageFlow` «Escalar a no conformidad» era falso.**
`Riesgo.escalar_a_no_conformidad` existía y no lo invocaba **nada**: ni el
workflow, ni un hook, ni el frontend. Materializar un riesgo no creaba ninguna No
Conformidad y la cadena §6.1 → §10.2 estaba muerta. Se corrigió **el código, no
el diagrama** —dos sitios ya declaraban que el salto ocurría al materializar—:
entrar en «Materializado» crea ahora la NC.

**Y el cálculo de nivel de riesgo nunca existió.** `score` y `nivel` se
declaraban «calculado en F4 (Server Script)» y ese script no existe; ambos son
`read_only`, así que nadie podía ni corregirlos a mano. Con probabilidad 1 e
impacto 1 salía **score 0, nivel «Bajo»**; con 5×5, exactamente igual. **Un
inventario de riesgos donde todo sale «Bajo»** afirma lo contrario de lo que ISO
9001 §6.1 obliga a determinar. Ahora `score = probabilidad × impacto` y el nivel
sale de los umbrales de la matriz; **si el riesgo no declara matriz, el nivel
queda en blanco**, porque sin criterios no hay valoración (ISO 31000 §6.4.4) y es
preferible no saberlo a mentir.

Además: el ciclo entero se recorría sin una sola evaluación ni tratamiento
detrás; se cerraba un riesgo con su tratamiento a medias; se cerraba un riesgo
materializado sin NC; y `evaluado_por` era tecleable — el Dueño de Proceso
atribuyó a la DPGC una evaluación suya.

### 14 · Tratamiento de Riesgo

La vuelta «Verificar no eficaz» **está viva** (comprobada de punta a punta).

Dos cosas que el diagrama afirmaba y el sistema no hacía: (a) «quien implementa
el tratamiento no verifica su resultado» era **falso** (ver la sección sobre
`allow_self_approval`); (b) «el riesgo residual: el nivel que este proceso
registra» era falso — **no existía el campo**. Ahora `nivel_residual` es
obligatorio para verificar. Añadidos los sellos de implementación y verificación,
las validaciones del plan de tratamiento (ISO 31000 §6.5.3) y el guard que impide
colgar tratamientos nuevos de un riesgo ya cerrado.

**El `.bpmn` no necesitó cambios: se corrigió el sistema para que el diagrama
dijera la verdad.**

### 15 · Revisión por la Dirección

Solo el Rectorado cierra —a la DPGC ni le aparece la acción— y el Rectorado no
puede crear revisiones. Cuatro huecos: (a) **§9.3.2 no se exigía**: bastaba una
entrada, incluso una fila vacía, para dar la revisión por realizada; ahora se
exigen los seis incisos a)–f) y cada fila debe llevar resumen o fuente; (b) la
escalada de privilegios descrita más abajo; (c) una revisión ya **cerrada seguía
siendo editable** sin reabrirla — se sustituyó el acta y se reescribió una
decisión del §9.3.3 en silencio; (d) el cierre no dejaba firma.

**Pendiente de decisión:** §9.3.2 c) tiene siete sub-incisos en la norma
(satisfacción, objetivos, desempeño de procesos, no conformidades, seguimiento,
auditorías, proveedores) y el modelo lo colapsa en **una** fila. Un resumen
genérico puede ocultar que nadie miró las auditorías o los proveedores.

### Decisiones abiertas que dejan estos cinco

- **No existe la vuelta «Monitoreado → En tratamiento»** en el riesgo, que ISO
  31000 §6.5.2 supone (el tratamiento es iterativo). Hoy un riesgo mal tratado
  solo puede cerrarse en falso o esperar a materializarse.
- **Ni `Tratamiento Riesgo` ni `Auditoria` tienen estado «Cancelado»**, así que
  uno abandonado bloquea el cierre de su padre para siempre y hay que borrarlo.
- **La NC que nace de un riesgo es siempre «mayor» y «crítica»**, sin mirar el
  nivel evaluado. §10.2.1 pide acciones «apropiadas a los efectos»; ahora que el
  nivel por fin se calcula, se puede mapear bien.
- **Un documento cerrado sigue siendo editable desde el servidor** en todo el
  SGC: el `allow_edit` del workflow solo protege la interfaz. En el 15 se cerró
  con un guard propio; el patrón es general.

## Lo que `allow_self_approval=0` protege, y lo que no

Es la regla en la que se apoya toda la segregación de funciones del SGC, y
conviene saber exactamente qué compara: **`frappe.session.user` contra
`doc.owner`**. Es decir, contra **quien creó la ficha**, no contra quien hizo el
trabajo que se está aprobando.

Para el caso normal basta y sobra, y así se comprobó en los recorridos 01, 05,
06 y 10: quien redacta un documento no lo aprueba, quien redacta un informe no lo
presenta, quien levanta un hallazgo no lo cierra. En todos ellos el autor del
trabajo *es* el creador de la ficha.

**Deja de bastar en cuanto el ejecutor y el creador son personas distintas**, que
es justo lo que pasa cuando una ficha se abre en nombre de otro:

- En el **14** el Dueño de Proceso creó el tratamiento y puso de `responsable` a
  otra persona con rol DPGC; esa persona implementó y **verificó su propio
  trabajo**, porque el `owner` era el primero. El diagrama decía «quien
  implementa el tratamiento no verifica su resultado» y era falso. Se arregló
  comparando contra `responsable` y contra el sello `implementado_por` — el
  primero solo no valía, porque es tecleable hasta el último segundo y bastaba
  cambiarlo para esquivar la regla.
- En el **11** y el **12** ocurre lo contrario y por eso no muerde: la DPGC no
  tiene permiso de creación sobre esos DocTypes, así que nunca es `owner` y la
  comparación jamás se activa. Ahí la separación real la impone el RBAC, no el
  workflow.

**Regla para el futuro:** cuando el proceso diga «quien hace X no aprueba X», y
X lo ejecute alguien que puede no ser el creador, `allow_self_approval=0` no lo
garantiza. Hay que compararlo contra el campo que identifica al ejecutor, y
preferiblemente contra un sello puesto por el sistema, no contra un Link que el
interesado puede reescribir.

## Un método whitelisted solo exige LEER para poder invocarse

`@frappe.whitelist()` hace un método llamable por HTTP, y `run_doc_method`
comprueba **permiso de lectura** sobre el documento. Si dentro el método escribe
con `ignore_permissions=True`, cualquiera que pueda *abrir* el documento puede
*modificarlo* por esa vía.

Comprobado en el 15: `Revision Direccion.consolidar_salidas` guardaba así, y un
**Auditor Interno de solo lectura redactó las tres salidas del §9.3.3** de la
revisión — el auditado escribiendo las conclusiones sobre sí mismo — quedando
además como `modified_by`.

Barrido del repo tras el hallazgo: seis whitelisted escriben con
`ignore_permissions`. Dos son lecturas legítimas (portada pública sin PII,
catálogo de escala). Los dos escalados a No Conformidad (`Riesgo`,
`Hallazgo Auditoria`) están cubiertos **indirectamente** porque pasan por el
motor de workflow, que rechaza la transición al rol equivocado — comprobado en
producción, y comprobado también que al fallar a medias el rollback no deja
No Conformidades huérfanas. El que sí estaba abierto era
`Informe Cumplimiento.generar_pdf(adjuntar=True)`: escribía un adjunto en el
documento, incluido uno **ya presentado a la Sunedu**, que se supone inmutable.
Cerrado con `check_permission("write")`.

**Regla:** todo whitelisted que escriba comprueba permisos explícitamente. Que el
DocType tenga bien puestos los suyos no basta, porque `ignore_permissions` los
salta por definición.

## Riesgo de deriva

Nada compara automáticamente los `.bpmn` en disco contra lo que generaría el
código. **Ya falló una vez**: al crear el workflow del hallazgo de auditoría
hubo 15 workflows y 14 diagramas hasta que alguien lo notó.

Un test que regenere en memoria y falle si el disco difiere cerraría el hueco, y
ahora es viable: el generador ya no necesita un bench para leer los specs.

**Ojo con Camunda:** abrir un diagrama y guardarlo reescribe el fichero. El
layout se conserva al regenerar, pero **editar flechas a mano se pierde** — y
puede romper el modelo. Pasó el 2026-08-23: una edición manual en
`evidencia.bpmn` dejó el estado final «Válida» inalcanzable y una referencia a
un flujo borrado. El fichero seguía siendo XML válido; el proceso, no.
