import { useMemo, useState } from "react";
import { Plot } from "../components/Plot";
import { Loading, Section, Stat } from "../components/ui";
import { modelColor, modelDash, withAlpha } from "../lib/colors";
import { loadReplay } from "../lib/data";
import { berlinAxis, mw, pct, signedMw } from "../lib/format";
import { token } from "../lib/theme";
import { MODEL_LABEL, modelsIn, headlineModel, type ModelName } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;

export function Replay({ theme }: { theme: string }) {
  const { data, error } = useAsync(loadReplay);
  const [idx, setIdx] = useState<number | null>(null);
  const [picked, setModel] = useState<ModelName | null>(null);
  const model: ModelName = picked ?? (data ? headlineModel(data.models) : "lightgbm");
  const [level, setLevel] = useState<0 | 1>(0);
  const [showBaseline, setShowBaseline] = useState(true);

  const view = useMemo(() => {
    if (!data) return null;
    const i = idx ?? data.origins_utc.length - 1;
    const origin = data.origins_utc[i];
    const hours = Array.from({ length: 168 }, (_, h) => new Date(Date.parse(origin) + h * 3600e3).toISOString());
    const actual = data.actual_mw[i];
    const m = data.models[model];
    const point = m.point_mw[i];
    const lo = m.bounds_mw[i][level * 2];
    const hi = m.bounds_mw[i][level * 2 + 1];
    const base = data.models.snaive168.point_mw[i];
    const maeModel = mean(actual.map((a, h) => Math.abs(a - point[h])));
    const maeBase = mean(actual.map((a, h) => Math.abs(a - base[h])));
    const cover = mean(actual.map((a, h) => (a >= lo[h] && a <= hi[h] ? 1 : 0)));
    const bias = mean(point.map((p, h) => p - actual[h]));
    return { i, origin, hours, actual, point, lo, hi, base, maeModel, maeBase, cover, bias };
  }, [data, idx, model, level]);

  if (!data || !view) return <Loading error={error} />;
  const n = data.origins_utc.length;
  const color = modelColor(model);
  const x = view.hours.map(berlinAxis);
  const lvl = Math.round(data.levels[level] * 100);
  const showBase = showBaseline && model !== "snaive168";

  const traces = [
    { x, y: view.lo, mode: "lines", line: { width: 0, color }, showlegend: false, hoverinfo: "skip" },
    {
      x,
      y: view.hi,
      name: `Interval ${lvl}%`,
      mode: "lines",
      fill: "tonexty",
      fillcolor: withAlpha(color, 0.18),
      line: { width: 0, color },
      hoverinfo: "skip",
    },
    ...(showBase
      ? [
          {
            x,
            y: view.base,
            name: MODEL_LABEL.snaive168,
            mode: "lines",
            line: { color: modelColor("snaive168"), width: 1.5, dash: modelDash("snaive168") },
            hovertemplate: "%{y:,.0f} MW<extra>Naive mingguan</extra>",
          },
        ]
      : []),
    {
      x,
      y: view.point,
      name: MODEL_LABEL[model],
      mode: "lines",
      line: { color, width: 2, dash: modelDash(model) },
      hovertemplate: "%{y:,.0f} MW<extra>Prakiraan</extra>",
    },
    {
      x,
      y: view.actual,
      name: "Aktual",
      mode: "lines",
      line: { color: token("--text-primary"), width: 2 },
      hovertemplate: "%{y:,.0f} MW<extra>Aktual</extra>",
    },
  ];

  const better = view.maeModel < view.maeBase;
  return (
    <div className="stack">
      <Section
        title="Uji mundur: bandingkan prakiraan dengan kenyataan"
        id="judul-replay"
        lead={
          <>
            Setiap Senin pada periode uji (2019 sampai September 2020) model membuat prakiraan 7 hari hanya dari data
            sebelum hari itu. Pilih minggunya untuk melihat seberapa dekat prakiraan dengan beban aktual. Situs
            menampilkan {n} origin Senin; metrik resmi di tab Kinerja memakai semua origin harian.
          </>
        }
      >
        <div className="toolbar">
          <div className="week-nav">
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setIdx(Math.max(0, view.i - 1))}
              disabled={view.i === 0}
              aria-label="Minggu sebelumnya"
            >
              ‹
            </button>
            <label className="select">
              <span>Minggu mulai</span>
              <select value={view.i} onChange={(e) => setIdx(Number(e.target.value))}>
                {data.origins_utc.map((o, i) => (
                  <option key={o} value={i}>
                    {new Intl.DateTimeFormat("id-ID", { timeZone: "UTC", day: "numeric", month: "short", year: "numeric" }).format(new Date(o))}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setIdx(Math.min(n - 1, view.i + 1))}
              disabled={view.i === n - 1}
              aria-label="Minggu berikutnya"
            >
              ›
            </button>
          </div>
          <label className="select">
            <span>Model</span>
            <select value={model} onChange={(e) => setModel(e.target.value as ModelName)}>
              {modelsIn(data.models).map((m) => (
                <option key={m} value={m}>
                  {MODEL_LABEL[m]}
                </option>
              ))}
            </select>
          </label>
          <label className="select">
            <span>Interval</span>
            <select value={level} onChange={(e) => setLevel(Number(e.target.value) as 0 | 1)}>
              <option value={0}>80%</option>
              <option value={1}>95%</option>
            </select>
          </label>
          {model !== "snaive168" ? (
            <label className="check">
              <input type="checkbox" checked={showBaseline} onChange={(e) => setShowBaseline(e.target.checked)} />
              Tampilkan naive mingguan
            </label>
          ) : null}
        </div>
        <div className="stats">
          <Stat label={`Galat rata-rata ${MODEL_LABEL[model]}`} value={mw(view.maeModel)} note="MAE minggu ini" />
          <Stat label="Galat naive mingguan" value={mw(view.maeBase)} note={better ? "model lebih baik minggu ini" : "baseline sama atau lebih baik"} />
          <Stat label={`Aktual di dalam interval ${lvl}%`} value={pct(view.cover)} note={`target ${lvl}%`} />
          <Stat label="Bias" value={signedMw(view.bias)} note={view.bias > 0 ? "prakiraan terlalu tinggi" : "prakiraan terlalu rendah"} />
        </div>
        <Plot
          data={traces}
          height={400}
          theme={theme}
          layout={{ yaxis: { title: { text: "Beban (MW)", font: { size: 12 } } } }}
          label={`Grafik beban aktual dan prakiraan ${MODEL_LABEL[model]} untuk minggu yang dipilih`}
        />
        <p className="help">Satu minggu tidak mewakili kinerja keseluruhan. Lihat tab Kinerja untuk angka dari semua origin.</p>
      </Section>
    </div>
  );
}
