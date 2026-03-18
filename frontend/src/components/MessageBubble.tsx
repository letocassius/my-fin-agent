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
import { MarkdownRenderer } from "./MarkdownRenderer";

interface MessageBubbleProps {
  message: Message;
}

function QueryTypeBadge({ queryType, sourceType }: { queryType: "market" | "knowledge"; sourceType?: string | null }) {
  const isMarket = queryType === "market";
  const isWikipedia = sourceType === "wikipedia";

  let colorClasses: string;
  let dotClasses: string;
  let label: string;

  if (isMarket) {
    colorClasses = "bg-terminal-blue/10 text-terminal-blue border-terminal-blue/30";
    dotClasses = "bg-terminal-blue";
    label = "Market Data";
  } else if (isWikipedia) {
    colorClasses = "bg-terminal-green/10 text-terminal-green border-terminal-green/30";
    dotClasses = "bg-terminal-green";
    label = "Wikipedia";
  } else {
    colorClasses = "bg-terminal-purple/10 text-terminal-purple border-terminal-purple/30";
    dotClasses = "bg-terminal-purple";
    label = "Knowledge Base";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest border ${colorClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotClasses}`} />
      {label}
    </span>
  );
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
            <QueryTypeBadge queryType={message.query_type} sourceType={message.source_type} />
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
                <MarkdownRenderer content={message.analysis_section} />
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
              <MarkdownRenderer content={message.content} />
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
