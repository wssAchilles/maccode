import { Bot } from "lucide-react";
import { useState } from "react";

import { useAIReport } from "../hooks/useAIReport";
import type { FrameReport } from "../types/frameReport";

interface AIReportProps {
  report: FrameReport;
}

export function AIReport({ report }: AIReportProps) {
  const aiReport = useAIReport();
  const [locationLabel, setLocationLabel] = useState("学校门口");
  const [sceneTags, setSceneTags] = useState("school_zone,rain");

  function runReport() {
    void aiReport.run(report, {
      location_label: locationLabel,
      scene_tags: sceneTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    });
  }

  return (
    <section className="panel page-panel ai-panel">
      <div className="panel-heading">
        <h2>AI 路况报告</h2>
        <button
          className="primary-button"
          disabled={aiReport.isLoading}
          onClick={runReport}
          type="button"
        >
          <Bot size={18} />
          <span>{aiReport.isLoading ? "生成中" : "生成报告"}</span>
        </button>
      </div>
      <div className="context-form">
        <label>
          地理标签
          <input
            onChange={(event) => setLocationLabel(event.target.value)}
            value={locationLabel}
          />
        </label>
        <label>
          场景标签
          <input onChange={(event) => setSceneTags(event.target.value)} value={sceneTags} />
        </label>
      </div>
      {aiReport.report && (
        <div className="context-summary">
          <strong>Dynamic Context</strong>
          <span>{aiReport.report.dynamic_context.scene.location_label}</span>
          <span>{aiReport.report.dynamic_context.scene.scene_tags.join(", ")}</span>
        </div>
      )}
      <article className="report-output">
        {aiReport.report?.report_markdown ?? "## 路况解析\n\n等待统计 JSON 输入。"}
      </article>
    </section>
  );
}
