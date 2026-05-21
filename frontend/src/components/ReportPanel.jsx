import { useState } from 'react'
import { api } from '../api'

export default function ReportPanel({ engagementId, onRefresh }) {
  const [generating, setGenerating]       = useState(false)
  const [generateError, setGenerateError] = useState(null)
  const [openingFolder, setOpeningFolder] = useState(false)

  // Persist saved path and audit report across navigation
  const pathKey  = `report_path_${engagementId}`
  const auditKey = `report_audit_${engagementId}`
  const [savedTo, setSavedTo] = useState(
    () => localStorage.getItem(pathKey) || null
  )
  const [audit, setAudit] = useState(() => {
    try {
      const raw = localStorage.getItem(auditKey)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [expanded, setExpanded] = useState(new Set())

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError(null)
    try {
      const result = await api.reporting.generateReport(engagementId)
      setSavedTo(result.saved_to)
      setAudit(result.audit || null)
      localStorage.setItem(pathKey, result.saved_to)
      if (result.audit) {
        localStorage.setItem(auditKey, JSON.stringify(result.audit))
      }
      // Auto-expand failed dimensions on a fresh run so the consultant sees evidence immediately
      const fresh = new Set()
      ;(result.audit?.results || []).forEach((r, i) => {
        if (r.status === 'fail') fresh.add(i)
      })
      setExpanded(fresh)
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleOpenFolder = async () => {
    setOpeningFolder(true)
    try {
      await api.reporting.openReportsFolder(engagementId)
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setOpeningFolder(false)
    }
  }

  const toggle = (i) => {
    const next = new Set(expanded)
    if (next.has(i)) next.delete(i)
    else next.add(i)
    setExpanded(next)
  }

  const statusIcon = (status) => {
    if (status === 'pass') return <span className="text-green-600 font-bold">✓</span>
    if (status === 'fail') return <span className="text-red-600 font-bold">✗</span>
    return <span className="text-gray-400">—</span>
  }

  const statusBg = (status) => {
    if (status === 'fail') return 'bg-red-50 border-red-200'
    if (status === 'pass') return 'bg-green-50 border-green-200'
    return 'bg-gray-50 border-gray-200'
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">OPD Transformation Roadmap Report</h2>
          <p className="text-xs text-gray-500 mt-1">
            Generates a Word document from all engagement data and runs the narrator audit.
            Requires accepted Synthesizer output.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {generating ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {generateError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {generateError}
        </div>
      )}

      {audit && (
        <div className="mb-4 border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-gray-900">Narrator Audit — Trust Report</div>
              <div className="text-xs text-gray-600">
                <span className="text-green-700 font-medium">✓ {audit.summary.pass} passed</span>
                <span className="mx-2 text-gray-300">·</span>
                <span className="text-red-700 font-medium">✗ {audit.summary.fail} flagged</span>
                <span className="mx-2 text-gray-300">·</span>
                <span className="text-gray-500">— {audit.summary.na} n/a</span>
              </div>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Mechanical checks on the narrator output. Clean dimensions are verified — focus
              review on flagged dimensions and on judgment areas (voice, client appropriateness)
              the audit cannot check.
            </p>
          </div>
          <ul className="divide-y divide-gray-100">
            {audit.results.map((r, i) => {
              const isOpen = expanded.has(i)
              const clickable = r.status === 'fail' || r.evidence
              return (
                <li key={i} className={`px-4 py-2 text-xs ${statusBg(r.status)}`}>
                  <button
                    onClick={() => clickable && toggle(i)}
                    disabled={!clickable}
                    className={`w-full flex items-center justify-between text-left ${
                      clickable ? 'cursor-pointer' : 'cursor-default'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {statusIcon(r.status)}
                      <span className="text-gray-800">{r.dimension}</span>
                    </div>
                    {clickable && (
                      <span className="text-gray-400 text-xs">{isOpen ? '▾' : '▸'}</span>
                    )}
                  </button>
                  {isOpen && r.evidence && (
                    <div className="mt-2 ml-6 p-2 bg-white border border-gray-200 rounded text-gray-700 font-mono whitespace-pre-wrap break-words">
                      {r.evidence}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {savedTo && (
        <div className="p-3 bg-green-50 border border-green-200 rounded">
          <div className="text-xs font-medium text-green-800 mb-1">Report saved</div>
          <div className="text-xs font-mono text-green-700 break-all">{savedTo}</div>
          <button
            onClick={handleOpenFolder}
            disabled={openingFolder}
            className="mt-2 px-3 py-1 border border-green-400 text-green-700 rounded text-xs font-medium hover:bg-green-100 disabled:opacity-50 transition-colors"
          >
            {openingFolder ? 'Opening...' : 'Open folder'}
          </button>
        </div>
      )}
    </div>
  )
}
