import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";

import { getZones, updateZones } from "./api/zones";
import { AppLayout } from "./components/layout/AppLayout";
import type { PageKey } from "./components/layout/Sidebar";
import { useStatsHistory } from "./hooks/useStatsHistory";
import { useRealtimeStats } from "./hooks/useRealtimeStats";
import { useVideoTask } from "./hooks/useVideoTask";
import { AIReport } from "./pages/AIReport";
import { CalibrationWorkbench } from "./pages/CalibrationWorkbench";
import { HistoricalAnalysis } from "./pages/HistoricalAnalysis";
import { RealtimeMonitor } from "./pages/RealtimeMonitor";
import { ZoneConfig } from "./pages/ZoneConfig";
import type { ZoneConfig as ZoneConfigType } from "./types/zoneConfig";
import "./styles.css";

function App() {
  const [activePage, setActivePage] = useState<PageKey>("realtime");
  const [zones, setZones] = useState<ZoneConfigType[]>([]);
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
          setZones([]);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (videoTask.task?.status !== "running") {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void refresh();
      void statsHistory.refresh();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [refresh, statsHistory.refresh, videoTask.task?.status]);

  async function startTask(file: File) {
    const nextTask = await videoTask.start(file);
    if (!nextTask) {
      return;
    }
    await Promise.all([refresh(), statsHistory.refresh()]);
  }

  async function startSample(source: string) {
    const nextTask = await videoTask.startSource(source);
    if (!nextTask) {
      return;
    }
    await Promise.all([refresh(), statsHistory.refresh()]);
  }

  async function stopTask() {
    const stoppedTask = await videoTask.stop();
    if (!stoppedTask) {
      return;
    }
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
          history={statsHistory.history}
          isTaskLoading={videoTask.isLoading}
          onStartSample={(source) => void startSample(source)}
          onStartTask={(file) => void startTask(file)}
          onStopTask={() => void stopTask()}
          report={report}
          task={videoTask.task}
          taskError={videoTask.error}
        />
      )}
      {activePage === "history" && (
        <HistoricalAnalysis cumulative={statsHistory.cumulative} history={statsHistory.history} />
      )}
      {activePage === "zones" && <ZoneConfig onSave={(nextZones) => void saveZones(nextZones)} zones={zones} />}
      {activePage === "calibration" && <CalibrationWorkbench />}
      {activePage === "ai" && <AIReport report={report} />}
    </AppLayout>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
