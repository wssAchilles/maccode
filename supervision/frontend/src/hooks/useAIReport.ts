import { useEffect, useState } from "react";

import { generateAIReport } from "../api/aiReport";
import type { AIReportResult } from "../types/aiReport";
import type { FrameReport } from "../types/frameReport";

export function useAIReport() {
  const [report, setReport] = useState<AIReportResult | null>(null);
  const [displayedMarkdown, setDisplayedMarkdown] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const markdown = report?.report_markdown ?? "";
    setDisplayedMarkdown("");
    if (!markdown) {
      setIsTyping(false);
      return undefined;
    }
    setIsTyping(true);
    let index = 0;
    const timer = window.setInterval(() => {
      index = Math.min(index + 8, markdown.length);
      setDisplayedMarkdown(markdown.slice(0, index));
      if (index >= markdown.length) {
        window.clearInterval(timer);
        setIsTyping(false);
      }
    }, 18);
    return () => window.clearInterval(timer);
  }, [report]);

  async function run(
    stats: FrameReport,
    context: { location_label?: string; scene_tags?: string[] } = {}
  ) {
    setIsLoading(true);
    setError(null);
    setReport(null);
    setDisplayedMarkdown("");
    try {
      setReport(await generateAIReport(stats, context));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "AI 报告生成失败");
    } finally {
      setIsLoading(false);
    }
  }

  return { report, displayedMarkdown, isTyping, isLoading, error, run };
}
