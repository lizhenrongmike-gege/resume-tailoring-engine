export default function Navbar({ activeTab, onTabChange }) {
  return (
    <nav className="topnav">
      <div className="topnav-logo">JobCapture</div>
      <div className="topnav-tabs">
        <button
          className={`topnav-tab${activeTab === "batch" ? " active" : ""}`}
          onClick={() => onTabChange("batch")}
        >
          Current Batch
        </button>
        <button
          className={`topnav-tab${activeTab === "history" ? " active" : ""}`}
          onClick={() => onTabChange("history")}
        >
          Application History
        </button>
      </div>
      <div className="topnav-right">
        <div className="topnav-avatar">U</div>
      </div>
    </nav>
  );
}
