import { useState } from "react";
import Navbar from "./components/Navbar";
import CurrentBatch from "./pages/CurrentBatch";
import ApplicationHistory from "./pages/ApplicationHistory";

export default function App() {
  const [tab, setTab] = useState("batch");

  return (
    <>
      <Navbar activeTab={tab} onTabChange={setTab} />
      <div className="main">
        {tab === "batch" ? <CurrentBatch /> : <ApplicationHistory />}
      </div>
    </>
  );
}
