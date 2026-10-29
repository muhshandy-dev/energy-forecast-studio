const nf0 = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const mw = (v: number) => `${nf0.format(v)} MW`;
export const gw = (v: number) => `${nf1.format(v / 1000)} GW`;
export const num0 = (v: number) => nf0.format(v);
export const num1 = (v: number) => nf1.format(v);
export const num2 = (v: number) => nf2.format(v);
export const pct = (v: number, digits = 1) =>
  `${new Intl.NumberFormat("id-ID", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v * 100)}%`;
export const signedPct = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${pct(Math.abs(v))}`;
export const signedMw = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${nf0.format(Math.abs(v))} MW`;

const TZ = "Europe/Berlin";
const dtf = new Intl.DateTimeFormat("id-ID", {
  timeZone: TZ,
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const df = new Intl.DateTimeFormat("id-ID", {
  timeZone: TZ,
  day: "numeric",
  month: "long",
  year: "numeric",
});
const dfUtc = new Intl.DateTimeFormat("id-ID", {
  timeZone: "UTC",
  day: "numeric",
  month: "long",
  year: "numeric",
});

/** Waktu lokal Jerman (data beban adalah beban Jerman). */
export const localTime = (iso: string) => dtf.format(new Date(iso));
export const localDate = (iso: string) => df.format(new Date(iso));
/** Tanggal kalender tanpa zona (mis. "2019-03-04"). */
export const plainDate = (ymd: string) => dfUtc.format(new Date(`${ymd}T00:00:00Z`));

/** ISO UTC -> string waktu lokal Jerman "YYYY-MM-DD HH:mm" untuk sumbu Plotly. */
export function berlinAxis(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}
