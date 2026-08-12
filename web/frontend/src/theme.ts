/**
 * JenPy 主题常量与共享工具。
 *
 * 参考 Jenkins 经典配色（深蓝 header、状态红），但比例现代化。
 * 所有视图共用此处的状态映射和格式化函数，避免三处重复定义。
 */

// Jenkins 风格配色
export const colors = {
  // header 深蓝（Jenkins 经典）
  headerBg: '#335061',
  headerText: '#ffffff',
  // 链接蓝（Jenkins 链接色）
  link: '#0f6ab0',
  // 状态色
  success: '#16a34a',
  failed: '#dc2626',
  running: '#2563eb',
  queued: '#9ca3af',
  // 文本
  textPrimary: '#333333',
  textSecondary: '#666666',
  textMuted: '#999999',
  // 背景
  bgPage: '#f0f0f0',
  bgCard: '#ffffff',
  bgHover: '#f5f5f5',
  border: '#e0e0e0',
} as const

/**
 * 状态 -> Naive UI Tag type 映射。
 * 保留给需要 NTag 的场景（表格内小标签）。
 */
export function statusTagType(status: string): 'success' | 'error' | 'default' | 'info' {
  return ({ success: 'success', failed: 'error', queued: 'default', running: 'info' } as const)[status] || 'default'
}

/** 状态中文标签 */
export function statusText(status: string): string {
  return ({ success: '成功', failed: '失败', queued: '排队中', running: '运行中' } as const)[status] || status
}

/** 格式化耗时：秒以下显示毫秒 */
export function fmtDuration(d: number): string {
  if (d < 1) return `${(d * 1000).toFixed(0)}ms`
  if (d < 60) return `${d.toFixed(1)}s`
  const m = Math.floor(d / 60)
  const s = Math.round(d % 60)
  return `${m}m${s}s`
}

/**
 * 从 build_id 提取 Jenkins 风格的短编号。
 * build_id 形如 20260812-161329-5fki，取时间部分作为 #编号。
 */
export function buildNumber(buildId: string): string {
  // 取 HHMMSS 部分作为简短编号
  const parts = buildId.split('-')
  if (parts.length >= 2) return parts[1]  // 161329
  return buildId.slice(-6)
}
