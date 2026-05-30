import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

// Minimal panel for QA-1 development. The integrated QA tab (QA-5) will
// replace this with a richer layout that wraps QA-1/QA-2/QA-3 in one surface.

const TIER_META = {
  1: { label: 'Tier 1 — Obvious Accept', tone: 'green',  defaultExpanded: false },
  2: { label: 'Tier 2 — Judgment Call',  tone: 'amber',  defaultExpanded: true  },
  3: { label: 'Tier 3 — Low Confidence', tone: 'gray',   defaultExpanded: false },
}

const STATUS_PILL = {
  pending:  'bg-gray-100  text-gray-700',
  accepted: 'bg-green-600 text-white',
  rejected: 'bg-red-600   text-white',
}

const STATUS_LABEL = {
  pending:  'PENDING',
  accepted: '✓ ACCEPTED',
  rejected: '✗ REJECTED',
}

// Whole-card visual treatment per status — left accent border + tinted
// background lets the consultant scan the list and see at a glance what's
// been handled. The status pill is reinforcement, not the primary signal.
const CARD_STATE = {
  pending:  'border-l-4 border-l-gray-200 border-y border-r border-gray-200 bg-white',
  accepted: 'border-l-4 border-l-green-500 border-y border-r border-green-200 bg-green-50',
  rejected: 'border-l-4 border-l-gray-400 border-y border-r border-gray-200 bg-gray-50 opacity-70',
}

function CoverageItem({ item, onAccept, onReject }) {
  const partial = item.appears_in_roadmap === 1
  const accepted = item.status === 'accepted'
  const rejected = item.status === 'rejected'
  const acceptBtn = accepted
    ? "px-3 py-1 text-xs rounded bg-green-600 text-white font-medium"
    : "px-3 py-1 text-xs rounded border border-green-300 text-green-700 hover:bg-green-50"
  const rejectBtn = rejected
    ? "px-3 py-1 text-xs rounded bg-red-600 text-white font-medium"
    : "px-3 py-1 text-xs rounded border border-red-300 text-red-700 hover:bg-red-50"
  return (
    <div className={`rounded p-3 ${CARD_STATE[item.status]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900 text-sm">{item.who_said_it}</span>
            {partial && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                PARTIAL
              </span>
            )}
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${STATUS_PILL[item.status]}`}>
              {STATUS_LABEL[item.status]}
            </span>
          </div>
          <p className={`text-sm mt-1.5 leading-relaxed ${rejected ? 'text-gray-500 line-through' : 'text-gray-700'}`}>
            {item.what_was_said}
          </p>
          <div className="text-xs text-gray-500 mt-2 space-y-0.5">
            <div>
              <span className="font-mono">{item.source_file}</span>
              {' · '}
              {item.location_in_source}
            </div>
            {partial && item.roadmap_location && (
              <div className="italic">
                Partial coverage in roadmap: {item.roadmap_location}
              </div>
            )}
            <div className="text-[10px] text-gray-400 font-mono">{item.qa_coverage_id}</div>
          </div>
        </div>
        <div className="flex flex-col gap-1 shrink-0">
          <button
            onClick={() => onAccept(item.qa_coverage_id)}
            disabled={accepted}
            className={acceptBtn + (accepted ? '' : ' cursor-pointer')}
          >
            {accepted ? '✓ Accepted' : 'Accept'}
          </button>
          <button
            onClick={() => onReject(item.qa_coverage_id)}
            disabled={rejected}
            className={rejectBtn + (rejected ? '' : ' cursor-pointer')}
          >
            {rejected ? '✗ Rejected' : 'Reject'}
          </button>
        </div>
      </div>
    </div>
  )
}

