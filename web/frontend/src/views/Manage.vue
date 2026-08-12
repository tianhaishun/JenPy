<script setup lang="ts">
import { NCard } from 'naive-ui'
</script>

<template>
  <div>
    <h2 class="page-title">管理 Jenkins</h2>
    <NCard size="small">
      <div style="color: #999; padding: 40px; text-align: center;">
        <p style="font-size: 14px; color: #666; margin-bottom: 8px;">管理面板（开发中）</p>
        <p style="font-size: 13px;">计划功能：系统配置、环境变量管理、执行器设置、插件管理</p>
        <p style="font-size: 12px; margin-top: 16px; color: #bbb;">
          欢迎在 GitHub 提 Issue 建议你想要的管理功能
        </p>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.page-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
</style>
