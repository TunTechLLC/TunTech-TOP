import { useState, useEffect } from 'react'
import { api } from '../api'
import { DOMAINS, PHASES, PRIORITIES, EFFORTS } from '../constants'

const STATUSES = ['Proposed', 'In Progress', 'Complete', 'On Hold']

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

const EMPTY_FORM = {
  initiative_name:  '',
  domain:           'Delivery Operations',
  phase:            'Stabilize',
  priority:         'High',
  effort:           'Medium',
  estimated_impact: '',
  finding_id:       '',
  owner:            '',
  target_date:      '',
  status:           'Proposed',
}

export default function RoadmapPanel({ engagementId }) {
  const [items, setItems]         = useState([])
  const [findings, setFindings]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [showForm, setShowForm]   = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const [saveError, setSaveError] = useState(null)

  const fetchData = () => {
    Promise.all([
      api.roadmap.list(engagementId),
      api.findings.list(engagementId),
    ])
      .then(([r, f]) => { setItems(r); setFindings(f) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading roadmap...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async () => {
    if (!form.initiative_name) {
      setSaveError('Initiative name is required.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await api.roadmap.create(engagementId, {
        ...form,
        finding_id: form.finding_id || null,
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

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">{items.length} roadmap items</div>
        <button
          onClick={() => { setShowForm(!showForm); setSaveError(null) }}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Item'}
        </button>
      </div>

      {/* Add item form */}
      {showForm && (
        <div className="border border-blue-200 rounded-lg p-4 mb-6 bg-blue-50">
          <h3 className="text-sm font-semibold text-blue-900 mb-4">New Roadmap Item</h3>

          {saveError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              {saveError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 mb-3">

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Initiative name *</label>
              <input
                name="initiative_name"
                value={form.initiative_name}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Implement Formal Sales-to-Delivery Handoff Process"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Domain *</label>
              <select name="domain" value={form.domain} onChange={handleChange} className={sel}>
                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Phase *</label>
              <select name="phase" value={form.phase} onChange={handleChange} className={sel}>
                {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>

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
              <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
              <select name="status" value={form.status} onChange={handleChange} className={sel}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Target date</label>
              <input
                name="target_date"
                value={form.target_date}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. 2026-06-30"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
              <input
                name="owner"
                value={form.owner}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Director of Delivery"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Linked finding</label>
              <select name="finding_id" value={form.finding_id} onChange={handleChange} className={sel}>
                <option value="">— none —</option>
                {findings.map(f => (
                  <option key={f.finding_id} value={f.finding_id}>
                    {f.finding_id} — {f.finding_title}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Estimated impact</label>
              <input
                name="estimated_impact"
                value={form.estimated_impact}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Reduces project overrun frequency by establishing estimation baseline"
              />
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
              {saving ? 'Saving...' : 'Save Item'}
            </button>
          </div>
        </div>
      )}

      {/* Roadmap list grouped by phase */}
      <div className="space-y-8">
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
                  <div
                    key={item.item_id}
                    className="border border-gray-200 rounded-lg p-4 bg-white hover:border-gray-300 transition-colors"
                  >
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
                        {item.finding_title && (
                          <p className="text-xs text-blue-600 mt-1">Finding: {item.finding_title}</p>
                        )}
                      </div>
                      <div className="text-right text-xs text-gray-400 whitespace-nowrap">
                        {item.owner && <div className="font-medium text-gray-600">{item.owner}</div>}
                        {item.target_date && <div>{item.target_date}</div>}
                        <div className="mt-1">{item.effort} effort</div>
                        <div className="mt-1">{item.status}</div>
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

    </div>
  )
}
