import type { ModelName } from "./types";
import { token } from "./theme";

/** Warna identitas model (urutan slot kategori tetap; tervalidasi CVD). */
export function modelColor(m: ModelName): string {
  return token(`--series-${m}`);
}

/** Baseline harian dibedakan dengan garis putus-putus (pengodean sekunder). */
export function modelDash(m: ModelName): string {
  return m === "snaive24" ? "dot" : m === "snaive168" ? "dash" : "solid";
}

/** Warna dengan alfa untuk pita interval. */
export function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.replace(/(.)/g, "$1$1") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}
