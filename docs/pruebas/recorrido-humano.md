# Recorrido humano del SGC, flujo por flujo y rol por rol

Guía para recorrer el sistema **como lo hará Calidad**, no como lo prueba un
script. Cada flujo va con el usuario que le toca, el orden de los pasos y —lo
más útil— **qué debe rechazarte y con qué mensaje**: si un rechazo esperado no
aparece, eso es el hallazgo.

> **Antes de empezar.** El acceso por usuario y contraseña está abierto de forma
> temporal para estas pruebas. **Ciérralo al terminar** (ver el final del
> documento): mientras esté abierto, el SSO deja de ser el único camino.

## Los usuarios

Uno por rol, todos con la misma contraseña (la que fijaste al abrir la ventana;
no se guarda en este repo, que es público).

| Usuario | Rol | Qué hace en el sistema |
|---|---|---|
| `prueba-dpgc@sgc.local` | DPGC | Dirección de calidad: aprueba, revisa, cierra |
| `prueba-dpgc2@sgc.local` | DPGC | **Segunda persona de la DPGC.** Imprescindible: muchos controles comparan IDENTIDAD, no rol |
| `prueba-analista@sgc.local` | Analista de Calidad (DPGC) | Perfil operativo de la DPGC |
| `prueba-rcp@sgc.local` | Responsable de Calidad de Programa | Autoevalúa, trata hallazgos y no conformidades |
| `prueba-auditor@sgc.local` | Auditor Interno | Programa y ejecuta auditorías |
| `prueba-aprobador@sgc.local` | Autoridad Aprobadora | Publica documentos y presenta a SUNEDU |
| `prueba-rector@sgc.local` | Rectorado/VR | Cierra la revisión por la dirección |
| `prueba-multirol@sgc.local` | DPGC + Autoridad Aprobadora | Para comprobar que acumular roles **no** rompe la segregación |
| `prueba-dueno@sgc.local` | Dueño de Proceso | |
| `prueba-data@sgc.local` | Data Steward | |

### La regla que más sorprende

**Acumular roles suma permisos, pero no permite autoaprobarse.** Los controles
usan `allow_self_approval=0`, que compara la **persona**, no el rol. Por eso
`prueba-multirol` —que es DPGC *y* Autoridad Aprobadora— **no puede** aprobar ni
presentar un documento que creó él mismo; sí puede hacerlo con el de otro.

**Corolario práctico para UPeU: cada paso de control necesita dos personas
reales.** Si una sola persona acumula los dos roles y es la única, el flujo se
atasca — y eso no es un fallo del sistema, es la segregación funcionando.

---

## Orden recomendado

Los quince están numerados por dependencia: el 01 no necesita nada previo, el 10
recibe lo que escalan el 08 y el 09. Si vas a probar solo unos cuantos, el
recorrido más informativo es **01 → 02 → 03 → 05** (el núcleo documental y de
licenciamiento) y **06 → 07 → 08 → 10** (la cadena de auditoría hasta la acción
correctiva).

---

## 01 · Documento Controlado

**Quién:** DPGC redacta · DPGC2 revisa/aprueba · Autoridad Aprobadora publica.

1. `prueba-dpgc` crea un documento y adjunta el archivo. → **Enviar a revisión**.
2. `prueba-dpgc` intenta **Aprobar** el suyo. → debe rechazar: *Self approval is not allowed*.
3. `prueba-dpgc2` **Aprueba**. Mira el campo **Aprobado por**: debe decir `prueba-dpgc2`, y **no debe dejarte escribirlo** (es de solo lectura).
4. `prueba-aprobador` **Publica**.
5. Publica un segundo documento que **reemplace** al primero → el primero pasa solo a **Obsoleto**.

**Lo que debe rechazarte:** enviar a revisión sin archivo; aprobar sin declarar quién revisó; publicar sin las firmas.

## 02 · Evidencia

**Quién:** RCP o Analista registra · DPGC valida.

1. `prueba-rcp` crea una evidencia (tipo Enlace, con URL) con vigencia.
2. `prueba-dpgc` la **Observa** → vuelve al RCP → el RCP la **Subsana** → la DPGC la **Valida**.
3. Al validar, mira que se sincronice la **Trazabilidad** hacia el criterio o proceso enlazado.

**Nota:** una evidencia caduca sola al vencer la vigencia (pasa a **Vencida**, sin acción disponible). Es un final del camino, no un error.

## 03 · Autoevaluación

**Quién:** RCP valora · DPGC consolida y cierra.

1. `prueba-rcp` crea la autoevaluación sobre un marco del **Coneau** (no sobre el de licenciamiento: el sistema lo impide a propósito).
2. Valora criterios. Los que queden **No cumple** o **Cumple parcial** generan **Hallazgo** (flujo 09).
3. `prueba-dpgc` consolida y cierra → al cerrar se promueve la **vigencia oficial**.

## 04 · Aplicación de Instrumento (encuestas)

