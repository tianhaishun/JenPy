<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  lines: string[]
  containerRef?: HTMLElement | null
}>()

const scrollRef = ref<HTMLElement | null>(null)

// 自动滚动到底部
watch(() => props.lines.length, async () => {
  await nextTick()
  const el = scrollRef.value || props.containerRef
  if (el) el.scrollTop = el.scrollHeight
})
</script>

<template>
  <div
    ref="scrollRef"
    class="log-viewer"
  >
    <div v-for="(line, i) in lines" :key="i" class="log-line">
      <span class="line-no">{{ i + 1 }}</span>
      <span class="line-text">{{ line }}</span>
    </div>
    <div v-if="lines.length === 0" class="empty">
      （等待输出...）
    </div>
  </div>
</template>

<style scoped>
.log-viewer {
  background: #1a1b1e;
  border-radius: 6px;
  padding: 12px;
  max-height: 480px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.log-line {
  display: flex;
  white-space: pre-wrap;
  word-break: break-all;
}
.line-no {
  color: #4a5568;
  user-select: none;
  margin-right: 16px;
  min-width: 48px;
  text-align: right;
  flex-shrink: 0;
}
.line-text {
  color: #d0d0d0;
  flex: 1;
}
.empty {
  color: #4a5568;
  font-style: italic;
  text-align: center;
  padding: 20px;
}
</style>
