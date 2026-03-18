/**
 * MessageBubble: Renders a single chat message.
 *
 * For user messages: simple right-aligned bubble.
 * For assistant messages:
 *   - Shows query type badge (MARKET DATA / KNOWLEDGE BASE)
 *   - For market answers: shows DATA card + ANALYSIS section
 *   - For knowledge answers: shows answer + sources list
 */

import type { Message } from "../types";
import { MarketDataCard } from "./MarketDataCard";

interface MessageBubbleProps {
  message: Message;
}

function QueryTypeBadge({ queryType }: { queryType: "market" | "knowledge" }) {
  const isMarket = queryType === "market";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest border ${
        isMarket
          ? "bg-terminal-blue/10 text-terminal-blue border-terminal-blue/30"
          : "bg-terminal-purple/10 text-terminal-purple border-terminal-purple/30"
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isMarket ? "bg-terminal-blue" : "bg-terminal-purple"
        }`}
      />
      {isMarket ? "Market Data" : "Knowledge Base"}
    </span>
  );
}

function AnalysisSection({ content }: { content: string }) {
  // Render markdown-like formatting (headers, bold)
  const lines = content.split("\n");
  return (
    <div className="text-sm text-terminal-text leading-relaxed space-y-1.5">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return (
            <h3 key={i} className="font-semibold text-terminal-text text-sm mt-3 mb-1">
              {line.replace(/^## /, "")}
            </h3>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h2 key={i} className="font-bold text-terminal-text text-base mt-3 mb-1">
              {line.replace(/^# /, "")}
            </h2>
          );
        }
        if (line.startsWith("**") && line.endsWith("**")) {
          return (
            <p key={i} className="font-semibold text-terminal-text">
              {line.replace(/^\*\*|\*\*$/g, "")}
            </p>
          );
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2 ml-2">
              <span className="text-terminal-muted mt-0.5">·</span>
              <span>{renderInlineMarkdown(line.replace(/^[-*]\s/, ""))}</span>
            </div>
          );
        }
        if (line.trim() === "") {
          return <div key={i} className="h-1" />;
        }
        return (
          <p key={i} className="text-terminal-text">
            {renderInlineMarkdown(line)}
          </p>
        );
      })}
    </div>
  );
}

function renderInlineMarkdown(text: string): React.ReactNode {
  // Handle **bold** and *italic* inline
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold text-terminal-text">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i} className="italic">{part.slice(1, -1)}</em>;
    }
    return <span key={i}>{part}</span>;
  });
}

function SourcesList({ sources }: { sources: string[] }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-terminal-border/50">
      <span className="text-[10px] font-mono text-terminal-muted uppercase tracking-widest">
        Sources
      </span>
      <div className="flex flex-wrap gap-1.5 mt-1.5">
        {sources.map((source, i) => (
          <span
            key={i}
            className="text-[10px] font-mono px-2 py-0.5 rounded bg-terminal-surface border border-terminal-border text-terminal-muted"
          >
            {source}
          </span>
        ))}
      </div>
    </div>
  );
}

function LatencyBadge({ ms }: { ms: number }) {
  return (
    <span className="text-[10px] font-mono text-terminal-muted/60">
      {ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
}

function ErrorMessage({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2.5 rounded border border-terminal-red/30 bg-terminal-red/5">
      <span className="text-terminal-red text-sm mt-0.5">!</span>
      <p className="text-sm text-terminal-red/90">{content}</p>
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] px-4 py-2.5 rounded-lg bg-terminal-blue/15 border border-terminal-blue/25">
          <p className="text-sm text-terminal-text">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start mb-6">
      <div className="w-full max-w-[90%]">
        {/* Header row: type badge + latency */}
        <div className="flex items-center gap-2 mb-2">
          {message.query_type && !message.error && (
            <QueryTypeBadge queryType={message.query_type} />
          )}
          {message.latency_ms !== undefined && message.latency_ms !== null && (
            <LatencyBadge ms={message.latency_ms} />
          )}
        </div>

        {/* Message content */}
        {message.error ? (
          <ErrorMessage content={message.content} />
        ) : message.query_type === "market" ? (
          <div className="space-y-3">
            {/* Data section in terminal card */}
            {message.data_section && (
              <MarketDataCard
                ticker={message.ticker ?? null}
                dataSection={message.data_section}
              />
            )}

            {/* Analysis section in prose */}
            {message.analysis_section && (
              <div className="px-1">
                <div className="text-[10px] font-mono text-terminal-muted uppercase tracking-widest mb-1.5">
                  Analysis
                </div>
                <AnalysisSection content={message.analysis_section} />
              </div>
            )}

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="px-1">
                <SourcesList sources={message.sources} />
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {/* Knowledge answer in prose */}
            <div className="px-1">
              <AnalysisSection content={message.content} />
            </div>

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="px-1">
                <SourcesList sources={message.sources} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
