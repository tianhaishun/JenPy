<script setup lang="ts">
import { h, computed } from 'vue'
import { NConfigProvider, NMessageProvider, NDialogProvider, NLayout, NLayoutHeader, NLayoutSider, NLayoutContent, NIcon, NMenu } from 'naive-ui'
import { RouterView, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import type { Component } from 'vue'
import {
  SpeedometerOutline,
  TimeOutline,
  CubeOutline,
  HammerOutline,
} from '@vicons/ionicons5'
import { colors } from './theme'

const route = useRoute()

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// Jenkins 风格侧边栏：New Item / Build History / 流水线 等
const menuOptions: MenuOption[] = [
  { label: 'Dashboard', key: '/dashboard', icon: renderIcon(SpeedometerOutline) },
  { label: '构建历史', key: '/history', icon: renderIcon(TimeOutline) },
  { label: '流水线', key: '/pipelines', icon: renderIcon(CubeOutline) },
  { label: '管理', key: '/manage', icon: renderIcon(HammerOutline) },
]

// 高亮当前路由对应的菜单项
const activeKey = computed(() => {
  // /builds/:id 归到构建历史
  if (route.path.startsWith('/builds')) return '/history'
  if (route.path.startsWith('/editor')) return '/pipelines'
  return route.path
})

// Naive UI 浅色主题覆盖：注入 Jenkins 配色
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
          <!-- Jenkins 经典深蓝 header 条 -->
          <NLayoutHeader bordered class="jenkins-header">
            <div class="header-brand">
              <span class="brand-logo">🛠</span>
              <span class="brand-name">JenPy</span>
              <span class="brand-sub">CI/CD 平台</span>
            </div>
            <div class="header-right">
              <a href="/docs" target="_blank" class="header-link">API 文档</a>
            </div>
          </NLayoutHeader>

          <NLayout position="absolute" style="top: 48px" has-sider>
            <!-- 左侧导航 -->
            <NLayoutSider
              bordered
              :width="200"
              content-style="padding-top: 8px; background: #fafafa;"
            >
              <NMenu
                :value="activeKey"
                :options="menuOptions"
                :indent="18"
                @update:value="(key: string) => $router.push(key)"
              />
              <!-- Jenkins 风格底部状态 -->
              <div class="sider-footer">
                <div class="executor-status">
                  <div class="executor-title">构建执行器</div>
                  <div class="executor-info">
                    <span class="dot active" />
                    在线 · 串行模式
                  </div>
                </div>
              </div>
            </NLayoutSider>

            <!-- 主内容区 -->
            <NLayoutContent content-style="padding: 20px; background: #f0f0f0;">
              <RouterView />
            </NLayoutContent>
          </NLayout>
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

/* Jenkins 经典深蓝 header */
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
.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}
.brand-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-left: 4px;
}

.header-right { display: flex; align-items: center; }
.header-link {
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  text-decoration: none;
}
.header-link:hover { color: #fff; }

/* 侧边栏底部执行器状态（Jenkins 标志性 widget 简化版） */
.sider-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
  background: #fafafa;
}
.executor-title {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.executor-info {
  font-size: 12px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
}
.executor-info .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #16a34a;
}
.executor-info .dot.active {
  box-shadow: 0 0 6px rgba(22, 163, 74, 0.6);
}

/* 全局：表格/卡片圆角更小，信息密度更高（Jenkins 风格） */
.n-card {
  border-radius: 4px !important;
}
</style>
