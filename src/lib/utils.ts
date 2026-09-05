/** Slug pro detailové stránky ETF: "IEMO.MI" -> "iemo-mi" */
export const etfSlug = (ticker: string): string =>
  ticker.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

/** Formátování procent v českém stylu: 6.42 -> "+6,4 %" */
export const fmtPct = (v: number | null | undefined): string =>
  v == null
    ? '–'
    : `${v > 0 ? '+' : ''}${v.toLocaleString('cs-CZ', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
