import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard        from './components/Dashboard'
import NewEngagement    from './components/NewEngagement'
import EngagementDetail from './components/EngagementDetail'
import CrossEngagement  from './components/CrossEngagement'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/"                 element={<Dashboard />} />
          <Route path="/engagements/new"  element={<NewEngagement />} />
          <Route path="/engagements/:id"  element={<EngagementDetail />} />
          <Route path="/cross-engagement" element={<CrossEngagement />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
