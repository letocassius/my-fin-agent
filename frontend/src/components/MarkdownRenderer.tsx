import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import type { Components } from "react-markdown";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-terminal-text mt-4 mb-2">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-bold text-terminal-text mt-3 mb-1.5">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-terminal-text mt-3 mb-1">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-sm text-terminal-text leading-relaxed mb-2">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-terminal-text">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => (
    <ul className="ml-4 space-y-1 mb-2">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="ml-4 space-y-1 mb-2 list-decimal">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-sm text-terminal-text leading-relaxed flex gap-2">
      <span className="text-terminal-muted select-none">·</span>
      <span>{children}</span>
    </li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-terminal-blue/40 pl-3 my-2 text-sm text-terminal-muted italic">
      {children}
    </blockquote>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code className="text-xs font-mono text-terminal-text leading-relaxed">
          {children}
        </code>
      );
    }
    return (
      <code className="px-1.5 py-0.5 rounded bg-terminal-surface border border-terminal-border text-xs font-mono text-terminal-blue">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <div className="my-2 rounded bg-terminal-surface border border-terminal-border overflow-x-auto max-w-full">
      <pre className="p-3 overflow-x-auto">{children}</pre>
    </div>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded border border-terminal-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-terminal-surface border-b border-terminal-border">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-1.5 text-left text-xs font-mono font-semibold text-terminal-muted uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-1.5 text-sm text-terminal-text border-t border-terminal-border/50">
      {children}
    </td>
  ),
  hr: () => <hr className="my-3 border-terminal-border/50" />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-terminal-blue hover:underline"
    >
      {children}
    </a>
  ),
};

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-content overflow-hidden min-w-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
