/**
 * MarketDataCard: Displays structured market data in a terminal-style card.
 * Renders the DATA section from a market query response.
 */

interface MarketDataCardProps {
  ticker: string | null;
  dataSection: string;
}

export function MarketDataCard({ ticker, dataSection }: MarketDataCardProps) {
  return (
    <div className="mt-3 rounded border border-terminal-border bg-terminal-bg overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center gap-2 px-3 py-2 bg-[#1c2128] border-b border-terminal-border">
        <span className="text-xs font-mono font-semibold text-terminal-muted uppercase tracking-widest">
          Market Data
        </span>
        {ticker && (
          <>
            <span className="text-terminal-border">·</span>
            <span className="text-xs font-mono font-bold text-terminal-blue">
              {ticker}
            </span>
          </>
        )}
        <div className="ml-auto flex gap-1">
          <div className="w-2 h-2 rounded-full bg-terminal-green opacity-60" />
          <div className="w-2 h-2 rounded-full bg-terminal-yellow opacity-60" />
          <div className="w-2 h-2 rounded-full bg-terminal-red opacity-60" />
        </div>
      </div>

      {/* Data content */}
      <div className="px-4 py-3">
        <pre className="font-mono text-xs text-terminal-text leading-relaxed whitespace-pre-wrap break-words">
          {dataSection}
        </pre>
      </div>
    </div>
  );
}
