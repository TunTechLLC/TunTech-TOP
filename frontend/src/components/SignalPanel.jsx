import { useState, useEffect } from 'react'
import { api } from '../api'

const DOMAINS = [
  'Sales & Pipeline',
  'Sales-to-Delivery Transition',
  'Delivery Operations',
  'Resource Management',
  'Project Governance / PMO',
  'Consulting Economics',
  'Customer Experience',
]

const CONFIDENCE_LEVELS = ['High', 'Medium', 'Hypothesis']
const SOURCES = ['Interview', 'Document', 'Observation']

const confidenceColors = {
  High:       'bg-red-100 text-red-800',
  Medium:     'bg-yellow-100 text-yellow-800',
  Hypothesis: 'bg-gray-100 text-gray-600',
}

const sourceColors = {
  Interview: 'bg-blue-100 text-blue-700',
  Document:  'bg-purple-100 text-purple-700',
}

const EMPTY_FORM = {
  signal_name:        '',
  domain:             DOMAINS[0],
  observed_value:     '',
  normalized_band:    '',
  signal_confidence:  'High',
  source:             'Interview',
  economic_relevance: '',
  notes:              '',
}

export default function SignalPanel({ engagementId }) {
  const [signals, setSignals]   = useState([])
  const [summary, setSummary]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [filter, setFilter]     = useState('All')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]         = useState(EMPTY_FORM)
  const [saving, setSaving]     = useState(false)
  const [saveError, setSaveError] = useState(null)

  const fetchData = () => {
    Promise.all([
      api.signals.list(engagementId),
      api.signals.summary(engagementId),
    ])
      .then(([sigs, sum]) => { setSignals(sigs); setSummary(sum) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading signals...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const filtered = filter === 'All' ? signals : signals.filter(s => s.domain === filter)

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async () => {
    if (!form.signal_name || !form.observed_value || !form.normalized_band) {
      setSaveError('Signal name, observed value, and normalized band are required.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await api.signals.create(engagementId, form)
      setForm(EMPTY_FORM)
      setShowForm(false)
      fetchData()
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const sel = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
  const inp = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"

  return (
    <div className="p-6">

      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          {signals.length} signals total
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setSaveError(null) }}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Signal'}
        </button>
      </div>

      {/* Add signal form */}
      {showForm && (
        <div className="border border-blue-200 rounded-lg p-4 mb-6 bg-blue-50">
          <h3 className="text-sm font-semibold text-blue-900 mb-4">New Signal</h3>

          {saveError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              {saveError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Signal name *</label>
              <input name="signal_name" value={form.signal_name} onChange={handleChange}
                className={inp} placeholder="e.g. Projects on schedule" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Domain *</label>
              <select name="domain" value={form.domain} onChange={handleChange} className={sel}>
                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Confidence *</label>
              <select name="signal_confidence" value={form.signal_confidence} onChange={handleChange} className={sel}>
                {CONFIDENCE_LEVELS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Observed value *</label>
              <input name="observed_value" value={form.observed_value} onChange={handleChange}
                className={inp} placeholder="e.g. 57%" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Normalized band *</label>
              <input name="normalized_band" value={form.normalized_band} onChange={handleChange}
                className={inp} placeholder="e.g. Below 80% target" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Source *</label>
              <select name="source" value={form.source} onChange={handleChange} className={sel}>
                {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Economic relevance</label>
              <input name="economic_relevance" value={form.economic_relevance} onChange={handleChange}
                className={inp} placeholder="e.g. Delivery margin" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
              <textarea name="notes" value={form.notes} onChange={handleChange}
                className={inp} rows={2} placeholder="Supporting detail, context, source quote" />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setShowForm(false); setForm(EMPTY_FORM); setSaveError(null) }}
              className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded text-xs hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={saving}
              className="px-4 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Signal'}
            </button>
          </div>
        </div>
      )}

      {/* Domain filter badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setFilter('All')}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
            filter === 'All'
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 text-gray-600 hover:border-gray-400'
          }`}
        >
          All · {signals.length}
        </button>
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
            Clear ×
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