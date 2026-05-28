import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";

import { getZones, updateZones } from "./api/zones";
import { AppLayout } from "./components/layout/AppLayout";
import type { PageKey } from "./components/layout/Sidebar";
import { useStatsHistory } from "./hooks/useStatsHistory";
import { useRealtimeStats } from "./hooks/useRealtimeStats";
import { useVideoTask } from "./hooks/useVideoTask";
import { AIReport } from "./pages/AIReport";
import { HistoricalAnalysis } from "./pages/HistoricalAnalysis";
import { RealtimeMonitor } from "./pages/RealtimeMonitor";
import { ZoneConfig } from "./pages/ZoneConfig";
import type { ZoneConfig as ZoneConfigType } from "./types/zoneConfig";
import { demoZones } from "./utils/constants";
import "./styles.css";

function App() {
  const [activePage, setActivePage] = useState<PageKey>("realtime");
  const [zones, setZones] = useState<ZoneConfigType[]>(demoZones);
  const { report, refresh, status } = useRealtimeStats();
  const videoTask = useVideoTask();
  const statsHistory = useStatsHistory();

  useEffect(() => {
    let isMounted = true;
    getZones()
      .then((data) => {
        if (isMounted) {
          setZones(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setZones(demoZones);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  async function startTask(file?: File) {
    await videoTask.start(file);
    await Promise.all([refresh(), statsHistory.refresh()]);
  }

  async function stopTask() {
    await videoTask.stop();
    await statsHistory.refresh();
  }

  async function saveZones(nextZones: ZoneConfigType[]) {
    try {
      setZones(await updateZones(nextZones));
      await refresh();
    } catch {
      setZones(nextZones);
    }
  }

  return (
    <AppLayout activePage={activePage} onPageChange={setActivePage} status={status}>
      {activePage === "realtime" && (
        <RealtimeMonitor
          isTaskLoading={videoTask.isLoading}
          onStartTask={(file) => void startTask(file)}
          onStopTask={() => void stopTask()}
          report={report}
          task={videoTask.task}
        />
      )}
      {activePage === "history" && (
        <HistoricalAnalysis cumulative={statsHistory.cumulative} history={statsHistory.history} />
      )}
      {activePage === "zones" && <ZoneConfig onSave={(nextZones) => void saveZones(nextZones)} zones={zones} />}
      {activePage === "ai" && <AIReport report={report} />}
    </AppLayout>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
