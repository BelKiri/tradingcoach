import * as React from "react";

/**
 * Matches dollar PNL amounts only (e.g. -$1,234.56, ~$200/week).
 * Does not match trade counts, percentages, or bare numbers.
 */
const DOLLAR_HIGHLIGHT_RE =
  /(-\$[\d,]+(?:\.\d+)?(?:\/(?:month|week))?)|((?:~)?\$[\+]?[\d,]+(?:\.\d+)?(?:\/(?:month|week))?)/g;

export function highlightDollarsInPlainText(text: string): React.ReactNode {
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
        key={`pnl-$-${k++}`}
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
