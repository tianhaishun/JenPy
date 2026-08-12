<script setup lang="ts">
/**
 * Dashboard —— 一比一对照 Jenkins 首页。
 *
 * 结构：
 *   - 顶部：面包屑 + 标题 + 操作按钮
 *   - 主体：Job 列表表格（JobList 组件）
 *   - 底部：Build Queue + Build Executor Status 两个并排 widget（Jenkins 标志性布局）
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NButton, NSpace, NCard } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import JobList from './JobList.vue'
import StatusBall from '../components/StatusBall.vue'
import { buildNumber } from '../theme'

const router = useRouter()
const message = useMessage()
const builds = ref<BuildRecord[]>([])
const loading = ref(false)

const jobListRef = ref<InstanceType<typeof JobList> | null>(null)

// 队列中的构建（从 JobList 暴露，或独立加载）
const runningBuilds = computed(() =>
  builds.value.filter(b => b.status === 'running' || b.status === 'queued')
)

async function refresh() {
  loading.value = true
  try {
    builds.value = await api.listBuilds(100)
    jobListRef.value?.refresh()
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <!-- 面包屑（Jenkins 风格） -->
    <div class="breadcrumb">
      <span class="crumb-current">Dashboard</span>
    </div>

    <!-- 标题栏 -->
    <div class="page-header">
      <h1 class="page-title">构建仪表盘</h1>
      <NSpace>
        <NButton size="small" @click="refresh" :loading="loading">刷新</NButton>
      </NSpace>
    </div>

    <!-- Job 列表表格（Jenkins 核心） -->
    <NCard size="small" style="margin-bottom: 16px;">
      <template #header>
        <span class="card-title">Job 列表</span>
      </template>
      <template #header-extra>
        <NButton text size="small" @click="router.push('/history')">构建历史</NButton>
      </template>
      <JobList ref="jobListRef" />
    </NCard>

    <!-- 底部：Build Queue + Executor Status（Jenkins 标志性布局） -->
    <div class="bottom-widgets">
      <!-- Build Queue -->
      <NCard size="small" class="widget-card">
        <template #header>
          <span class="card-title">Build Queue</span>
        </template>
        <div v-if="runningBuilds.length === 0" class="widget-empty">
          No builds in the queue.
        </div>
        <div v-else>
          <div v-for="b in runningBuilds" :key="b.build_id" class="queue-item">
            <StatusBall :status="b.status" :size="12" />
            <span class="queue-name">{{ b.pipeline }}</span>
            <span class="queue-num">#{{ buildNumber(b.build_id) }}</span>
          </div>
        </div>
      </NCard>

      <!-- Build Executor Status -->
      <NCard size="small" class="widget-card">
        <template #header>
          <span class="card-title">Build Executor Status</span>
        </template>
        <div class="executor-item">
          <span class="executor-name">executor-1</span>
          <span class="executor-state idle">Idle</span>
        </div>
        <div class="executor-meta">
          串行模式 · 同一时刻仅一个构建运行
        </div>
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.breadcrumb {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}
.crumb-current { color: #333; font-weight: 500; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

/* 底部 widget 区域 */
.bottom-widgets {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.widget-card {
  min-height: 100px;
}

.widget-empty {
  color: #999;
  font-size: 13px;
  padding: 12px 0;
  font-style: italic;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
}
.queue-name { color: #0f6ab0; }
.queue-num { color: #999; font-size: 12px; margin-left: auto; }

.executor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}
.executor-name { color: #333; font-weight: 500; }
.executor-state { font-size: 12px; }
.executor-state.idle { color: #16a34a; }

.executor-meta {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  font-size: 11px;
  color: #999;
}
</style>
