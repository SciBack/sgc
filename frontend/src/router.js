import { createRouter, createWebHistory } from 'vue-router'
import { useSessionStore } from './stores/session'

const routes = [
  {
    path: '/',
    component: () => import('./layouts/AppShell.vue'),
    children: [
      { path: '', name: 'Home', component: () => import('./pages/Home.vue') },
      {
        path: 'lista/:doctype',
        name: 'DoctypeList',
        component: () => import('./pages/DoctypeList.vue'),
        props: true,
      },
      {
        path: 'doc/:doctype/new',
        name: 'DocNew',
        component: () => import('./pages/DocForm.vue'),
        props: (route) => ({ doctype: route.params.doctype, name: 'new' }),
      },
      {
        path: 'doc/:doctype/:name',
        name: 'DocForm',
        component: () => import('./pages/DocForm.vue'),
        props: true,
      },
      {
        path: 'tablero',
        name: 'Tablero',
        component: () => import('./pages/Tablero.vue'),
      },
      {
        path: 'acreditacion/autoevaluacion/:name',
        name: 'AutoevaluacionDetalle',
        component: () => import('./pages/AutoevaluacionDetalle.vue'),
        props: true,
      },
    ],
  },
  { path: '/:pathMatch(.*)*', name: 'NotFound', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory('/sgc'),
  routes,
})

router.beforeEach((to) => {
  const session = useSessionStore()
  if (!session.isLoggedIn) {
    session.redirectToLogin()
    return false
  }
})
