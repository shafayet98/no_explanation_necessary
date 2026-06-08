import { useState, useRef, useCallback } from 'react'
import ConceptGroupSection from './components/ConceptGroupSection.jsx'
import FilterPanel from './components/FilterPanel.jsx'

const EMPTY_FILTERS = { pos: '', starts_with: '', max_length: '', lucky: false }

export default function App() {
  const [input, setInput] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const inputRef = useRef(null)

  const submit = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    setLoading(true)
    setError(null)
    setResponse(null)

    // Build request body — omit empty/null filter fields
    const filtersPayload = {}
    if (filters.pos) filtersPayload.pos = filters.pos
    if (filters.starts_with) filtersPayload.starts_with = filters.starts_with
    if (filters.max_length) filtersPayload.max_length = parseInt(filters.max_length, 10)

    const body = {
      text,
      lucky: filters.lucky,
      ...(Object.keys(filtersPayload).length > 0 && { filters: filtersPayload }),
    }

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail?.detail ?? `Server error ${res.status}`)
      }
      setResponse(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [input, filters, loading])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const isGrouped = response?.mode === 'grouped'
  const hasResults = response?.groups?.some(g => g.results.length > 0)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-16">
      <div className="w-full max-w-2xl">

        {/* Header */}
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Reverse Dictionary</h1>
          <p className="mt-2 text-sm text-gray-400">Describe a meaning — get the word.</p>
        </div>

        {/* Input */}
        <div className="relative">
          <textarea
            ref={inputRef}
            autoFocus
            rows={3}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="the smell of rain on dry earth…"
            disabled={loading}
            className="w-full resize-none rounded-xl border border-gray-200 bg-white px-4 py-3 pr-24 text-gray-900 placeholder-gray-300 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-transparent disabled:opacity-50 transition-shadow"
          />
          <button
            onClick={submit}
            disabled={loading || !input.trim()}
            className="absolute right-3 bottom-3 px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <span className="flex items-center gap-1.5">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Searching
              </span>
            ) : 'Search'}
          </button>
        </div>

        {/* Filters */}
        <div className="mt-3">
          <FilterPanel
            filters={filters}
            onChange={setFilters}
            onClear={() => setFilters(EMPTY_FILTERS)}
          />
        </div>

        {/* Results */}
        <div className="mt-8">
          {error && (
            <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          {response && !hasResults && (
            <p className="text-sm text-gray-400 italic text-center">No matches found.</p>
          )}

          {response && hasResults && (
            <div className="flex flex-col gap-6">
              {response.groups.map((group, i) => (
                <ConceptGroupSection
                  key={i}
                  group={group}
                  showLabel={isGrouped}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
