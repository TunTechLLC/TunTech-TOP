import { useState, useEffect } from 'react'
import { api } from '../api'

const typeColors = {
  'Pattern Refinement': 'bg-purple-100 text-purple-700',
  'Process Note':       'bg-blue-100 text-blue-700',
  'Prompt Improvement': 'bg-orange-100 text-orange-700',
  'New Signal':         'bg-teal-100 text-teal-700',
}

export default function KnowledgePanel({ engagementId }) {
  const [promotions, setPromotions] = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)

  useEffect(() => {
    api.knowledge.list(engagementId)
      .then(setPromotions)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading knowledge promotions...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const types = [...new Set(promotions.map(p => p.promotion_type))]

  return (
    <div className="p-6 space-y-6">
      {promotions.length === 0 ? (
        <p className="text-gray-400 text-sm">No knowledge promotions yet.</p>
      ) : (
        types.map(type => {
          const typeItems = promotions.filter(p => p.promotion_type === type)
          return (
            <div key={type}>
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold mb-3 ${typeColors[type] || 'bg-gray-100 text-gray-600'}`}>
                {type} — {typeItems.length}
              </div>
              <div className="space-y-3">
                {typeItems.map(p => (
                  <div key={p.promotion_id}
                    className="border border-gray-100 rounded-lg p-4 hover:border-gray-300 transition-colors">
                    <p className="text-sm text-gray-700 leading-relaxed">{p.description}</p>
                    {p.applied_to && (
                      <p className="text-xs text-gray-400 mt-2">
                        Applied to: {p.applied_to}
                      </p>
                    )}
                    {(p.pattern_name || p.finding_title) && (
                      <div className="flex gap-2 mt-2">
                        {p.pattern_name && (
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {p.pattern_name}
                          </span>
                        )}
                        {p.finding_title && (
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {p.finding_title}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}