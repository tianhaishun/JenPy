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
  unstable: '#f0ad4e',   // Jenkins 黄色：不稳定
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

// ----------------- Jenkins 健康度（天气图标） -----------------

/** 健康度级别，对应 Jenkins 天气图标 */
export type HealthLevel = 'sunny' | 'cloudy' | 'partly-cloudy' | 'rain'

/** 健康度对应的天气 emoji */
export const healthEmoji: Record<HealthLevel, string> = {
  sunny: '☀️',
  'partly-cloudy': '⛅',
  cloudy: '🌥️',
  rain: '🌧️',
}

/** 健康度对应的文字描述 */
export const healthText: Record<HealthLevel, string> = {
  sunny: '健康',
  'partly-cloudy': '基本健康',
  cloudy: '不稳定',
  rain: '危险',
}

/**
 * 根据成功率计算健康度级别（Jenkins 天气图标）。
 * @param successRate 0-1 之间的成功率
 */
export function healthLevel(successRate: number): HealthLevel {
  if (successRate >= 1) return 'sunny'        // 100% → 晴
  if (successRate >= 0.8) return 'partly-cloudy'  // 80-99% → 多云
  if (successRate >= 0.6) return 'cloudy'     // 60-79% → 阴
  return 'rain'                                // <60% → 雨
}

// ----------------- Job 聚合（Jenkins 首页表格数据） -----------------

export interface JobSummary {
  name: string
  lastStatus: string       // 最新构建状态（决定 S 列球色）
  lastBuildId: string
  health: HealthLevel       // 健康度（决定 W 列天气）
  successRate: number       // 成功率 0-1
  lastSuccess: string       // 最近成功时间
  lastFailure: string       // 最近失败时间
  lastDuration: number      // 最近构建耗时
  buildCount: number        // 总构建次数
}

/**
 * 将构建记录列表按 pipeline 名聚合为 Jenkins Job 列表。
 * 每个 Job 计算最近状态、健康度、最近成功/失败/耗时。
 */
export function aggregateJobs(builds: Array<{
  build_id: string; pipeline: string; status: string
  started_at: string; duration: number
}>): JobSummary[] {
  const groups: Record<string, typeof builds> = {}
  // 按 pipeline 分组（builds 是新的在前）
  for (const b of builds) {
    if (!groups[b.pipeline]) groups[b.pipeline] = []
    groups[b.pipeline].push(b)
  }

  return Object.entries(groups).map(([name, records]) => {
    // records 可能不是严格按时间排序，按 build_id 排序（build_id 含时间戳）
    const sorted = [...records].sort((a, b) => a.build_id.localeCompare(b.build_id))
    const latest = sorted[sorted.length - 1]  // 最新
    const recent = sorted.slice(-10)           // 最近 10 次算健康度

    const successCount = recent.filter(r => r.status === 'success').length
    const successRate = recent.length > 0 ? successCount / recent.length : 0

    // 找最近成功/失败
    const lastSuccessRec = [...sorted].reverse().find(r => r.status === 'success')
    const lastFailureRec = [...sorted].reverse().find(r => r.status === 'failed')

    return {
      name,
      lastStatus: latest?.status || 'unknown',
      lastBuildId: latest?.build_id || '',
      health: healthLevel(successRate),
      successRate,
      lastSuccess: lastSuccessRec?.started_at || 'N/A',
      lastFailure: lastFailureRec?.started_at || 'N/A',
      lastDuration: latest?.duration || 0,
      buildCount: sorted.length,
    }
  }).sort((a, b) => a.name.localeCompare(b.name))
}
