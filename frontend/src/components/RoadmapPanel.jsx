import { useState, useEffect } from 'react'
import { api } from '../api'

const PHASES = ['Stabilize', 'Optimize', 'Scale']

const phaseColors = {
  Stabilize: 'bg-red-50 border-red-200 text-red-800',
  Optimize:  'bg-yellow-50 border-yellow-200 text-yellow-800',
  Scale:     'bg-green-50 border-green-200 text-green-800',
}

const priorityColors = {
  High:   'bg-red-100 text-red-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Low:    'bg-gray-100 text-gray-600',
}

export default function RoadmapPanel({ engagementId }) {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    api.roadmap.list(engagementId)
      .then(setItems)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading roadmap...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  return (
    <div className="p-6 space-y-8">
      {PHASES.map(phase => {
        const phaseItems = items.filter(i => i.phase === phase)
        if (phaseItems.length === 0) return null
        return (
          <div key={phase}>
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border mb-4 ${phaseColors[phase]}`}>
              {phase} — {phaseItems.length} initiative{phaseItems.length !== 1 ? 's' : ''}
            </div>
            <div className="space-y-3">
              {phaseItems.map(item => (
                <div key={item.item_id}
                  className="border border-gray-200 rounded-lg p-4 bg-white hover:border-gray-300 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${priorityColors[item.priority] || 'bg-gray-100'}`}>
                          {item.priority}
                        </span>
                        <span className="text-xs text-gray-400">{item.domain}</span>
                      </div>
                      <p className="font-medium text-gray-900 text-sm">{item.initiative_name}</p>
                      {item.estimated_impact && (
                        <p className="text-xs text-gray-500 mt-1">{item.estimated_impact}</p>
                      )}
                    </div>
                    <div className="text-right text-xs text-gray-400 whitespace-nowrap">
                      {item.owner && <div className="font-medium text-gray-600">{item.owner}</div>}
                      {item.target_date && <div>{item.target_date}</div>}
                      <div className="mt-1">{item.effort} effort</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
      {items.length === 0 && (
        <p className="text-gray-400 text-sm">No roadmap items yet.</p>
      )}
    </div>
  )
}