/**
 * ChatInterface: Main chat UI component with input, message history, and scroll behavior.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { sendQuery, ApiClientError } from "../api/client";

const EXAMPLE_QUERIES = [
  "What is Alibaba's current stock price?",
  "How has BABA performed over the last 30 days?",
  "What is a P/E ratio?",
  "How has Tesla performed this year?",
  "What is the difference between revenue and net income?",
  "What is NVDA's recent price trend?",
];

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function LoadingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-terminal-surface border border-terminal-border">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-muted animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-muted animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-muted animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
        <span className="text-xs font-mono text-terminal-muted">Processing query...</span>
      </div>
    </div>
  );
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const handleSubmit = useCallback(
    async (queryText?: string) => {
      const query = (queryText ?? inputValue).trim();
      if (!query || isLoading) return;

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: query,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue("");
      setIsLoading(true);

      try {
        const response = await sendQuery({ query });

        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: response.answer,
          query_type: response.query_type,
          data_section: response.data_section,
          analysis_section: response.analysis_section,
          sources: response.sources,
          ticker: response.ticker,
          latency_ms: response.latency_ms ?? undefined,
          source_type: response.source_type,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        let errorContent = "An unexpected error occurred. Please try again.";

        if (err instanceof ApiClientError) {
          if (err.status === 503) {
            errorContent = `Service unavailable: ${err.detail ?? "Backend may not be running or API keys may be missing."}`;
          } else if (err.status === 500) {
            errorContent = `Server error: ${err.detail ?? "Internal server error."}`;
          } else {
            errorContent = err.detail ?? err.message;
          }
        } else if (err instanceof TypeError && (err as TypeError).message.includes("fetch")) {
          errorContent = "Cannot connect to the backend. Check that the API URL is correct and the backend service is reachable.";
        }

        const errorMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: errorContent,
          timestamp: new Date(),
          error: true,
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [inputValue, isLoading]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleExampleClick = useCallback(
    (query: string) => {
      if (!isLoading) {
        handleSubmit(query);
      }
    },
    [handleSubmit, isLoading]
  );

  const isEmpty = messages.length === 0;

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-36 pt-4 space-y-1 md:pb-32">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-8 py-12">
            {/* Empty state */}
            <div className="text-center space-y-2">
              <div className="flex items-center justify-center gap-2 mb-4">
                <span className="text-terminal-green font-mono text-xl">$</span>
                <h2 className="text-lg font-semibold text-terminal-text font-mono">
                  fin-agent
                </h2>
              </div>
              <p className="text-sm text-terminal-muted max-w-md leading-relaxed">
                Ask about stock prices, market trends, or financial concepts.
                Market queries fetch live data; knowledge queries use external reference sources.
              </p>
            </div>

            {/* Example queries */}
            <div className="w-full max-w-lg space-y-2">
              <p className="text-[10px] font-mono text-terminal-muted uppercase tracking-widest text-center mb-3">
                Example queries
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleExampleClick(q)}
                    disabled={isLoading}
                    className="text-left px-3 py-2.5 rounded border border-terminal-border bg-terminal-surface hover:border-terminal-blue/50 hover:bg-terminal-blue/5 transition-colors duration-150 group"
                  >
                    <span className="text-terminal-muted text-xs font-mono group-hover:text-terminal-blue transition-colors">
                      &gt;
                    </span>
                    <span className="ml-2 text-xs text-terminal-text/80 group-hover:text-terminal-text transition-colors">
                      {q}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="absolute bottom-0 left-0 right-0 z-10 border-t border-terminal-border bg-terminal-surface/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-terminal-surface/85">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <span className="font-mono text-terminal-green text-sm mb-2.5 select-none">$</span>
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a financial question..."
              disabled={isLoading}
              rows={1}
              className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2.5 text-sm font-mono text-terminal-text placeholder-terminal-muted/50 focus:outline-none focus:border-terminal-blue/60 focus:ring-1 focus:ring-terminal-blue/20 resize-none disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed"
              style={{
                minHeight: "42px",
                maxHeight: "120px",
                overflowY: inputValue.split("\n").length > 3 ? "auto" : "hidden",
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = Math.min(target.scrollHeight, 120) + "px";
              }}
            />
          </div>
          <button
            onClick={() => handleSubmit()}
            disabled={isLoading || !inputValue.trim()}
            className="mb-0.5 px-4 py-2.5 rounded border border-terminal-blue/40 bg-terminal-blue/10 text-terminal-blue text-sm font-mono font-medium hover:bg-terminal-blue/20 hover:border-terminal-blue/60 transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {isLoading ? "..." : "Send"}
          </button>
        </div>
        <div className="text-[10px] font-mono text-terminal-muted/40 text-center mt-1.5 max-w-4xl mx-auto">
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