function TierSection({ tier, items, expanded, onToggle, onAccept, onReject, onConfirmTier1 }) {
  const meta = TIER_META[tier]
  const pending  = items.filter(i => i.status === 'pending').length
  const accepted = items.filter(i => i.status === 'accepted').length
  const rejected = items.filter(i => i.status === 'rejected').length
  const toneBorder = {
    green: 'border-green-200', amber: 'border-amber-200', gray: 'border-gray-200',
  }[meta.tone]
  const toneBadge = {
    green: 'bg-green-100 text-green-800',
    amber: 'bg-amber-100 text-amber-800',
    gray:  'bg-gray-100  text-gray-700',
  }[meta.tone]

  return (
    <div className={`rounded-lg border ${toneBorder} mb-4`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-900">{meta.label}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded ${toneBadge}`}>
            {items.length}
          </span>
          <span className="text-xs">
            <span className="text-gray-600">{pending} pending</span>
            <span className="text-gray-400"> · </span>
            <span className={accepted > 0 ? 'text-green-700 font-semibold' : 'text-gray-500'}>
              {accepted} accepted
            </span>
            <span className="text-gray-400"> · </span>
            <span className={rejected > 0 ? 'text-red-700 font-semibold' : 'text-gray-500'}>
              {rejected} rejected
            </span>
          </span>
        </div>
        <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {items.length === 0 && (
            <div className="text-xs text-gray-400 italic py-2">No items in this tier.</div>
          )}
          {tier === 1 && pending > 0 && (
            <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded px-3 py-2">
              <div className="text-xs text-green-900">
                {pending} Tier 1 items pending — click to batch-accept all (rejected items are left alone).
              </div>
              <button
                onClick={onConfirmTier1}
                className="px-3 py-1 text-xs font-medium rounded bg-green-600 text-white hover:bg-green-700"
              >
                Confirm Tier 1 — proceed
              </button>
            </div>
          )}
          {items.map(item => (
            <CoverageItem
              key={item.qa_coverage_id}
              item={item}
              onAccept={onAccept}
              onReject={onReject}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function QACoveragePanel({ engagementId }) {
  const [items, setItems] = useState([])
  const [loading, setLoading]   = useState(true)
  const [running, setRunning]   = useState(false)
  const [error, setError]       = useState(null)
  const [runSummary, setRunSummary] = useState(null)
  const [expanded, setExpanded] = useState({ 1: false, 2: true, 3: false })

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.qaCoverage.list(engagementId)
      setItems(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [engagementId])

  useEffect(() => { fetchItems() }, [fetchItems])

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const summary = await api.qaCoverage.run(engagementId)
      setRunSummary(summary)
      // Reset expansion to defaults so Tier 2 is visible on fresh run
      setExpanded({ 1: false, 2: true, 3: false })
      await fetchItems()
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const handleUpdate = async (qaId, status) => {
    try {
      await api.qaCoverage.update(engagementId, qaId, { status })
      await fetchItems()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleConfirmTier1 = async () => {
    try {
      await api.qaCoverage.confirmTier1(engagementId)
      await fetchItems()
    } catch (err) {
      setError(err.message)
    }
  }

  const tierItems = { 1: [], 2: [], 3: [] }
  for (const item of items) {
    if (tierItems[item.tier]) tierItems[item.tier].push(item)
  }

  const totalPending = items.filter(i => i.status === 'pending').length

  return (
    <div className="p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-blue-900">QA-1 Coverage Check</h2>
          <p className="text-xs text-gray-500 mt-1">
            Items present in source documents missing or partially addressed in the v1 roadmap.
            Detection uses Opus (latest, currently 4.7) — matches the Cowork detection model.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {running ? 'Running detection…' : (items.length > 0 ? 'Re-run Coverage Check' : 'Run Coverage Check')}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {runSummary && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-900">
          Detection complete: {runSummary.items_count} items
          {' '}(T1: {runSummary.by_tier[1]}, T2: {runSummary.by_tier[2]}, T3: {runSummary.by_tier[3]}).
        </div>
      )}

      {loading && <div className="text-sm text-gray-400">Loading…</div>}

      {!loading && items.length === 0 && !running && (
        <div className="text-sm text-gray-500 italic py-6 text-center border border-dashed border-gray-300 rounded">
          No coverage items yet. Click "Run Coverage Check" to detect gaps between source documents
          and the generated v1 roadmap. (The Report Generator must have been run first.)
        </div>
      )}

      {!loading && items.length > 0 && (
        <>
          <div className="text-xs text-gray-500 mb-3">
            Total: {items.length} items · {totalPending} pending review
          </div>
          {[1, 2, 3].map(tier => (
            <TierSection
              key={tier}
              tier={tier}
              items={tierItems[tier]}
              expanded={expanded[tier]}
              onToggle={() => setExpanded(prev => ({ ...prev, [tier]: !prev[tier] }))}
              onAccept={qid => handleUpdate(qid, 'accepted')}
              onReject={qid => handleUpdate(qid, 'rejected')}
              onConfirmTier1={handleConfirmTier1}
            />
          ))}
        </>
      )}
    </div>
  )
}
