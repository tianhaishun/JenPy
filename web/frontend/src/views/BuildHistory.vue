<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NDataTable, NButton, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import StatusBall from '../components/StatusBall.vue'
import { fmtDuration, buildNumber, statusText } from '../theme'

const router = useRouter()
const message = useMessage()
const data = ref<BuildRecord[]>([])
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    data.value = await api.listBuilds(100)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

const columns: DataTableColumns<BuildRecord> = [
  {
    title: 'S',
    key: 'status_ball',
    width: 36,
    render: (row) => h(StatusBall, { status: row.status, size: 14 }),
  },
  {
    title: '构建',
    key: 'build_num',
    render(row) {
      return h('a', {
        class: 'build-link',
        onClick: () => router.push(`/builds/${row.build_id}`),
      }, `#${buildNumber(row.build_id)}`)
    },
  },
  { title: '流水线', key: 'pipeline' },
  {
    title: '状态', key: 'status_text',
    render: (row) => h('span', {
      class: `status-text ${row.status}`,
    }, statusText(row.status)),
  },
  {
    title: '耗时', key: 'duration',
    render: (row) => fmtDuration(row.duration),
  },
  { title: '开始时间', key: 'started_at' },
  {
    title: '步骤', key: 'steps',
    render: (row) => {
      const ok = row.steps.filter(s => s.success).length
      return `${ok}/${row.steps.length}`
    },
  },
]

onMounted(refresh)
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">构建历史</h2>
      <NButton size="small" @click="refresh" :loading="loading">刷新</NButton>
    </div>
    <NDataTable
      :columns="columns"
      :data="data"
      :loading="loading"
      size="small"
      striped
    />
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
</style>

<style>
/* 表格内的链接和状态样式（非 scoped 因为 render 函数生成的 DOM） */
.build-link {
  color: #0f6ab0;
  cursor: pointer;
  font-weight: 500;
}
.build-link:hover { text-decoration: underline; }

.status-text { font-size: 13px; }
.status-text.success { color: #16a34a; }
.status-text.failed { color: #dc2626; }
.status-text.running { color: #2563eb; }
.status-text.queued { color: #999; }
</style>
