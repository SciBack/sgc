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
