"use client";

import * as React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/** react-markdown passes `node` (hast); strip before spreading onto DOM elements. */
function omitHastNode<T extends Record<string, unknown>>(props: T): Omit<T, "node"> {
  return Object.fromEntries(
    Object.entries(props).filter(([key]) => key !== "node"),
  ) as Omit<T, "node">;
}

/**
 * Ported from legacy FormattedResponse, with `/week` and optional `~` prefix
 * so patterns like ~$200/week match. Leading `-$…` is matched first so the
 * span always covers the minus (legacy regex order could miss that case).
 */
const DOLLAR_HIGHLIGHT_RE =
  /(-\$[\d,]+(?:\.\d+)?(?:\/(?:month|week))?)|((?:~)?\$[\+]?[\d,]+(?:\.\d+)?(?:\/(?:month|week))?)/g;

function highlightDollarsInPlainText(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  const re = new RegExp(DOLLAR_HIGHLIGHT_RE.source, "g");
  let k = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      parts.push(text.slice(last, m.index));
    }
    const full = m[0];
    const isNeg = m[1] != null || full.includes("-");
    parts.push(
      <span
        key={`coach-$-${k++}`}
        className={isNeg ? "text-red-400 font-medium" : "text-emerald-400 font-medium"}
      >
        {full}
      </span>,
    );
    last = m.index + full.length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  if (parts.length === 0) {
    return text;
  }
  if (parts.length === 1 && typeof parts[0] === "string") {
    return parts[0];
  }
  return <>{parts}</>;
}

function processChildren(children: React.ReactNode): React.ReactNode {
  return React.Children.map(children, (child) => {
    if (child == null || typeof child === "boolean") {
      return child;
    }
    if (typeof child === "string") {
      return highlightDollarsInPlainText(child);
    }
    if (typeof child === "number") {
      return child;
    }
    if (!React.isValidElement(child)) {
      return child;
    }
    // Do not mutate fenced / inline code (no HTML injection; dollars stay literal).
    if (child.type === "pre" || child.type === "code") {
      return child;
    }
    const { children: inner, ...rest } = child.props as {
      children?: React.ReactNode;
    };
    if (inner == null) {
      return child;
    }
    return React.cloneElement(child, {
      ...rest,
      children: processChildren(inner),
    } as never);
  });
}

function withDollarHighlights(
  Tag: keyof React.JSX.IntrinsicElements,
  className?: string,
): React.ComponentType<Record<string, unknown>> {
  return function MdElement(props: Record<string, unknown>) {
    const { children, className: cnProp, ...rest } = omitHastNode(props);
    return React.createElement(
      Tag,
      { ...rest, className: cn(className, cnProp as string | undefined) },
      processChildren(children as React.ReactNode),
    );
  };
}

const markdownComponents = {
  h1: withDollarHighlights("h1", "mt-6 mb-2 text-2xl font-bold text-foreground"),
  h2: withDollarHighlights("h2", "mt-5 mb-2 text-xl font-semibold text-foreground"),
  h3: withDollarHighlights("h3", "mt-4 mb-1 text-lg font-semibold text-foreground"),
  h4: withDollarHighlights("h4", "mt-3 mb-1 text-base font-semibold text-foreground"),
  h5: withDollarHighlights("h5", "mt-3 mb-1 text-sm font-semibold text-foreground"),
  h6: withDollarHighlights("h6", "mt-3 mb-1 text-sm font-medium text-muted-foreground"),
  p: withDollarHighlights("p", "mb-3 last:mb-0 leading-relaxed"),
  ul: withDollarHighlights("ul", "mb-3 list-disc space-y-1 pl-5"),
  ol: withDollarHighlights("ol", "mb-3 list-decimal space-y-1 pl-5"),
  li: withDollarHighlights("li", "pl-0.5"),
  blockquote: withDollarHighlights(
    "blockquote",
    "my-3 border-l-2 border-muted-foreground/40 pl-4 italic text-muted-foreground",
  ),
  a: (props) => {
    const { children, className, ...rest } = omitHastNode(
      props as unknown as Record<string, unknown>,
    );
    return (
      <a
        {...rest}
        className={cn("text-primary underline underline-offset-2", className as string | undefined)}
        target="_blank"
        rel="noopener noreferrer"
      >
        {processChildren(children as React.ReactNode)}
      </a>
    );
  },
  strong: withDollarHighlights("strong", "font-semibold text-foreground"),
  em: withDollarHighlights("em", "italic"),
  del: withDollarHighlights("del", "line-through text-muted-foreground"),
  hr: (props) => {
    const { className, ...rest } = omitHastNode(props as unknown as Record<string, unknown>);
    return (
      <hr {...rest} className={cn("my-6 border-border", className as string | undefined)} />
    );
  },
  table: (props) => {
    const { children, className, ...rest } = omitHastNode(
      props as unknown as Record<string, unknown>,
    );
    return (
      <div className="my-3 overflow-x-auto">
        <table
          {...rest}
          className={cn("w-full border-collapse text-sm", className as string | undefined)}
        >
          {children as React.ReactNode}
        </table>
      </div>
    );
  },
  thead: withDollarHighlights("thead", ""),
  tbody: withDollarHighlights("tbody", ""),
  tr: withDollarHighlights("tr", ""),
  th: withDollarHighlights("th", "border border-border bg-muted/50 px-2 py-1.5 text-left font-medium"),
  td: withDollarHighlights("td", "border border-border px-2 py-1.5 align-top"),
  pre: (props) => {
    const { children, className, ...rest } = omitHastNode(
      props as unknown as Record<string, unknown>,
    );
    return (
    <pre
      {...rest}
      className={cn(
        "my-3 overflow-x-auto rounded-md border border-border bg-muted/40 p-3 text-xs",
        className as string | undefined,
      )}
    >
      {children as React.ReactNode}
    </pre>
    );
  },
  code: (props) => {
    const { className, children, ...rest } = omitHastNode(
      props as unknown as Record<string, unknown>,
    );
    const isBlock = Boolean(className?.toString().includes("language-"));
    if (isBlock) {
      return (
        <code {...rest} className={className as string | undefined}>
          {children as React.ReactNode}
        </code>
      );
    }
    return (
      <code
        {...rest}
        className={cn("rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]", className as string | undefined)}
      >
        {children as React.ReactNode}
      </code>
    );
  },
} as Components;

export function CoachMarkdown({ text }: { text: string }) {
  return (
    <div className="coach-markdown space-y-1 text-sm leading-relaxed text-foreground">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
