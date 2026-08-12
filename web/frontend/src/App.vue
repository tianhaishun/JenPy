<script setup lang="ts">
import { h, computed } from 'vue'
import { NConfigProvider, NMessageProvider, NDialogProvider, NLayout, NLayoutHeader, NLayoutSider, NLayoutContent, NIcon, NMenu } from 'naive-ui'
import { RouterView, useRoute, useRouter } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import type { Component } from 'vue'
import {
  SpeedometerOutline,
  TimeOutline,
  CubeOutline,
  HammerOutline,
  AddCircleOutline,
  PeopleOutline,
} from '@vicons/ionicons5'
import { colors } from './theme'

const route = useRoute()
const router = useRouter()

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// Jenkins 经典侧边栏菜单顺序：New Item / People / Build History / Manage Jenkins / My Views
const menuOptions: MenuOption[] = [
  { label: 'Dashboard', key: '/dashboard', icon: renderIcon(SpeedometerOutline) },
  { type: 'divider', key: 'd1' },
  { label: 'New Item', key: '/pipelines', icon: renderIcon(AddCircleOutline) },
  { label: 'People', key: '/people', icon: renderIcon(PeopleOutline), disabled: true },
  { label: 'Build History', key: '/history', icon: renderIcon(TimeOutline) },
  { label: 'Manage JenPy', key: '/manage', icon: renderIcon(HammerOutline) },
]

// 高亮当前路由
const activeKey = computed(() => {
  if (route.path.startsWith('/builds')) return '/history'
  if (route.path.startsWith('/job')) return '/dashboard'
  if (route.path.startsWith('/editor')) return '/pipelines'
  return route.path
})

// 面包屑
const breadcrumbs = computed(() => {
  const crumbs: { label: string; path?: string }[] = [{ label: 'Dashboard', path: '/dashboard' }]
  if (route.path === '/dashboard') return [{ label: 'Dashboard' }]
  if (route.path.startsWith('/history')) crumbs.push({ label: 'Build History' })
  if (route.path.startsWith('/pipelines')) crumbs.push({ label: 'New Item / Pipelines' })
  if (route.path.startsWith('/manage')) crumbs.push({ label: 'Manage JenPy' })
  if (route.path.startsWith('/builds/')) crumbs.push({ label: 'Build Detail' })
  if (route.path.startsWith('/job/')) crumbs.push({ label: decodeURIComponent(route.params.name as string) })
  return crumbs
})

const themeOverrides = {
  common: {
    primaryColor: colors.headerBg,
    primaryColorHover: '#406278',
    primaryColorPressed: '#284553',
    bodyColor: colors.bgPage,
    cardColor: colors.bgCard,
    textColorBase: colors.textPrimary,
    textColor1: colors.textPrimary,
    textColor2: colors.textSecondary,
    textColor3: colors.textMuted,
    borderColor: colors.border,
  },
}
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <NLayout position="absolute" style="height: 100vh">
          <!-- Jenkins 经典深蓝 header -->
          <NLayoutHeader bordered class="jenkins-header">
            <div class="header-brand" @click="router.push('/dashboard')" style="cursor: pointer;">
              <span class="brand-logo">🛠</span>
              <span class="brand-name">JenPy</span>
              <span class="brand-sub">[Jenkins]</span>
            </div>
            <div class="header-search">
              <input type="text" placeholder="搜索..." class="search-input" />
            </div>
            <div class="header-right">
              <a href="/docs" target="_blank" class="header-link">API 文档</a>
              <span class="header-user">admin</span>
            </div>
          </NLayoutHeader>

          <NLayout position="absolute" style="top: 48px; bottom: 28px;" has-sider>
            <!-- 左侧导航（Jenkins #side-panel） -->
            <NLayoutSider
              bordered
              :width="200"
              content-style="padding-top: 8px; background: #f8f8f8;"
            >
              <NMenu
                :value="activeKey"
                :options="menuOptions"
                :indent="18"
                @update:value="(key: string) => router.push(key)"
              />
            </NLayoutSider>

            <!-- 主内容区 -->
            <NLayoutContent content-style="padding: 16px 20px; background: #f0f0f0;">
              <!-- 面包屑导航 -->
              <div class="breadcrumb-bar" v-if="breadcrumbs.length > 0">
                <template v-for="(crumb, i) in breadcrumbs" :key="i">
                  <a v-if="crumb.path" class="crumb-link" @click="router.push(crumb.path!)">{{ crumb.label }}</a>
                  <span v-else class="crumb-current">{{ crumb.label }}</span>
                  <span v-if="i < breadcrumbs.length - 1" class="crumb-sep">/</span>
                </template>
              </div>
              <RouterView />
            </NLayoutContent>
          </NLayout>

          <!-- Jenkins 风格 footer -->
          <div class="jenkins-footer">
            <span>JenPy ver. 0.1.0</span>
            <span class="footer-sep">·</span>
            <a href="/docs" target="_blank" class="footer-link">REST API</a>
          </div>
        </NLayout>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
}

/* Jenkins 深蓝 header */
.jenkins-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: linear-gradient(180deg, #3b5a6b 0%, #335061 100%);
  color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}
.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brand-logo { font-size: 20px; }
.brand-name { font-size: 18px; font-weight: 700; color: #fff; }
.brand-sub { font-size: 12px; color: rgba(255, 255, 255, 0.5); margin-left: 4px; }

.header-search { flex: 1; display: flex; justify-content: center; }
.search-input {
  width: 240px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 3px;
  background: rgba(255,255,255,0.1);
  color: #fff;
  font-size: 12px;
  outline: none;
}
.search-input::placeholder { color: rgba(255,255,255,0.4); }
.search-input:focus { background: rgba(255,255,255,0.15); }

.header-right { display: flex; align-items: center; gap: 16px; }
.header-link { color: rgba(255,255,255,0.85); font-size: 13px; text-decoration: none; }
.header-link:hover { color: #fff; }
.header-user { color: rgba(255,255,255,0.7); font-size: 13px; }

/* 面包屑 */
.breadcrumb-bar {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e0;
}
.crumb-link { color: #0f6ab0; cursor: pointer; }
.crumb-link:hover { text-decoration: underline; }
.crumb-current { color: #333; font-weight: 500; }
.crumb-sep { margin: 0 6px; color: #ccc; }

/* Jenkins footer */
.jenkins-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #fff;
  border-top: 1px solid #e0e0e0;
  font-size: 11px;
  color: #999;
}
.footer-sep { color: #ccc; }
.footer-link { color: #0f6ab0; text-decoration: none; }
.footer-link:hover { text-decoration: underline; }

/* 全局卡片圆角 */
.n-card { border-radius: 4px !important; }
</style>
