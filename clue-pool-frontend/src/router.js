import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('./views/Login.vue'), meta: { public: true } },
  { path: '/welcome', component: () => import('./views/Welcome.vue'), meta: { public: true, bare: true } },
  { path: '/', component: () => import('./views/Home.vue') },
  { path: '/clue/:id', component: () => import('./views/Detail.vue') },
  { path: '/submit', component: () => import('./views/Submit.vue') },
  { path: '/mine', component: () => import('./views/Mine.vue') },
  { path: '/admin', component: () => import('./views/Admin.vue') },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach(to => {
  if (!to.meta.public && !localStorage.getItem('token')) return '/login'
})

export default router
