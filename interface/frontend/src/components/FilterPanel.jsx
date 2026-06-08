const POS_OPTIONS = [
  { value: '', label: 'Any part of speech' },
  { value: 'n', label: 'Noun' },
  { value: 'v', label: 'Verb' },
  { value: 'a', label: 'Adjective' },
  { value: 'r', label: 'Adverb' },
]

export default function FilterPanel({ filters, onChange, onClear }) {
  function set(key, value) {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Part of speech */}
      <select
        value={filters.pos}
        onChange={e => set('pos', e.target.value)}
        className="text-sm rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
      >
        {POS_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {/* Starts with */}
      <input
        type="text"
        maxLength={8}
        placeholder="Starts with…"
        value={filters.starts_with}
        onChange={e => set('starts_with', e.target.value)}
        className="text-sm rounded-md border border-gray-200 bg-white px-2.5 py-1.5 w-32 text-gray-700 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-300"
      />

      {/* Max length */}
      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-400 whitespace-nowrap">Max length</label>
        <input
          type="number"
          min={1}
          max={30}
          placeholder="—"
          value={filters.max_length}
          onChange={e => set('max_length', e.target.value)}
          className="text-sm rounded-md border border-gray-200 bg-white px-2 py-1.5 w-16 text-gray-700 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
      </div>

      {/* Feeling lucky toggle */}
      <label className="flex items-center gap-1.5 cursor-pointer select-none">
        <div className="relative">
          <input
            type="checkbox"
            className="sr-only peer"
            checked={filters.lucky}
            onChange={e => set('lucky', e.target.checked)}
          />
          <div className="w-8 h-4 rounded-full bg-gray-200 peer-checked:bg-indigo-500 transition-colors" />
          <div className="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
        </div>
        <span className="text-xs text-gray-500">Feeling lucky</span>
      </label>

      {/* Clear */}
      <button
        onClick={onClear}
        className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2 transition-colors"
      >
        Clear
      </button>
    </div>
  )
}
