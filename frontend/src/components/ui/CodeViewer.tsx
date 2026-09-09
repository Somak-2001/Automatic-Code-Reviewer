interface CodeViewerProps {
  filePath: string
  content: string
  highlightStart?: number | null
  highlightEnd?: number | null
  lineHint?: string
}

export function CodeViewer({
  filePath,
  content,
  highlightStart,
  highlightEnd,
  lineHint,
}: CodeViewerProps) {
  const lines = content.split('\n')

  // Determine which lines to show (context around highlight)
  const contextLines = 5
  let startLine = 0
  let endLine = lines.length

  if (highlightStart) {
    startLine = Math.max(0, highlightStart - 1 - contextLines)
    endLine = Math.min(lines.length, (highlightEnd ?? highlightStart) + contextLines)
  }

  const visibleLines = lines.slice(startLine, endLine)

  const isHighlighted = (lineIdx: number) => {
    const lineNum = startLine + lineIdx + 1 // 1-based
    if (!highlightStart) return false
    return lineNum >= highlightStart && lineNum <= (highlightEnd ?? highlightStart)
  }

  return (
    <div className="rounded-lg overflow-hidden border border-gray-700/50">
      {/* Header */}
      <div className="flex items-center justify-between bg-[#1a2035] px-4 py-2.5 border-b border-gray-700/40">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-indigo-400 text-xs">⬡</span>
          <span className="text-xs text-gray-300 font-mono truncate">{filePath}</span>
        </div>
        {lineHint && (
          <span className="text-xs text-gray-500 ml-4 shrink-0">{lineHint}</span>
        )}
      </div>

      {/* Code */}
      <div className="bg-[#0d1117] overflow-x-auto code-scroll max-h-72">
        <table className="w-full text-sm">
          <tbody>
            {visibleLines.map((line, idx) => {
              const lineNum = startLine + idx + 1
              const highlighted = isHighlighted(idx)
              return (
                <tr
                  key={lineNum}
                  className={highlighted ? 'bg-yellow-900/20' : ''}
                >
                  <td
                    className={`select-none text-right pr-4 pl-4 py-0.5 text-xs font-mono w-12 border-r border-gray-800 ${
                      highlighted ? 'text-yellow-400' : 'text-gray-600'
                    }`}
                  >
                    {lineNum}
                  </td>
                  <td className="pl-4 pr-4 py-0.5 font-mono text-xs text-gray-300 whitespace-pre">
                    {highlighted && (
                      <span className="text-yellow-400 mr-2 select-none">▶</span>
                    )}
                    {line}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {endLine < lines.length && (
          <p className="text-xs text-gray-600 text-center py-2 font-mono">
            … {lines.length - endLine} more lines
          </p>
        )}
      </div>
    </div>
  )
}

