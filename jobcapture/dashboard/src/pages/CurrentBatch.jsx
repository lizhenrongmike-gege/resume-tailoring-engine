import { useState, useEffect } from "react";
import { api } from "../api";
import StatCard from "../components/StatCard";
import JobTable from "../components/JobTable";
import BatchActions from "../components/BatchActions";

export default function CurrentBatch() {
  const [batchJobs, setBatchJobs] = useState([]);
  const [stats, setStats] = useState({ total: 0, interviewing: 0, thisWeek: 0 });

  async function loadData() {
    const [batch, allJobs, history] = await Promise.all([
      api.listJobs("active_batch"),
      api.listJobs(),
      api.listHistory(),
    ]);
    setBatchJobs(batch);

    const interviewing = history.filter((h) => h.outcome === "interviewing").length;
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const thisWeek = history.filter((h) => new Date(h.applied_at) > weekAgo).length;

    setStats({
      total: history.length,
      interviewing,
      thisWeek,
    });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleDelete(id) {
    await api.deleteJob(id);
    loadData();
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Current Batch</div>
          <div className="page-subtitle">
            {batchJobs.length} jobs saved{batchJobs.length > 0 ? " · Ready to export" : ""}
          </div>
        </div>
        <BatchActions jobCount={batchJobs.length} onBatchFinished={loadData} />
      </div>

      <div className="stats-row">
        <StatCard label="In Batch" value={batchJobs.length} />
        <StatCard label="Total Applied" value={stats.total} />
        <StatCard label="Interviewing" value={stats.interviewing} />
        <StatCard label="This Week" value={stats.thisWeek} />
      </div>

      <JobTable jobs={batchJobs} columns={["delete"]} onDelete={handleDelete} />
    </>
  );
}
