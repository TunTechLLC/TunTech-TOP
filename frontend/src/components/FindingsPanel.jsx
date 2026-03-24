import { useState, useEffect } from 'react'
import { api } from '../api'

const confidenceColors = {
  High:   'bg-red-100 text-red-800',
  Medium: 'bg-yellow-100 text-yellow-800',
  Low:    'bg-gray-100 text-gray-600',
}

const priorityColors = {
  High:   'bg-red-50 border-red-200',
  Medium: 'bg-yellow-50 border-yellow-200',
  Low:    'bg-gray-50 border-gray-200',
}

export default function FindingsPanel({ engagementId }) {
  const [findings, setFindings] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    api.findings.list(engagementId)
      .then(setFindings)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading findings...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const toggle = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  return (
    <div className="p-6">
      {findings.length === 0 ? (
        <p className="text-gray-400 text-sm">No findings yet.</p>
      ) : (
        <div className="space-y-4">
          {findings.map((f, idx) => (
            <div key={f.finding_id}
              className={`border rounded-lg overflow-hidden ${priorityColors[f.priority] || 'bg-white border-gray-200'}`}>

              {/* Finding header */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-gray-400">F{String(idx + 1).padStart(3, '0')}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColors[f.confidence] || 'bg-gray-100'}`}>
                        {f.confidence}
                      </span>
                      <span className="text-xs text-gray-500">{f.domain}</span>
                    </div>
                    <h3 className="font-semibold text-gray-900 text-sm">{f.finding_title}</h3>
                    {f.economic_impact && (
                      <p className="text-xs text-blue-700 font-medium mt-1">{f.economic_impact}</p>
                    )}
                  </div>
                  <button
                    onClick={() => toggle(f.finding_id)}
                    className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap"
                  >
                    {expanded[f.finding_id] ? 'Less ↑' : 'More ↓'}
                  </button>
                </div>
              </div>

              {/* Expanded detail */}
              {expanded[f.finding_id] && (
                <div className="px-4 pb-4 space-y-3 border-t border-gray-200 pt-3">
                  {f.operational_impact && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Operational Impact</div>
                      <p className="text-xs text-gray-700 leading-relaxed">{f.operational_impact}</p>
                    </div>
                  )}
                  {f.root_cause && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Root Cause</div>
                      <p className="text-xs text-gray-700 leading-relaxed">{f.root_cause}</p>
                    </div>
                  )}
                  {f.recommendation && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Recommendation</div>
                      <p className="text-xs text-gray-700 leading-relaxed">{f.recommendation}</p>
                    </div>
                  )}
                </div>
              )}

            </div>
          ))}
        </div>
      )}
    </div>
  )
}