import { api } from "../api";

export default function BatchActions({ jobCount, onBatchFinished }) {
  async function handleFinish() {
    if (jobCount === 0) return;
    try {
      await api.finishBatch();
      onBatchFinished();
    } catch (e) {
      console.error("Failed to finish batch:", e);
    }
  }

  function handleExport() {
    window.open(api.exportUrl(), "_blank");
  }

  return (
    <div style={{ display: "flex", gap: "12px" }}>
      <button className="btn-export" onClick={handleExport} disabled={jobCount === 0}>
        Export to batch_jds.xlsx
      </button>
      <button
        className="btn-export"
        onClick={handleFinish}
        disabled={jobCount === 0}
        style={{
          background: "linear-gradient(135deg, rgba(209, 250, 229, 0.6) 0%, rgba(167, 243, 208, 0.4) 100%)",
          borderColor: "rgba(110, 231, 183, 0.3)",
          color: "#065f46",
        }}
      >
        Finish Batch
      </button>
    </div>
  );
}
