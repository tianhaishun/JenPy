<script setup lang="ts">
/**
 * Jenkins 天气健康度图标（W 列）。
 *
 * Jenkins 标志性元素：用天气图标表示 Job 近期健康状况。
 * ☀️ 晴=全过、⛅ 多云=基本健康、🌥️ 阴=不稳定、🌧️ 雨=频繁失败
 */
import { computed } from 'vue'
import { healthEmoji, healthText, type HealthLevel } from '../theme'

const props = defineProps<{
  level: HealthLevel
  size?: number
}>()

const emoji = computed(() => healthEmoji[props.level])
const text = computed(() => healthText[props.level])
</script>

<template>
  <span
    class="health-icon"
    :style="{ fontSize: (size || 18) + 'px' }"
    :title="text"
  >{{ emoji }}</span>
</template>

<style scoped>
.health-icon {
  display: inline-block;
  line-height: 1;
  vertical-align: middle;
}
</style>
