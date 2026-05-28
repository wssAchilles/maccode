import { Bot } from "lucide-react";

import { useAIReport } from "../hooks/useAIReport";
import type { FrameReport } from "../types/frameReport";

interface AIReportProps {
  report: FrameReport;
}

export function AIReport({ report }: AIReportProps) {
  const aiReport = useAIReport();

  return (
    <section className="panel page-panel ai-panel">
      <div className="panel-heading">
        <h2>AI 路况报告</h2>
        <button
          className="primary-button"
          disabled={aiReport.isLoading}
          onClick={() => void aiReport.run(report)}
          type="button"
        >
          <Bot size={18} />
          <span>{aiReport.isLoading ? "生成中" : "生成报告"}</span>
        </button>
      </div>
      <article className="report-output">
        {aiReport.report?.report_markdown ?? "## 路况解析\n\n等待统计 JSON 输入。"}
      </article>
    </section>
  );
}
