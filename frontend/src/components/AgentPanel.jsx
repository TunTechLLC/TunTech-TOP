import { useState, useEffect } from 'react'
import { api } from '../api'

const statusColors = {
  1: 'bg-green-100 text-green-700',
  0: 'bg-gray-100 text-gray-600',
}

export default function AgentPanel({ engagementId }) {
  const [runs, setRuns]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    api.agents.list(engagementId)
      .then(setRuns)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading agent runs...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const toggleExpanded = (runId) => {
    setExpanded(prev => ({ ...prev, [runId]: !prev[runId] }))
  }

  return (
    <div className="p-6">
      <div className="space-y-4">
        {runs.length === 0 ? (
          <p className="text-gray-400 text-sm">No agent runs yet.</p>
        ) : (
          runs.map((run, idx) => (
            <div key={run.run_id} className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="flex items-center justify-between p-4 bg-gray-50">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-gray-400 bg-white border border-gray-200 px-2 py-0.5 rounded">
                    {idx + 1}
                  </span>
                  <span className="font-medium text-gray-900 text-sm">{run.agent_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[run.accepted]}`}>
                    {run.accepted === 1 ? 'Accepted' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">{run.run_date}</span>
                  <button
                    onClick={() => toggleExpanded(run.run_id)}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    {expanded[run.run_id] ? 'Hide output' : 'View output'}
                  </button>
                </div>
              </div>
              {run.output_summary && (
                <div className="px-4 py-3 border-t border-gray-100">
                  <p className="text-xs text-gray-600 leading-relaxed">{run.output_summary}</p>
                </div>
              )}
              {expanded[run.run_id] && run.output_doc_link && (
                <div className="px-4 py-3 border-t border-gray-100 bg-blue-50">
                  <span className="text-xs text-blue-600">{run.output_doc_link}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
