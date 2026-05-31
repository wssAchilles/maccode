import { Bot } from "lucide-react";
import { useState } from "react";

import { LLMReportViewer } from "../components/ai/LLMReportViewer";
import { useAIReport } from "../hooks/useAIReport";
import type { FrameReport } from "../types/frameReport";

interface AIReportProps {
  report: FrameReport | null;
}

export function AIReport({ report }: AIReportProps) {
  const aiReport = useAIReport();
  const [locationLabel, setLocationLabel] = useState("");
  const [sceneTags, setSceneTags] = useState("");

  function runReport() {
    if (!report) {
      return;
    }
    void aiReport.run(report, {
      location_label: locationLabel || undefined,
      scene_tags: sceneTags
        .split(/[,，\s]+/)
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
          disabled={!report || aiReport.isLoading}
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
      {aiReport.error && <p className="task-error">AI 报告生成失败：{aiReport.error}</p>}
      <LLMReportViewer
        className="report-output"
        emptyText="等待真实分析完成。报告将使用后端返回的 FrameReport JSON。"
        isLoading={aiReport.isLoading}
        isTyping={aiReport.isTyping}
        loadingText="正在读取当前 FrameReport 与动态上下文..."
        markdown={aiReport.displayedMarkdown}
      />
    </section>
  );
}
