import { useState } from "react";
import { Plot } from "../components/Plot";
import { Loading, Section, Segmented, SwatchLine } from "../components/ui";
import { modelColor, modelDash } from "../lib/colors";
import { loadErrors, loadMetrics } from "../lib/data";
import { num0, num2, pct, plainDate, signedMw } from "../lib/format";
import { token } from "../lib/theme";
import { MODEL_LABEL, chartModels, modelsIn, type MetaFile, type PeriodName } from "../lib/types";
import { useAsync } from "../lib/useAsync";
import { verdict } from "../lib/verdict";

const PERIODS: { value: PeriodName; label: string }[] = [
  { value: "test", label: "Uji 2019–2020" },
  { value: "test_2019", label: "Uji 2019" },
  { value: "test_2020", label: "Uji 2020" },
  { value: "validation", label: "Validasi 2018" },
];

export function Performance({ meta, theme }: { meta: MetaFile; theme: string }) {
  const { data, error } = useAsync(loadMetrics);
  const errs = useAsync(loadErrors);
  const [period, setPeriod] = useState<PeriodName>("test");
  const [level, setLevel] = useState<"80" | "95">("80");
  if (!data) return <Loading error={error} />;
  const p = data.metrics[period];
  const v = verdict(p);
  const hAxis = Array.from({ length: 168 }, (_, i) => i + 1);

  const maeTraces = chartModels(data.per_horizon_test).map((m) => ({
    x: hAxis,
    y: data.per_horizon_test[m].mae,
    name: MODEL_LABEL[m],
    mode: "lines",
    line: { color: modelColor(m), width: 2, dash: modelDash(m) },
    hovertemplate: `%{y:,.0f} MW<extra>${MODEL_LABEL[m]}</extra>`,
  }));
  const covKey = level === "80" ? "coverage80" : "coverage95";
  const covTraces = chartModels(data.per_horizon_test).map((m) => ({
    x: hAxis,
    y: data.per_horizon_test[m][covKey].map((c) => c * 100),
    name: MODEL_LABEL[m],
    mode: "lines",
    line: { color: modelColor(m), width: 2, dash: modelDash(m) },
    hovertemplate: `%{y:.1f}%<extra>${MODEL_LABEL[m]}</extra>`,
  }));
  const nominal = Number(level);
  const hLayout = (title: string, extra: Record<string, unknown> = {}) => ({
    hovermode: "x unified",
    xaxis: { title: { text: "Jam ke depan (h)", font: { size: 12 } }, tickvals: [1, 24, 48, 72, 96, 120, 144, 168] },
    yaxis: { title: { text: title, font: { size: 12 } }, ...extra },
  });

  return (
    <div className="stack">
      <Section title="Ringkasan metrik" id="judul-kinerja">
        <Segmented label="Periode" value={period} options={PERIODS} onChange={setPeriod} />
        <p className={`verdict verdict-${v.kind}`}>{v.text}</p>
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Tabel, bisa digulir">
          <table className="metrics">
            <caption>
              {p.n_origins} origin harian. MAE dalam MW; MASE = MAE dibagi {num0(meta.protocol.mase_scale_mw)} MW (galat
              naive mingguan di data latih 2015–2017). Rentang dalam kurung adalah interval kepercayaan 95% (bootstrap
              blok 7 hari).
            </caption>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col" className="num">MAE 24 jam</th>
                <th scope="col" className="num">MAE 7 hari</th>
                <th scope="col" className="num">MASE 7 hari</th>
                <th scope="col" className="num">Selisih vs naive mingguan</th>
                <th scope="col" className="num">Coverage 80%</th>
                <th scope="col" className="num">Coverage 95%</th>
                <th scope="col" className="num">Lebar 80%</th>
              </tr>
            </thead>
            <tbody>
              {modelsIn(p).map((m) => {
                const r = p[m];
                const w = r.week_ahead;
                return (
                  <tr key={m} className={m === v.model ? "best" : ""}>
                    <th scope="row">
                      <SwatchLine color={modelColor(m)} dash={modelDash(m)} /> {MODEL_LABEL[m]}
                    </th>
                    <td className="num">{num0(r.day_ahead.mae)}</td>
                    <td className="num">
                      {num0(w.mae)}
                      <small>
                        {" "}
                        ({num0(w.mae_ci95[0])}–{num0(w.mae_ci95[1])})
                      </small>
                    </td>
                    <td className="num">{num2(w.mase)}</td>
                    <td className="num">
                      {m === "snaive168" ? (
                        "acuan"
                      ) : (
                        <>
                          {signedMw(w.mae_minus_snaive168)}
                          <small>
                            {" "}
                            ({signedMw(w.mae_minus_snaive168_ci95[0])} s.d. {signedMw(w.mae_minus_snaive168_ci95[1])})
                          </small>
                        </>
                      )}
                    </td>
                    <td className="num">{pct(r.interval["80"].coverage)}</td>
                    <td className="num">{pct(r.interval["95"].coverage)}</td>
                    <td className="num">{num0(r.interval["80"].mean_width)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="help">
          Coverage adalah proporsi jam ketika beban aktual jatuh di dalam interval. Interval yang jujur punya coverage dekat
          targetnya (80% atau 95%); di bawah target berarti interval terlalu sempit.
        </p>
      </Section>

      <Section
        title="Galat bertambah seiring horizon"
        id="judul-horizon"
        lead="MAE pada periode uji untuk setiap jam ke depan. Garis putus-putus adalah baseline."
      >
        <Plot data={maeTraces} layout={hLayout("MAE (MW)")} height={320} theme={theme} label="Grafik MAE per jam ke depan untuk empat model" />
      </Section>

      <Section title="Apakah interval menepati janjinya?" id="judul-coverage">
        <Segmented
          label="Level interval"
          value={level}
          options={[
            { value: "80", label: "80%" },
            { value: "95", label: "95%" },
          ]}
          onChange={setLevel}
        />
        <Plot
          data={covTraces}
          height={300}
          theme={theme}
          layout={{
            ...hLayout("Coverage", { ticksuffix: "%", range: [Math.max(0, nominal - 40), 100] }),
            shapes: [
              {
                type: "line",
                xref: "paper",
                x0: 0,
                x1: 1,
                y0: nominal,
                y1: nominal,
                line: { color: token("--text-muted"), width: 1.5, dash: "dash" },
              },
            ],
            annotations: [
              {
                xref: "paper",
                x: 0,
                y: nominal,
                xanchor: "left",
                yanchor: "bottom",
                text: `target ${nominal}%`,
                showarrow: false,
                font: { size: 11, color: token("--text-muted") },
              },
            ],
          }}
          label={`Grafik coverage interval ${nominal} persen per jam ke depan`}
        />
      </Section>

      {errs.data ? (
        <Section
          title="Galat per minggu sepanjang periode uji"
          id="judul-mingguan"
          lead="Rata-rata MAE 7 hari dari origin dalam tiap minggu. Lonjakan biasanya terjadi di sekitar libur dan pada guncangan permintaan musim semi 2020."
        >
          <Plot
            data={chartModels(errs.data.weekly_mae)
              .filter((m) => m !== "snaive24")
              .map((m) => ({
              x: errs.data!.weekly_mae.week_start,
              y: errs.data!.weekly_mae[m],
              name: MODEL_LABEL[m],
              mode: "lines",
              line: { color: modelColor(m), width: 2, dash: modelDash(m) },
              hovertemplate: `%{y:,.0f} MW<extra>${MODEL_LABEL[m]}</extra>`,
            }))}
            layout={{ yaxis: { title: { text: "MAE (MW)", font: { size: 12 } } } }}
            height={300}
            theme={theme}
            label="Grafik MAE mingguan sepanjang periode uji"
          />
          <p className="help">
            Minggu pertama: {plainDate(errs.data.weekly_mae.week_start[0])}. Minggu terakhir:{" "}
            {plainDate(errs.data.weekly_mae.week_start[errs.data.weekly_mae.week_start.length - 1])}.
          </p>
        </Section>
      ) : null}
    </div>
  );
}
