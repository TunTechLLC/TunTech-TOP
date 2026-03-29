import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function CrossEngagement() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    api.reporting.crossEngagement()
      .then(d => setData(d))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>
  if (error)   return <div className="p-8 text-red-600 text-sm">Error: {error}</div>

  const { pattern_frequency, economic_impact, agent_run_log } = data

  const toggleExpand = (key) =>
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <div className="max-w-6xl mx-auto p-8">

      {/* Page header */}
      <div className="mb-8">
        <Link to="/" className="text-xs text-blue-600 hover:text-blue-800">← Dashboard</Link>
        <h1 className="text-2xl font-bold text-blue-900 mt-2">Cross-Engagement Report</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pattern frequency, economic impact, and agent run log across all engagements.
        </p>
      </div>

      {/* Section 1: Pattern Frequency */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-gray-900 mb-1">Pattern Frequency</h2>
        <p className="text-xs text-gray-400 mb-3">
          Highlighted rows detected in 2 or more engagements.
        </p>
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Pattern</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Domain</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Detected</th>
                <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Accepted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pattern_frequency.map(p => (
                <tr
                  key={p.pattern_id}
                  className={p.times_detected >= 2 ? 'bg-yellow-50' : 'bg-white'}
                >
                  <td className="px-4 py-2">
                    <span className="font-mono text-xs text-gray-400 mr-2">{p.pattern_id}</span>
                    <span className="text-sm text-gray-800">{p.pattern_name}</span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500">{p.domain}</td>
                  <td className="px-4 py-2 text-center">
                    <span className={
                      'text-sm font-semibold ' +
                      (p.times_detected >= 2 ? 'text-yellow-700' : 'text-gray-600')
                    }>
                      {p.times_detected}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center text-sm text-gray-600">
                    {p.times_accepted}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 2: Economic Impact by Engagement */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-gray-900 mb-3">
          Economic Impact by Engagement
        </h2>
        <div className="space-y-4">
          {economic_impact.map(row => (
            <div key={row.engagement_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <Link
                    to={`/engagements/${row.engagement_id}`}
                    className="font-semibold text-blue-700 hover:text-blue-900 text-sm"
                  >
                    {row.firm_name}
                  </Link>
                  <span className="text-xs text-gray-400 ml-2">{row.engagement_name}</span>
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded shrink-0 ml-4">
                  {row.patterns_accepted} patterns accepted
                </span>
              </div>
              {row.impact_summary ? (
                <div>
                  <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {expanded[row.engagement_id]
                      ? row.impact_summary
                      : row.impact_summary.slice(0, 300) +
                        (row.impact_summary.length > 300 ? '…' : '')}
                  </p>
                  {row.impact_summary.length > 300 && (
                    <button
                      onClick={() => toggleExpand(row.engagement_id)}
                      className="text-xs text-blue-600 hover:text-blue-800 mt-1"
                    >
                      {expanded[row.engagement_id] ? 'Show less ↑' : 'Show more ↓'}
                    </button>
                  )}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic">No impact data yet.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: Agent Run Log */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-gray-900 mb-3">Agent Run Log</h2>
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Firm</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Agent</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {agent_run_log.map(r => (
                <tr key={r.run_id} className="bg-white hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs text-gray-700 whitespace-nowrap">{r.firm_name}</td>
                  <td className="px-4 py-2 text-xs font-medium text-gray-800 whitespace-nowrap">{r.agent_name}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">{r.run_date}</td>
                  <td className="px-4 py-2 whitespace-nowrap">
                    {r.accepted
                      ? <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Accepted</span>
                      : <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs font-medium">Pending</span>
                    }
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500 max-w-sm truncate">{r.output_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

    </div>
  )
}
