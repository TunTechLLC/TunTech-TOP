const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const handle = async (res) => {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(error.detail || error.error || res.statusText);
  }
  return res.json();
};

const json = (data) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

const patch = (data) => ({
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

export const api = {
  engagements: {
    list:           ()         => fetch(`${BASE}/engagements`).then(handle),
    get:            (id)       => fetch(`${BASE}/engagements/${id}`).then(handle),
    create:         (data)     => fetch(`${BASE}/engagements`, json(data)).then(handle),
    update:         (id, data) => fetch(`${BASE}/engagements/${id}`, patch(data)).then(handle),
    updateSettings: (id, data) => fetch(`${BASE}/engagements/${id}/settings`, patch(data)).then(handle),
  },
  signals: {
    list:           (id)       => fetch(`${BASE}/engagements/${id}/signals`).then(handle),
    summary:        (id)       => fetch(`${BASE}/engagements/${id}/signals/summary`).then(handle),
    create:         (id, data) => fetch(`${BASE}/engagements/${id}/signals`, json(data)).then(handle),
    processFiles:   (id)       => fetch(`${BASE}/engagements/${id}/signals/process-files`,
                                    { method: 'POST' }).then(handle),
    loadCandidates: (id, data) => fetch(`${BASE}/engagements/${id}/signals/load-candidates`,
                                    json(data)).then(handle),
  },
  patterns: {
    list:    (id)          => fetch(`${BASE}/engagements/${id}/patterns`).then(handle),
    detect:  (id)          => fetch(`${BASE}/engagements/${id}/patterns/detect`,
                               { method: 'POST' }).then(handle),
    load:    (id, data)    => fetch(`${BASE}/engagements/${id}/patterns/load`, json(data)).then(handle),
    update:  (id, epId, data) => fetch(`${BASE}/engagements/${id}/patterns/${epId}`,
                                   patch(data)).then(handle),
    library: ()            => fetch(`${BASE}/patterns/library`).then(handle),
  },
  agents: {
    registry: ()           => fetch(`${BASE}/engagements/agents/registry`).then(handle),
    list:     (id)         => fetch(`${BASE}/engagements/${id}/agents`).then(handle),
    run:      (id, name)   => fetch(`${BASE}/engagements/${id}/agents/${name}/run`,
                                { method: 'POST' }).then(handle),
    accept:   (id, runId)  => fetch(`${BASE}/engagements/${id}/agents/${runId}/accept`,
                                { method: 'PATCH' }).then(handle),
    reject:   (id, runId)  => fetch(`${BASE}/engagements/${id}/agents/${runId}/reject`,
                                { method: 'PATCH' }).then(handle),
  },
  findings: {
    list:   (id)            => fetch(`${BASE}/engagements/${id}/findings`).then(handle),
    create: (id, data)      => fetch(`${BASE}/engagements/${id}/findings`, json(data)).then(handle),
    update: (id, fid, data) => fetch(`${BASE}/engagements/${id}/findings/${fid}`,
                                 patch(data)).then(handle),
  },
  roadmap: {
    list:   (id)       => fetch(`${BASE}/engagements/${id}/roadmap`).then(handle),
    create: (id, data) => fetch(`${BASE}/engagements/${id}/roadmap`, json(data)).then(handle),
  },
  knowledge: {
    list:   (id)       => fetch(`${BASE}/engagements/${id}/knowledge`).then(handle),
    create: (id, data) => fetch(`${BASE}/engagements/${id}/knowledge`, json(data)).then(handle),
  },
  reporting: {
    crossEngagement: () => fetch(`${BASE}/cross-engagement`).then(handle),
  },
};