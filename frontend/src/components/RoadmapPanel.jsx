import { useState, useEffect } from 'react'
import { api } from '../api'
import { DEFAULT_DOMAIN, DOMAINS, PHASES, PRIORITIES, EFFORTS } from '../constants'

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
  initiative_name:        '',
  domain:                 DEFAULT_DOMAIN,
  phase:                  'Stabilize',
  priority:               'High',
  effort:                 'Medium',
  estimated_impact:       '',
  finding_id:             '',
  owner:                  '',
  target_date:            '',
  status:                 'Proposed',
  capability:             '',
  addressing_finding_ids: '[]',
  depends_on:             '[]',
}

export default function RoadmapPanel({ engagementId, onRefresh }) {
  const [items, setItems]         = useState([])
  const [findings, setFindings]   = useState([])
  const [agentRuns, setAgentRuns] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [showForm, setShowForm]         = useState(false)
  const [form, setForm]                 = useState(EMPTY_FORM)
  const [saving, setSaving]             = useState(false)
  const [saveError, setSaveError]       = useState(null)
  const [editingId, setEditingId]       = useState(null)
  const [editForm, setEditForm]         = useState(EMPTY_FORM)
  const [editSaving, setEditSaving]     = useState(false)
  const [editError, setEditError]       = useState(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [roadmapCandidates, setRoadmapCandidates] = useState([])
  const [candidateApproved, setCandidateApproved] = useState({})
  const [parsing, setParsing]           = useState(false)
  const [parseError, setParseError]     = useState(null)
  const [loadingItems, setLoadingItems] = useState(false)

  const fetchData = () => {
    Promise.all([
      api.roadmap.list(engagementId),
      api.findings.list(engagementId),
      api.agents.list(engagementId),
    ])
      .then(([r, f, a]) => { setItems(r); setFindings(f); setAgentRuns(a) })
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

  const handleEditOpen = (item) => {
    setEditingId(item.item_id)
    setEditForm({
      initiative_name:        item.initiative_name        || '',
      domain:                 item.domain                 || DEFAULT_DOMAIN,
      phase:                  item.phase                  || 'Stabilize',
      priority:               item.priority               || 'High',
      effort:                 item.effort                 || 'Medium',
      estimated_impact:       item.estimated_impact       || '',
      finding_id:             item.finding_id             || '',
      owner:                  item.owner                  || '',
      target_date:            item.target_date            || '',
      status:                 item.status                 || 'Proposed',
      capability:             item.capability             || '',
      addressing_finding_ids: item.addressing_finding_ids || '[]',
      depends_on:             item.depends_on             || '[]',
    })
    setEditError(null)
  }

  const handleEditChange = (e) => {
    setEditForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleEditSave = async (itemId) => {
    if (!editForm.initiative_name) {
      setEditError('Initiative name is required.')
      return
    }
    setEditSaving(true)
    setEditError(null)
    try {
      await api.roadmap.update(engagementId, itemId, {
        ...editForm,
        finding_id: editForm.finding_id || null,
      })
      setEditingId(null)
      fetchData()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setEditSaving(false)
    }
  }

  const handleDelete = async (itemId) => {
    try {
      await api.roadmap.delete(engagementId, itemId)
      setConfirmDeleteId(null)
      fetchData()
    } catch (err) {
      setEditError(err.message)
    }
  }

  const synthesizerAccepted = agentRuns.some(r => r.agent_name === 'Synthesizer' && r.accepted === 1)
  const approvedCount = Object.values(candidateApproved).filter(Boolean).length

  const handleParseRoadmap = async () => {
    setParsing(true)
    setParseError(null)
    try {
      const data = await api.roadmap.parseSynthesizer(engagementId)
      const candidates = data.candidates || []
      setRoadmapCandidates(candidates)
      const allApproved = {}
      candidates.forEach((_, idx) => { allApproved[idx] = true })
      setCandidateApproved(allApproved)
    } catch (err) {
      setParseError(err.message)
    } finally {
      setParsing(false)
    }
  }

  const handleCandidateChange = (idx, field, value) => {
    setRoadmapCandidates(prev => prev.map((c, i) => i === idx ? { ...c, [field]: value } : c))
  }

  const handleLoadRoadmapItems = async () => {
    const approvedList = roadmapCandidates.filter((_, idx) => candidateApproved[idx])
    if (approvedList.length === 0) {
      setParseError('Select at least one item to load.')
      return
    }
    setLoadingItems(true)
    setParseError(null)
    try {
      for (const item of approvedList) {
        await api.roadmap.create(engagementId, {
          initiative_name:        item.initiative_name,
          domain:                 item.domain,
          phase:                  item.phase,
          priority:               item.priority,
          effort:                 item.effort,
          estimated_impact:       item.estimated_impact || '',
          owner:                  item.owner || '',
          capability:             item.capability || '',
          addressing_finding_ids: item.addressing_finding_ids || '[]',
        })
      }
      setRoadmapCandidates([])
      setCandidateApproved({})
      fetchData()
    } catch (err) {
      setParseError(err.message)
    } finally {
      setLoadingItems(false)
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

      {/* Parse Roadmap button — visible when Synthesizer accepted, no items yet, no candidates pending */}
      {synthesizerAccepted && items.length === 0 && roadmapCandidates.length === 0 && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded flex items-center justify-between">
          <span className="text-xs text-green-800">
            Synthesizer accepted — extract roadmap initiatives automatically from the synthesis output.
          </span>
          <button
            onClick={handleParseRoadmap}
            disabled={parsing}
            className="px-3 py-1.5 bg-green-700 text-white rounded text-xs font-medium hover:bg-green-800 disabled:opacity-50 ml-4 whitespace-nowrap"
          >
            {parsing ? 'Parsing...' : 'Parse Roadmap'}
          </button>
        </div>
      )}

      {parseError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {parseError}
        </div>
      )}

      {/* Roadmap candidates review */}
      {roadmapCandidates.length > 0 && (
        <div className="mb-6 border border-green-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-green-50">
            <div>
              <span className="text-sm font-semibold text-green-900">
                {roadmapCandidates.length} roadmap candidates
              </span>
              <span className="text-xs text-green-600 ml-2">{approvedCount} selected</span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { const a = {}; roadmapCandidates.forEach((_, i) => { a[i] = true }); setCandidateApproved(a) }}
                className="text-xs text-green-700 hover:text-green-900"
              >
                Select all
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => setCandidateApproved({})}
                className="text-xs text-green-700 hover:text-green-900"
              >
                Select none
              </button>
              <button
                onClick={handleLoadRoadmapItems}
                disabled={loadingItems || approvedCount === 0}
                className="px-3 py-1 bg-green-700 text-white rounded text-xs font-medium hover:bg-green-800 disabled:opacity-50 ml-2"
              >
                {loadingItems ? 'Loading...' : `Load ${approvedCount} Item(s)`}
              </button>
              <button
                onClick={() => { setRoadmapCandidates([]); setCandidateApproved({}); setParseError(null) }}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Discard
              </button>
            </div>
          </div>

          <div className="divide-y divide-gray-100 max-h-screen overflow-y-auto">
            {['Stabilize', 'Optimize', 'Scale'].map(phase => {
              const phaseIdxs = roadmapCandidates
                .map((c, i) => ({ c, i }))
                .filter(({ c }) => c.phase === phase)
              if (phaseIdxs.length === 0) return null
              return (
                <div key={phase}>
                  <div className={`px-4 py-2 text-xs font-semibold border-b ${phaseColors[phase]}`}>
                    {phase} — {phaseIdxs.length} initiative{phaseIdxs.length !== 1 ? 's' : ''}
                  </div>
                  {phaseIdxs.map(({ c, i: idx }) => (
                    <div
                      key={idx}
                      className={'p-4 transition-colors ' + (candidateApproved[idx] ? 'bg-white' : 'bg-gray-50 opacity-60')}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={candidateApproved[idx] || false}
                          onChange={() => setCandidateApproved(prev => ({ ...prev, [idx]: !prev[idx] }))}
                          className="mt-1 shrink-0"
                        />
                        <div className="flex-1 space-y-2">

                          {/* Initiative name */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Initiative name</div>
                            <input
                              value={c.initiative_name || ''}
                              onChange={e => handleCandidateChange(idx, 'initiative_name', e.target.value)}
                              className="w-full border border-gray-200 rounded px-2 py-1 text-sm font-medium focus:outline-none focus:border-blue-400"
                            />
                          </div>

                          {/* Domain / Phase / Priority / Effort */}
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <div className="text-xs text-gray-500 mb-0.5">Domain</div>
                              <select
                                value={c.domain || DEFAULT_DOMAIN}
                                onChange={e => handleCandidateChange(idx, 'domain', e.target.value)}
                                className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                              >
                                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                              </select>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-0.5">Phase</div>
                              <select
                                value={c.phase || 'Stabilize'}
                                onChange={e => handleCandidateChange(idx, 'phase', e.target.value)}
                                className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                              >
                                {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-0.5">Priority</div>
                              <select
                                value={c.priority || 'Medium'}
                                onChange={e => handleCandidateChange(idx, 'priority', e.target.value)}
                                className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                              >
                                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-0.5">Effort</div>
                              <select
                                value={c.effort || 'Medium'}
                                onChange={e => handleCandidateChange(idx, 'effort', e.target.value)}
                                className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                              >
                                {EFFORTS.map(e => <option key={e} value={e}>{e}</option>)}
                              </select>
                            </div>
                          </div>

                          {/* Estimated impact */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Estimated impact</div>
                            <input
                              value={c.estimated_impact || ''}
                              onChange={e => handleCandidateChange(idx, 'estimated_impact', e.target.value)}
                              className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                            />
                          </div>

                          {/* Owner */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Owner</div>
                            <input
                              value={c.owner || ''}
                              onChange={e => handleCandidateChange(idx, 'owner', e.target.value)}
                              className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                            />
                          </div>

                          {/* Capability */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Capability</div>
                            <input
                              value={c.capability || ''}
                              onChange={e => handleCandidateChange(idx, 'capability', e.target.value)}
                              className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                              placeholder="What the organisation will be able to do once this is complete"
                            />
                          </div>

                          {/* Addressing findings — read only */}
                          {(() => {
                            try {
                              const fids = JSON.parse(c.addressing_finding_ids || '[]')
                              if (fids.length === 0) return null
                              const titles = fids.map(fid => {
                                const f = findings.find(f => f.finding_id === fid)
                                return f ? `[${fid}] ${f.finding_title}` : fid
                              })
                              return (
                                <div className="text-xs text-blue-600 border-l-2 border-blue-200 pl-2">
                                  Addresses: {titles.join(', ')}
                                </div>
                              )
                            } catch { return null }
                          })()}

                          {/* Rationale — read only */}
                          {c.rationale && (
                            <div className="text-xs text-gray-400 italic border-l-2 border-gray-200 pl-2">
                              {c.rationale}
                            </div>
                          )}

                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        </div>
      )}

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

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Capability</label>
              <textarea
                name="capability"
                value={form.capability}
                onChange={handleChange}
                className={inp}
                rows={2}
                placeholder="What the organisation will be able to do once this initiative is complete"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Depends on
                <span className="text-gray-400 font-normal ml-1">— select prerequisites</span>
              </label>
              {items.length === 0 ? (
                <p className="text-xs text-gray-400 italic">No existing roadmap items to depend on.</p>
              ) : (
                <div className="space-y-1 max-h-32 overflow-y-auto border border-gray-200 rounded p-2 bg-white">
                  {items.map(i => {
                    const deps = (() => { try { return JSON.parse(form.depends_on || '[]') } catch { return [] } })()
                    return (
                      <label key={i.item_id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                        <input
                          type="checkbox"
                          checked={deps.includes(i.item_id)}
                          onChange={() => {
                            const cur = (() => { try { return JSON.parse(form.depends_on || '[]') } catch { return [] } })()
                            const next = cur.includes(i.item_id) ? cur.filter(id => id !== i.item_id) : [...cur, i.item_id]
                            setForm(prev => ({ ...prev, depends_on: JSON.stringify(next) }))
                          }}
                          className="shrink-0"
                        />
                        <span className="text-xs text-gray-700">{i.phase} — {i.initiative_name}</span>
                      </label>
                    )
                  })}
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
                    className="border border-gray-200 rounded-lg bg-white overflow-hidden"
                  >
                    {editingId === item.item_id ? (
                      /* ── Inline edit form ── */
                      <div className="p-4 bg-blue-50 border-b border-blue-200">
                        {editError && (
                          <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                            {editError}
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-3 mb-3">
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">Initiative name *</label>
                            <input name="initiative_name" value={editForm.initiative_name} onChange={handleEditChange} className={inp} />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Domain</label>
                            <select name="domain" value={editForm.domain} onChange={handleEditChange} className={sel}>
                              {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Phase</label>
                            <select name="phase" value={editForm.phase} onChange={handleEditChange} className={sel}>
                              {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Priority</label>
                            <select name="priority" value={editForm.priority} onChange={handleEditChange} className={sel}>
                              {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Effort</label>
                            <select name="effort" value={editForm.effort} onChange={handleEditChange} className={sel}>
                              {EFFORTS.map(e => <option key={e} value={e}>{e}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
                            <select name="status" value={editForm.status} onChange={handleEditChange} className={sel}>
                              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Target date</label>
                            <input name="target_date" value={editForm.target_date} onChange={handleEditChange} className={inp} placeholder="e.g. 2026-06-30" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                            <input name="owner" value={editForm.owner} onChange={handleEditChange} className={inp} />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">Linked finding</label>
                            <select name="finding_id" value={editForm.finding_id} onChange={handleEditChange} className={sel}>
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
                            <input name="estimated_impact" value={editForm.estimated_impact} onChange={handleEditChange} className={inp} />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">Capability</label>
                            <textarea name="capability" value={editForm.capability || ''} onChange={handleEditChange} className={inp} rows={2} placeholder="What the organisation will be able to do once this initiative is complete" />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Depends on
                              <span className="text-gray-400 font-normal ml-1">— select prerequisites</span>
                            </label>
                            {items.filter(i => i.item_id !== item.item_id).length === 0 ? (
                              <p className="text-xs text-gray-400 italic">No other roadmap items to depend on.</p>
                            ) : (
                              <div className="space-y-1 max-h-32 overflow-y-auto border border-gray-200 rounded p-2 bg-white">
                                {items.filter(i => i.item_id !== item.item_id).map(i => {
                                  const deps = (() => { try { return JSON.parse(editForm.depends_on || '[]') } catch { return [] } })()
                                  return (
                                    <label key={i.item_id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                                      <input
                                        type="checkbox"
                                        checked={deps.includes(i.item_id)}
                                        onChange={() => {
                                          const cur = (() => { try { return JSON.parse(editForm.depends_on || '[]') } catch { return [] } })()
                                          const next = cur.includes(i.item_id) ? cur.filter(id => id !== i.item_id) : [...cur, i.item_id]
                                          setEditForm(prev => ({ ...prev, depends_on: JSON.stringify(next) }))
                                        }}
                                        className="shrink-0"
                                      />
                                      <span className="text-xs text-gray-700">{i.phase} — {i.initiative_name}</span>
                                    </label>
                                  )
                                })}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => { setEditingId(null); setEditError(null) }}
                            className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded text-xs hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleEditSave(item.item_id)}
                            disabled={editSaving}
                            className="px-4 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                          >
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* ── Read-only row ── */
                      <div className="p-4 hover:border-gray-300 transition-colors">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${priorityColors[item.priority] || 'bg-gray-100'}`}>
                                {item.priority}
                              </span>
                              <span className="text-xs text-gray-400">{item.domain}</span>
                            </div>
                            <p className="font-medium text-gray-900 text-sm">{item.initiative_name}</p>
                            {item.capability && (
                              <p className="text-xs text-gray-600 italic mt-1">Capability: {item.capability}</p>
                            )}
                            {item.estimated_impact && (
                              <p className="text-xs text-gray-500 mt-1">{item.estimated_impact}</p>
                            )}
                            {item.finding_title && (
                              <p className="text-xs text-blue-600 mt-1">Finding: {item.finding_title}</p>
                            )}
                            {(() => {
                              try {
                                const fids = JSON.parse(item.addressing_finding_ids || '[]')
                                if (fids.length === 0) return null
                                const linked = fids.map(fid => findings.find(f => f.finding_id === fid)).filter(Boolean)
                                if (linked.length === 0) return null
                                return (
                                  <div className="mt-1 space-y-0.5">
                                    {linked.map(f => (
                                      <p key={f.finding_id} className="text-xs text-blue-500">
                                        Addresses [{f.finding_id}]: {f.economic_impact || f.finding_title}
                                      </p>
                                    ))}
                                  </div>
                                )
                              } catch { return null }
                            })()}
                            {(() => {
                              try {
                                const deps = JSON.parse(item.depends_on || '[]')
                                if (deps.length === 0) return null
                                const names = deps.map(id => {
                                  const d = items.find(i => i.item_id === id)
                                  return d ? d.initiative_name : id
                                })
                                return (
                                  <p className="text-xs text-gray-400 mt-1">
                                    Prerequisites: {names.join(', ')}
                                  </p>
                                )
                              } catch { return null }
                            })()}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <div className="text-right text-xs text-gray-400 whitespace-nowrap">
                              {item.owner && <div className="font-medium text-gray-600">{item.owner}</div>}
                              {item.target_date && <div>{item.target_date}</div>}
                              <div className="mt-1">{item.effort} effort</div>
                              <div className="mt-1">{item.status}</div>
                            </div>
                            <div className="flex items-center gap-2 mt-2">
                              {confirmDeleteId === item.item_id ? (
                                <>
                                  <span className="text-xs text-red-600">Delete?</span>
                                  <button
                                    onClick={() => handleDelete(item.item_id)}
                                    className="text-xs px-2 py-0.5 bg-red-600 text-white rounded hover:bg-red-700"
                                  >
                                    Yes
                                  </button>
                                  <button
                                    onClick={() => setConfirmDeleteId(null)}
                                    className="text-xs px-2 py-0.5 border border-gray-300 text-gray-600 rounded hover:bg-gray-50"
                                  >
                                    No
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    onClick={() => handleEditOpen(item)}
                                    className="text-xs text-blue-600 hover:text-blue-800"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    onClick={() => setConfirmDeleteId(item.item_id)}
                                    className="text-xs text-red-400 hover:text-red-600"
                                  >
                                    Delete
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
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
