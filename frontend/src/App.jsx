import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard        from './components/Dashboard'
import NewEngagement    from './components/NewEngagement'
import EngagementDetail from './components/EngagementDetail'

function CrossEngagementPlaceholder() {
  return (
    <div className="max-w-5xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-blue-900">Cross-Engagement Report</h1>
      <p className="text-gray-500 mt-2">
        Step 9 — not yet built. Will show pattern frequency table, economic impact
        comparison, and agent run log across all engagements.
        Backend data already available at /api/cross-engagement.
      </p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/"                 element={<Dashboard />} />
          <Route path="/engagements/new"  element={<NewEngagement />} />
          <Route path="/engagements/:id"  element={<EngagementDetail />} />
          <Route path="/cross-engagement" element={<CrossEngagementPlaceholder />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
