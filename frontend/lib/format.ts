/** Shared formatting utilities for P&L values, percentages, and adaptive font sizing. */

export function fmtPnl(val: number): string {
  if (val >= 0)
    return `+$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `-$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtPercent(val: number): string {
  return `${val.toFixed(1)}%`;
}

export function adaptiveFontSize(value: string): string {
  const len = value.length;
  if (len <= 7) return "11px";
  if (len <= 10) return "10px";
  if (len <= 13) return "9px";
  return "8px";
}
