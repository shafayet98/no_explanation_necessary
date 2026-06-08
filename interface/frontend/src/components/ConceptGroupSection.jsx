import ResultCard from './ResultCard.jsx'

export default function ConceptGroupSection({ group, showLabel }) {
  const isInterpretation = group.results.some(r => r.is_interpretation)

  return (
    <div>
      {showLabel && (
        <div className="flex items-center gap-2 mb-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            {group.label}
          </h2>
          {isInterpretation && (
            <span className="px-1.5 py-0.5 text-xs rounded bg-amber-50 text-amber-600 border border-amber-200">
              interpretation
            </span>
          )}
        </div>
      )}
      {group.results.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No matches found.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {group.results.map((result, i) => (
            <ResultCard key={`${result.word}-${i}`} result={result} />
          ))}
        </div>
      )}
    </div>
  )
}
