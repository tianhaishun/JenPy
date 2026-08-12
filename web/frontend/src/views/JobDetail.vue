<script setup lang="ts">
/**
 * Job 详情页 —— 对照 Jenkins 点击 Job 名后的页面。
 *
 * 显示该 Job（pipeline）的：状态球+名称标题、健康度、构建历史列表。
 * 构建历史每行：状态球 + #编号 + 时间 + 耗时，点击进单次构建详情。
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, NButton, NSpace, NEmpty } from 'naive-ui'
import { api, type BuildRecord } from '../api/client'
import StatusBall from '../components/StatusBall.vue'
import HealthIcon from '../components/HealthIcon.vue'
import { fmtDuration, buildNumber, aggregateJobs } from '../theme'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const jobName = computed(() => decodeURIComponent(route.params.name as string))
const allBuilds = ref<BuildRecord[]>([])
const loading = ref(false)

// 该 Job 的构建历史（按时间倒序）
const jobBuilds = computed(() =>
  allBuilds.value
    .filter(b => b.pipeline === jobName.value)
    .sort((a, b) => b.build_id.localeCompare(a.build_id))
)

// 该 Job 的聚合信息
const jobSummary = computed(() => {
  const jobs = aggregateJobs(allBuilds.value)
  return jobs.find(j => j.name === jobName.value)
})

async function loadData() {
  loading.value = true
  try {
    allBuilds.value = await api.listBuilds(100)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

async function buildNow() {
  const file = jobName.value === 'example-pipeline' ? 'examples/jenpy.yaml' : 'jenpy.yaml'
  try {
    const resp = await api.triggerBuild(file)
    message.success(`构建已触发`)
    setTimeout(() => router.push(`/builds/${resp.build_id}`), 500)
  } catch (e) {
    message.error(`触发失败: ${(e as Error).message}`)
  }
}

onMounted(loadData)
</script>

<template>
  <div>
    <!-- 面包屑 -->
    <div class="breadcrumb">
      <a @click="router.push('/dashboard')" class="crumb-link">Dashboard</a>
      <span class="crumb-sep">/</span>
      <span class="crumb-current">{{ jobName }}</span>
    </div>

    <!-- Job 标题栏（Jenkins 风格：状态球 + 名称 + 健康度） -->
    <div class="job-header">
      <div class="job-title-bar">
        <StatusBall :status="jobSummary?.lastStatus || 'unknown'" :size="20" />
        <h2 class="job-title">{{ jobName }}</h2>
        <HealthIcon v-if="jobSummary" :level="jobSummary.health" :size="20" />
      </div>
      <NSpace>
        <NButton size="small" @click="router.push('/dashboard')">返回</NButton>
        <NButton size="small" type="primary" @click="buildNow" :loading="loading">
          ▶ 立即构建
        </NButton>
      </NSpace>
    </div>

    <!-- Job 统计 -->
    <div class="job-stats" v-if="jobSummary">
      <span>共 {{ jobSummary.buildCount }} 次构建</span>
      <span>·</span>
      <span>成功率 {{ Math.round(jobSummary.successRate * 100) }}%</span>
      <span>·</span>
      <span>最近耗时 {{ fmtDuration(jobSummary.lastDuration) }}</span>
    </div>

    <!-- 构建历史列表（Jenkins 风格表格） -->
    <div class="history-section">
      <h3 class="section-title">构建历史</h3>
      <table class="build-history-table" v-if="jobBuilds.length > 0">
        <thead>
          <tr>
            <th class="col-s">S</th>
            <th class="col-num">#</th>
            <th class="col-time">时间</th>
            <th class="col-dur">耗时</th>
            <th class="col-result">结果</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="b in jobBuilds"
            :key="b.build_id"
            class="hist-row"
            @click="router.push(`/builds/${b.build_id}`)"
          >
            <td class="col-s"><StatusBall :status="b.status" :size="12" /></td>
            <td class="col-num">{{ buildNumber(b.build_id) }}</td>
            <td class="col-time">{{ b.started_at.replace('T', ' ') }}</td>
            <td class="col-dur">{{ fmtDuration(b.duration) }}</td>
            <td class="col-result">{{ b.steps.filter(s => s.success).length }}/{{ b.steps.length }} 步骤通过</td>
          </tr>
        </tbody>
      </table>
      <NEmpty v-else description="该 Job 暂无构建记录" style="padding: 30px;" />
    </div>
  </div>
</template>

<style scoped>
.breadcrumb {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}
.crumb-link {
  color: #0f6ab0;
  cursor: pointer;
}
.crumb-link:hover { text-decoration: underline; }
.crumb-sep { margin: 0 6px; }
.crumb-current { color: #333; }

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.job-title-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.job-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.job-stats {
  font-size: 13px;
  color: #666;
  margin-bottom: 20px;
  display: flex;
  gap: 6px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px 0;
}

/* 构建历史表格 */
.build-history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}
.build-history-table th {
  background: #f0f0f0;
  color: #666;
  font-weight: 600;
  font-size: 11px;
  text-align: left;
  padding: 6px 8px;
  border-bottom: 2px solid #d0d0d0;
  text-transform: uppercase;
}
.hist-row {
  cursor: pointer;
  border-bottom: 1px solid #e8e8e8;
}
.hist-row:nth-child(even) { background: #fafafa; }
.hist-row:hover { background: #e8f0fe; }
.hist-row td {
  padding: 6px 8px;
  vertical-align: middle;
  color: #333;
}
.col-s { width: 28px; text-align: center; }
.col-num { width: 80px; color: #0f6ab0; font-weight: 500; }
.col-time { width: 160px; color: #666; font-size: 12px; }
.col-dur { width: 80px; color: #666; }
.col-result { color: #666; font-size: 12px; }
</style>