**Quién:** RCP planifica y ejecuta · DPGC cierra.

1. Necesitas un **Instrumento** creado (ver «Datos maestros» al final).
2. `prueba-rcp` crea la aplicación → **Iniciar campo** → registra resultados → **Cerrar aplicación**.
3. **Al cerrar, el sistema publica solo los valores de indicador.** Compruébalo en `Valor Indicador`: es el efecto que el diagrama dibuja en el carril «Sistema».

**Lo que debe rechazarte:** cerrar sin fecha de fin de campo.

## 05 · Informe de Cumplimiento (SUNEDU)

**Quién:** DPGC redacta · DPGC2 aprueba · Autoridad Aprobadora presenta.

1. `prueba-dpgc` crea el informe del año, sobre el marco **CBC-SUNEDU-2026**. Las 8 condiciones se autopoblan solas.
2. Evalúa las 8. Deja una en **Cumple parcial** y **no la justifiques**: al guardar debe rechazarte.
3. Justifícala → **Enviar a revisión** → `prueba-dpgc2` **Aprueba** (el autor no puede).
4. `prueba-aprobador` **Presenta a SUNEDU**. La fecha de presentación se sella sola.
5. Intenta **editar** el informe presentado → debe rechazarte: el hecho externo es inmutable.

**Prueba interesante:** con `prueba-multirol`, crea un informe y llévalo hasta Aprobado; intenta presentarlo tú mismo → rechazado, aunque tengas el rol.

## 06 · Programa de Auditoría

**Quién:** Auditor redacta · DPGC aprueba y cierra.

1. `prueba-auditor` crea el programa anual con responsable.
2. `prueba-dpgc` **Aprueba**. Mira **Aprobado por**: dice `prueba-dpgc` y es de solo lectura, aunque el auditor hubiera escrito otro nombre antes.
3. `prueba-auditor` **Inicia ejecución** → crea una auditoría bajo el programa (flujo 07).
4. `prueba-dpgc` intenta **Cerrar el programa** con esa auditoría sin concluir → **debe rechazarte**.

## 07 · Auditoría

**Quién:** Auditor ejecuta · DPGC cierra.

1. `prueba-auditor` crea la auditoría y **intenta iniciarla sin equipo** → rechazo; **sin criterios** → rechazo; **con un equipo sin nadie independiente** → rechazo.
2. Añade un miembro marcado *independiente del área* → **Iniciar auditoría** → **Marcar ejecutada**.
3. Emite el **Informe de Auditoría** y vincúlalo → **Emitir informe**.
4. `prueba-dpgc` **Cierra** (el auditor no puede).

**Prueba el candado nuevo:** pon a `prueba-auditor` como *responsable* de un proceso, crea una auditoría **a ese proceso** y ponte a ti mismo en el equipo → **debe rechazarte**: nadie audita su propio trabajo.

## 08 · Hallazgo de Auditoría

**Quién:** Auditor levanta · DPGC cierra.

1. `prueba-auditor` levanta un hallazgo tipo **No conformidad mayor**.
2. Intenta **Cerrarlo sin escalar** → **debe rechazarte**: una no conformidad se trata en su documento propio.
3. **Escala a NC** → se crea la **No Conformidad** (flujo 10) y el hallazgo queda *Escalado a NC*.
4. `prueba-dpgc` lo **Cierra**. Para reabrirlo, usa **Reabrir escalado** (no «Reabrir», que es para los que nunca escalaron — y te lo dirá).
5. Levanta un hallazgo tipo **Fortaleza** e intenta escalarlo → rechazo.

## 09 · Hallazgo (de autoevaluación)

**Quién:** RCP trata · DPGC verifica.

1. `prueba-rcp` crea un hallazgo (el código se genera solo: `HALL-2026-NNNN`).
2. **Tratar** → **Enviar a verificación**.
3. `prueba-rcp` intenta **Cerrar eficaz** → rechazo: quien trata no verifica.
4. `prueba-dpgc` **Cierra eficaz** o **no eficaz**, o **Reabre**.
5. Prueba a escalar una **Fortaleza** → rechazo.

**Ojo:** *Cerrado no eficaz* no tiene salida. Es una decisión de proceso pendiente de tu criterio (ver CONCORDANCIA).

## 10 · No Conformidad

**Quién:** RCP analiza y trata · DPGC verifica y cierra.

1. Ábrela como **No conformidad mayor** → verás que se marca sola *requiere análisis de causa*.
2. **Analizar causa** sin responsable → rechazo. Asigna responsable → pasa.
3. **Tratar** sin análisis redactado → rechazo.
4. **Enviar a verificación** sin plazo → rechazo; sin plan ni corrección → rechazo.
5. `prueba-dpgc` **Cierra eficaz** con evidencia de cierre. Mira **Verificada por**: dice `prueba-dpgc` y es de solo lectura.

## 11 · Plan de Mejora

**Quién:** RCP redacta · DPGC aprueba y cierra. (La DPGC **no puede crear** planes: la separación aquí la impone el permiso, no el workflow.)

