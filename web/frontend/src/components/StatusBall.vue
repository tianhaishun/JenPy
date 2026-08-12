<script setup lang="ts">
/**
 * Jenkins 风格状态球图标。
 *
 * Jenkins 最具辨识度的视觉符号：用圆形彩色球表示构建状态。
 * - 蓝色脉冲 = 构建中（running）
 * - 绿色      = 成功（success）
 * - 红色      = 失败（failed）
 * - 灰色      = 排队/未构建（queued）
 *
 * 纯 CSS 实现，无图片依赖。running 状态的脉冲动画是 Jenkins 的灵魂。
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  status: string
  size?: number
}>(), {
  size: 18,
})

const colorClass = computed(() => {
  switch (props.status) {
    case 'success': return 'ball-success'
    case 'failed': return 'ball-failed'
    case 'running': return 'ball-running'
    case 'queued': return 'ball-queued'
    default: return 'ball-unknown'
  }
})

const isAnimated = computed(() => props.status === 'running')
</script>

<template>
  <span
    class="status-ball"
    :class="[colorClass, { animated: isAnimated }]"
    :style="{ width: size + 'px', height: size + 'px' }"
    :title="status"
  />
</template>

<style scoped>
.status-ball {
  display: inline-block;
  border-radius: 50%;
  flex-shrink: 0;
  vertical-align: middle;
  transition: box-shadow 0.3s;
}

/* Jenkins 经典状态色 */
.ball-success {
  background: radial-gradient(circle at 35% 35%, #4ade80, #16a34a);
  box-shadow: 0 0 4px rgba(22, 163, 74, 0.5);
}
.ball-failed {
  background: radial-gradient(circle at 35% 35%, #f87171, #dc2626);
  box-shadow: 0 0 4px rgba(220, 38, 38, 0.5);
}
.ball-running {
  background: radial-gradient(circle at 35% 35%, #60a5fa, #2563eb);
  box-shadow: 0 0 6px rgba(37, 99, 235, 0.7);
}
.ball-queued {
  background: radial-gradient(circle at 35% 35%, #d1d5db, #9ca3af);
  box-shadow: 0 0 3px rgba(156, 163, 175, 0.4);
}
.ball-unknown {
  background: radial-gradient(circle at 35% 35%, #d1d5db, #6b7280);
}

/* 构建中：Jenkins 灵魂——蓝色脉冲呼吸动画 */
.status-ball.animated {
  animation: pulse-blue 1.5s ease-in-out infinite;
}

@keyframes pulse-blue {
  0%, 100% {
    box-shadow: 0 0 4px rgba(37, 99, 235, 0.5);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 12px rgba(37, 99, 235, 0.9), 0 0 20px rgba(37, 99, 235, 0.4);
    transform: scale(1.1);
  }
}
</style>
