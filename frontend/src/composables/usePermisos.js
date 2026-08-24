/**
 * Permisos efectivos del usuario, para pintar la interfaz según su rol.
 *
 * El mapa llega en el boot (`window.permisos_ui`, ver sgc/permisos_ui.py), así
 * que no cuesta ninguna llamada: está disponible desde el primer render.
 *
 * ⚠️ Esto NO es un control de seguridad — quien decide es el backend en cada
 * operación. Sirve para no ofrecerle a nadie una pantalla donde solo va a
 * chocar: antes, un rol de solo lectura veía el botón «Nuevo», rellenaba el
 * formulario entero y recibía un 403 al final.
 *
 * Ante la duda, PERMITE. Un DocType que no está en el mapa (File, User, o uno
 * recién creado que nadie listó) no debe desaparecer de la interfaz por
 * omisión: se deja pasar y que mande el backend. Ocultar de más es peor que
 * ocultar de menos, porque un botón que falta no da ningún mensaje de error.
 */
import { computed } from 'vue'

function mapa() {
  // En dev (Vite, sin el boot de Jinja) no hay mapa: no se oculta nada.
  return typeof window !== 'undefined' ? window.permisos_ui || null : null
}

/** ¿Puede el usuario hacer `accion` sobre `doctype`? */
export function puede(doctype, accion = 'read') {
  const m = mapa()
  if (!m || !doctype) return true
  const p = m[doctype]
  if (!p) return true // DocType ajeno al SGC: no opinamos
  return Boolean(p[accion])
}

/**
 * DocTypes sobre los que esta persona EJECUTA acciones de flujo.
 *
 * No es lo mismo que lo que puede leer, y confundirlo es lo que dejaba el menú
 * sin personalizar: medido en producción el 2026-08-24, un Dueño de Proceso
 * trabajaba 4 DocTypes y veía 36. Filtrar por lectura casi no filtra, porque en
 * un sistema de calidad casi todos pueden leer casi todo — y deben: un auditor
 * no puede auditar lo que no ve.
 *
 * Lo calcula el backend desde los workflows vivos (ver `doctypes_de_trabajo`),
 * así que si una transición cambia de rol, el menú cambia con ella.
 *
 * Lista vacía = «no sé»: en dev no hay boot, y un usuario sin transiciones
 * asignadas no debe quedarse sin menú. El llamador decide qué hacer con eso.
 */
export function doctypesDeTrabajo() {
  if (typeof window === 'undefined') return []
  return window.doctypes_trabajo || []
}

/**
 * ¿Este DocType se mueve por un ciclo de vida (Workflow activo)?
 *
 * Se deduciría de que el campo `estado` fuese de solo lectura, pero en este
 * sitio ninguno lo es —comprobado contra los 15 workflows—, así que el backend
 * manda la lista explícita en el boot.
 *
 * Sin lista (dev, sin boot) devuelve false: mejor no pintar acciones que
 * pintarlas donde no las hay.
 */
export function tieneFlujo(doctype) {
  if (typeof window === 'undefined' || !doctype) return false
  return (window.doctypes_con_flujo || []).includes(doctype)
}

/** Roles del usuario (los inyecta el boot). */
export function rolesUsuario() {
  return (typeof window !== 'undefined' && window.user_roles) || []
}

export function tieneRol(rol) {
  return rolesUsuario().includes(rol)
}

export function usePermisos() {
  return {
    puede,
    puedeLeer: (dt) => puede(dt, 'read'),
    puedeCrear: (dt) => puede(dt, 'create'),
    puedeEditar: (dt) => puede(dt, 'write'),
    roles: computed(() => rolesUsuario()),
    tieneRol,
  }
}
