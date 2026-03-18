/**
 * App: Root component for the Financial Asset Q&A system.
 * Renders the main layout with header and chat interface.
 */

import { useState, useEffect } from "react";
import { ChatInterface } from "./components/ChatInterface";
import { checkHealth } from "./api/client";

function StatusIndicator() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let mounted = true;
    checkHealth()
      .then(() => {
        if (mounted) setStatus("online");
      })
      .catch(() => {
        if (mounted) setStatus("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`w-1.5 h-1.5 rounded-full ${
          status === "online"
            ? "bg-terminal-green"
            : status === "offline"
            ? "bg-terminal-red"
            : "bg-terminal-yellow animate-pulse"
        }`}
      />
      <span className="text-[10px] font-mono text-terminal-muted uppercase tracking-widest">
        {status === "online" ? "Connected" : status === "offline" ? "Offline" : "Connecting"}
      </span>
    </div>
  );
}

export default function App() {
  return (
    <div className="flex flex-col h-screen bg-terminal-bg text-terminal-text font-sans antialiased">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-terminal-border bg-terminal-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          </div>
          <div className="h-4 w-px bg-terminal-border" />
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-terminal-text tracking-tight">
              fin-agent
            </span>
            <span className="text-[10px] font-mono text-terminal-muted/60 border border-terminal-border/50 px-1.5 py-0.5 rounded">
              v0.1.0
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatusIndicator />
          <div className="hidden sm:flex items-center gap-1 text-[10px] font-mono text-terminal-muted/50">
            <span className="text-terminal-blue/60">Market</span>
            <span className="mx-1">·</span>
            <span className="text-terminal-purple/60">Knowledge</span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto w-full">
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}
