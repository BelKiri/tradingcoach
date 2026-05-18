import * as React from "react";

/** Signed dollar PNL only; unsigned `$N` stays default text color. */
const SIGNED_DOLLAR_AMOUNT =
  String.raw`[\d,]+(?:\.\d+)?(?:\/(?:month|week))?`;

const DOLLAR_HIGHLIGHT_RE = new RegExp(
  String.raw`(-\$${SIGNED_DOLLAR_AMOUNT})` +
    String.raw`|(\+\$${SIGNED_DOLLAR_AMOUNT})` +
    String.raw`|(\$-${SIGNED_DOLLAR_AMOUNT})` +
    String.raw`|(\$\+${SIGNED_DOLLAR_AMOUNT})`,
  "g",
);

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
    const isNeg = m[1] != null || m[3] != null;
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
