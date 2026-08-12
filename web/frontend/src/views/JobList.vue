<script setup lang="ts">
/**
 * Jenkins 首页核心：Job 列表表格。
 *
 * 一比一对照 Jenkins 经典 dashboard 的 "All" 视图：
 * 列顺序：S(状态球) | W(天气健康度) | Name | Last Success | Last Failure | Last Duration | 构建按钮
 *
 * 数据来自前端聚合：listBuilds(100) → aggregateJobs() 按 pipeline 分组。
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NButton, NEmpty, NSpin } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import StatusBall from '../components/StatusBall.vue'
import HealthIcon from '../components/HealthIcon.vue'
import { aggregateJobs, fmtDuration, type JobSummary } from '../theme'

const router = useRouter()
const message = useMessage()
const builds = ref<BuildRecord[]>([])
const loading = ref(false)
const triggeringJob = ref<string | null>(null)

// 聚合成 Job 列表
const jobs = computed<JobSummary[]>(() => aggregateJobs(builds.value))

// 队列中的构建
const runningBuilds = computed(() =>
  builds.value.filter(b => b.status === 'running' || b.status === 'queued')
)

async function refresh() {
  loading.value = true
  try {
    builds.value = await api.listBuilds(100)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

async function triggerJob(job: JobSummary, event: Event) {
  event.stopPropagation()
  triggeringJob.value = job.name
  try {
    const file = job.name === 'example-pipeline' ? 'examples/jenpy.yaml' : 'jenpy.yaml'
    const resp = await api.triggerBuild(file)
    message.success(`${job.name} 构建已触发: #${resp.build_id.slice(-8)}`)
    setTimeout(() => router.push(`/builds/${resp.build_id}`), 800)
  } catch (e) {
    message.error(`触发失败: ${(e as Error).message}`)
  } finally {
    triggeringJob.value = null
  }
}

function fmtTime(ts: string): string {
  if (ts === 'N/A') return 'N/A'
  // started_at 形如 2026-08-12T16:13:29，只显示日期+时分
  return ts.replace('T', ' ').slice(5, 16)  // 08-12 16:13
}

onMounted(refresh)
defineExpose({ refresh, runningBuilds })
</script>

<template>
  <div class="job-list-wrap">
    <!-- Jenkins 风格表格头 -->
    <table class="jenkins-job-table">
      <thead>
        <tr>
          <th class="col-s" title="构建状态">S</th>
          <th class="col-w" title="健康度">W</th>
          <th class="col-name">名称</th>
          <th class="col-ts">最近成功</th>
          <th class="col-ts">最近失败</th>
          <th class="col-dur">最近耗时</th>
          <th class="col-build"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="job in jobs"
          :key="job.name"
          class="job-row"
          @click="router.push(`/job/${encodeURIComponent(job.name)}`)"
        >
          <!-- S 列：状态球 -->
          <td class="col-s">
            <StatusBall :status="job.lastStatus" :size="14" />
          </td>
          <!-- W 列：天气健康度 -->
          <td class="col-w">
            <HealthIcon :level="job.health" :size="16" />
          </td>
          <!-- Name 列 -->
          <td class="col-name">
            <a class="job-name-link" @click.stop="router.push(`/job/${encodeURIComponent(job.name)}`)">
              {{ job.name }}
            </a>
            <span class="job-desc">{{ job.buildCount }} 次构建 · {{ Math.round(job.successRate * 100) }}% 成功</span>
          </td>
          <!-- Last Success -->
          <td class="col-ts">{{ fmtTime(job.lastSuccess) }}</td>
          <!-- Last Failure -->
          <td class="col-ts">{{ fmtTime(job.lastFailure) }}</td>
          <!-- Last Duration -->
          <td class="col-dur">{{ fmtDuration(job.lastDuration) }}</td>
          <!-- 构建按钮 -->
          <td class="col-build">
            <button
              class="build-trigger-btn"
              :disabled="triggeringJob === job.name"
              :title="`构建 ${job.name}`"
              @click="triggerJob(job, $event)"
            >
              <span v-if="triggeringJob === job.name">⏳</span>
              <span v-else>▶</span>
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 空状态 -->
    <div v-if="jobs.length === 0 && !loading" class="empty-state">
      <NEmpty description="暂无 Job">
        <template #extra>
          <NButton size="small" type="primary" @click="refresh">刷新</NButton>
        </template>
      </NEmpty>
    </div>

    <!-- 加载中 -->
    <div v-if="loading && jobs.length === 0" class="loading-state">
      <NSpin size="small" />
    </div>
  </div>
</template>

<style scoped>
.jenkins-job-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

/* Jenkins 风格表头 */
.jenkins-job-table th {
  background: #f0f0f0;
  color: #666;
  font-weight: 600;
  font-size: 11px;
  text-align: left;
  padding: 6px 8px;
  border-bottom: 2px solid #d0d0d0;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.jenkins-job-table th.col-s,
.jenkins-job-table th.col-w {
  text-align: center;
  width: 28px;
}

/* 数据行 */
.job-row {
  cursor: pointer;
  border-bottom: 1px solid #e8e8e8;
  transition: background 0.1s;
}
.job-row:nth-child(even) {
  background: #fafafa;  /* Jenkins 斑马纹 */
}
.job-row:hover {
  background: #e8f0fe !important;  /* Jenkins 淡蓝 hover */
}
.job-row td {
  padding: 7px 8px;
  vertical-align: middle;
  color: #333;
}

.col-s, .col-w {
  text-align: center;
  width: 28px;
}
.col-name { min-width: 140px; }
.col-ts { width: 110px; color: #666; font-size: 12px; }
.col-dur { width: 90px; color: #666; }
.col-build { width: 40px; text-align: center; }

/* Job 名称链接（Jenkins 蓝） */
.job-name-link {
  color: #0f6ab0;
  cursor: pointer;
  font-weight: 500;
  text-decoration: none;
}
.job-name-link:hover { text-decoration: underline; }

.job-desc {
  display: block;
  color: #999;
  font-size: 11px;
  margin-top: 1px;
}

/* 构建触发按钮（Jenkins 绿色播放按钮） */
.build-trigger-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid #16a34a;
  background: #dcfce7;
  color: #16a34a;
  cursor: pointer;
  font-size: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.build-trigger-btn:hover {
  background: #16a34a;
  color: #fff;
}
.build-trigger-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state, .loading-state {
  padding: 40px;
  text-align: center;
}
</style>
