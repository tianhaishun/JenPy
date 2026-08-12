<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NCard, NButton, NSpace, NStatistic, NGrid, NGridItem, NEmpty } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import StatusBall from '../components/StatusBall.vue'
import { fmtDuration, buildNumber, statusText, colors } from '../theme'

const router = useRouter()
const message = useMessage()
const builds = ref<BuildRecord[]>([])
const loading = ref(false)

const successCount = computed(() => builds.value.filter(b => b.status === 'success').length)
const failCount = computed(() => builds.value.filter(b => b.status === 'failed').length)
const runningBuilds = computed(() => builds.value.filter(b => b.status === 'running' || b.status === 'queued'))

async function refresh() {
  loading.value = true
  try {
    builds.value = await api.listBuilds(50)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

async function triggerRun() {
  try {
    const resp = await api.triggerBuild('jenpy.yaml')
    message.success(`构建已触发: ${resp.build_id}`)
    setTimeout(() => router.push(`/builds/${resp.build_id}`), 500)
  } catch (e) {
    message.error(`触发失败: ${(e as Error).message}`)
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <h2 class="page-title">Dashboard</h2>
      <NSpace>
        <NButton size="small" @click="refresh" :loading="loading">刷新</NButton>
        <NButton size="small" type="primary" @click="triggerRun">
          🚀 立即构建
        </NButton>
      </NSpace>
    </div>

    <!-- 统计卡片（Jenkins 风格紧凑数字） -->
    <NGrid :cols="4" :x-gap="12" style="margin-bottom: 16px;">
      <NGridItem>
        <NCard size="small">
          <NStatistic label="总构建" :value="builds.length" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard size="small">
          <div class="stat-label">成功</div>
          <div class="stat-value" style="color: #16a34a;">
            {{ successCount }}
          </div>
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard size="small">
          <div class="stat-label">失败</div>
          <div class="stat-value" style="color: #dc2626;">
            {{ failCount }}
          </div>
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard size="small">
          <div class="stat-label">成功率</div>
          <div class="stat-value" style="color: #335061;">
            {{ builds.length ? Math.round(successCount / builds.length * 100) : 0 }}%
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <NGrid :cols="3" :x-gap="12" :y-gap="12">
      <!-- 左侧 2/3：构建历史列表（Jenkins 紧凑行风格） -->
      <NGridItem :span="2">
        <NCard size="small">
          <template #header>
            <span class="card-title">构建历史</span>
          </template>
          <template #header-extra>
            <NButton text size="small" @click="router.push('/history')">查看全部</NButton>
          </template>

          <div v-if="builds.length === 0 && !loading">
            <NEmpty description="暂无构建记录" style="padding: 30px;">
              <template #extra>
                <NButton size="small" type="primary" @click="triggerRun">开始第一次构建</NButton>
              </template>
            </NEmpty>
          </div>

          <!-- Jenkins 风格：每行一个构建，状态球开头 -->
          <table v-else class="build-table">
            <tbody>
              <tr
                v-for="b in builds"
                :key="b.build_id"
                class="build-row"
                @click="router.push(`/builds/${b.build_id}`)"
              >
                <td class="col-ball">
                  <StatusBall :status="b.status" :size="16" />
                </td>
                <td class="col-pipeline">
                  <span class="pipeline-name">{{ b.pipeline }}</span>
                  <span class="build-num">#{{ buildNumber(b.build_id) }}</span>
                </td>
                <td class="col-status">
                  <span class="status-label" :class="b.status">{{ statusText(b.status) }}</span>
                </td>
                <td class="col-duration">{{ fmtDuration(b.duration) }}</td>
                <td class="col-time">{{ b.started_at.slice(11) }}</td>
              </tr>
            </tbody>
          </table>
        </NCard>
      </NGridItem>

      <!-- 右侧 1/3：Build Queue + 执行器状态（Jenkins 标志性 widget） -->
      <NGridItem :span="1">
        <NCard size="small" style="margin-bottom: 12px;">
          <template #header>
            <span class="card-title">构建队列</span>
          </template>
          <div v-if="runningBuilds.length === 0" class="queue-empty">
            队列为空
          </div>
          <div v-else>
            <div v-for="b in runningBuilds" :key="b.build_id" class="queue-item">
              <StatusBall :status="b.status" :size="12" />
              <span class="queue-name">{{ b.pipeline }}</span>
              <span class="queue-num">#{{ buildNumber(b.build_id) }}</span>
            </div>
          </div>
        </NCard>

        <NCard size="small">
          <template #header>
            <span class="card-title">执行器状态</span>
          </template>
          <div class="executor-row">
            <StatusBall status="success" :size="10" />
            <span>executor-1</span>
            <span class="executor-state">空闲</span>
          </div>
          <div class="executor-meta">
            串行模式 · 同一时刻仅一个构建运行
          </div>
        </NCard>
      </NGridItem>
    </NGrid>
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

.stat-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

/* Jenkins 风格构建列表表格 */
.build-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.build-row {
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.build-row:hover {
  background: #f5f5f5;
}
.build-row td {
  padding: 8px 6px;
  vertical-align: middle;
}
.col-ball { width: 28px; }
.col-pipeline { min-width: 0; }
.col-status { width: 70px; }
.col-duration { width: 70px; color: #666; }
.col-time { width: 70px; color: #999; font-size: 12px; }

.pipeline-name {
  font-weight: 500;
  color: #333;
  margin-right: 8px;
}
.build-num {
  color: #999;
  font-size: 12px;
}

.status-label {
  font-size: 12px;
}
.status-label.success { color: #16a34a; }
.status-label.failed { color: #dc2626; }
.status-label.running { color: #2563eb; }
.status-label.queued { color: #999; }

/* 队列 widget */
.queue-empty {
  color: #999;
  font-size: 13px;
  padding: 12px 0;
  text-align: center;
}
.queue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}
.queue-name { color: #333; }
.queue-num { color: #999; font-size: 12px; margin-left: auto; }

/* 执行器 widget */
.executor-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #333;
  padding: 4px 0;
}
.executor-state {
  margin-left: auto;
  color: #16a34a;
  font-size: 12px;
}
.executor-meta {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  font-size: 11px;
  color: #999;
}
</style>
