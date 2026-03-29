const SECTIONS = [
  { num: 1, title: 'Executive Summary',            note: 'Written by consultant after download' },
  { num: 2, title: 'Engagement Overview',          note: 'Auto-generated from engagement record' },
  { num: 3, title: 'Operational Maturity Overview',note: 'Auto-generated from signal domains' },
  { num: 4, title: 'Domain Analysis',              note: 'Auto-generated from findings by domain' },
  { num: 5, title: 'Root Cause Analysis',          note: 'Auto-generated from finding root causes' },
  { num: 6, title: 'Economic Impact Analysis',     note: 'Auto-generated from finding economic impact' },
  { num: 7, title: 'Improvement Opportunities',    note: 'Auto-generated from recommendations' },
  { num: 8, title: 'Transformation Roadmap',       note: 'Auto-generated from roadmap items by phase' },
]

export default function ReportPanel({ engagementId }) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">OPD Transformation Roadmap Report</h2>
          <p className="text-xs text-gray-500 mt-1">
            Word document generated from engagement data. Section 1 requires manual completion.
          </p>
        </div>

        {/* Download Report — enabled in Step 10 when report_generator.py is built */}
        <button
          disabled
          title="Report generation not yet implemented — Step 10"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium opacity-40 cursor-not-allowed"
        >
          Download Report
        </button>
      </div>

      <div className="space-y-2">
        {SECTIONS.map(s => (
          <div key={s.num}
            className="flex items-start gap-4 p-3 border border-gray-100 rounded-lg">
            <span className="text-xs font-mono text-gray-400 w-6 shrink-0 pt-0.5">{s.num}</span>
            <div>
              <p className="text-sm font-medium text-gray-900">{s.title}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.note}</p>
            </div>
            {s.num === 1 ? (
              <span className="ml-auto text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">Manual</span>
            ) : (
              <span className="ml-auto text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Auto</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
