import { useState } from 'react'

const POS_LABELS = { n: 'noun', v: 'verb', a: 'adj', r: 'adv' }

export default function ResultCard({ result }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(result.word).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="flex items-start justify-between gap-4 px-4 py-3 rounded-lg bg-white border border-gray-100 hover:border-gray-200 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg font-bold text-gray-900">{result.word}</span>
          <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
            {POS_LABELS[result.pos] ?? result.pos}
          </span>
          {result.is_interpretation && (
            <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-amber-50 text-amber-600 border border-amber-200">
              interpretation
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-gray-600 leading-relaxed">{result.definition}</p>
      </div>
      <button
        onClick={handleCopy}
        title="Copy word"
        className="shrink-0 mt-0.5 px-2.5 py-1 text-xs rounded border border-gray-200 text-gray-400 hover:text-gray-700 hover:border-gray-300 transition-colors"
      >
        {copied ? 'copied!' : 'copy'}
      </button>
    </div>
  )
}
