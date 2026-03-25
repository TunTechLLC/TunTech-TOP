import { useState, useEffect } from 'react'
import { api } from '../api'

const confidenceColors = {
  High:       'bg-red-100 text-red-800',
  Medium:     'bg-yellow-100 text-yellow-800',
  Hypothesis: 'bg-gray-100 text-gray-600',
}

export default function PatternPanel({ engagementId }) {
  const [patterns, setPatterns]       = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [filter, setFilter]           = useState('All')
  const [detecting, setDetecting]     = useState(false)
  const [detectError, setDetectError] = useState(null)
  const [detected, setDetected]       = useState(null)
  const [loading2, setLoading2]       = useState(false)

  const fetchPatterns = () => {
    api.patterns.list(engagementId)
      .then(setPatterns)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchPatterns() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading patterns...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const counts = {
    All:        patterns.length,
    High:       patterns.filter(p => p.confidence === 'High').length,
    Medium:     patterns.filter(p => p.confidence === 'Medium').length,
    Hypothesis: patterns.filter(p => p.confidence === 'Hypothesis').length,
  }

  const filtered = filter === 'All'
    ? patterns
    : patterns.filter(p => p.confidence === filter)

  const handleDetect = async () => {
    setDetecting(true)
    setDetectError(null)
    setDetected(null)
    try {
      const results = await api.patterns.detect(engagementId)
      setDetected(results)
    } catch (err) {
      setDetectError(err.message)
    } finally {
      setDetecting(false)
    }
  }

  const handleLoad = async () => {
    if (!detected) return
    setLoading2(true)
    try {
      await api.patterns.load(engagementId, detected)
      setDetected(null)
      setDetectError(null)
      fetchPatterns()
    } catch (err) {
      setDetectError(err.message)
    } finally {
      setLoading2(false)
    }
  }

  return (
    <div className="p-6">

      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          {patterns.length} patterns detected
        </div>
        <button
          onClick={handleDetect}
          disabled={detecting}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {detecting ? 'Detecting...' : 'Detect Patterns'}
        </button>
      </div>

      {/* Detection error */}
      {detectError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {detectError}
        </div>
      )}

      {/* Detection results — shown before loading */}
      {detected && (
        <div className="mb-6 border border-blue-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-blue-50">
            <div>
              <span className="text-sm font-semibold text-blue-900">
                {detected.length} patterns detected by Claude
              </span>
              <span className="text-xs text-blue-600 ml-2">Review before loading</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setDetected(null)}
                className="px-3 py-1 border border-blue-300 text-blue-600 rounded text-xs hover:bg-blue-100"
              >
                Discard
              </button>
              <button
                onClick={handleLoad}
                disabled={loading2}
                className="px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading2 ? 'Loading...' : 'Load Patterns'}
              </button>
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {detected.map((p, idx) => (
              <div key={idx} className="px-4 py-3 flex items-start gap-3">
                <span className="text-xs font-mono text-gray-400 w-10 shrink-0 pt-0.5">{p.pattern_id}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColors[p.confidence] || 'bg-gray-100'}`}>
                      {p.confidence}
                    </span>
                  </div>
                  {p.notes && (
                    <p className="text-xs text-gray-600 leading-relaxed">{p.notes}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {Object.entries(counts).map(([level, count]) => (
          <button
            key={level}
            onClick={() => setFilter(level)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === level
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-400'
            }`}
          >
            {level} · {count}
          </button>
        ))}
      </div>

      {/* Pattern list */}
      <div className="space-y-3">
        {filtered.map(pattern => (
          <div key={pattern.ep_id}
            className="border border-gray-100 rounded-lg p-4 hover:border-gray-300 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-gray-400">{pattern.pattern_id}</span>
                  <span className="font-medium text-gray-900 text-sm">{pattern.pattern_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColors[pattern.confidence] || 'bg-gray-100'}`}>
                    {pattern.confidence}
                  </span>
                  {pattern.accepted === 1 && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                      Accepted
                    </span>
                  )}
                </div>
                {pattern.notes && (
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{pattern.notes}</p>
                )}
                {pattern.economic_impact_est && (
                  <p className="text-xs text-blue-600 mt-1 font-medium">{pattern.economic_impact_est}</p>
                )}
              </div>
              <div className="text-xs text-gray-400 whitespace-nowrap text-right">
                <div>{pattern.domain}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}