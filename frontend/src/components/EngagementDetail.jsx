import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import SignalPanel   from './SignalPanel'
import PatternPanel  from './PatternPanel'
import AgentPanel    from './AgentPanel'
import FindingsPanel from './FindingsPanel'
import RoadmapPanel  from './RoadmapPanel'
import KnowledgePanel from './KnowledgePanel'
import ReportPanel   from './ReportPanel'

const TABS = [
  { id: 'signals',    label: 'Signals' },
  { id: 'patterns',   label: 'Patterns' },
  { id: 'agents',     label: 'Agents' },
  { id: 'findings',   label: 'Findings' },
  { id: 'roadmap',    label: 'Roadmap' },
  { id: 'knowledge',  label: 'Knowledge' },
  { id: 'report',     label: 'Report' },
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
  const [showSettings, setShowSettings]   = useState(false)
  const [settingsForm, setSettingsForm]   = useState({
    interviews_folder: '',
    documents_folder:  '',
    candidates_folder: '',
  })
  const [settingsSaving, setSettingsSaving] = useState(false)
  const [settingsError, setSettingsError]   = useState(null)

  useEffect(() => {
  api.engagements.get(id)
    .then(eng => {
      setEngagement(eng)
      setSettingsForm({
        interviews_folder: eng.interviews_folder || '',
        documents_folder:  eng.documents_folder  || '',
        candidates_folder: eng.candidates_folder || '',
      })
    })
    .catch(err => setError(err.message))
    .finally(() => setLoading(false))
}, [id])

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>
  if (error)   return <div className="p-8 text-red-600">Error: {error}</div>
  if (!engagement) return <div className="p-8 text-gray-500">Engagement not found.</div>

const handleSettingsSave = async () => {
  setSettingsSaving(true)
  setSettingsError(null)
  try {
    await api.engagements.updateSettings(id, settingsForm)
    setEngagement(prev => ({ ...prev, ...settingsForm }))
    setShowSettings(false)
  } catch (err) {
    setSettingsError(err.message)
  } finally {
    setSettingsSaving(false)
  }
}

 const renderPanel = () => {
  switch (activeTab) {
    case 'signals':   return <SignalPanel    engagementId={id} />
    case 'patterns':  return <PatternPanel   engagementId={id} />
    case 'agents':    return <AgentPanel     engagementId={id} />
    case 'findings':  return <FindingsPanel  engagementId={id} />
    case 'roadmap':   return <RoadmapPanel   engagementId={id} />
    case 'knowledge': return <KnowledgePanel engagementId={id} />
    case 'report':    return <ReportPanel    engagementId={id} />
    default:          return null
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

      {/* Edit Settings button */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          {showSettings ? 'Hide settings ↑' : 'Edit settings ↓'}
        </button>

        {showSettings && (
          <div className="mt-3 space-y-3">
            {settingsError && (
              <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {settingsError}
              </div>
            )}
            {[
              { key: 'interviews_folder', label: 'Interviews folder' },
              { key: 'documents_folder',  label: 'Client documents folder' },
              { key: 'candidates_folder', label: 'Candidates folder' },
            ].map(field => (
              <div key={field.key}>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  {field.label}
                </label>
                <input
                  value={settingsForm[field.key]}
                  onChange={e => setSettingsForm(prev => ({
                    ...prev, [field.key]: e.target.value
                  }))}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-blue-500"
                  placeholder={`C:\\Users\\varic\\OneDrive\\...\\${field.label}`}
                />
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded text-xs hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSettingsSave}
                disabled={settingsSaving}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {settingsSaving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>

    {/* Tabs */}

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