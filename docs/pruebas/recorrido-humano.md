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
