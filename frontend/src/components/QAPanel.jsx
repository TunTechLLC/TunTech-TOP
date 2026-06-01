import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import QACoveragePanel from './QACoveragePanel'
import QACoherencePanel from './QACoherencePanel'
import QAEditorialPanel from './QAEditorialPanel'

// QA-5 — the integrated QA tab. Gates on a v1 roadmap existing, wraps the three
// detection panels (Coverage / Coherence / Editorial) as collapsible sections
// with live counts, then exposes the QA-4 Revision as a verify-after step: the
// edits are applied to produce v2, and this tab shows what changed (grouped by
// outcome) so the consultant can confirm with minimal effort. v1 is preserved;
// both documents are downloadable for the authoritative Word side-by-side.

const TONE_BORDER = { green: 'border-green-200', amber: 'border-amber-200', gray: 'border-gray-200', red: 'border-red-200' }

// ── Section wrapper (collapsible) ────────────────────────────────────────────
function Section({ label, hint, counts, open, onToggle, children }) {
  const c = counts || { total: 0, accepted: 0, rejected: 0, pending: 0 }
  return (
    <div className="rounded-lg border border-gray-200 mb-4">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-sm font-semibold text-gray-900">{label}</span>
          {counts == null ? (
            <span className="text-xs text-gray-400">not run</span>
          ) : (
            <span className="text-xs">
              <span className="text-gray-700 font-medium">{c.total} items</span>
              <span className="text-gray-400"> · </span>
              <span className="text-gray-600">{c.pending} pending</span>
              <span className="text-gray-400"> · </span>
              <span className={c.accepted > 0 ? 'text-green-700 font-semibold' : 'text-gray-500'}>{c.accepted} accepted</span>
              <span className="text-gray-400"> · </span>
              <span className={c.rejected > 0 ? 'text-red-700 font-semibold' : 'text-gray-500'}>{c.rejected} rejected</span>
            </span>
          )}
        </div>
        <span className="text-gray-400 text-sm shrink-0 ml-3">{open ? '▲' : '▼'}</span>
      </button>
      {hint && open && (
        <div className="px-4 -mt-1 pb-1 text-[11px] text-gray-400">{hint}</div>
      )}
      {/* Kept mounted while collapsed so each panel fetches and reports its
          counts to the header — only hidden visually. */}
      <div className={open ? 'border-t border-gray-100' : 'hidden'}>
        {children}
      </div>
    </div>
  )
}

// ── Revision edit-list (verify-after comparison) ─────────────────────────────
const OUTCOME_META = {
  applied:            { label: 'Applied',          tone: 'green', desc: 'Found and replaced cleanly in v2 — skim to confirm.' },
  flagged_unresolved: { label: 'Needs your hand',  tone: 'amber', desc: 'Location found but not safely auto-applied — apply in Word.' },
  manual:             { label: 'Manual',           tone: 'amber', desc: 'Structural change (e.g. a new table) — apply by hand in Word.' },
  unaddressed:        { label: 'Verify coverage',  tone: 'red',   desc: 'You accepted this but no edit was produced — confirm it is covered elsewhere, or catch a genuine drop.' },
  manual_done:        { label: 'Handled',          tone: 'gray',  desc: 'You marked this done.' },
}
const OUTCOME_ORDER = ['applied', 'flagged_unresolved', 'manual', 'unaddressed', 'manual_done']

const SOURCE_CHIP = {
  coverage:  'bg-blue-50   text-blue-900   border-blue-200',
  coherence: 'bg-orange-50 text-orange-900 border-orange-200',
  editorial: 'bg-violet-50 text-violet-900 border-violet-200',
}

