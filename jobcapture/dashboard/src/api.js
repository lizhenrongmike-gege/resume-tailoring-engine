// jobcapture/dashboard/src/api.js
const BASE = "/api";

async function request(path, options = {}) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (resp.status === 204) return null;
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail);
  }
  return resp.json();
}

export const api = {
  listJobs: (status) => request(`/jobs${status ? `?status=${status}` : ""}`),
  deleteJob: (id) => request(`/jobs/${id}`, { method: "DELETE" }),
  updateJob: (id, data) => request(`/jobs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  finishBatch: () => request("/batches/finish", { method: "POST" }),
  listHistory: (outcome) => request(`/history${outcome ? `?outcome=${outcome}` : ""}`),
  updateHistory: (id, data) => request(`/history/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  exportUrl: () => `${BASE}/export/batch_jds`,
};
