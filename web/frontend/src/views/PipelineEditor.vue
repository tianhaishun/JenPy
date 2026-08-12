<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage, NCard, NButton, NSpace, NInput, NInputNumber, NSwitch } from 'naive-ui'
import { api, type Pipeline, type Stage, type Step } from '../api/client'
import { dumpYamlLocal } from '../utils/yaml'

const route = useRoute()
const message = useMessage()

const fileName = ref(decodeURIComponent(route.params.name as string))
const pipeline = ref<Pipeline | null>(null)
const yamlPreview = ref('')
const saving = ref(false)

function emptyPipeline(): Pipeline {
  return {
    name: 'new-pipeline',
    workspace: '.',
    env: {},
    stages: [{ name: '构建', when: null, steps: [{ name: '安装', run: 'pip install -r requirements.txt', timeout: 300, env: {}, continue_on_error: false, deploy: null }] }],
  }
}

function makeStep(): Step {
  return { name: '', run: '', timeout: null, env: {}, continue_on_error: false, deploy: null }
}

function makeStage(): Stage {
  return { name: '新阶段', when: null, steps: [makeStep()] }
}

function addStage() {
  if (!pipeline.value) return
  pipeline.value.stages.push(makeStage())
}

function addStep(stageIdx: number) {
  pipeline.value?.stages[stageIdx].steps.push(makeStep())
}

function removeStage(idx: number) {
  pipeline.value?.stages.splice(idx, 1)
}

function removeStep(stageIdx: number, stepIdx: number) {
  pipeline.value?.stages[stageIdx].steps.splice(stepIdx, 1)
}

watch(pipeline, () => {
  if (pipeline.value) yamlPreview.value = dumpYamlLocal(pipeline.value)
}, { deep: true })

async function load() {
  try {
    pipeline.value = await api.getPipeline(fileName.value)
    yamlPreview.value = dumpYamlLocal(pipeline.value)
  } catch {
    pipeline.value = emptyPipeline()
    yamlPreview.value = dumpYamlLocal(pipeline.value)
    message.info('文件不存在，使用空模板')
  }
}

async function save() {
  if (!pipeline.value) return
  saving.value = true
  try {
    await api.savePipeline(fileName.value, pipeline.value)
    message.success(`已保存到 ${fileName.value}`)
  } catch (e) {
    message.error(`保存失败: ${(e as Error).message}`)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">
        可视化编辑器
        <span class="file-name">{{ fileName }}</span>
      </h2>
      <NSpace>
        <NInput v-model:value="fileName" style="width: 180px;" size="small" />
        <NButton size="small" @click="load">重新加载</NButton>
        <NButton size="small" type="primary" @click="save" :loading="saving">保存</NButton>
      </NSpace>
    </div>

    <div v-if="pipeline" class="editor-layout">
      <!-- 左侧：可视化编辑 -->
      <div class="editor-main">
        <NCard size="small" style="margin-bottom: 12px;">
          <NSpace align="center">
            <span class="field-label">名称:</span>
            <NInput v-model:value="pipeline.name" style="width: 180px;" size="small" />
            <span class="field-label">工作目录:</span>
            <NInput v-model:value="pipeline.workspace" style="width: 120px;" size="small" />
          </NSpace>
        </NCard>

        <NCard v-for="(stage, si) in pipeline.stages" :key="si" size="small" style="margin-bottom: 12px;">
          <template #header>
            <NSpace align="center" size="small">
              <NInput v-model:value="stage.name" style="width: 140px;" size="small" />
              <NInput v-model:value="stage.when" placeholder="when 条件（可选）" style="width: 200px;" size="small" />
            </NSpace>
          </template>
          <template #header-extra>
            <NButton size="tiny" quaternary type="error" @click="removeStage(si)">删除阶段</NButton>
          </template>

          <div v-for="(step, ti) in stage.steps" :key="ti" class="step-row">
            <div class="step-top">
              <NInput v-model:value="step.name" placeholder="步骤名" style="width: 120px;" size="small" />
              <NInput v-model:value="step.run" placeholder="命令 (run)" style="flex: 1;" size="small" :disabled="!!step.deploy" />
              <NButton size="tiny" quaternary type="error" @click="removeStep(si, ti)">×</NButton>
            </div>
            <div class="step-opts">
              <span class="opt-label">timeout:</span>
              <NInputNumber v-model:value="step.timeout" placeholder="秒" :show-button="false" style="width: 70px;" size="small" />
              <span class="opt-label">continue_on_error:</span>
              <NSwitch v-model:value="step.continue_on_error" size="small" />
            </div>
          </div>

          <NButton size="small" dashed block @click="addStep(si)" style="margin-top: 8px;">
            + 添加步骤
          </NButton>
        </NCard>

        <NButton size="small" dashed block @click="addStage">+ 添加阶段</NButton>
      </div>

      <!-- 右侧：YAML 实时预览 -->
      <div class="editor-preview">
        <NCard size="small">
          <template #header>
            <span class="card-title">YAML 预览</span>
          </template>
          <pre class="yaml-preview">{{ yamlPreview }}</pre>
        </NCard>
      </div>
    </div>
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
.file-name {
  color: #999;
  font-size: 13px;
  font-weight: 400;
  margin-left: 8px;
}

.editor-layout {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.editor-main {
  flex: 1;
  min-width: 0;
}
.editor-preview {
  width: 400px;
  flex-shrink: 0;
}

.field-label {
  font-size: 13px;
  color: #666;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.step-row {
  padding: 8px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  margin-bottom: 8px;
  background: #fafafa;
}
.step-top {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}
.step-opts {
  display: flex;
  gap: 12px;
  padding-left: 4px;
  align-items: center;
}
.opt-label {
  color: #888;
  font-size: 12px;
}

/* YAML 预览区（浅色主题下也用深色终端风格，保持一致性） */
.yaml-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  max-height: 600px;
  overflow: auto;
  white-space: pre-wrap;
  margin: 0;
}
</style>