function MatchBadge({ method }) {
  if (!method) return null
  const exact = method === 'exact'
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${exact ? 'bg-gray-100 text-gray-500' : 'bg-amber-100 text-amber-800'}`}>
      {method}
    </span>
  )
}

function EditCard({ edit, onMarkHandled }) {
  const handleable = edit.outcome === 'flagged_unresolved' || edit.outcome === 'manual' || edit.outcome === 'unaddressed'
  const srcChip = SOURCE_CHIP[edit.qa_source] || 'bg-gray-50 text-gray-700 border-gray-200'
  const done = edit.outcome === 'manual_done'
  return (
    <div className={`rounded border p-3 ${done ? 'border-gray-200 bg-gray-50 opacity-70' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {edit.source_item_id && (
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${srcChip}`}>
                {edit.source_item_id}
              </span>
            )}
            <span className="text-[10px] text-gray-400">{edit.qa_source}</span>
            <MatchBadge method={edit.match_method} />
          </div>

          {edit.outcome === 'unaddressed' ? (
            <p className="text-sm mt-2 text-gray-700">
              No edit was produced for this accepted item.
            </p>
          ) : (
            <div className="mt-2 space-y-1">
              {edit.anchor && (
                <div className="text-xs">
                  <span className="text-red-700 font-mono">−</span>{' '}
                  <span className="text-gray-500 line-through">{edit.anchor}</span>
                </div>
              )}
              {edit.new_text && (
                <div className="text-xs">
                  <span className="text-green-700 font-mono">+</span>{' '}
                  <span className="text-gray-900">{edit.new_text}</span>
                </div>
              )}
            </div>
          )}

          {edit.reason && (
            <div className="mt-2 text-xs text-gray-500 italic">{edit.reason}</div>
          )}
          <div className="text-[10px] text-gray-400 font-mono mt-1">{edit.qa_revision_id}</div>
        </div>
        {handleable && (
          <button
            onClick={() => onMarkHandled(edit.qa_revision_id)}
            className="shrink-0 px-3 py-1 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Mark handled
          </button>
        )}
        {done && <span className="shrink-0 text-xs text-gray-500">✓ handled</span>}
      </div>
    </div>
  )
}

function OutcomeGroup({ outcome, edits, onMarkHandled }) {
  const meta = OUTCOME_META[outcome]
  if (!meta || edits.length === 0) return null
  // Within "applied", float non-exact matches to the top — those deserve a closer look.
  const ordered = outcome === 'applied'
    ? [...edits].sort((a, b) => (a.match_method === 'exact' ? 1 : 0) - (b.match_method === 'exact' ? 1 : 0))
    : edits
  return (
    <div className={`rounded-lg border ${TONE_BORDER[meta.tone]} mb-4`}>
      <div className="px-4 py-2.5 border-b border-gray-100">
        <div className="text-sm font-semibold text-gray-900">{meta.label} <span className="text-gray-400 font-normal">· {edits.length}</span></div>
        <div className="text-[11px] text-gray-500 mt-0.5">{meta.desc}</div>
      </div>
      <div className="p-3 space-y-2">
        {ordered.map(e => (
          <EditCard key={e.qa_revision_id} edit={e} onMarkHandled={onMarkHandled} />
        ))}
      </div>
    </div>
  )
}

// ── Main panel ───────────────────────────────────────────────────────────────
export default function QAPanel({ engagementId }) {
  const [status, setStatus]   = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError]     = useState(null)

  const [counts, setCounts] = useState({ coverage: null, coherence: null, editorial: null })
  const [open, setOpen]     = useState({ coverage: false, coherence: false, editorial: false })

  const [edits, setEdits]   = useState([])
  const [revisionRunning, setRevisionRunning] = useState(false)
  const [revisionError, setRevisionError]     = useState(null)
  const [revisionSummary, setRevisionSummary] = useState(null)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await api.qaStatus(engagementId)
      setStatus(s)
      setStatusError(null)
    } catch (err) {
      setStatusError(err.message)
    } finally {
      setStatusLoading(false)
    }
  }, [engagementId])

  const fetchEdits = useCallback(async () => {
    try {
      const e = await api.qaRevision.list(engagementId)
      setEdits(e)
    } catch (err) {
      // A missing revision is not an error — it just means it hasn't run yet.
      setEdits([])
    }
  }, [engagementId])

  useEffect(() => { fetchStatus(); fetchEdits() }, [fetchStatus, fetchEdits])

  const totalAccepted =
    (counts.coverage?.accepted  || 0) +
    (counts.coherence?.accepted || 0) +
    (counts.editorial?.accepted || 0)

  const handleRunRevision = async () => {
    setRevisionRunning(true)
    setRevisionError(null)
    try {
      const summary = await api.qaRevision.run(engagementId)
      setRevisionSummary(summary)
      await fetchEdits()
      await fetchStatus()  // v2 now exists — enables the v2 download
    } catch (err) {
      setRevisionError(err.message)
    } finally {
      setRevisionRunning(false)
    }
  }

  const handleMarkHandled = async (qrId) => {
    try {
      await api.qaRevision.updateOutcome(engagementId, qrId, { outcome: 'manual_done' })
      await fetchEdits()
    } catch (err) {
      setRevisionError(err.message)
    }
  }

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const handleDownload = async (which) => {
    setRevisionError(null)
    try {
      const blob = which === 'v1'
        ? await api.qaRevision.downloadV1(engagementId)
        : await api.qaRevision.downloadV2(engagementId)
      downloadBlob(blob, `OPD_Transformation_Roadmap_${engagementId}_${which}.docx`)
    } catch (err) {
      setRevisionError(err.message)
    }
  }

  if (statusLoading) {
    return <div className="p-6 text-sm text-gray-400">Loading QA status…</div>
  }

  if (statusError) {
    return (
      <div className="p-6">
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{statusError}</div>
      </div>
    )
  }

  // ── Gate: no v1 → the QA stage cannot run ──────────────────────────────────
  if (!status?.v1_exists) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-bold text-blue-900 mb-2">Quality Assurance</h2>
        <div className="p-6 text-center border border-dashed border-amber-300 bg-amber-50 rounded">
          <p className="text-sm text-amber-900 font-medium">Generate the roadmap first.</p>
          <p className="text-xs text-amber-700 mt-1">
            The QA stage reviews the v1 roadmap document. Open the <span className="font-semibold">Report</span> tab
            and run <span className="font-semibold">Generate Report</span> to produce it, then return here.
          </p>
        </div>
      </div>
    )
  }

  // ── Revision edit grouping ──────────────────────────────────────────────────
  const grouped = OUTCOME_ORDER.reduce((acc, o) => { acc[o] = []; return acc }, {})
  for (const e of edits) {
    if (grouped[e.outcome]) grouped[e.outcome].push(e)
  }
  const appliedExact = grouped.applied.filter(e => e.match_method === 'exact').length
  const appliedGlance = grouped.applied.length - appliedExact
  const hasRevision = edits.length > 0

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-blue-900">Quality Assurance</h2>
        <p className="text-xs text-gray-500 mt-1">
          Three detection passes over the v1 roadmap, then a revision that applies what you accept.
          The goal is confidence and risk reduction — a delivery-ready v2 without a paranoid
          blank-slate re-read. Run the passes in order, review each, then run the revision below.
        </p>
      </div>

      {/* Detection sections */}
      <Section
        label="Coverage" counts={counts.coverage}
        hint="Source items missing or only partially addressed in the v1 roadmap."
        open={open.coverage} onToggle={() => setOpen(p => ({ ...p, coverage: !p.coverage }))}
      >
        <QACoveragePanel engagementId={engagementId} onCountsChange={c => setCounts(p => ({ ...p, coverage: c }))} />
      </Section>

      <Section
        label="Coherence" counts={counts.coherence}
        hint="Internal contradictions, math errors, and priority mismatches within the roadmap."
        open={open.coherence} onToggle={() => setOpen(p => ({ ...p, coherence: !p.coherence }))}
      >
        <QACoherencePanel engagementId={engagementId} onCountsChange={c => setCounts(p => ({ ...p, coherence: c }))} />
      </Section>

      <Section
        label="Editorial" counts={counts.editorial}
        hint="Leaked signal codes, undefined acronyms, terminology drift, and voice intrusions."
        open={open.editorial} onToggle={() => setOpen(p => ({ ...p, editorial: !p.editorial }))}
      >
        <QAEditorialPanel engagementId={engagementId} onCountsChange={c => setCounts(p => ({ ...p, editorial: c }))} />
      </Section>

      {/* Revision (verify-after) */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="text-base font-bold text-blue-900">Final Revision</h3>
            <p className="text-xs text-gray-500 mt-1">
              Applies your accepted items to v1 in place and writes v2. v1 is never modified.
              Review the changes below; fix any outliers in Word.
            </p>
          </div>
          <button
            onClick={handleRunRevision}
            disabled={revisionRunning || totalAccepted === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 shrink-0"
            title={totalAccepted === 0 ? 'Accept at least one QA item first' : ''}
          >
            {revisionRunning ? 'Revising…' : (hasRevision ? 'Re-run Final Revision' : 'Run Final Revision')}
          </button>
        </div>

        {totalAccepted === 0 && !hasRevision && (
          <div className="text-xs text-gray-500 italic py-3 text-center border border-dashed border-gray-300 rounded">
            Accept at least one Coverage, Coherence, or Editorial item above to enable the revision.
          </div>
        )}

        {revisionError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{revisionError}</div>
        )}

        {hasRevision && (
          <>
            {/* Orientation line — where your attention goes */}
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-900">
              <span className="font-semibold">{grouped.applied.length} applied</span>
              {grouped.applied.length > 0 && (
                <span className="text-blue-700"> ({appliedExact} exact{appliedGlance > 0 ? ` · ${appliedGlance} to glance` : ''})</span>
              )}
              {grouped.flagged_unresolved.length > 0 && <span> · <span className="font-semibold">{grouped.flagged_unresolved.length}</span> need your hand</span>}
              {grouped.manual.length > 0 && <span> · <span className="font-semibold">{grouped.manual.length}</span> manual</span>}
              {grouped.unaddressed.length > 0 && <span> · <span className="font-semibold">{grouped.unaddressed.length}</span> to verify coverage</span>}
              {grouped.manual_done.length > 0 && <span> · {grouped.manual_done.length} handled</span>}
            </div>

            {/* Document access — the authoritative side-by-side in Word */}
            <div className="mb-4 flex items-center gap-2">
              <button
                onClick={() => handleDownload('v1')}
                className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Download v1 (original)
              </button>
              <button
                onClick={() => handleDownload('v2')}
                disabled={!status?.v2_exists}
                className="px-3 py-1.5 text-xs rounded border border-blue-300 text-blue-700 hover:bg-blue-50 disabled:opacity-50"
              >
                Download v2 (revised)
              </button>
              <span className="text-[11px] text-gray-400">Optional — open both in Word for the full side-by-side.</span>
            </div>

            {OUTCOME_ORDER.map(o => (
              <OutcomeGroup key={o} outcome={o} edits={grouped[o]} onMarkHandled={handleMarkHandled} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