1. `prueba-rcp` crea el plan y le cuelga acciones de mejora.
2. `prueba-dpgc` intenta **Aprobar y ejecutar** sin acciones o sin responsable → rechazo.
3. Aprueba. Mira **Aprobado por**: lo puso el sistema.
4. Intenta **Cerrar el plan** con alguna acción sin verificar → rechazo. Solo cierra con **todas** en *Verificada eficaz*.

## 12 · Acción de Mejora

**Quién:** RCP ejecuta · DPGC verifica.

1. `prueba-rcp` crea la acción y la **Inicia**: sin responsable o sin fecha de compromiso → rechazo. (No es burocracia: sin fecha, la acción nunca pone el plan en rojo, y sin responsable el aviso de vencimiento no llega a nadie.)
2. **Marcar ejecutada** → el avance sube a 100.
3. `prueba-dpgc` intenta **Verificar eficaz** sin evidencia de cierre → rechazo.
4. Verifica. Mira **Verificada por**.
5. Prueba **Verificar no eficaz** → el avance vuelve a 0 → **Reabrir** → vuelve a ejecución.

## 13 · Riesgo

**Quién:** Dueño de Proceso avanza · DPGC cierra y materializa.

1. `prueba-dueno` crea el riesgo **y le asigna la matriz `MR-5x5`** (sin matriz, el nivel no se puede calcular y queda en blanco a propósito).
2. Crea una **Evaluación de Riesgo** con probabilidad e impacto → comprueba que el **score y el nivel se calculan** (1×1 → Bajo, 5×5 → Extremo). Sin probabilidad o impacto → rechazo.
3. **Evaluar** sin ninguna evaluación registrada → rechazo. **Iniciar tratamiento** sin ningún tratamiento → rechazo.
4. **Monitorear** → `prueba-dpgc` **Materializa** → **se crea sola una No Conformidad** (flujo 10). Compruébalo.
5. Intenta **Cerrar** el riesgo materializado con esa NC abierta → rechazo.

**Prueba el candado de independencia:** pon de `propietario` del riesgo a la misma persona que va a cerrarlo → rechazo.

## 14 · Tratamiento de Riesgo

**Quién:** Dueño de Proceso implementa · DPGC verifica.

1. `prueba-dueno` crea el tratamiento e intenta **Iniciar** sin estrategia, sin descripción, sin responsable o sin plazo → rechazo en cada caso.
2. **Marcar implementado** sin evidencia vinculada → rechazo. Crea una `Evidencia` y vincúlala.
3. **Verificar** sin resultado o sin **nivel residual** → rechazo.
4. **Lo importante:** intenta verificar siendo el **responsable** del tratamiento → rechazo. *Quien implementa no verifica.*
5. Prueba **Verificar no eficaz** → vuelve a ejecución y **se borra el sello de implementación**, para que la siguiente vuelta firme de nuevo.

## 15 · Revisión por la Dirección

**Quién:** DPGC prepara y realiza · **Rectorado cierra** (`prueba-rector@sgc.local`).

1. `prueba-dpgc` crea la revisión y registra entradas. Intenta **Realizar** con menos de las **seis** entradas del §9.3.2 → rechazo, con la lista de las que faltan. Una fila vacía no cuenta.
2. Registra las tres salidas del §9.3.3 con responsable y adjunta el acta.
3. `prueba-dpgc` intenta **Cerrar** → no le aparece la acción: es del Rectorado.
4. `prueba-rector` **Cierra**. Mira **Cerrada por**.
5. Intenta editar la revisión **ya cerrada** → rechazo. La única vía es **Reabrir revisión**.

---

## Datos maestros que ya están sembrados

Para que ningún flujo se quede a medias por falta de catálogo:

| Qué | Para qué |
|---|---|
| `MR-5x5` (Matriz de Riesgo) | Sin ella el nivel de riesgo **no se calcula** y queda en blanco (deliberado: sin criterios no hay valoración) |
| `INS-SAT-EST` (Instrumento) | El flujo 04 no se puede crear sin un instrumento |
| `GI-EST` (Grupo de Interés) | Lo pide el instrumento |

Ya existían: 3 marcos normativos con 185 elementos, 22 procesos, 32 programas-sede, 93 indicadores y el periodo 2026-I.

**Producción está a cero de documentos operativos**: todo lo que crees será tuyo, y lo que veas en un tablero será consecuencia de lo que hayas hecho.

---

## Al terminar: cerrar la ventana de acceso por contraseña

Mientras siga abierta, el SSO no es el único camino de entrada. El comando lo tienes tú (es el inverso del que usaste para abrirla); en cuanto lo corras, estos usuarios de prueba dejan de poder entrar por contraseña.

Los usuarios `prueba-*@sgc.local` pueden quedarse deshabilitados en vez de borrarse: conservan la trazabilidad de lo que hicieron durante las pruebas, que es justo lo que un auditor querría poder mirar.
