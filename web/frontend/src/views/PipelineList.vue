<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NCard, NButton, NInput, NSpace, NTag } from 'naive-ui'
import { api, type Pipeline } from '../api/client'

const router = useRouter()
const message = useMessage()

const fileName = ref('jenpy.yaml')
const pipeline = ref<Pipeline | null>(null)
const loading = ref(false)

async function loadFile() {
  if (!fileName.value) return
  loading.value = true
  try {
    pipeline.value = await api.getPipeline(fileName.value)
    message.success(`已加载: ${pipeline.value.name}`)
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

function openEditor() {
  router.push(`/editor/${encodeURIComponent(fileName.value)}`)
}

function createNew() {
  router.push(`/editor/${encodeURIComponent('jenpy.yaml')}`)
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">流水线</h2>
      <NButton size="small" type="primary" @click="createNew">+ 新建流水线</NButton>
    </div>

    <NCard size="small" style="margin-bottom: 12px;">
      <NSpace align="center">
        <span>配置文件：</span>
        <NInput v-model:value="fileName" placeholder="jenpy.yaml" style="width: 220px;" size="small" />
        <NButton size="small" @click="loadFile" :loading="loading">加载</NButton>
        <NButton size="small" type="primary" @click="openEditor" :disabled="!pipeline">
          可视化编辑
        </NButton>
      </NSpace>
    </NCard>

    <NCard v-if="pipeline" size="small" :title="`流水线: ${pipeline.name}`">
      <div class="pipeline-meta">
        工作目录: <code>{{ pipeline.workspace }}</code>
        <span v-if="Object.keys(pipeline.env).length">
          · 环境变量: {{ Object.keys(pipeline.env).join(', ') }}
        </span>
      </div>
      <div v-for="(stage, i) in pipeline.stages" :key="i" class="stage-block">
        <div class="stage-header">
          <span class="stage-icon">📁</span>
          [{{ i + 1 }}] {{ stage.name }}
          <NTag v-if="stage.when" size="small" type="warning" style="margin-left: 8px;">
            when: {{ stage.when }}
          </NTag>
        </div>
        <div v-for="(step, j) in stage.steps" :key="j" class="step-line">
          <span class="step-bullet">▸</span>
          <span class="step-label">{{ step.name || '(未命名)' }}:</span>
          <code v-if="step.run" class="cmd-code">{{ step.run }}</code>
          <NTag v-if="step.deploy" size="small" type="info">deploy: {{ step.deploy.method }}</NTag>
          <NTag v-if="step.continue_on_error" size="small">continue_on_error</NTag>
        </div>
      </div>
    </NCard>

    <NCard v-else size="small">
      <div style="color: #999; text-align: center; padding: 40px;">
        输入配置文件名并加载，或点击「新建流水线」创建
      </div>
    </NCard>
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

.pipeline-meta {
  font-size: 13px;
  color: #666;
  margin-bottom: 16px;
}
.pipeline-meta code {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
}

.stage-block {
  margin-bottom: 16px;
  padding: 10px;
  background: #fafafa;
  border-radius: 4px;
}
.stage-header {
  font-weight: 600;
  color: #335061;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.stage-icon { font-size: 14px; }

.step-line {
  padding: 4px 0 4px 24px;
  color: #444;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.step-bullet { color: #999; }
.step-label { color: #555; }
.cmd-code {
  background: #eef;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #335061;
}
</style>
