import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// Mismo patrón que Frappe CRM / Helpdesk: la sesión vive en la cookie
// `user_id` que Frappe ya setea al iniciar sesión (same-origin, sin CORS).
// No hay pantalla de login propia — se delega al /login nativo de Frappe
// (mismo dominio, mismo tema de marca vía hooks.py) y se vuelve a /sgc
// via ?redirect-to.
export const useSessionStore = defineStore('sgc-session', () => {
  function sessionUser() {
    const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    const user = cookies.get('user_id')
    return user && user !== 'Guest' ? decodeURIComponent(user) : null
  }

  const user = ref(sessionUser())
  const isLoggedIn = computed(() => !!user.value)

  // window.user_fullname solo existe en producción (inyectado por www/sgc.py
  // vía jinjaBootData); en dev no hay boot, así que cae al email de sesión.
  const displayName = computed(() => window.user_fullname || user.value)

  // El endpoint /api/method/logout solo acepta POST (Frappe api/v2). Una
  // navegación GET (window.location) devolvía 403. Se hace POST con el CSRF
  // token (inyectado en window por www/sgc.py) y luego se redirige al login.
  async function logout() {
    try {
      await fetch('/api/method/logout', {
        method: 'POST',
        headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
      })
    } catch (e) {
      // aunque falle la llamada, redirigimos igual al login
    }
    window.location.href = '/login?redirect-to=/sgc'
  }

  function redirectToLogin() {
    window.location.href = '/login?redirect-to=/sgc'
  }

  return { user, isLoggedIn, displayName, logout, redirectToLogin }
})
