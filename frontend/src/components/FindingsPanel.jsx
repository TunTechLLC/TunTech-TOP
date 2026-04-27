import { useState, useEffect } from 'react'
import { api } from '../api'
import { DEFAULT_DOMAIN, DOMAINS, FINDING_CONFIDENCES, PRIORITIES, EFFORTS } from '../constants'

function parseDollarToFloat(s) {
  if (!s) return null
  s = s.trim()
  if (s.startsWith('\u26a0 ')) s = s.slice(2).trim()
  s = s.replace(/[~$,\s]/g, '')
  s = s.split(/[–\-]/)[0]
  let multiplier = 1
  if (/[Kk]$/.test(s)) { multiplier = 1_000;           s = s.slice(0, -1) }
  else if (/[Mm]$/.test(s)) { multiplier = 1_000_000;  s = s.slice(0, -1) }
  else if (/[Bb]$/.test(s)) { multiplier = 1_000_000_000; s = s.slice(0, -1) }
  const val = parseFloat(s)
  return isNaN(val) ? null : val * multiplier
}

function formatFloat(val) {
  if (val == null) return ''
  if (val >= 1_000_000) {
    const n = val / 1_000_000
    return `$${n % 1 === 0 ? n.toFixed(0) : n.toFixed(1)}M`
  }
  if (val >= 1_000) return `$${Math.round(val / 1_000)}K`
  return `$${Math.round(val)}`
}

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

const FIGURE_TYPES = [
  { value: 'direct_exposure',    label: 'Direct Exposure' },
  { value: 'annual_drag',        label: 'Annual Drag' },
  { value: 'concentration_risk', label: 'Concentration Risk' },
  { value: 'opportunity',        label: 'Opportunity' },
  { value: 'replacement_cost',   label: 'Replacement Cost' },
]

