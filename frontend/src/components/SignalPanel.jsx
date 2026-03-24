import { useState, useEffect } from 'react'
import { api } from '../api'

const confidenceColors = {
  High:       'bg-red-100 text-red-800',
  Medium:     'bg-yellow-100 text-yellow-800',
  Hypothesis: 'bg-gray-100 text-gray-600',
}

const sourceColors = {
  Interview: 'bg-blue-100 text-blue-700',
  Document:  'bg-purple-100 text-purple-700',
}

export default function SignalPanel({ engagementId }) {
  const [signals, setSignals]   = useState([])
  const [summary, setSummary]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [filter, setFilter]     = useState('All')

  useEffect(() => {
    Promise.all([
      api.signals.list(engagementId),
      api.signals.summary(engagementId),
    ])
      .then(([sigs, sum]) => { setSignals(sigs); setSummary(sum) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading signals...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const domains = ['All', ...new Set(signals.map(s => s.domain))]
  const filtered = filter === 'All' ? signals : signals.filter(s => s.domain === filter)

  return (
    <div className="p-6">

      {/* Domain summary */}
      <div className="flex flex-wrap gap-2 mb-6">
        {summary.map(s => (
          <button
            key={`${s.domain}-${s.signal_confidence}`}
            onClick={() => setFilter(s.domain)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === s.domain
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-400'
            }`}
          >
            {s.domain} · {s.signal_confidence} · {s.signal_count}
          </button>
        ))}
        {filter !== 'All' && (
          <button
            onClick={() => setFilter('All')}
            className="px-3 py-1 rounded-full text-xs text-gray-400 hover:text-gray-600"
          >
            Clear filter ×
          </button>
        )}
      </div>

      {/* Signal count */}
      <div className="text-sm text-gray-500 mb-4">
        Showing {filtered.length} of {signals.length} signals
      </div>

      {/* Signal list */}
      <div className="space-y-3">
        {filtered.map(signal => (
          <div key={signal.signal_id}
            className="border border-gray-100 rounded-lg p-4 hover:border-gray-300 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-gray-900 text-sm">{signal.signal_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColors[signal.signal_confidence] || 'bg-gray-100 text-gray-600'}`}>
                    {signal.signal_confidence}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${sourceColors[signal.source] || 'bg-gray-100 text-gray-600'}`}>
                    {signal.source}
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">{signal.observed_value}</span>
                  {signal.normalized_band && (
                    <span className="text-gray-400"> · {signal.normalized_band}</span>
                  )}
                </div>
                {signal.notes && (
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{signal.notes}</p>
                )}
              </div>
              <div className="text-xs text-gray-400 whitespace-nowrap">{signal.domain}</div>
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}