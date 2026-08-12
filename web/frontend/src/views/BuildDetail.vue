<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, NCard, NButton, NSpace } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import StatusBall from '../components/StatusBall.vue'
import LogViewer from '../components/LogViewer.vue'
import { fmtDuration, buildNumber, statusText } from '../theme'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const buildId = route.params.id as string
const build = ref<BuildRecord | null>(null)
const logLines = ref<{ stage: string; step: string; line: string }[]>([])
const done = ref(false)
const logContainer = ref<HTMLElement | null>(null)

let eventSource: EventSource | null = null
let pollTimer: number | null = null

const steps = computed(() => build.value?.steps || [])

function stepBallStatus(success: boolean, isRunning: boolean): string {
  if (isRunning) return 'running'
  return success ? 'success' : 'failed'
}

async function loadBuild() {
  try {
    build.value = await api.getBuild(buildId)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  }
}

function connectStream() {
  eventSource = api.streamBuild(buildId)

  eventSource.addEventListener('line', (ev: MessageEvent) => {
    const data = JSON.parse(ev.data)
    logLines.value.push(data)
    if (data.line.trim()) {
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    }
  })

  eventSource.addEventListener('step', () => {
    // 步骤完成时刷新状态
    loadBuild()
  })

  eventSource.addEventListener('done', (ev: MessageEvent) => {
    done.value = true
    const data = JSON.parse(ev.data)
    message[data.success ? 'success' : 'error'](
      data.success ? '构建成功' : '构建失败'
    )
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    loadBuild()
  })

  eventSource.onerror = () => {
    if (!done.value) {
      setTimeout(loadBuild, 1000)
    }
  }
}

async function rerun() {
  if (!build.value) return
  try {
    const resp = await api.triggerBuild('jenpy.yaml')
    message.success(`重跑已触发: ${resp.build_id}`)
    setTimeout(() => router.push(`/builds/${resp.build_id}`), 500)
  } catch (e) {
    message.error(`重跑失败: ${(e as Error).message}`)
  }
}

onMounted(() => {
  loadBuild()
  connectStream()
  pollTimer = window.setInterval(() => {
    if (!done.value) loadBuild()
  }, 3000)
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <!-- 顶部构建信息栏（Jenkins 风格：状态球 + 标题 + 元信息） -->
    <div class="build-header">
      <div class="header-left">
        <StatusBall :status="build?.status || 'queued'" :size="20" />
        <h2 class="build-title">
          {{ build?.pipeline || '...' }}
          <span class="build-num">#{{ buildNumber(buildId) }}</span>
        </h2>
        <span class="build-status-label" :class="build?.status">
          {{ build ? statusText(build.status) : '加载中...' }}
        </span>
      </div>
      <NSpace>
        <NButton size="small" @click="router.push('/dashboard')">返回</NButton>
        <NButton size="small" type="warning" @click="rerun" :disabled="!done && build?.status === 'running'">
          重新构建
        </NButton>
      </NSpace>
    </div>

    <!-- 元信息 -->
    <div class="build-meta" v-if="build">
      <span>构建 ID: <code>{{ build.build_id }}</code></span>
      <span>·</span>
      <span>耗时 {{ fmtDuration(build.duration) }}</span>
      <span>·</span>
      <span>{{ build.started_at }}</span>
      <span>·</span>
      <span>步骤 {{ steps.filter(s => s.success).length }}/{{ steps.length }} 通过</span>
    </div>

    <!-- 步骤列表（Jenkins 风格：每步状态球 + 名称 + 耗时） -->
    <NCard size="small" style="margin-bottom: 12px;">
      <template #header>
        <span class="card-title">阶段步骤</span>
      </template>
      <div class="steps-list">
        <div v-for="(s, i) in steps" :key="i" class="step-item">
          <StatusBall :status="stepBallStatus(s.success, false)" :size="14" />
          <span class="step-stage">[{{ s.stage }}]</span>
          <span class="step-name">{{ s.step }}</span>
          <span class="step-duration">{{ fmtDuration(s.duration) }}</span>
        </div>
        <div v-if="steps.length === 0 && !done" class="step-item">
          <StatusBall status="running" :size="14" />
          <span class="step-name">等待构建开始...</span>
        </div>
      </div>
    </NCard>

    <!-- 控制台输出（保留深色终端风格 —— 现代 CI 共识） -->
    <NCard size="small">
      <template #header>
        <span class="card-title">控制台输出</span>
      </template>
      <LogViewer :lines="logLines.map(l => l.line)" :container-ref="logContainer" />
    </NCard>
  </div>
</template>

<style scoped>
.build-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.build-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
.build-num {
  color: #999;
  font-size: 14px;
  font-weight: 400;
  margin-left: 4px;
}
.build-status-label {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}
.build-status-label.success { color: #16a34a; background: #dcfce7; }
.build-status-label.failed { color: #dc2626; background: #fee2e2; }
.build-status-label.running { color: #2563eb; background: #dbeafe; }
.build-status-label.queued { color: #666; background: #f3f4f6; }

.build-meta {
  font-size: 13px;
  color: #666;
  margin-bottom: 16px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.build-meta code {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.steps-list {
  display: flex;
  flex-direction: column;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 4px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}
.step-item:last-child { border-bottom: none; }
.step-stage {
  color: #2563eb;
  font-size: 12px;
}
.step-name {
  color: #333;
  flex: 1;
}
.step-duration {
  color: #999;
  font-size: 12px;
}
</style>
