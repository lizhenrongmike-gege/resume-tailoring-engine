const STATUS_CLASSES = {
  active_batch: "status-saved",
  applied: "status-applied",
  interviewing: "status-interviewing",
  rejected: "status-rejected",
  offered: "status-offered",
};

const STATUS_LABELS = {
  active_batch: "Saved",
  applied: "Applied",
  interviewing: "Interviewing",
  rejected: "Rejected",
  offered: "Offered",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge ${STATUS_CLASSES[status] || "status-saved"}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}