const EMPTY_FORM = {
  finding_title:       '',
  domain:              DEFAULT_DOMAIN,
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

export default function FindingsPanel({ engagementId, onRefresh }) {
  const [findings, setFindings]             = useState([])
  const [patterns, setPatterns]             = useState([])
  const [agentRuns, setAgentRuns]           = useState([])
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState(null)
  const [expanded, setExpanded]             = useState({})
  const [showForm, setShowForm]             = useState(false)
  const [form, setForm]                     = useState(EMPTY_FORM)
  const [saving, setSaving]                 = useState(false)
  const [saveError, setSaveError]           = useState(null)
  const [synthCandidates, setSynthCandidates] = useState([])
  const [synthApproved, setSynthApproved]   = useState({})
  const [parsing, setParsing]               = useState(false)
  const [parseError, setParseError]         = useState(null)
  const [loadingFindings, setLoadingFindings] = useState(false)
  const [displayEdits, setDisplayEdits]       = useState({})
  const [savingDisplay, setSavingDisplay]     = useState({})
  const [saveDisplayError, setSaveDisplayError] = useState({})
  const [expandedEvidence, setExpandedEvidence] = useState(new Set())

  const initDisplayState = (f) => {
    const hasWarning = typeof f.suggested_figure === 'string' && f.suggested_figure.startsWith('\u26a0 ')

    const stripWarn = (s) => (typeof s === 'string' && s.startsWith('\u26a0 ')) ? s.slice(2) : s
    const isWarn    = (s) => typeof s === 'string' && s.startsWith('\u26a0 ')

    // Confirmed Exposure
    const confVal = f.confirmed_figure != null
      ? formatFloat(f.confirmed_figure)
      : (stripWarn(f.suggested_confirmed_figure) || '')
    // Derived Exposure
    const derivVal = f.derived_figure != null
      ? formatFloat(f.derived_figure)
      : (stripWarn(f.suggested_derived_figure) || '')
    // Annual Drag
    const dragVal = f.annual_drag_figure != null
      ? formatFloat(f.annual_drag_figure)
      : (stripWarn(f.suggested_annual_drag_figure) || '')

    if (f.display_figure != null) {
      return {
        display_figure:       f.display_figure,
        display_label:        f.display_label  || '',
        figure_type:          f.figure_type    || 'direct_exposure',
        include_in_executive: !!f.include_in_executive,
        isDirty:              true,
        hasWarning:           false,
        confirmed_figure:     confVal,
        derived_figure:       derivVal,
        annual_drag_figure:   dragVal,
        confirmedSuggested:   f.confirmed_figure == null && !!stripWarn(f.suggested_confirmed_figure),
        derivedSuggested:     f.derived_figure   == null && !!stripWarn(f.suggested_derived_figure),
        annualDragSuggested:  f.annual_drag_figure == null && !!stripWarn(f.suggested_annual_drag_figure),
        confirmedWarning:     f.confirmed_figure   == null && isWarn(f.suggested_confirmed_figure),
        derivedWarning:       f.derived_figure     == null && isWarn(f.suggested_derived_figure),
        annualDragWarning:    f.annual_drag_figure  == null && isWarn(f.suggested_annual_drag_figure),
      }
    }
    if (f.suggested_figure != null) {
      return {
        display_figure:       hasWarning ? f.suggested_figure.slice(2) : f.suggested_figure,
        display_label:        f.suggested_label       || '',
        figure_type:          f.suggested_figure_type || 'direct_exposure',
        include_in_executive: false,
        isDirty:              false,
        hasWarning,
        confirmed_figure:     confVal,
        derived_figure:       derivVal,
        annual_drag_figure:   dragVal,
        confirmedSuggested:   f.confirmed_figure == null && !!stripWarn(f.suggested_confirmed_figure),
        derivedSuggested:     f.derived_figure   == null && !!stripWarn(f.suggested_derived_figure),
        annualDragSuggested:  f.annual_drag_figure == null && !!stripWarn(f.suggested_annual_drag_figure),
        confirmedWarning:     f.confirmed_figure   == null && isWarn(f.suggested_confirmed_figure),
        derivedWarning:       f.derived_figure     == null && isWarn(f.suggested_derived_figure),
        annualDragWarning:    f.annual_drag_figure  == null && isWarn(f.suggested_annual_drag_figure),
      }
    }
    return {
      display_figure: '', display_label: '', figure_type: 'direct_exposure',
      include_in_executive: false, isDirty: false, hasWarning: false,
      confirmed_figure: confVal, derived_figure: derivVal, annual_drag_figure: dragVal,
      confirmedSuggested:  f.confirmed_figure   == null && !!stripWarn(f.suggested_confirmed_figure),
      derivedSuggested:    f.derived_figure     == null && !!stripWarn(f.suggested_derived_figure),
      annualDragSuggested: f.annual_drag_figure  == null && !!stripWarn(f.suggested_annual_drag_figure),
      confirmedWarning:    f.confirmed_figure   == null && isWarn(f.suggested_confirmed_figure),
      derivedWarning:      f.derived_figure     == null && isWarn(f.suggested_derived_figure),
      annualDragWarning:   f.annual_drag_figure  == null && isWarn(f.suggested_annual_drag_figure),
    }
  }

  const fetchData = () => {
    Promise.all([
      api.findings.list(engagementId),
      api.patterns.list(engagementId),
      api.agents.list(engagementId),
    ])
      .then(([f, p, a]) => {
        setFindings(f)
        setPatterns(p)
        setAgentRuns(a)
        const edits = {}
        f.forEach(finding => { edits[finding.finding_id] = initDisplayState(finding) })
        setDisplayEdits(edits)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading findings...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  // Show all loaded patterns in checklists — accepted=1 is set atomically when findings
  // are created, so filtering to accepted=1 would show nothing before the first finding exists.
  const acceptedPatterns    = patterns
  const synthesizerAccepted = agentRuns.some(r => r.agent_name === 'Synthesizer' && r.accepted === 1)
  const synthApprovedCount  = Object.values(synthApproved).filter(Boolean).length

  const toggle = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  const handleParseSynthesizer = async () => {
    setParsing(true)
    setParseError(null)
    try {
      const data = await api.findings.parseSynthesizer(engagementId)
      const candidatesWithEpIds = (data.candidates || []).map(c => {
        const suggestedEpIds = (c.suggested_pattern_ids || [])
          .map(pid => acceptedPatterns.find(p => p.pattern_id === pid))
          .filter(Boolean)
          .map(p => p.ep_id)
        return { ...c, contributing_ep_ids: suggestedEpIds }
      })
      setSynthCandidates(candidatesWithEpIds)
      const allApproved = {}
      candidatesWithEpIds.forEach((_, idx) => { allApproved[idx] = true })
      setSynthApproved(allApproved)
    } catch (err) {
      setParseError(err.message)
    } finally {
      setParsing(false)
    }
  }

  const handleSynthCandidateChange = (idx, field, value) => {
    setSynthCandidates(prev => prev.map((c, i) => i === idx ? { ...c, [field]: value } : c))
  }

  const toggleEvidence = (idx) => {
    setExpandedEvidence(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleSynthPatternToggle = (idx, epId) => {
    setSynthCandidates(prev => prev.map((c, i) => {
      if (i !== idx) return c
      const ids = c.contributing_ep_ids || []
      return {
        ...c,
        contributing_ep_ids: ids.includes(epId)
          ? ids.filter(id => id !== epId)
          : [...ids, epId],
      }
    }))
  }

  const handleLoadSynthFindings = async () => {
    const approvedList = synthCandidates.filter((_, idx) => synthApproved[idx])
    if (approvedList.length === 0) {
      setParseError('Select at least one finding to load.')
      return
    }
    const missingPatterns = approvedList.filter(f => !f.contributing_ep_ids || f.contributing_ep_ids.length === 0)
    if (missingPatterns.length > 0) {
      setParseError(`${missingPatterns.length} selected finding(s) have no contributing patterns. Select at least one pattern for each approved finding.`)
      return
    }
    setLoadingFindings(true)
    setParseError(null)
    try {
      for (const finding of approvedList) {
        await api.findings.create(engagementId, {
          finding_title:       finding.finding_title,
          domain:              finding.domain,
          confidence:          finding.confidence,
          operational_impact:  finding.operational_impact,
          economic_impact:     finding.economic_impact,
          root_cause:          finding.root_cause,
          recommendation:      finding.recommendation,
          priority:            finding.priority,
          effort:              finding.effort,
          opd_section:         finding.opd_section ? parseInt(finding.opd_section, 10) : null,
          contributing_ep_ids: finding.contributing_ep_ids || [],
        })
      }
      setSynthCandidates([])
      setSynthApproved({})
      fetchData()
      onRefresh?.()
    } catch (err) {
      setParseError(err.message)
    } finally {
      setLoadingFindings(false)
    }
  }

  const handleDisplayChange = (findingId, field, value) => {
    setDisplayEdits(prev => ({
      ...prev,
      [findingId]: { ...prev[findingId], [field]: value, isDirty: true },
    }))
  }

  const handleSaveDisplay = async (findingId) => {
    const edit = displayEdits[findingId]
    if (!edit) return
    setSavingDisplay(prev => ({ ...prev, [findingId]: true }))
    setSaveDisplayError(prev => ({ ...prev, [findingId]: null }))
    try {
      await api.findings.update(engagementId, findingId, {
        display_figure:       edit.display_figure       || null,
        display_label:        edit.display_label        || null,
        figure_type:          edit.figure_type          || null,
        include_in_executive: edit.include_in_executive ? 1 : 0,
        confirmed_figure:     parseDollarToFloat(edit.confirmed_figure),
        derived_figure:       parseDollarToFloat(edit.derived_figure),
        annual_drag_figure:   parseDollarToFloat(edit.annual_drag_figure),
      })
      // Refresh findings so stored values reflect the save
      fetchData()
      onRefresh?.()
    } catch (err) {
      setSaveDisplayError(prev => ({ ...prev, [findingId]: err.message }))
    } finally {
      setSavingDisplay(prev => ({ ...prev, [findingId]: false }))
    }
  }

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
      onRefresh?.()
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

      {/* Parse Findings button — visible when Synthesizer accepted, no findings yet, no candidates pending */}
      {synthesizerAccepted && findings.length === 0 && synthCandidates.length === 0 && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded flex items-center justify-between">
          <span className="text-xs text-green-800">
            Synthesizer accepted — parse findings automatically from the synthesis output.
          </span>
          <button
            onClick={handleParseSynthesizer}
            disabled={parsing}
            className="px-3 py-1.5 bg-green-700 text-white rounded text-xs font-medium hover:bg-green-800 disabled:opacity-50 ml-4 whitespace-nowrap"
          >
            {parsing ? 'Parsing...' : 'Parse Findings'}
          </button>
        </div>
      )}

      {parseError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {parseError}
        </div>
      )}

      {/* Synthesizer finding candidates review */}
      {synthCandidates.length > 0 && (
        <div className="mb-6 border border-green-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-green-50">
            <div>
              <span className="text-sm font-semibold text-green-900">
                {synthCandidates.length} finding candidates
              </span>
              <span className="text-xs text-green-600 ml-2">{synthApprovedCount} selected</span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { const a = {}; synthCandidates.forEach((_, i) => { a[i] = true }); setSynthApproved(a) }}
                className="text-xs text-green-700 hover:text-green-900"
              >
                Select all
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => setSynthApproved({})}
                className="text-xs text-green-700 hover:text-green-900"
              >
                Select none
              </button>
              <button
                onClick={handleLoadSynthFindings}
                disabled={loadingFindings || synthApprovedCount === 0}
                className="px-3 py-1 bg-green-700 text-white rounded text-xs font-medium hover:bg-green-800 disabled:opacity-50 ml-2"
              >
                {loadingFindings ? 'Loading...' : 'Load ' + synthApprovedCount + ' Finding(s)'}
              </button>
              <button
                onClick={() => { setSynthCandidates([]); setSynthApproved([]); setParseError(null) }}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Discard
              </button>
            </div>
          </div>

          <div className="divide-y divide-gray-100 max-h-screen overflow-y-auto">
            {synthCandidates.map((c, idx) => (
              <div
                key={idx}
                className={'p-4 transition-colors ' + (synthApproved[idx] ? 'bg-white' : 'bg-gray-50 opacity-60')}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={synthApproved[idx] || false}
                    onChange={() => setSynthApproved(prev => ({ ...prev, [idx]: !prev[idx] }))}
                    className="mt-1 shrink-0"
                  />
                  <div className="flex-1 space-y-2">

                    {/* Title */}
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Finding title</div>
                      <input
                        value={c.finding_title || ''}
                        onChange={e => handleSynthCandidateChange(idx, 'finding_title', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-sm font-medium focus:outline-none focus:border-blue-400"
                        placeholder="Finding title"
                      />
                    </div>

                    {/* Domain + confidence */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2">
                        <div className="text-xs text-gray-500 mb-0.5">Domain</div>
                        <select
                          value={c.domain || DEFAULT_DOMAIN}
                          onChange={e => handleSynthCandidateChange(idx, 'domain', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        >
                          {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                        </select>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">Confidence</div>
                        <select
                          value={c.confidence || 'High'}
                          onChange={e => handleSynthCandidateChange(idx, 'confidence', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        >
                          {FINDING_CONFIDENCES.map(v => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </div>
                    </div>

                    {/* Priority + effort + OPD section */}
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">Priority</div>
                        <select
                          value={c.priority || 'High'}
                          onChange={e => handleSynthCandidateChange(idx, 'priority', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        >
                          {PRIORITIES.map(v => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">Effort</div>
                        <select
                          value={c.effort || 'Medium'}
                          onChange={e => handleSynthCandidateChange(idx, 'effort', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        >
                          {EFFORTS.map(v => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">OPD section (1–8)</div>
                        <input
                          value={c.opd_section || ''}
                          onChange={e => handleSynthCandidateChange(idx, 'opd_section', parseInt(e.target.value, 10) || '')}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          placeholder="1–8"
                        />
                      </div>
                    </div>

                    {/* Impact fields */}
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">Operational impact</div>
                        <textarea
                          value={c.operational_impact || ''}
                          onChange={e => handleSynthCandidateChange(idx, 'operational_impact', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          rows={2}
                        />
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-0.5">Economic impact</div>
                        <textarea
                          value={c.economic_impact || ''}
                          onChange={e => handleSynthCandidateChange(idx, 'economic_impact', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          rows={2}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Root cause</div>
                      <textarea
                        value={c.root_cause || ''}
                        onChange={e => handleSynthCandidateChange(idx, 'root_cause', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        rows={2}
                      />
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Recommendation</div>
                      <textarea
                        value={c.recommendation || ''}
                        onChange={e => handleSynthCandidateChange(idx, 'recommendation', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                        rows={2}
                      />
                    </div>

                    {/* Contributing patterns checklist */}
                    {acceptedPatterns.length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-gray-600 mb-1">
                          Contributing patterns
                          {c.suggested_pattern_ids && c.suggested_pattern_ids.length > 0 && (
                            <span className="text-gray-400 font-normal ml-1">
                              — pre-selected by Claude: {c.suggested_pattern_ids.join(', ')}
                            </span>
                          )}
                        </div>
                        <div className="space-y-1 max-h-32 overflow-y-auto border border-gray-100 rounded p-2 bg-gray-50">
                          {acceptedPatterns.map(p => (
                            <label
                              key={p.ep_id}
                              className="flex items-start gap-2 cursor-pointer hover:bg-white p-1 rounded"
                            >
                              <input
                                type="checkbox"
                                checked={(c.contributing_ep_ids || []).includes(p.ep_id)}
                                onChange={() => handleSynthPatternToggle(idx, p.ep_id)}
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
                      </div>
                    )}

                    {/* Evidence summary */}
                    {c.evidence_summary && (
                      <p className="text-xs text-gray-500 italic">{c.evidence_summary}</p>
                    )}

                    {/* Key quotes */}
                    {c.key_quotes && (() => {
                      try {
                        const quotes = JSON.parse(c.key_quotes)
                        if (quotes.length === 0) return null
                        return (
                          <div>
                            <div className="text-xs font-medium text-gray-600 mb-1">Key quotes</div>
                            <ul className="space-y-1">
                              {quotes.map((q, qi) => (
                                <li key={qi} className="text-xs text-gray-600 border-l-2 border-gray-300 pl-2 italic">
                                  "{q}"
                                </li>
                              ))}
                            </ul>
                          </div>
                        )
                      } catch { return null }
                    })()}

                    {/* Evidence chain */}
                    {c.evidence_chain && (
                      <div>
                        <button
                          onClick={() => toggleEvidence(idx)}
                          className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                        >
                          <span>{expandedEvidence.has(idx) ? '▼' : '▶'}</span>
                          <span>
                            Evidence Chain ({c.evidence_chain.patterns.length} pattern{c.evidence_chain.patterns.length !== 1 ? 's' : ''},{' '}
                            {c.evidence_chain.signals.length + c.evidence_chain.signals_hidden} signal{(c.evidence_chain.signals.length + c.evidence_chain.signals_hidden) !== 1 ? 's' : ''})
                          </span>
                        </button>
                        {expandedEvidence.has(idx) && (
                          <div className="mt-2 space-y-2 border-l-2 border-gray-200 pl-3">
                            <div className="space-y-1">
                              {c.evidence_chain.patterns.map(p => (
                                <div key={p.pattern_id} className="text-xs text-gray-600 flex items-center gap-1 flex-wrap">
                                  <span className="font-mono text-gray-400">{p.pattern_id}</span>
                                  <span>—</span>
                                  <span className="font-medium">{p.pattern_name}</span>
                                  <span className={`px-1.5 py-0.5 rounded font-medium ${confidenceColors[p.confidence] || 'bg-gray-100 text-gray-500'}`}>{p.confidence}</span>
                                  {p.signal_ids.length > 0 && (
                                    <span className="text-gray-400">→ {p.signal_ids.join(', ')}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                            {c.evidence_chain.signals.length > 0 && (
                              <div className="space-y-1 pt-1 border-t border-gray-100">
                                {c.evidence_chain.signals.map(s => (
                                  <div key={s.signal_id} className="text-xs text-gray-500">
                                    <span className="font-mono text-gray-400">{s.signal_id}</span>
                                    {' '}
                                    <span className="font-medium text-gray-700">{s.signal_name}</span>
                                    {' · '}
                                    <span>{s.confidence}</span>
                                    {s.quote && <span className="text-gray-500 italic"> · "{s.quote}"</span>}
                                    {s.source_file && <span className="text-gray-400"> [{s.source_file}]</span>}
                                  </div>
                                ))}
                                {c.evidence_chain.signals_hidden > 0 && (
                                  <div className="text-xs text-gray-400 italic">
                                    + {c.evidence_chain.signals_hidden} more signal{c.evidence_chain.signals_hidden !== 1 ? 's' : ''} not shown
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
                        Confidence: {f.confidence}
                      </span>
                      <span className="text-xs text-gray-600 font-medium">
                        Priority: {f.priority}
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
                  {f.evidence_summary && (
                    <p className="text-xs text-gray-500 italic">{f.evidence_summary}</p>
                  )}
                  {f.key_quotes && (() => {
                    try {
                      const quotes = JSON.parse(f.key_quotes)
                      if (quotes.length === 0) return null
                      return (
                        <div>
                          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                            Key Quotes
                          </div>
                          <ul className="space-y-1">
                            {quotes.map((q, qi) => (
                              <li key={qi} className="text-xs text-gray-600 border-l-2 border-gray-300 pl-2 italic">
                                "{q}"
                              </li>
                            ))}
                          </ul>
                        </div>
                      )
                    } catch { return null }
                  })()}

                  {/* Executive Display */}
                  {(() => {
                    const edit = displayEdits[f.finding_id] || {}
                    const isSuggestion = !edit.isDirty
                    const inputCls = isSuggestion
                      ? 'w-full border border-gray-200 rounded px-2 py-1 text-xs text-gray-400 italic focus:outline-none focus:border-blue-400'
                      : 'w-full border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-blue-400'
                    const warnInputCls = isSuggestion
                      ? 'w-full border border-red-400 rounded px-2 py-1 text-xs text-gray-400 italic focus:outline-none focus:border-red-500'
                      : 'w-full border border-red-400 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-red-500'
                    return (
                      <div className="border-t border-gray-100 pt-3">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                          Executive Display
                        </div>
                        <div className="space-y-2">

                          {/* Figure */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Figure</div>
                            <input
                              value={edit.display_figure || ''}
                              onChange={e => handleDisplayChange(f.finding_id, 'display_figure', e.target.value)}
                              className={edit.hasWarning ? warnInputCls : inputCls}
                              placeholder="e.g. $526K"
                            />
                            {isSuggestion && edit.display_figure && (
                              <div className="text-xs text-gray-400 mt-0.5">
                                suggested — verify before saving
                              </div>
                            )}
                            {edit.hasWarning && (
                              <div className="text-xs text-red-600 mt-0.5">
                                ⚠ Exceeds confirmed client revenue — verify before accepting
                              </div>
                            )}
                          </div>

                          {/* Label */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Label</div>
                            <input
                              value={edit.display_label || ''}
                              onChange={e => handleDisplayChange(f.finding_id, 'display_label', e.target.value)}
                              className={inputCls}
                              placeholder="e.g. Annual gross profit shortfall"
                            />
                            {isSuggestion && edit.display_label && (
                              <div className="text-xs text-gray-400 mt-0.5">
                                suggested — verify before saving
                              </div>
                            )}
                          </div>

                          {/* Type */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Type</div>
                            <select
                              value={edit.figure_type || 'direct_exposure'}
                              onChange={e => handleDisplayChange(f.finding_id, 'figure_type', e.target.value)}
                              className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                            >
                              {FIGURE_TYPES.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                              ))}
                            </select>
                          </div>

                          {/* Checkbox */}
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!edit.include_in_executive}
                              onChange={e => handleDisplayChange(f.finding_id, 'include_in_executive', e.target.checked)}
                              className="shrink-0"
                            />
                            <span className="text-xs text-gray-600">Include in executive summary</span>
                          </label>

                          {/* Confirmed Exposure */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Confirmed Exposure</div>
                            <input
                              value={edit.confirmed_figure || ''}
                              onChange={e => handleDisplayChange(f.finding_id, 'confirmed_figure', e.target.value)}
                              className={edit.confirmedWarning
                                ? 'w-full border border-red-400 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-red-500'
                                : 'w-full border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-blue-400'}
                              placeholder="e.g. $85K"
                            />
                            {edit.confirmedSuggested && edit.confirmed_figure && (
                              <div className="text-xs text-gray-400 mt-0.5">suggested — verify before saving</div>
                            )}
                            {edit.confirmedWarning && (
                              <div className="text-xs text-red-600 mt-0.5">⚠ Exceeds confirmed client revenue — verify before accepting</div>
                            )}
                          </div>

                          {/* Derived Exposure */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Derived Exposure</div>
                            <input
                              value={edit.derived_figure || ''}
                              onChange={e => handleDisplayChange(f.finding_id, 'derived_figure', e.target.value)}
                              className={edit.derivedWarning
                                ? 'w-full border border-red-400 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-red-500'
                                : 'w-full border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-blue-400'}
                              placeholder="e.g. $368K"
                            />
                            {edit.derivedSuggested && edit.derived_figure && (
                              <div className="text-xs text-gray-400 mt-0.5">suggested — verify before saving</div>
                            )}
                            {edit.derivedWarning && (
                              <div className="text-xs text-red-600 mt-0.5">⚠ Exceeds confirmed client revenue — verify before accepting</div>
                            )}
                          </div>

                          {/* Annual Drag */}
                          <div>
                            <div className="text-xs text-gray-500 mb-0.5">Annual Drag</div>
                            <input
                              value={edit.annual_drag_figure || ''}
                              onChange={e => handleDisplayChange(f.finding_id, 'annual_drag_figure', e.target.value)}
                              className={edit.annualDragWarning
                                ? 'w-full border border-red-400 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-red-500'
                                : 'w-full border border-gray-300 rounded px-2 py-1 text-xs text-gray-900 focus:outline-none focus:border-blue-400'}
                              placeholder="e.g. $220K"
                            />
                            {edit.annualDragSuggested && edit.annual_drag_figure && (
                              <div className="text-xs text-gray-400 mt-0.5">suggested — verify before saving</div>
                            )}
                            {edit.annualDragWarning && (
                              <div className="text-xs text-red-600 mt-0.5">⚠ Exceeds confirmed client revenue — verify before accepting</div>
                            )}
                          </div>

                          {/* Save */}
                          {saveDisplayError[f.finding_id] && (
                            <div className="text-xs text-red-600">{saveDisplayError[f.finding_id]}</div>
                          )}
                          <div className="flex justify-end">
                            <button
                              onClick={() => handleSaveDisplay(f.finding_id)}
                              disabled={!!savingDisplay[f.finding_id]}
                              className="px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                            >
                              {savingDisplay[f.finding_id] ? 'Saving...' : 'Save display settings'}
                            </button>
                          </div>

                        </div>
                      </div>
                    )
                  })()}

                </div>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  )
}
