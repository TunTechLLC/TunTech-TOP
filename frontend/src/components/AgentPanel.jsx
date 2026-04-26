import { useState, useEffect } from 'react'
import { api } from '../api'

const SEQUENCE = [
  'Diagnostician',
  'Delivery Operations',
  'Consulting Economics',
  'Skeptic',
  'Synthesizer',
]

const PREREQUISITES = {
  'Diagnostician':        [],
  'Delivery Operations':  ['Diagnostician'],
  'Consulting Economics': ['Diagnostician'],
  'Skeptic':              ['Diagnostician', 'Delivery Operations', 'Consulting Economics'],
  'Synthesizer':          ['Diagnostician', 'Delivery Operations', 'Consulting Economics', 'Skeptic'],
}

const extractQuote = (notes) => {
  if (!notes) return null
  const m = notes.match(/Quote:\s*'([\s\S]*?)'\s*(?=[⁃—|]|\s*$)/)
  return m ? m[1].trim() : notes
}

const confBadgeClass = (conf) => {
  if (conf === 'High')       return 'bg-green-100 text-green-700'
  if (conf === 'Medium')     return 'bg-yellow-100 text-yellow-700'
  if (conf === 'Hypothesis') return 'bg-gray-100 text-gray-600'
  return 'bg-gray-100 text-gray-500'
}

