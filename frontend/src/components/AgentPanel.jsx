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

export default function AgentPanel({ engagementId }) {
  const [runs, setRuns]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expanded, setExpanded] = useState({})
  const [running, setRunning]   = useState({})
  const [runError, setRunError] = useState({})

  const fetchRuns = () => {
    api.agents.list(engagementId)
      .then(setRuns)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchRuns() }, [engagementId])

  if (loading) return <div className="p-6 text-gray-500 text-sm">Loading agent runs...</div>
  if (error)   return <div className="p-6 text-red-600 text-sm">Error: {error}</div>

  const toggleExpanded = (runId) => {
    setExpanded(prev => ({ ...prev, [runId]: !prev[runId] }))
  }

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

  return (
    <div className="p-6">
      <div className="space-y-4">
        {SEQUENCE.map((agentName, idx) => {
          const run        = latestRun(agentName)
          const isRunning  = running[agentName]
          const prereqsMet = canRun(agentName)
          const err        = runError[agentName]

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

                  {/* View output toggle */}
                  {run && (
                    <button
                      onClick={() => toggleExpanded(run.run_id)}
                      className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1"
                    >
                      {expanded[run.run_id] ? 'Hide' : 'View'}
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

                  {/* Run button — when no pending run and prereqs met */}
                  {(!run || run.accepted === 1) && prereqsMet && !isRunning && (
                    <button
                      onClick={() => handleRun(agentName)}
                      className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
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

              {/* Output summary always visible if run exists */}
              {run && run.output_summary && (
                <div className="px-4 py-3 border-t border-gray-100">
                  <p className="text-xs text-gray-600 leading-relaxed">{run.output_summary}</p>
                </div>
              )}

              {/* Full output expandable */}
              {run && expanded[run.run_id] && run.output_doc_link && (
                <div className="px-4 py-3 border-t border-gray-100 bg-blue-50">
                  <p className="text-xs text-gray-500 font-mono break-all">{run.output_doc_link}</p>
                </div>
              )}

            </div>
          )
        })}
      </div>
    </div>
  )
}