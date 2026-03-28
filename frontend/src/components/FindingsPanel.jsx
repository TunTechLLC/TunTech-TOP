import { useState, useEffect } from 'react'
import { api } from '../api'
import { DOMAINS, FINDING_CONFIDENCES, PRIORITIES, EFFORTS } from '../constants'

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

const EMPTY_FORM = {
  finding_title:       '',
  domain:              'Delivery Operations',
  confidence:          'High',
  priority:            'High',
  effort:              'Medium',
  opd_section:         '',
  operational_impact:  '',
  economic_impact:     '',
  root_cause:          '',
  recommendation:      '',
  contributing_ep_ids: [],
}

export default function FindingsPanel({ engagementId }) {
  const [findings, setFindings]   = useState([])
  const [patterns, setPatterns]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [expanded, setExpanded]   = useState({})
  const [showForm, setShowForm]   = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const [saveError, setSaveError] = useState(null)

  const fetchData = () => {
    Promise.all([
      api.findings.list(engagementId),
      api.patterns.list(engagementId),
    ])
      .then(([f, p]) => { setFindings(f); setPatterns(p) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading findings...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const acceptedPatterns = patterns.filter(p => p.accepted === 1)

  const toggle = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handlePatternToggle = (epId) => {
    setForm(prev => ({
      ...prev,
      contributing_ep_ids: prev.contributing_ep_ids.includes(epId)
        ? prev.contributing_ep_ids.filter(id => id !== epId)
        : [...prev.contributing_ep_ids, epId]
    }))
  }

  const handleSubmit = async () => {
    if (!form.finding_title || !form.operational_impact ||
        !form.economic_impact || !form.root_cause || !form.recommendation) {
      setSaveError('Please fill in all required fields.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await api.findings.create(engagementId, {
        ...form,
        opd_section: form.opd_section ? parseInt(form.opd_section, 10) : null,
      })
      setForm(EMPTY_FORM)
      setShowForm(false)
      fetchData()
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inp = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
  const sel = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
  const ta  = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">{findings.length} findings</div>
        <button
          onClick={() => { setShowForm(!showForm); setSaveError(null) }}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Finding'}
        </button>
      </div>

      {/* Parse Findings button — Step 8 Extension 2 (not yet built)
          Appears here when Synthesizer is accepted and finding count is zero.
          Calls api.findings.parseSynthesizer() which does not exist yet.
          Build in Step 8 Extension 2. */}

      {/* Finding form */}
      {showForm && (
        <div className="border border-blue-200 rounded-lg p-4 mb-6 bg-blue-50">
          <h3 className="text-sm font-semibold text-blue-900 mb-4">New Finding</h3>

          {saveError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              {saveError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 mb-3">

            {/* Finding title */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Finding title *</label>
              <input
                name="finding_title"
                value={form.finding_title}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Chronic Project Overruns"
              />
            </div>

            {/* Domain and confidence */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Domain *</label>
              <select name="domain" value={form.domain} onChange={handleChange} className={sel}>
                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Confidence *</label>
              <select name="confidence" value={form.confidence} onChange={handleChange} className={sel}>
                {FINDING_CONFIDENCES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            {/* Priority, effort, OPD section */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Priority *</label>
              <select name="priority" value={form.priority} onChange={handleChange} className={sel}>
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Effort *</label>
              <select name="effort" value={form.effort} onChange={handleChange} className={sel}>
                {EFFORTS.map(e => <option key={e} value={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">OPD section number</label>
              <input
                name="opd_section"
                value={form.opd_section}
                onChange={handleChange}
                className={inp}
                placeholder="1-8"
              />
            </div>

            {/* Text areas */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Operational impact *</label>
              <textarea
                name="operational_impact"
                value={form.operational_impact}
                onChange={handleChange}
                className={ta}
                rows={2}
                placeholder="What is the operational consequence of this finding?"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Economic impact *</label>
              <textarea
                name="economic_impact"
                value={form.economic_impact}
                onChange={handleChange}
                className={ta}
                rows={2}
                placeholder="e.g. $130K-$280K/year in direct overrun cost (INFERRED)"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Root cause *</label>
              <textarea
                name="root_cause"
                value={form.root_cause}
                onChange={handleChange}
                className={ta}
                rows={2}
                placeholder="One sentence root cause statement"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Recommendation *</label>
              <textarea
                name="recommendation"
                value={form.recommendation}
                onChange={handleChange}
                className={ta}
                rows={2}
                placeholder="One sentence actionable recommendation"
              />
            </div>

            {/* Contributing patterns */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Contributing patterns
                <span className="text-gray-400 font-normal ml-1">
                  — select accepted patterns that support this finding
                </span>
              </label>
              {acceptedPatterns.length === 0 ? (
                <p className="text-xs text-gray-400 italic">
                  No accepted patterns yet. Accept patterns in the Patterns tab first.
                </p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto border border-gray-200 rounded p-2 bg-white">
                  {acceptedPatterns.map(p => (
                    <label
                      key={p.ep_id}
                      className="flex items-start gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={form.contributing_ep_ids.includes(p.ep_id)}
                        onChange={() => handlePatternToggle(p.ep_id)}
                        className="mt-0.5 shrink-0"
                      />
                      <div>
                        <span className="text-xs font-medium text-gray-700">
                          {p.pattern_id} — {p.pattern_name}
                        </span>
                        <span className="text-xs text-gray-400 ml-2">{p.domain}</span>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

          </div>

          <div className="flex justify-end gap-2 mt-2">
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
              {saving ? 'Saving...' : 'Save Finding'}
            </button>
          </div>
        </div>
      )}

      {/* Findings list */}
      {findings.length === 0 ? (
        <p className="text-gray-400 text-sm">No findings yet.</p>
      ) : (
        <div className="space-y-4">
          {findings.map((f, idx) => (
            <div
              key={f.finding_id}
              className={`border rounded-lg overflow-hidden ${priorityColors[f.priority] || 'bg-white border-gray-200'}`}
            >
              <div className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-gray-400">
                        F{String(idx + 1).padStart(3, '0')}
                      </span>
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
              {expanded[f.finding_id] && (
                <div className="px-4 pb-4 space-y-3 border-t border-gray-200 pt-3">
                  {f.operational_impact && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                        Operational Impact
                      </div>
                      <p className="text-xs text-gray-700 leading-relaxed">{f.operational_impact}</p>
                    </div>
                  )}
                  {f.root_cause && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                        Root Cause
                      </div>
                      <p className="text-xs text-gray-700 leading-relaxed">{f.root_cause}</p>
                    </div>
                  )}
                  {f.recommendation && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                        Recommendation
                      </div>
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
