import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from './utils/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('./views/AuthView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('./views/ChatView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const isPublic = to.meta?.public
  const requiresAuth = to.meta?.requiresAuth
  
  if (requiresAuth && !isAuthenticated()) {
    next('/login')
  } else if (isPublic && isAuthenticated()) {
    next('/')
  } else {
    next()
  }
})

export default router
