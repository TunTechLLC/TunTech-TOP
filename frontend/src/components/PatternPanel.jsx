import { useState, useEffect } from 'react'
import { api } from '../api'

const confidenceColors = {
  High:       'bg-red-100 text-red-800',
  Medium:     'bg-yellow-100 text-yellow-800',
  Hypothesis: 'bg-gray-100 text-gray-600',
}

export default function PatternPanel({ engagementId, onRefresh }) {
  const [patterns, setPatterns]       = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [filter, setFilter]           = useState('All')
  const [detecting, setDetecting]     = useState(false)
  const [detectError, setDetectError] = useState(null)
  const [detected, setDetected]       = useState(null)
  const [approved, setApproved]       = useState({})
  const [loading2, setLoading2]       = useState(false)

  // Skeptic recommendations
  const [hasAcceptedSkeptic, setHasAcceptedSkeptic] = useState(false)
  const [skepticRecs, setSkepticRecs]               = useState(null)
  const [loadingRecs, setLoadingRecs]               = useState(false)
  const [recsError, setRecsError]                   = useState(null)
  const [dismissedIds, setDismissedIds]             = useState(new Set())
  const [applyingId, setApplyingId]                 = useState(null)

  const fetchPatterns = () => {
    api.patterns.list(engagementId)
      .then(setPatterns)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchPatterns()
    api.agents.list(engagementId)
      .then(runs => {
        setHasAcceptedSkeptic(runs.some(r => r.agent_name === 'Skeptic' && r.accepted === 1))
      })
      .catch(() => {})
  }, [engagementId])

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
      const all = {}
      results.forEach((_, i) => { all[i] = true })
      setApproved(all)
    } catch (err) {
      setDetectError(err.message)
    } finally {
      setDetecting(false)
    }
  }

  const handleLoad = async () => {
    if (!detected) return
    const toLoad = detected.filter((_, i) => approved[i])
    if (toLoad.length === 0) return
    setLoading2(true)
    try {
      await api.patterns.load(engagementId, toLoad)
      setDetected(null)
      setDetectError(null)
      fetchPatterns()
      onRefresh?.()
    } catch (err) {
      setDetectError(err.message)
    } finally {
      setLoading2(false)
    }
  }

  const handleParseRecommendations = async () => {
    setLoadingRecs(true)
    setRecsError(null)
    try {
      const data = await api.agents.parseSkepticRecommendations(engagementId)
      setSkepticRecs(data)
      setDismissedIds(new Set())
    } catch (err) {
      setRecsError(err.message)
    } finally {
      setLoadingRecs(false)
    }
  }

  const handleApply = async (downgrade) => {
    setApplyingId(downgrade.ep_id)
    setRecsError(null)
    try {
      await api.patterns.update(engagementId, downgrade.ep_id, { confidence: downgrade.recommended_confidence })
      setDismissedIds(prev => new Set([...prev, downgrade.pattern_id]))
      fetchPatterns()
      onRefresh?.()
    } catch (err) {
      setRecsError('Failed to apply downgrade: ' + err.message)
    } finally {
      setApplyingId(null)
    }
  }

  const handleDismiss = (patternId) => {
    setDismissedIds(prev => new Set([...prev, patternId]))
  }

  const visibleDowngrades = (skepticRecs?.downgrades ?? []).filter(
    d => !dismissedIds.has(d.pattern_id) &&
         !(d.in_engagement && d.current_confidence === d.recommended_confidence)
  )

  return (
    <div className="p-6">

      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          {patterns.length} patterns detected
        </div>
        <div className="flex gap-2">
          {hasAcceptedSkeptic && !skepticRecs && (
            <button
              onClick={handleParseRecommendations}
              disabled={loadingRecs}
              className="px-3 py-1.5 border border-amber-500 text-amber-700 rounded text-xs font-medium hover:bg-amber-50 disabled:opacity-50 transition-colors"
            >
              {loadingRecs ? 'Parsing...' : 'Parse Skeptic Recommendations'}
            </button>
          )}
          <button
            onClick={handleDetect}
            disabled={detecting}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {detecting ? 'Detecting...' : 'Detect Patterns'}
          </button>
        </div>
      </div>

      {/* Detection error */}
      {detectError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {detectError}
        </div>
      )}

      {/* Recommendations error */}
      {recsError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {recsError}
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
              <span className="text-xs text-blue-600 ml-2">
                {Object.values(approved).filter(Boolean).length} selected
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { const a = {}; detected.forEach((_, i) => { a[i] = true }); setApproved(a) }}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Select all
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => setApproved({})}
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Select none
              </button>
              <button
                onClick={() => { setDetected(null); setApproved({}) }}
                className="px-3 py-1 border border-blue-300 text-blue-600 rounded text-xs hover:bg-blue-100"
              >
                Discard
              </button>
              <button
                onClick={handleLoad}
                disabled={loading2 || Object.values(approved).filter(Boolean).length === 0}
                className="px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading2 ? 'Loading...' : `Load ${Object.values(approved).filter(Boolean).length} Pattern(s)`}
              </button>
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {detected.map((p, idx) => (
              <div key={idx} className={`px-4 py-3 flex items-start gap-3 ${approved[idx] ? '' : 'opacity-50 bg-gray-50'}`}>
                <input
                  type="checkbox"
                  checked={approved[idx] || false}
                  onChange={() => setApproved(prev => ({ ...prev, [idx]: !prev[idx] }))}
                  className="mt-0.5 shrink-0"
                />
                <span className="text-xs font-mono text-gray-400 w-10 shrink-0 pt-0.5">{p.pattern_id}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {p.pattern_name && (
                      <span className="font-medium text-gray-900 text-sm">{p.pattern_name}</span>
                    )}
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

      {/* Skeptic Recommendations */}
      {skepticRecs && skepticRecs.downgrades.length === 0 && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
          Skeptic output contained no downgrade recommendations.
        </div>
      )}
      {skepticRecs && skepticRecs.downgrades.length > 0 && visibleDowngrades.length === 0 && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
          All Skeptic downgrade recommendations have been applied or dismissed.
        </div>
      )}
      {skepticRecs && visibleDowngrades.length > 0 && (
        <div className="mb-6 border border-amber-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-amber-50 flex items-center justify-between">
            <span className="text-sm font-semibold text-amber-900">
              Skeptic Recommendations ({visibleDowngrades.length})
            </span>
            <span className="text-xs text-amber-600">
              Apply updates pattern confidence · Dismiss skips for this session
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {visibleDowngrades.map(d => (
              <div key={d.pattern_id} className={`px-4 py-3 ${!d.in_engagement ? 'bg-gray-50' : ''}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className={`flex-1 ${!d.in_engagement ? 'opacity-50' : ''}`}>
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono text-gray-400">{d.pattern_id}</span>
                      {d.pattern_name && (
                        <span className="text-sm font-medium text-gray-900">{d.pattern_name}</span>
                      )}
                      <span className="flex items-center gap-1 text-xs">
                        <span className={`px-1.5 py-0.5 rounded font-medium ${confidenceColors[d.current_confidence] || 'bg-gray-100 text-gray-500'}`}>
                          {d.current_confidence || '—'}
                        </span>
                        <span className="text-gray-400">→</span>
                        <span className={`px-1.5 py-0.5 rounded font-medium ${confidenceColors[d.recommended_confidence] || 'bg-gray-100 text-gray-500'}`}>
                          {d.recommended_confidence}
                        </span>
                      </span>
                    </div>
                    {!d.in_engagement && (
                      <p className="text-xs text-gray-400 italic mb-1">Pattern not detected in this engagement</p>
                    )}
                    {d.reason && (
                      <p className="text-xs text-gray-500 leading-relaxed">{d.reason}</p>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0 mt-0.5">
                    <button
                      onClick={() => handleApply(d)}
                      disabled={!d.in_engagement || applyingId === d.ep_id}
                      className="px-2.5 py-1 bg-amber-600 text-white rounded text-xs font-medium hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {applyingId === d.ep_id ? 'Applying...' : 'Apply'}
                    </button>
                    <button
                      onClick={() => handleDismiss(d.pattern_id)}
                      className="px-2.5 py-1 border border-gray-300 text-gray-500 rounded text-xs hover:bg-gray-50 transition-colors"
                    >
                      Dismiss
                    </button>
                  </div>
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
