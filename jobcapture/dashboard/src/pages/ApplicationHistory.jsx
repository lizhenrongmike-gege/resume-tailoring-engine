import { useState, useEffect } from "react";
import { api } from "../api";
import JobTable from "../components/JobTable";

const FILTERS = [
  { label: "All", value: null },
  { label: "Applied", value: "applied" },
  { label: "Interviewing", value: "interviewing" },
  { label: "Outcomes", value: "outcomes" },
];

export default function ApplicationHistory() {
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState(null);

  async function loadHistory() {
    let outcome = filter;
    if (filter === "outcomes") outcome = null;
    const data = await api.listHistory(outcome === "outcomes" ? null : outcome);

    if (filter === "outcomes") {
      setHistory(data.filter((h) => h.outcome === "rejected" || h.outcome === "offered"));
    } else {
      setHistory(data);
    }
  }

  useEffect(() => {
    loadHistory();
  }, [filter]);

  async function handleStatusChange(entryId, outcome) {
    await api.updateHistory(entryId, { outcome });
    loadHistory();
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Application History</div>
          <div className="page-subtitle">{history.length} applications</div>
        </div>
      </div>

      <div className="section-tabs">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            className={`section-tab${filter === f.value ? " active" : ""}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <JobTable
        jobs={history}
        columns={["applied", "status"]}
        onStatusChange={handleStatusChange}
      />
    </>
  );
}
