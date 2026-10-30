/**
 * Transformasi skenario yang valid secara matematis atas prakiraan tersimpan.
 *
 * - Geser level: y' = y × (1 + s). Karena fungsi naik monoton, kuantil ikut dikali
 *   faktor yang sama (kuantil dari aY adalah a × kuantil Y untuk a > 0).
 * - Peluang melampaui batas kapasitas C: 1 − F(C), dengan F diinterpolasi linear di antara
 *   kuantil tersimpan. Di luar kuantil terluar, nilai hanya diketahui sebagai batas
 *   (mis. "< 2,5%"), tidak diekstrapolasi.
 *
 * Fungsi yang sama ada di Python (energy_forecast/scenario.py); vektor uji dibagi bersama.
 */

export type Exceedance = {
  /** Peluang beban > C (0..1). Bila `bound` bukan "exact", ini nilai batasnya. */
  p: number;
  bound: "exact" | "atLeast" | "atMost";
};

export function scaleFactor(shiftPct: number): number {
  if (!Number.isFinite(shiftPct) || shiftPct <= -100) {
    throw new RangeError("geser level harus > -100%");
  }
  return 1 + shiftPct / 100;
}

export function applyShift(values: number[], shiftPct: number): number[] {
  const f = scaleFactor(shiftPct);
  return values.map((v) => v * f);
}

/** `probs` naik ketat, `quantiles` tidak turun, panjang sama. */
export function exceedance(probs: number[], quantiles: number[], capacity: number): Exceedance {
  const n = probs.length;
  if (n < 2 || quantiles.length !== n) throw new RangeError("grid kuantil tidak valid");
  if (capacity < quantiles[0]) return { p: 1 - probs[0], bound: "atLeast" };
  if (capacity >= quantiles[n - 1]) return { p: 1 - probs[n - 1], bound: "atMost" };
  // indeks terakhir i dengan q_i <= C (q_0 <= C < q_{n-1} terjamin di sini)
  let i = 0;
  while (i + 1 < n && quantiles[i + 1] <= capacity) i += 1;
  const q0 = quantiles[i];
  const q1 = quantiles[i + 1];
  const cdf = q1 === q0 ? probs[i + 1] : probs[i] + ((capacity - q0) / (q1 - q0)) * (probs[i + 1] - probs[i]);
  return { p: 1 - cdf, bound: "exact" };
}

/**
 * Peluang per jam untuk satu model.
 * `quantilesByProb[k][h]` = kuantil ke-k pada jam h (bentuk ekspor planning.json).
 */
export function exceedanceByHour(
  probs: number[],
  quantilesByProb: number[][],
  capacity: number,
  shiftPct: number,
  hours: number,
): Exceedance[] {
  const f = scaleFactor(shiftPct);
  const out: Exceedance[] = [];
  for (let h = 0; h < hours; h += 1) {
    out.push(exceedance(probs, quantilesByProb.map((row) => row[h] * f), capacity));
  }
  return out;
}

/**
 * Perkiraan jumlah jam di atas batas = jumlah peluang per jam (linearitas ekspektasi).
 * Jam dengan peluang yang hanya diketahui batasnya membuat hasil berupa rentang.
 */
export function expectedHoursAbove(ex: Exceedance[]): { low: number; high: number } {
  let low = 0;
  let high = 0;
  for (const e of ex) {
    if (e.bound === "exact") {
      low += e.p;
      high += e.p;
    } else if (e.bound === "atLeast") {
      low += e.p;
      high += 1;
    } else {
      high += e.p;
    }
  }
  return { low, high };
}

/** Indeks kuantil untuk interval sentral `level` (mis. 0,8 -> 0,1 dan 0,9). */
export function intervalIndices(probs: number[], level: number): [number, number] {
  const lo = (1 - level) / 2;
  const hi = 1 - lo;
  const iLo = probs.findIndex((p) => Math.abs(p - lo) < 1e-9);
  const iHi = probs.findIndex((p) => Math.abs(p - hi) < 1e-9);
  if (iLo < 0 || iHi < 0) throw new RangeError(`level ${level} tidak ada di grid kuantil`);
  return [iLo, iHi];
}
