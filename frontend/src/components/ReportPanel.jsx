import { useState } from 'react'
import { api } from '../api'

export default function ReportPanel({ engagementId, onRefresh }) {
  const [generating, setGenerating]     = useState(false)
  const [generateError, setGenerateError] = useState(null)
  const [openingFolder, setOpeningFolder] = useState(false)

  // Persist the last saved path across navigation using localStorage
  const storageKey = `report_path_${engagementId}`
  const [savedTo, setSavedTo] = useState(
    () => localStorage.getItem(storageKey) || null
  )

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError(null)
    try {
      const result = await api.reporting.generateReport(engagementId)
      setSavedTo(result.saved_to)
      localStorage.setItem(storageKey, result.saved_to)
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

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">OPD Transformation Roadmap Report</h2>
          <p className="text-xs text-gray-500 mt-1">
            Generates a Word document from all engagement data. Requires accepted Synthesizer output.
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