export default function AgentPanel({ engagementId }) {
  const [runs, setRuns]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [running, setRunning]   = useState({})
  const [runError, setRunError] = useState({})

  // Consultant correction state — keyed by run_id
  const [correctionOpen,   setCorrectionOpen]   = useState({})
  const [corrections,      setCorrections]      = useState({})
  const [correctionSaving, setCorrectionSaving] = useState({})
  const [correctionSaved,  setCorrectionSaved]  = useState({})

  const [signalMap,         setSignalMap]         = useState({})
  const [expandedSignalKey, setExpandedSignalKey] = useState({})

  const fetchRuns = () => {
    Promise.all([
      api.agents.list(engagementId),
      api.signals.list(engagementId),
    ])
      .then(([runs, signals]) => {
        setRuns(runs)
        const map = {}
        signals.forEach(s => { map[s.signal_id] = s })
        setSignalMap(map)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchRuns() }, [engagementId])

  // Seed correction text from DB on load — only sets keys not already in state
  // so in-progress edits are not overwritten by a background refresh.
  useEffect(() => {
    setCorrections(prev => {
      const next = { ...prev }
      runs.forEach(r => {
        if (!(r.run_id in next)) {
          next[r.run_id] = r.consultant_correction || ''
        }
      })
      return next
    })
  }, [runs])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading agent runs...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const anyRunning = Object.values(running).some(Boolean)

  const acceptedAgents = new Set(
    runs.filter(r => r.accepted === 1).map(r => r.agent_name)
  )

  const latestRun = (agentName) =>
    runs.filter(r => r.agent_name === agentName).slice(-1)[0]

  const canRun = (agentName) => {
    const prereqs = PREREQUISITES[agentName] || []
    return prereqs.every(p => acceptedAgents.has(p))
  }

  const handleRun = async (agentName) => {
    setRunning(prev => ({ ...prev, [agentName]: true }))
    setRunError(prev => ({ ...prev, [agentName]: null }))
    try {
      await api.agents.run(engagementId, agentName)
      fetchRuns()
    } catch (err) {
      setRunError(prev => ({ ...prev, [agentName]: err.message }))
    } finally {
      setRunning(prev => ({ ...prev, [agentName]: false }))
    }
  }

  const handleAccept = async (runId) => {
    try {
      await api.agents.accept(engagementId, runId)
      fetchRuns()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleReject = async (runId) => {
    try {
      await api.agents.reject(engagementId, runId)
      fetchRuns()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSaveCorrection = async (runId) => {
    setCorrectionSaving(prev => ({ ...prev, [runId]: true  }))
    setCorrectionSaved (prev => ({ ...prev, [runId]: false }))
    try {
      await api.agents.updateCorrection(engagementId, runId, {
        consultant_correction: corrections[runId] || ''
      })
      setCorrectionSaved(prev => ({ ...prev, [runId]: true }))
      setTimeout(() => setCorrectionSaved(prev => ({ ...prev, [runId]: false })), 2000)
    } catch (err) {
      setError(err.message)
    } finally {
      setCorrectionSaving(prev => ({ ...prev, [runId]: false }))
    }
  }

  return (
    <div className="p-6">
      <div className="space-y-4">
        {SEQUENCE.map((agentName, idx) => {
          const run        = latestRun(agentName)
          const isRunning  = running[agentName]
          const prereqsMet = canRun(agentName)
          const err        = runError[agentName]
          const isExpanded = run && expandedId === run.run_id

          return (
            <div key={agentName}
              className="border border-gray-200 rounded-lg overflow-hidden">

              {/* Agent header */}
              <div className="flex items-center justify-between p-4 bg-gray-50">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-gray-400 bg-white border border-gray-200 px-2 py-0.5 rounded">
                    {idx + 1}
                  </span>
                  <span className="font-medium text-gray-900 text-sm">{agentName}</span>
                  {run && (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      run.accepted === 1
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {run.accepted === 1 ? 'Accepted' : 'Pending Review'}
                    </span>
                  )}
                  {!run && !isRunning && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                      {prereqsMet ? 'Ready' : 'Waiting for prerequisites'}
                    </span>
                  )}
                  {isRunning && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 animate-pulse">
                      Running...
                    </span>
                  )}
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  {run && (
                    <span className="text-xs text-gray-400 mr-2">{run.run_date}</span>
                  )}

                  {/* View/Hide full output toggle */}
                  {run && (
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : run.run_id)}
                      className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1"
                    >
                      {isExpanded ? 'Hide Output' : 'View Full Output'}
                    </button>
                  )}

                  {/* Accept button — only on pending runs */}
                  {run && run.accepted === 0 && (
                    <button
                      onClick={() => handleAccept(run.run_id)}
                      className="text-xs px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                    >
                      Accept
                    </button>
                  )}

                  {/* Reject button — only on pending runs */}
                  {run && run.accepted === 0 && (
                    <button
                      onClick={() => handleReject(run.run_id)}
                      className="text-xs px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                    >
                      Reject
                    </button>
                  )}

                  {/* Run button — whenever prerequisites are met */}
                  {prereqsMet && !isRunning && (
                    <button
                      onClick={() => handleRun(agentName)}
                      disabled={anyRunning}
                      className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {run ? 'Re-run' : 'Run'}
                    </button>
                  )}

                  {/* Running spinner */}
                  {isRunning && (
                    <span className="text-xs text-blue-600 px-3 py-1">
                      Working...
                    </span>
                  )}
                </div>
              </div>

              {/* Error message */}
              {err && (
                <div className="px-4 py-2 bg-red-50 border-t border-red-100">
                  <p className="text-xs text-red-600">{err}</p>
                </div>
              )}

              {/* Output summary — always visible if run exists */}
              {run && run.output_summary && (
                <div className="px-4 py-3 border-t border-gray-100">
                  <p className="text-xs text-gray-600 leading-relaxed">{run.output_summary}</p>
                </div>
              )}

              {/* Full output — expandable text area */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-gray-100">
                  <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs
                                  whitespace-pre-wrap text-gray-700 max-h-96 overflow-y-auto
                                  font-sans leading-relaxed">
                    {run.output_full || run.output_summary}
                  </pre>
                </div>
              )}

              {/* Referenced Signals — shown when expanded and refs exist */}
              {isExpanded && run.referenced_signal_ids?.length > 0 && (
                <div className="border-t border-gray-100">
                  <button
                    onClick={() => setExpandedSignalKey(prev => ({
                      ...prev,
                      [`${run.run_id}__section`]: !prev[`${run.run_id}__section`]
                    }))}
                    className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
                  >
                    <span className="font-medium text-gray-600">
                      Referenced Signals
                      <span className="ml-2 font-normal">({run.referenced_signal_ids.length})</span>
                    </span>
                    <span className="text-gray-400">
                      {expandedSignalKey[`${run.run_id}__section`] ? '▲' : '▼'}
                    </span>
                  </button>

                  {expandedSignalKey[`${run.run_id}__section`] && (
                    <div className="px-4 pb-4 space-y-1">
                      {run.referenced_signal_ids.map(sigId => {
                        const sig     = signalMap[sigId]
                        const cardKey = `${run.run_id}__${sigId}`
                        const isCardExpanded = !!expandedSignalKey[cardKey]

                        if (!sig) {
                          return (
                            <div key={sigId}
                              className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                              <span className="font-mono font-medium">{sigId}</span>
                              <span>— Signal not found — possible hallucinated reference</span>
                            </div>
                          )
                        }

                        const quote     = extractQuote(sig.notes)
                        const badgeCls  = confBadgeClass(sig.signal_confidence)
                        const isFlagged = (corrections[run.run_id] || '').includes(`[${sigId}]`)

                        return (
                          <div key={sigId} className="border border-gray-200 rounded overflow-hidden">

                            {/* Compact row */}
                            <button
                              onClick={() => setExpandedSignalKey(prev => ({
                                ...prev, [cardKey]: !prev[cardKey]
                              }))}
                              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-gray-50 transition-colors"
                            >
                              <span className="font-mono text-gray-500 shrink-0">{sigId}</span>
                              <span className="text-gray-800 font-medium truncate flex-1">{sig.signal_name}</span>
                              <span className={`px-1.5 py-0.5 rounded text-xs font-medium shrink-0 ${badgeCls}`}>
                                {sig.signal_confidence}
                              </span>
                              <span className="text-gray-400 shrink-0 hidden sm:block">{sig.domain}</span>
                              <span className="text-gray-400 shrink-0">{isCardExpanded ? '▲' : '▼'}</span>
                            </button>

                            {/* Expanded detail */}
                            {isCardExpanded && (
                              <div className="px-3 pb-3 pt-2 border-t border-gray-100 space-y-2 bg-gray-50">
                                {sig.source_file && (
                                  <p className="text-xs text-gray-500">
                                    <span className="font-medium text-gray-600">Source:</span> {sig.source_file}
                                  </p>
                                )}
                                {quote && (
                                  <p className="text-xs text-gray-700 italic leading-relaxed border-l-2 border-gray-300 pl-2">
                                    "{quote}"
                                  </p>
                                )}
                                <button
                                  onClick={() => {
                                    const flag = `[${sigId}] — Flagged for review: `
                                    setCorrections(prev => {
                                      const existing = (prev[run.run_id] || '').trim()
                                      return {
                                        ...prev,
                                        [run.run_id]: existing ? `${existing}\n${flag}` : flag
                                      }
                                    })
                                    setCorrectionOpen(prev => ({ ...prev, [run.run_id]: true }))
                                  }}
                                  className={`text-xs px-2 py-1 rounded border transition-colors ${
                                    isFlagged
                                      ? 'bg-amber-100 border-amber-300 text-amber-800'
                                      : 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100'
                                  }`}
                                >
                                  {isFlagged ? 'Flagged ✓' : 'Flag for review'}
                                </button>
                                <p className="text-xs text-gray-400 italic">
                                  Flagging opens the Consultant Correction below. Add your note and save before running the next agent.
                                </p>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Consultant Correction — collapsible */}
              {run && (
                <div className="border-t border-gray-100">
                  <button
                    onClick={() => setCorrectionOpen(prev => ({ ...prev, [run.run_id]: !prev[run.run_id] }))}
                    className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-medium text-gray-600">Consultant Correction</span>
                      {corrections[run.run_id] && (
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                          Active
                        </span>
                      )}
                    </span>
                    <span className="text-gray-400">{correctionOpen[run.run_id] ? '▲' : '▼'}</span>
                  </button>
                  {correctionOpen[run.run_id] && (
                    <div className="px-4 pb-4 space-y-2">
                      <p className="text-xs text-gray-400 italic">
                        Appended to this agent's output when passed to downstream agents.
                        Leave blank if no correction is needed.
                      </p>
                      <textarea
                        value={corrections[run.run_id] || ''}
                        onChange={e => setCorrections(prev => ({ ...prev, [run.run_id]: e.target.value }))}
                        rows={4}
                        className="w-full text-xs border border-gray-200 rounded p-2 font-sans
                                   resize-y focus:outline-none focus:ring-1 focus:ring-blue-300"
                        placeholder="Optional. Describe what is incorrect and provide the correct information. Example: The Director of Delivery's tenure is 18 months, not 3 years as stated above."
                      />
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleSaveCorrection(run.run_id)}
                          disabled={correctionSaving[run.run_id]}
                          className="text-xs px-3 py-1 bg-blue-600 text-white rounded
                                     hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          {correctionSaving[run.run_id] ? 'Saving...' : 'Save Correction'}
                        </button>
                        {correctionSaved[run.run_id] && (
                          <span className="text-xs text-green-600">Saved</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>
          )
        })}
      </div>
    </div>
  )
}
