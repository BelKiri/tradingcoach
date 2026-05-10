/** Adaptive font for table cells (P&L by Day, P&L by Session) */
export function getAdaptiveFontSize(value: string): string {
  const len = value.length;
  if (len <= 7) return "11px";
  if (len <= 10) return "10px";
  if (len <= 13) return "9px";
  return "8px";
}

/** Adaptive font for metric card values (larger base size) */
export function getMetricFontSize(value: string): string {
  const len = value.length;
  if (len <= 7) return "22px";
  if (len <= 10) return "18px";
  if (len <= 13) return "15px";
  return "13px";
}
