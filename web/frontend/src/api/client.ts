// JenPy 后端 API 客户端
// 所有 fetch 调用集中在此，便于统一错误处理和类型维护

export interface BuildRecord {
  build_id: string
  pipeline: string
  status: string
  started_at: string
  duration: number
  log_dir: string | null
  steps: StepRecord[]
}

export interface StepRecord {
  stage: string
  step: string
  success: boolean
  duration: number
  log_file: string | null
}

export interface Pipeline {
  name: string
  workspace: string
  env: Record<string, string>
  stages: Stage[]
}

export interface Stage {
  name: string
  when: string | null
  steps: Step[]
}

export interface Step {
  name: string
  run: string | null
  timeout: number | null
  env: Record<string, string>
  continue_on_error: boolean
  deploy: DeployConfig | null
}

export interface DeployConfig {
  method: string
  source: string | null
  target: string | null
  delete: boolean
  run: string | null
}

const BASE = ''

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try { msg = (await resp.json()).detail || msg } catch { /* ignore */ }
    throw new Error(msg)
  }
  return resp.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listBuilds: (limit = 50) =>
    request<BuildRecord[]>(`/api/builds?limit=${limit}`),

  getBuild: (id: string) =>
    request<BuildRecord>(`/api/builds/${id}`),

  triggerBuild: (file: string, context: Record<string, unknown> = {}) =>
    request<{ build_id: string; status: string }>('/api/builds', {
      method: 'POST',
      body: JSON.stringify({ file, context }),
    }),

  getPipeline: (name: string) =>
    request<Pipeline>(`/api/pipelines/${encodeURIComponent(name)}`),

  savePipeline: (name: string, pipeline: Pipeline) =>
    request<Pipeline>(`/api/pipelines/${encodeURIComponent(name)}`, {
      method: 'PUT',
      body: JSON.stringify(pipeline),
    }),

  // SSE 流：返回 EventSource，调用方自行管理生命周期
  streamBuild: (id: string) =>
    new EventSource(`/api/builds/${id}/stream`),
}
