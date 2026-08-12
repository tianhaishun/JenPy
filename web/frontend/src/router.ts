import { createRouter, createWebHashHistory } from 'vue-router'

// 用 hash history，避免 FastAPI SPA fallback 的边缘情况
export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
    { path: '/history', name: 'history', component: () => import('./views/BuildHistory.vue') },
    { path: '/builds/:id', name: 'build-detail', component: () => import('./views/BuildDetail.vue') },
    { path: '/job/:name', name: 'job-detail', component: () => import('./views/JobDetail.vue') },
    { path: '/pipelines', name: 'pipelines', component: () => import('./views/PipelineList.vue') },
    { path: '/editor/:name', name: 'editor', component: () => import('./views/PipelineEditor.vue') },
    { path: '/manage', name: 'manage', component: () => import('./views/Manage.vue') },
  ],
})
