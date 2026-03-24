import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import NewEngagement from './components/NewEngagement'

function Placeholder({ title }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-blue-900">{title}</h1>
      <p className="text-gray-500 mt-2">Coming soon.</p>
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
          <Route path="/engagements/:id"  element={<Placeholder title="Engagement Detail" />} />
          <Route path="/cross-engagement" element={<Placeholder title="Cross-Engagement Report" />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App