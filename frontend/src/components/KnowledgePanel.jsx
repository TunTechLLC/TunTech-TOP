import { useState, useEffect } from 'react'
import { api } from '../api'

const PROMOTION_TYPES = [
  'Pattern Refinement',
  'Process Note',
  'Prompt Improvement',
  'New Signal',
]

const typeColors = {
  'Pattern Refinement': 'bg-purple-100 text-purple-700',
  'Process Note':       'bg-blue-100 text-blue-700',
  'Prompt Improvement': 'bg-orange-100 text-orange-700',
  'New Signal':         'bg-teal-100 text-teal-700',
}

const EMPTY_FORM = {
  promotion_type:  PROMOTION_TYPES[0],
  description:     '',
  applied_to:      '',
  finding_id:      '',
  pattern_id:      '',
  promotion_date:  new Date().toISOString().split('T')[0],
}

export default function KnowledgePanel({ engagementId, onRefresh }) {
  const [promotions, setPromotions] = useState([])
  const [findings, setFindings]     = useState([])
  const [patterns, setPatterns]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [showForm, setShowForm]     = useState(false)
  const [form, setForm]             = useState(EMPTY_FORM)
  const [saving, setSaving]         = useState(false)
  const [saveError, setSaveError]   = useState(null)

  const fetchData = () => {
    Promise.all([
      api.knowledge.list(engagementId),
      api.findings.list(engagementId),
      api.patterns.list(engagementId),
    ])
      .then(([k, f, p]) => {
        setPromotions(k)
        setFindings(f)
        setPatterns(p)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading knowledge promotions...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const types = [...new Set(promotions.map(p => p.promotion_type))]

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async () => {
    if (!form.description) {
      setSaveError('Description is required.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await api.knowledge.create(engagementId, {
        ...form,
        finding_id: form.finding_id || null,
        pattern_id: form.pattern_id || null,
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
        <div className="text-sm text-gray-500">{promotions.length} knowledge promotions</div>
        <button
          onClick={() => { setShowForm(!showForm); setSaveError(null) }}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Promotion'}
        </button>
      </div>

      {/* Add promotion form */}
      {showForm && (
        <div className="border border-blue-200 rounded-lg p-4 mb-6 bg-blue-50">
          <h3 className="text-sm font-semibold text-blue-900 mb-4">New Knowledge Promotion</h3>

          {saveError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              {saveError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 mb-3">

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Type *</label>
              <select name="promotion_type" value={form.promotion_type} onChange={handleChange} className={sel}>
                {PROMOTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Promotion date</label>
              <input name="promotion_date" value={form.promotion_date} onChange={handleChange}
                className={inp} />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Description *</label>
              <textarea name="description" value={form.description} onChange={handleChange}
                className={inp} rows={3}
                placeholder="What was learned and what should change as a result?" />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Applied to</label>
              <input name="applied_to" value={form.applied_to} onChange={handleChange}
                className={inp} placeholder="e.g. Patterns table — P27 notes field" />
            </div>

            <div>
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

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Linked pattern</label>
              <select name="pattern_id" value={form.pattern_id} onChange={handleChange} className={sel}>
                <option value="">— none —</option>
                {patterns.map(p => (
                  <option key={p.ep_id} value={p.pattern_id}>
                    {p.pattern_id} — {p.pattern_name}
                  </option>
                ))}
              </select>
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
              {saving ? 'Saving...' : 'Save Promotion'}
            </button>
          </div>
        </div>
      )}

      {/* Promotions list grouped by type */}
      <div className="space-y-6">
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
                        <p className="text-xs text-gray-400 mt-2">Applied to: {p.applied_to}</p>
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

    </div>
  )
}