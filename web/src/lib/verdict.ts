import { MODEL_LABEL, type ModelName, type PeriodMetrics } from "./types";

export type Verdict = { model: ModelName; text: string; kind: "better" | "unclear" | "worse" };

/**
 * Kalimat ringkasan jujur dari metrik: model non-baseline terbaik vs naive mingguan,
 * memakai CI bootstrap selisih MAE (negatif = lebih baik).
 */
export function verdict(p: PeriodMetrics): Verdict {
  const candidates = (["ensemble", "lightgbm", "mstl_ets"] as ModelName[]).filter((m) => m in p);
  const best = candidates.reduce((a, b) => (p[a].week_ahead.mae <= p[b].week_ahead.mae ? a : b));
  const w = p[best].week_ahead;
  const [lo, hi] = w.mae_minus_snaive168_ci95;
  const skill = Math.round(w.skill_vs_snaive168 * 1000) / 10;
  const name = MODEL_LABEL[best];
  if (hi < 0)
    return {
      model: best,
      kind: "better",
      text: `${name} lebih akurat daripada naive mingguan: galat rata-rata 7 hari ${skill.toLocaleString("id-ID")}% lebih kecil, dan interval kepercayaan 95% selisihnya seluruhnya di bawah nol.`,
    };
  if (lo > 0)
    return {
      model: best,
      kind: "worse",
      text: `Tidak ada model yang mengalahkan naive mingguan pada periode ini. Model terbaik, ${name}, justru lebih buruk dan selisihnya meyakinkan.`,
    };
  return {
    model: best,
    kind: "unclear",
    text: `${name} sedikit berbeda dari naive mingguan (${skill.toLocaleString("id-ID")}%), tetapi interval kepercayaan 95% selisihnya mencakup nol, jadi keunggulannya belum meyakinkan.`,
  };
}
