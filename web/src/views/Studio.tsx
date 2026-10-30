import { useMemo, useState } from "react";
import { Plot } from "../components/Plot";
import { Loading, Section, Segmented, Stat } from "../components/ui";
import { modelColor, withAlpha } from "../lib/colors";
import { loadPlanning } from "../lib/data";
import { berlinAxis, gw, localTime, mw, num1, pct, utcDate } from "../lib/format";
import {
  applyShift,
  exceedanceByHour,
  expectedHoursAbove,
  intervalIndices,
  scaleFactor,
  type Exceedance,
} from "../lib/scenario";
import { token } from "../lib/theme";
import { MODEL_KIND, MODEL_LABEL, modelsIn, headlineModel, type MetaFile, type ModelName } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const HORIZONS = [24, 72, 168] as const;

export function exceedLabel(e: Exceedance): string {
  if (e.bound === "atMost") return `< ${pct(e.p)}`;
  if (e.bound === "atLeast") return `> ${pct(e.p)}`;
  return pct(e.p);
}

export function Studio({ meta, theme }: { meta: MetaFile; theme: string }) {
  const { data: plan, error } = useAsync(loadPlanning);
  const [picked, setModel] = useState<ModelName | null>(null);
  const model: ModelName = picked ?? (plan ? headlineModel(plan.models) : "lightgbm");
  const [horizon, setHorizon] = useState<number>(168);
  const [level, setLevel] = useState<number>(0.8);
  const [shift, setShift] = useState<number>(0);
  const [capacity, setCapacity] = useState<number | null>(null);

  const view = useMemo(() => {
    if (!plan) return null;
    const m = plan.models[model];
    const probs = plan.quantile_probs;
    const f = scaleFactor(shift);
    const point = applyShift(m.point_mw.slice(0, horizon), shift);
    const original = m.point_mw.slice(0, horizon);
    const [iLo, iHi] = intervalIndices(probs, level);
    const lo = m.quantiles_mw[iLo].slice(0, horizon).map((v) => v * f);
    const hi = m.quantiles_mw[iHi].slice(0, horizon).map((v) => v * f);
    const hours = plan.hours_utc.slice(0, horizon);
    let peak = 0;
    point.forEach((v, i) => {
      if (v > point[peak]) peak = i;
    });
    const defaultCap = Math.ceil((Math.max(...plan.models[headlineModel(plan.models)].point_mw) * 1.0) / 1000) * 1000;
    const cap = capacity ?? defaultCap;
    const ex = exceedanceByHour(probs, m.quantiles_mw, cap, shift, horizon);
    const expected = expectedHoursAbove(ex);
    let worst = 0;
    ex.forEach((e, i) => {
      if (e.p > ex[worst].p) worst = i;
    });
    return { point, original, lo, hi, hours, peak, cap, ex, expected, worst, defaultCap };
  }, [plan, model, horizon, level, shift, capacity]);

  if (!plan || !view) return <Loading error={error} />;

  const info = meta.models[model];
  const color = modelColor(model);
  const ink = token("--text-primary");
  const muted = token("--text-muted");
  const orange = token("--accent-orange");
  const histStart = plan.history_mw.length - 7 * 24;
  const histX = Array.from({ length: 7 * 24 }, (_, i) =>
    berlinAxis(new Date(Date.parse(plan.origin_utc) - (7 * 24 - i) * 3600e3).toISOString()),
  );
  const fx = view.hours.map(berlinAxis);
  const lvl = Math.round(level * 100);

  const traces = [
    {
      x: histX,
      y: plan.history_mw.slice(histStart),
      name: "Beban aktual (7 hari terakhir)",
      mode: "lines",
      line: { color: ink, width: 2 },
      hovertemplate: "%{y:,.0f} MW<extra>Aktual</extra>",
    },
    {
      x: fx,
      y: view.lo,
      name: `Batas bawah ${lvl}%`,
      mode: "lines",
      line: { width: 0, color },
      showlegend: false,
      hovertemplate: "%{y:,.0f} MW<extra>Batas bawah</extra>",
    },
    {
      x: fx,
      y: view.hi,
      name: `Interval prediksi ${lvl}%`,
      mode: "lines",
      fill: "tonexty",
      fillcolor: withAlpha(color, 0.18),
      line: { width: 0, color },
      hovertemplate: "%{y:,.0f} MW<extra>Batas atas</extra>",
    },
    ...(shift !== 0
      ? [
          {
            x: fx,
            y: view.original,
            name: "Prakiraan tanpa skenario",
            mode: "lines",
            line: { color: muted, width: 1.5, dash: "dot" },
            hovertemplate: "%{y:,.0f} MW<extra>Tanpa skenario</extra>",
          },
        ]
      : []),
    {
      x: fx,
      y: view.point,
      name: shift !== 0 ? `Prakiraan ${MODEL_LABEL[model]} + skenario` : `Prakiraan ${MODEL_LABEL[model]}`,
      mode: "lines",
      line: { color, width: 2 },
      hovertemplate: "%{y:,.0f} MW<extra>Prakiraan</extra>",
    },
  ];
  const layout = {
    yaxis: { title: { text: "Beban (MW)", font: { size: 12 } }, ticksuffix: "" },
    shapes: [
      {
        type: "line",
        xref: "paper",
        x0: 0,
        x1: 1,
        y0: view.cap,
        y1: view.cap,
        line: { color: token("--text-secondary"), width: 1.5, dash: "longdash" },
      },
      {
        type: "line",
        x0: fx[0],
        x1: fx[0],
        yref: "paper",
        y0: 0,
        y1: 1,
        line: { color: muted, width: 1 },
      },
    ],
    annotations: [
      {
        xref: "paper",
        x: 1,
        y: view.cap,
        yanchor: "top",
        xanchor: "right",
        text: `Batas kapasitas ${mw(view.cap)}`,
        showarrow: false,
        font: { color: token("--text-secondary"), size: 12 },
      },
      {
        x: fx[0],
        yref: "paper",
        y: 0,
        xanchor: "left",
        yanchor: "bottom",
        text: " Mulai prakiraan",
        showarrow: false,
        font: { color: muted, size: 11 },
      },
    ],
  };

  const exTrace = [
    {
      x: fx,
      y: view.ex.map((e) => e.p * 100),
      type: "bar",
      name: "Peluang melampaui batas",
      marker: { color: view.ex.map((e) => (e.bound === "exact" ? orange : muted)), opacity: 0.9 },
      customdata: view.ex.map(exceedLabel),
      hovertemplate: "%{customdata}<extra>Peluang > batas</extra>",
      showlegend: false,
    },
  ];
  const exLayout = {
    margin: { l: 64, r: 16, t: 8, b: 44 },
    bargap: 0.15,
    yaxis: { range: [0, 100], ticksuffix: "%", title: { text: "Peluang", font: { size: 12 } } },
  };

  const expText =
    Math.abs(view.expected.high - view.expected.low) < 0.05
      ? `${num1(view.expected.low)} jam`
      : `${num1(view.expected.low)} – ${num1(view.expected.high)} jam`;

  return (
    <div className="studio">
      <aside className="controls card" aria-label="Pengaturan skenario">
        <h2>Atur prakiraan</h2>
        <fieldset className="model-pick">
          <legend>Model</legend>
          {modelsIn(plan?.models ?? {}).map((m) => (
            <label key={m} className={m === model ? "on" : ""}>
              <input type="radio" name="model" checked={m === model} onChange={() => setModel(m)} />
              <span className="dot" style={{ background: modelColor(m) }} aria-hidden="true" />
              <span>
                <strong>{MODEL_LABEL[m]}</strong>
                <small>{MODEL_KIND[m]}</small>
              </span>
            </label>
          ))}
        </fieldset>
        <Segmented
          label="Horizon"
          value={horizon}
          options={HORIZONS.map((h) => ({ value: h, label: h === 24 ? "24 jam" : h === 72 ? "3 hari" : "7 hari" }))}
          onChange={setHorizon}
        />
        <Segmented
          label="Interval prediksi"
          value={level}
          options={[
            { value: 0.8, label: "80%" },
            { value: 0.95, label: "95%" },
          ]}
          onChange={setLevel}
        />
        <div className="field">
          <label htmlFor="shift">
            Skenario permintaan <output htmlFor="shift">{shift > 0 ? "+" : ""}{num1(shift)}%</output>
          </label>
          <input
            id="shift"
            type="range"
            min={-10}
            max={10}
            step={0.5}
            value={shift}
            onChange={(e) => setShift(Number(e.target.value))}
            aria-describedby="shift-help"
          />
          <p id="shift-help" className="help">
            Mengalikan seluruh prakiraan dan intervalnya: beban′ = beban × (1 + {num1(shift)}%).
          </p>
        </div>
        <div className="field">
          <label htmlFor="cap">
            Batas kapasitas <output htmlFor="cap">{mw(view.cap)}</output>
          </label>
          <input
            id="cap"
            type="range"
            min={40000}
            max={90000}
            step={500}
            value={view.cap}
            onChange={(e) => setCapacity(Number(e.target.value))}
          />
          <p className="help">Peluang beban melewati batas dihitung dari kuantil prakiraan tersimpan.</p>
        </div>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setShift(0);
            setCapacity(null);
            setLevel(0.8);
            setHorizon(168);
          }}
        >
          Kembalikan ke awal
        </button>
      </aside>

      <div className="studio-main">
        <div className="stats" aria-live="polite">
          <Stat label="Puncak prakiraan" value={gw(view.point[view.peak])} note={localTime(view.hours[view.peak])} />
          <Stat
            label={`Rentang ${lvl}% saat puncak`}
            value={`${gw(view.lo[view.peak])} – ${gw(view.hi[view.peak])}`}
            note="interval prediksi"
          />
          <Stat
            label="Perkiraan jam di atas batas"
            value={expText}
            note={`dari ${view.hours.length} jam`}
          />
          <Stat
            label="Peluang tertinggi melewati batas"
            value={exceedLabel(view.ex[view.worst])}
            note={localTime(view.hours[view.worst])}
          />
        </div>

        <Section
          title="Prakiraan beban listrik Jerman"
          id="judul-prakiraan"
          lead={
            <>
              Garis hitam adalah beban aktual 7 hari terakhir dalam data. Sesudah garis vertikal adalah prakiraan{" "}
              {MODEL_LABEL[model]} dengan pita interval {lvl}%. Waktu ditampilkan dalam waktu lokal Jerman.
            </>
          }
        >
          <Plot
            data={traces}
            layout={layout}
            height={380}
            theme={theme}
            label={`Grafik beban aktual dan prakiraan ${MODEL_LABEL[model]} ${view.hours.length} jam dengan interval ${lvl} persen`}
          />
          <h3 className="sub">Peluang beban melewati batas kapasitas, per jam</h3>
          <Plot
            data={exTrace}
            layout={exLayout}
            height={200}
            theme={theme}
            label="Grafik batang peluang beban melewati batas kapasitas per jam"
          />
          <p className="help">
            Batang abu-abu berarti peluangnya di luar kuantil tersimpan (di bawah 2,5% atau di atas 97,5%), sehingga
            hanya batasnya yang diketahui.
          </p>
          <details className="table-toggle">
            <summary>Lihat angka per jam</summary>
            <div className="table-wrap" tabIndex={0} role="region" aria-label="Tabel, bisa digulir">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Waktu (Jerman)</th>
                    <th scope="col" className="num">Prakiraan</th>
                    <th scope="col" className="num">Batas bawah {lvl}%</th>
                    <th scope="col" className="num">Batas atas {lvl}%</th>
                    <th scope="col" className="num">Peluang &gt; batas</th>
                  </tr>
                </thead>
                <tbody>
                  {view.hours.map((h, i) => (
                    <tr key={h}>
                      <td>{localTime(h)}</td>
                      <td className="num">{mw(view.point[i])}</td>
                      <td className="num">{mw(view.lo[i])}</td>
                      <td className="num">{mw(view.hi[i])}</td>
                      <td className="num">{exceedLabel(view.ex[i])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Section>

        <div className="provenance card">
          <p>
            <strong>Prakiraan tersimpan, bukan dihitung ulang di browser.</strong> Model {MODEL_LABEL[model]} versi{" "}
            <code>{info.version}</code>, dicocokkan pada seluruh data sampai {utcDate(meta.protocol.data_end_utc)} (UTC).
            Prakiraan dimulai {localTime(plan.origin_utc)} dan diekspor {meta.export_date}. Interval memakai residual uji
            mundur {info.conformal_window_days} hari terakhir.
          </p>
          <p>
            Skenario hanyalah transformasi <em>what-if</em> atas prakiraan tersimpan (perkalian dan perbandingan dengan
            batas), bukan estimasi sebab-akibat. Data OPSD berhenti 30 September 2020, jadi ini adalah prakiraan
            untuk minggu pertama Oktober 2020 yang tidak dapat dicek dengan data aktual di situs ini.
          </p>
        </div>
      </div>
    </div>
  );
}
