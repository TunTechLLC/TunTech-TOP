import { useState, useEffect } from 'react'
import { api } from '../api'

const confidenceColors = {
  High:       'bg-red-100 text-red-800',
  Medium:     'bg-yellow-100 text-yellow-800',
  Hypothesis: 'bg-gray-100 text-gray-600',
}

export default function PatternPanel({ engagementId }) {
  const [patterns, setPatterns] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [filter, setFilter]     = useState('All')

  useEffect(() => {
    api.patterns.list(engagementId)
      .then(setPatterns)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading patterns...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const counts = {
    All:       patterns.length,
    High:      patterns.filter(p => p.confidence === 'High').length,
    Medium:    patterns.filter(p => p.confidence === 'Medium').length,
    Hypothesis:patterns.filter(p => p.confidence === 'Hypothesis').length,
  }

  const filtered = filter === 'All'
    ? patterns
    : patterns.filter(p => p.confidence === filter)

  return (
    <div className="p-6">

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {Object.entries(counts).map(([level, count]) => (
          <button
            key={level}
            onClick={() => setFilter(level)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === level
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-400'
            }`}
          >
            {level} · {count}
          </button>
        ))}
      </div>

      {/* Pattern list */}
      <div className="space-y-3">
        {filtered.map(pattern => (
          <div key={pattern.ep_id}
            className="border border-gray-100 rounded-lg p-4 hover:border-gray-300 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-gray-400">{pattern.pattern_id}</span>
                  <span className="font-medium text-gray-900 text-sm">{pattern.pattern_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColors[pattern.confidence] || 'bg-gray-100'}`}>
                    {pattern.confidence}
                  </span>
                  {pattern.accepted === 1 && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                      Accepted
                    </span>
                  )}
                </div>
                {pattern.notes && (
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{pattern.notes}</p>
                )}
                {pattern.economic_impact_est && (
                  <p className="text-xs text-blue-600 mt-1 font-medium">{pattern.economic_impact_est}</p>
                )}
              </div>
              <div className="text-xs text-gray-400 whitespace-nowrap text-right">
                <div>{pattern.domain}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}