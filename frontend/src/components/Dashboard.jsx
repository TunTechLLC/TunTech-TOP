import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const statusColors = {
  'Active':    'bg-green-100 text-green-800',
  'Complete':  'bg-blue-100 text-blue-800',
  'On Hold':   'bg-yellow-100 text-yellow-800',
}

function StatBadge({ label, value }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-blue-900">{value}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
    </div>
  )
}

function EngagementCard({ engagement, onClick }) {
  const statusClass = statusColors[engagement.status] || 'bg-gray-100 text-gray-800'
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg border border-gray-200 p-6 cursor-pointer hover:border-blue-400 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{engagement.firm_name}</h2>
          <p className="text-sm text-gray-500 mt-1">{engagement.engagement_name}</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusClass}`}>
          {engagement.status}
        </span>
      </div>
      <div className="flex justify-around border-t border-gray-100 pt-4">
        <StatBadge label="Signals"  value={engagement.signal_count  ?? 0} />
        <StatBadge label="Patterns" value={engagement.pattern_count ?? 0} />
        <StatBadge label="Findings" value={engagement.finding_count ?? 0} />
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [engagements, setEngagements] = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.engagements.list()
      .then(setEngagements)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="p-8 text-gray-500">Loading engagements...</div>
  )

  if (error) return (
    <div className="p-8 text-red-600">Error: {error}</div>
  )

  return (
    <div className="max-w-5xl mx-auto p-8">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-blue-900">TunTech Operations Platform</h1>
          <p className="text-gray-500 mt-1">{engagements.length} engagement{engagements.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/cross-engagement')}
            className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors text-sm font-medium"
          >
            Cross-Engagement Report
          </button>
          <button
            onClick={() => navigate('/engagements/new')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            New Engagement
          </button>
        </div>
      </div>

      {/* Engagement cards */}
      {engagements.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No engagements yet.</p>
          <p className="text-sm mt-2">Click New Engagement to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {engagements.map(eng => (
            <EngagementCard
              key={eng.engagement_id}
              engagement={eng}
              onClick={() => navigate(`/engagements/${eng.engagement_id}`)}
            />
          ))}
        </div>
      )}

    </div>
  )
}