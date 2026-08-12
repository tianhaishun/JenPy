// 本地 YAML 序列化（用于编辑器实时预览，不依赖外部库）
// 仅处理 JenPy 用到的子集：dict / list / string / number / boolean / multiline
import type { Pipeline } from '../api/client'

export function dumpYamlLocal(p: Pipeline): string {
  const lines: string[] = []
  lines.push(`name: ${p.name}`)
  if (p.workspace && p.workspace !== '.') {
    lines.push(`workspace: ${p.workspace}`)
  }
  if (Object.keys(p.env).length) {
    lines.push('env:')
    for (const [k, v] of Object.entries(p.env)) {
      lines.push(`  ${k}: ${quoteVal(v)}`)
    }
  }
  lines.push('stages:')
  for (const stage of p.stages) {
    lines.push(`  - name: ${stage.name}`)
    if (stage.when) lines.push(`    when: ${quoteVal(stage.when)}`)
    lines.push('    steps:')
    for (const step of stage.steps) {
      const hasName = step.name && step.name !== step.run
      if (hasName) lines.push(`      - name: ${step.name}`)
      const indent = hasName ? '        ' : '      - '
      if (step.deploy) {
        lines.push(`${indent}deploy:`)
        lines.push(`          method: ${step.deploy.method}`)
        if (step.deploy.source) lines.push(`          source: ${step.deploy.source}`)
        if (step.deploy.target) lines.push(`          target: ${step.deploy.target}`)
      } else if (step.run) {
        // 多行 run 用 literal block
        if (step.run.includes('\n')) {
          lines.push(`${indent}run: |`)
          for (const ln of step.run.split('\n')) lines.push(`          ${ln}`)
        } else {
          lines.push(`${indent}run: ${step.run}`)
        }
      }
      if (step.timeout != null && hasName) lines.push(`        timeout: ${step.timeout}`)
      if (step.continue_on_error && hasName) lines.push(`        continue_on_error: true`)
    }
  }
  return lines.join('\n') + '\n'
}

function quoteVal(v: string | number): string {
  const s = String(v)
  // 需要引号的情况：含特殊字符、以特殊字符开头、空串
  if (s === '' || /[:#{}\[\],&*?|<>=!%@`]/.test(s) || /^[\s-]/.test(s)) {
    return `"${s.replace(/"/g, '\\"')}"`
  }
  return s
}
