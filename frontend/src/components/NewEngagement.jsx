import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const SERVICE_MODELS = [
  'IT Consulting — Project Delivery',
  'IT Consulting — Staff Augmentation',
  'IT Consulting — Hybrid',
  'Management Consulting',
  'Technology Services',
]

function Field({ label, name, value, onChange, required, multiline, placeholder }) {
  const base = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {multiline ? (
        <textarea
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          rows={3}
          className={base}
        />
      ) : (
        <input
          type="text"
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={base}
        />
      )}
    </div>
  )
}

export default function NewEngagement() {
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState(null)

  const [form, setForm] = useState({
    firm_name:         '',
    firm_size:         '',
    service_model:     SERVICE_MODELS[0],
    stated_problem:    '',
    client_hypothesis: '',
    previously_tried:  '',
    client_notes:      '',
    consultant_notes:  '',
  })

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async () => {
    if (!form.firm_name || !form.firm_size || !form.stated_problem ||
        !form.client_hypothesis || !form.previously_tried) {
      setError('Please fill in all required fields.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const engagement = await api.engagements.create({
        ...form,
        firm_size: parseInt(form.firm_size, 10),
      })
      navigate(`/engagements/${engagement.engagement_id}`)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-8">

      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/')}
          className="text-gray-400 hover:text-gray-600 text-sm"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-blue-900">New Engagement</h1>
      </div>

      {error && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-5">

        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Client Information
        </h2>

        <Field label="Firm name" name="firm_name" value={form.firm_name}
          onChange={handleChange} required placeholder="e.g. Acme Consulting Group" />

        <div className="grid grid-cols-2 gap-4">
          <Field label="Total headcount" name="firm_size" value={form.firm_size}
            onChange={handleChange} required placeholder="e.g. 65" />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Service model <span className="text-red-500">*</span>
            </label>
            <select
              name="service_model"
              value={form.service_model}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              {SERVICE_MODELS.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>

        <Field label="Client notes" name="client_notes" value={form.client_notes}
          onChange={handleChange} multiline
          placeholder="Key contacts, context, relationship history" />

        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide pt-2">
          Engagement Context
        </h2>

        <Field label="Stated problem" name="stated_problem" value={form.stated_problem}
          onChange={handleChange} required multiline
          placeholder="What does the client say is wrong?" />

        <Field label="Client hypothesis" name="client_hypothesis" value={form.client_hypothesis}
          onChange={handleChange} required multiline
          placeholder="What does the client think is causing the problem?" />

        <Field label="Previously tried" name="previously_tried" value={form.previously_tried}
          onChange={handleChange} required multiline
          placeholder="What has the client already attempted to fix this?" />

        <Field label="Consultant notes" name="consultant_notes" value={form.consultant_notes}
          onChange={handleChange} multiline
          placeholder="Your initial observations, concerns, hypotheses" />

      </div>

      <div className="flex justify-end gap-3 mt-6">
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          {saving ? 'Creating...' : 'Create Engagement'}
        </button>
      </div>

    </div>
  )
}