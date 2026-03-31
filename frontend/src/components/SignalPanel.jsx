import { useState, useEffect } from 'react'
import { api } from '../api'
import { DOMAINS, CONFIDENCE_LEVELS, SOURCES } from '../constants'

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
  domain:             'Delivery Operations',
  observed_value:     '',
  normalized_band:    '',
  signal_confidence:  'High',
  source:             'Interview',
  economic_relevance: '',
  notes:              '',
}

export default function SignalPanel({ engagementId }) {
  const [signals, setSignals]             = useState([])
  const [summary, setSummary]             = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(null)
  const [filter, setFilter]               = useState('All')
  const [showForm, setShowForm]           = useState(false)
  const [form, setForm]                   = useState(EMPTY_FORM)
  const [saving, setSaving]               = useState(false)
  const [saveError, setSaveError]         = useState(null)
  const [processing, setProcessing]               = useState(false)
  const [processResult, setProcessResult]         = useState(null)
  const [processError, setProcessError]           = useState(null)
  const [candidates, setCandidates]               = useState([])
  const [hypothesisCandidates, setHypothesisCands] = useState([])
  const [showHypothesis, setShowHypothesis]       = useState(false)
  const [cullStats, setCullStats]                 = useState(null)
  const [approved, setApproved]                   = useState({})
  const [loadingCands, setLoadingCands]           = useState(false)

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

  const handleProcessFiles = async () => {
    setProcessing(true)
    setProcessError(null)
    setProcessResult(null)
    setCandidates([])
    setHypothesisCands([])
    setShowHypothesis(false)
    setCullStats(null)
    try {
      const result = await api.signals.processFiles(engagementId)
      setProcessResult(result)

      if (result.merged_candidate_file) {
        const data = await api.signals.readCandidates(engagementId, result.merged_candidate_file)
        const main = data.candidates || []
        const hypo = data.hypothesis_candidates || []
        setCandidates(main)
        setHypothesisCands(hypo)
        setCullStats({
          dedupCount:      data.dedup_count       ?? result.dedup_count       ?? 0,
          domainCapCount:  data.domain_cap_count  ?? result.domain_cap_count  ?? 0,
          hypothesisCount: data.hypothesis_count  ?? result.hypothesis_count  ?? 0,
        })
        const allApproved = {}
        main.forEach(function(_, idx) { allApproved[idx] = true })
        setApproved(allApproved)
      }
    } catch (err) {
      setProcessError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleCandidateChange = (idx, field, value) => {
    if (idx < candidates.length) {
      setCandidates(prev => prev.map((c, i) => i === idx ? Object.assign({}, c, { [field]: value }) : c))
    } else {
      const hypoIdx = idx - candidates.length
      setHypothesisCands(prev => prev.map((c, i) => i === hypoIdx ? Object.assign({}, c, { [field]: value }) : c))
    }
  }

  const handleApproveToggle = (idx) => {
    setApproved(prev => Object.assign({}, prev, { [idx]: !prev[idx] }))
  }

  const displayCandidates = showHypothesis
    ? [...candidates, ...hypothesisCandidates]
    : candidates

  const handleApproveAll = () => {
    const all = {}
    displayCandidates.forEach(function(_, idx) { all[idx] = true })
    setApproved(all)
  }

  const handleApproveNone = () => setApproved({})

  const handleLoadCandidates = async () => {
    const approvedList = displayCandidates.filter((_, idx) => approved[idx])
    if (approvedList.length === 0) {
      setProcessError('Select at least one signal to load.')
      return
    }
    setLoadingCands(true)
    setProcessError(null)
    try {
      await api.signals.loadCandidates(engagementId, { candidates: approvedList })
      setCandidates([])
      setHypothesisCands([])
      setApproved({})
      setCullStats(null)
      setProcessResult(null)
      fetchData()
    } catch (err) {
      setProcessError(err.message)
    } finally {
      setLoadingCands(false)
    }
  }

  const approvedCount = Object.values(approved).filter(Boolean).length
  const sel = "w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500"
  const inp = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"

  return (
    <div className="p-6">

      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">{signals.length} signals total</div>
        <div className="flex gap-2">
          <button
            onClick={handleProcessFiles}
            disabled={processing}
            className="px-3 py-1.5 border border-blue-600 text-blue-600 rounded text-xs font-medium hover:bg-blue-50 disabled:opacity-50 transition-colors"
          >
            {processing ? 'Processing...' : 'Process Files'}
          </button>
          <button
            onClick={() => { setShowForm(!showForm); setSaveError(null) }}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
          >
            {showForm ? 'Cancel' : '+ Add Signal'}
          </button>
        </div>
      </div>

      {processResult && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
          {processResult.files_processed === 0
            ? 'No new files found to process.'
            : processResult.files_processed + ' file(s) processed — ' +
              processResult.total_candidates + ' signal candidates extracted.' +
              (candidates.length > 0 ? ' Review below.' : '')}
        </div>
      )}

      {processError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {processError}
        </div>
      )}

      {(candidates.length > 0 || cullStats) && (
        <div className="mb-6 border border-blue-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-blue-50">
            <div>
              <span className="text-sm font-semibold text-blue-900">
                {displayCandidates.length} signal candidates
              </span>
              <span className="text-xs text-blue-600 ml-2">{approvedCount} selected</span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={handleApproveAll} className="text-xs text-blue-600 hover:text-blue-800">
                Select all
              </button>
              <span className="text-gray-300">|</span>
              <button onClick={handleApproveNone} className="text-xs text-blue-600 hover:text-blue-800">
                Select none
              </button>
              <button
                onClick={handleLoadCandidates}
                disabled={loadingCands || approvedCount === 0}
                className="px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50 ml-2"
              >
                {loadingCands ? 'Loading...' : 'Load ' + approvedCount + ' Signal(s)'}
              </button>
              <button
                onClick={() => { setCandidates([]); setHypothesisCands([]); setApproved({}); setCullStats(null) }}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Discard
              </button>
            </div>
          </div>

          {cullStats && (
            <div className="px-4 py-2 bg-gray-50 border-b border-blue-100 flex items-center gap-4 text-xs text-gray-500">
              <span>{cullStats.dedupCount} duplicate{cullStats.dedupCount !== 1 ? 's' : ''} removed</span>
              <span className="text-gray-300">·</span>
              <span>{cullStats.domainCapCount} capped by domain</span>
              <span className="text-gray-300">·</span>
              <span>
                {cullStats.hypothesisCount} hypothesis signal{cullStats.hypothesisCount !== 1 ? 's' : ''} hidden
                {cullStats.hypothesisCount > 0 && (
                  <button
                    onClick={() => setShowHypothesis(v => !v)}
                    className="ml-2 text-blue-500 hover:text-blue-700 underline"
                  >
                    {showHypothesis ? 'Hide' : 'Show'}
                  </button>
                )}
              </span>
            </div>
          )}

          <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
            {displayCandidates.map((c, idx) => (
              <div key={idx}>
                {showHypothesis && idx === candidates.length && (
                  <div className="px-4 py-2 bg-gray-100 border-y border-gray-200 flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500">Hypothesis signals</span>
                    <span className="text-xs text-gray-400">— not selected by default</span>
                  </div>
                )}
                <div className={'p-3 transition-colors ' + (approved[idx] ? 'bg-white' : 'bg-gray-50 opacity-60')}>
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={approved[idx] || false}
                      onChange={() => handleApproveToggle(idx)}
                      className="mt-1 shrink-0"
                    />
                    <div className="flex-1 grid grid-cols-2 gap-2">
                      {c.source_file && (
                        <div className="col-span-2 text-xs text-gray-400 font-mono -mb-1">
                          {c.source_file}
                        </div>
                      )}
                      <div className="col-span-2">
                        <input
                          value={c.signal_name || ''}
                          onChange={e => handleCandidateChange(idx, 'signal_name', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs font-medium focus:outline-none focus:border-blue-400"
                          placeholder="Signal name"
                        />
                      </div>
                      <div>
                        <select
                          value={c.domain || 'Delivery Operations'}
                          onChange={e => handleCandidateChange(idx, 'domain', e.target.value)}
                          className={sel}
                        >
                          {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                        </select>
                      </div>
                      <div>
                        <select
                          value={c.signal_confidence || 'Medium'}
                          onChange={e => handleCandidateChange(idx, 'signal_confidence', e.target.value)}
                          className={sel}
                        >
                          {CONFIDENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                        </select>
                      </div>
                      <div>
                        <input
                          value={c.observed_value || ''}
                          onChange={e => handleCandidateChange(idx, 'observed_value', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          placeholder="Observed value"
                        />
                      </div>
                      <div>
                        <input
                          value={c.normalized_band || ''}
                          onChange={e => handleCandidateChange(idx, 'normalized_band', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          placeholder="Normalized band"
                        />
                      </div>
                      <div className="col-span-2">
                        <textarea
                          value={c.notes || ''}
                          onChange={e => handleCandidateChange(idx, 'notes', e.target.value)}
                          className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-400"
                          rows={2}
                          placeholder="Supporting quote and notes"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
              <input
                name="signal_name"
                value={form.signal_name}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Projects on schedule"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Domain *</label>
              <select
                name="domain"
                value={form.domain}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
              >
                {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Confidence *</label>
              <select
                name="signal_confidence"
                value={form.signal_confidence}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
              >
                {CONFIDENCE_LEVELS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Observed value *</label>
              <input
                name="observed_value"
                value={form.observed_value}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. 57%"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Normalized band *</label>
              <input
                name="normalized_band"
                value={form.normalized_band}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Below 80% target"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Source *</label>
              <select
                name="source"
                value={form.source}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-500"
              >
                {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Economic relevance</label>
              <input
                name="economic_relevance"
                value={form.economic_relevance}
                onChange={handleChange}
                className={inp}
                placeholder="e.g. Delivery margin"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                name="notes"
                value={form.notes}
                onChange={handleChange}
                className={inp}
                rows={2}
                placeholder="Supporting detail, context, source quote"
              />
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

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setFilter('All')}
          className={'px-3 py-1 rounded-full text-xs font-medium border transition-colors ' +
            (filter === 'All'
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 text-gray-600 hover:border-gray-400')}
        >
          All - {signals.length}
        </button>
        {summary.map(s => (
          <button
            key={s.domain + '-' + s.signal_confidence}
            onClick={() => setFilter(s.domain)}
            className={'px-3 py-1 rounded-full text-xs font-medium border transition-colors ' +
              (filter === s.domain
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-400')}
          >
            {s.domain} - {s.signal_confidence} - {s.signal_count}
          </button>
        ))}
        {filter !== 'All' && (
          <button
            onClick={() => setFilter('All')}
            className="px-3 py-1 rounded-full text-xs text-gray-400 hover:text-gray-600"
          >
            Clear x
          </button>
        )}
      </div>

      <div className="text-sm text-gray-500 mb-4">
        Showing {filtered.length} of {signals.length} signals
      </div>

      <div className="space-y-3">
        {filtered.map(signal => (
          <div
            key={signal.signal_id}
            className="border border-gray-100 rounded-lg p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-gray-900 text-sm">{signal.signal_name}</span>
                  <span className={'px-2 py-0.5 rounded text-xs font-medium ' +
                    (confidenceColors[signal.signal_confidence] || 'bg-gray-100 text-gray-600')}>
                    {signal.signal_confidence}
                  </span>
                  <span className={'px-2 py-0.5 rounded text-xs font-medium ' +
                    (sourceColors[signal.source] || 'bg-gray-100 text-gray-600')}>
                    {signal.source}
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">{signal.observed_value}</span>
                  {signal.normalized_band && (
                    <span className="text-gray-400"> - {signal.normalized_band}</span>
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
