import React from "react";
import ReactDOM from "react-dom/client";

import "./styles.css";

function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">AI Traffic Perception</p>
          <h1>TrafficPerceptionEngine</h1>
          <p className="summary">
            本地 M5 芯片运行 CV 感知链路，云端 LLM 只负责 JSON 统计后的路况解析。
          </p>
        </div>
      </section>
      <section className="dashboard-grid">
        <div className="panel video-panel">实时视频与目标轨迹区域</div>
        <div className="panel">流量 / 速度 / FPS 指标</div>
        <div className="panel wide">趋势图与 AI 路况分析输出</div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
