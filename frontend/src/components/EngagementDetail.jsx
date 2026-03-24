import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import SignalPanel from './SignalPanel'
import PatternPanel from './PatternPanel'

const TABS = [
  { id: 'signals',  label: 'Signals' },
  { id: 'patterns', label: 'Patterns' },
  { id: 'agents',   label: 'Agents' },
  { id: 'findings', label: 'Findings' },
  { id: 'roadmap',  label: 'Roadmap' },
  { id: 'knowledge',label: 'Knowledge' },
  { id: 'report',   label: 'Report' },
]

function Placeholder({ title }) {
  return (
    <div className="p-6 text-gray-400 text-sm">
      {title} panel — coming soon.
    </div>
  )
}

export default function EngagementDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [engagement, setEngagement] = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [activeTab, setActiveTab]   = useState('signals')

  useEffect(() => {
    api.engagements.get(id)
      .then(setEngagement)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>
  if (error)   return <div className="p-8 text-red-600">Error: {error}</div>
  if (!engagement) return <div className="p-8 text-gray-500">Engagement not found.</div>

  const renderPanel = () => {
    switch (activeTab) {
      case 'signals':  return <SignalPanel  engagementId={id} />
      case 'patterns': return <PatternPanel engagementId={id} />
      case 'agents':   return <Placeholder title="Agents" />
      case 'findings': return <Placeholder title="Findings" />
      case 'roadmap':  return <Placeholder title="Roadmap" />
      case 'knowledge':return <Placeholder title="Knowledge" />
      case 'report':   return <Placeholder title="Report" />
      default:         return null
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-8">

      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="text-gray-400 hover:text-gray-600 text-sm mb-6 block"
      >
        ← Back to Dashboard
      </button>

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-blue-900">{engagement.firm_name}</h1>
            <p className="text-gray-500 text-sm mt-1">{engagement.engagement_name}</p>
          </div>
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            {engagement.status}
          </span>
        </div>

        {/* Stats row */}
        <div className="flex gap-8 mt-6 pt-4 border-t border-gray-100">
          {[
            { label: 'Firm size',  value: `${engagement.firm_size} people` },
            { label: 'Signals',    value: engagement.signal_count  ?? 0 },
            { label: 'Patterns',   value: engagement.pattern_count ?? 0 },
            { label: 'Findings',   value: engagement.finding_count ?? 0 },
          ].map(stat => (
            <div key={stat.label}>
              <div className="text-lg font-bold text-blue-900">{stat.value}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-white border border-b-white border-gray-200 text-blue-600 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Panel */}
      <div className="bg-white rounded-lg border border-gray-200">
        {renderPanel()}
      </div>

    </div>
  )
}