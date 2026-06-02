import { animate, stagger } from "animejs";
import { useRef } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { useAnimeScope } from "../../hooks/useAnimeScope";

interface LLMReportViewerProps {
  className: string;
  emptyText: string;
  isLoading: boolean;
  isTyping: boolean;
  loadingText: string;
  markdown: string;
}

const markdownComponents: Components = {
  h1({ node: _node, children, ...props }) {
    return <h2 {...props}>{children}</h2>;
  },
  strong({ node: _node, children, ...props }) {
    return (
      <strong className="report-strong" {...props}>
        {children}
      </strong>
    );
  },
  table({ node: _node, children, ...props }) {
    return (
      <div className="report-table-wrap">
        <table {...props}>{children}</table>
      </div>
    );
  },
  code({ node: _node, children, className, ...props }) {
    return (
      <code className={className ? `report-code ${className}` : "report-code"} {...props}>
        {children}
      </code>
    );
  }
};

export function LLMReportViewer({
  className,
  emptyText,
  isLoading,
  isTyping,
  loadingText,
  markdown
}: LLMReportViewerProps) {
  const reportRef = useRef<HTMLElement | null>(null);
  const hasMarkdown = Boolean(markdown);
  useAnimeScope(
    reportRef,
    () => {
      const reportRoot = reportRef.current;
      if (!reportRoot || !hasMarkdown) {
        return;
      }
      const enteringBlocks = Array.from(
        reportRoot.querySelectorAll<HTMLElement>(".report-markdown > *")
      ).slice(-12);
      if (enteringBlocks.length === 0) {
        return;
      }
      animate(enteringBlocks, {
        opacity: [0, 1],
        y: [6, 0],
        delay: stagger(22),
        duration: 280,
        ease: "out(3)"
      });
    },
    [hasMarkdown, markdown]
  );

  return (
    <article
      className={hasMarkdown ? `${className} markdown-report` : `${className} empty`}
      ref={reportRef}
    >
      {hasMarkdown ? (
        <>
          <div className="prose prose-sm prose-invert max-w-none report-markdown">
            <Markdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
              {markdown}
            </Markdown>
          </div>
          {isTyping && <span className="typing-cursor" />}
        </>
      ) : isLoading ? (
        loadingText
      ) : (
        emptyText
      )}
    </article>
  );
}
