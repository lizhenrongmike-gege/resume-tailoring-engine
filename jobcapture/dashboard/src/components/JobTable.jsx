import StatusBadge from "./StatusBadge";

export default function JobTable({ jobs, columns, onDelete, onStatusChange }) {
  const showStatus = columns.includes("status");
  const showDelete = columns.includes("delete");
  const dateField = columns.includes("applied") ? "applied_at" : "created_at";
  const dateLabel = columns.includes("applied") ? "Applied" : "Saved";

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Role</th>
            <th>Location</th>
            <th>Team</th>
            <th>Link</th>
            <th>{dateLabel}</th>
            {showStatus && <th>Status</th>}
            {showDelete && <th></th>}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const record = job.job || job;
            const date = job[dateField] || record[dateField] || record.created_at;
            return (
              <tr key={job.id}>
                <td className="td-company">{record.company}</td>
                <td className="td-role">{record.title}</td>
                <td className="td-location">{record.location || "—"}</td>
                <td className="td-team">{record.team || "—"}</td>
                <td className="td-link">
                  {record.application_url ? (
                    <a href={record.application_url} target="_blank" rel="noopener noreferrer" className="apply-link">
                      Apply →
                    </a>
                  ) : "—"}
                </td>
                <td className="td-date">{formatDate(date)}</td>
                {showStatus && (
                  <td>
                    {onStatusChange ? (
                      <select
                        value={job.outcome || "applied"}
                        onChange={(e) => onStatusChange(job.id, e.target.value)}
                        className="status-select"
                      >
                        <option value="applied">Applied</option>
                        <option value="interviewing">Interviewing</option>
                        <option value="rejected">Rejected</option>
                        <option value="offered">Offered</option>
                      </select>
                    ) : (
                      <StatusBadge status={job.outcome || record.status} />
                    )}
                  </td>
                )}
                {showDelete && (
                  <td>
                    <button className="btn-row-delete" onClick={() => onDelete(record.id)}>
                      ×
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
          {jobs.length === 0 && (
            <tr>
              <td colSpan={showStatus ? 8 : 7} style={{ textAlign: "center", color: "#94a3b8", padding: "40px" }}>
                No jobs found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
