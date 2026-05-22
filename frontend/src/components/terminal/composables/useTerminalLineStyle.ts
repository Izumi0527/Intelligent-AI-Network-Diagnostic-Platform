/**
 * 终端输出行 → 语义类名映射（纯函数）。
 *
 * 行内出现"错误"/"失败"映射为 terminal-error，
 * "成功"/"已连接"映射为 terminal-success，
 * 以 ">" 开头的命令回显行映射为 terminal-command，
 * 出现"警告"映射为 terminal-warning，
 * 其它走默认 terminal-text。
 */
export function useTerminalLineStyle() {
  const getLineClass = (line: string): string => {
    if (line.includes('错误') || line.includes('失败')) return 'terminal-error'
    if (line.includes('成功') || line.includes('已连接')) return 'terminal-success'
    if (line.startsWith('>')) return 'terminal-command'
    if (line.includes('警告')) return 'terminal-warning'
    return 'terminal-text'
  }

  return { getLineClass }
}
