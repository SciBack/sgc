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

  function logout() {
    window.location.href = '/api/method/logout'
  }

  function redirectToLogin() {
    window.location.href = '/login?redirect-to=/sgc'
  }

  return { user, isLoggedIn, logout, redirectToLogin }
})
