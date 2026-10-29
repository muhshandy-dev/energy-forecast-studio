import { useState } from "react";
import { Plot } from "../components/Plot";
import { Loading, Section } from "../components/ui";
import { modelColor } from "../lib/colors";
import { loadErrors } from "../lib/data";
import { num0, plainDate, signedMw } from "../lib/format";
import { MODEL_LABEL, MODEL_ORDER, type ModelName } from "../lib/types";
import { useAsync } from "../lib/useAsync";

export function Errors({ theme }: { theme: string }) {
  const { data, error } = useAsync(loadErrors);
  const [model, setModel] = useState<ModelName>("lightgbm");
  if (!data) return <Loading error={error} />;
  const e = data.by_model[model];
  const color = modelColor(model);
  const hours = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);
  const barLayout = (title: string) => ({
    showlegend: false,
    hovermode: "closest",
    bargap: 0.25,
    yaxis: { title: { text: title, font: { size: 12 } }, zeroline: true },
  });

  return (
    <div className="stack">
      <Section
        title="Di mana model paling sering meleset?"
        id="judul-kesalahan"
        lead="Semua angka berasal dari periode uji (origin harian 2019 sampai September 2020). Pilih model untuk melihat pola galatnya."
      >
        <label className="select">
          <span>Model</span>
          <select value={model} onChange={(ev) => setModel(ev.target.value as ModelName)}>
            {MODEL_ORDER.map((m) => (
              <option key={m} value={m}>
                {MODEL_LABEL[m]}
              </option>
            ))}
          </select>
        </label>

        <div className="stats">
          <div className="stat">
            <div className="stat-label">MAE jam biasa</div>
            <div className="stat-value">{num0(e.mae_normal_hours)} MW</div>
          </div>
          <div className="stat">
            <div className="stat-label">MAE jam libur nasional</div>
            <div className="stat-value">{e.mae_holiday_hours == null ? "–" : `${num0(e.mae_holiday_hours)} MW`}</div>
          </div>
          <div className="stat">
            <div className="stat-label">MAE libur + 24–31 Des</div>
            <div className="stat-value">{e.mae_special_hours == null ? "–" : `${num0(e.mae_special_hours)} MW`}</div>
          </div>
        </div>

        <h3 className="sub">10 minggu prakiraan terburuk</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Origin</th>
                <th scope="col" className="num">MAE 7 hari</th>
                <th scope="col" className="num">Bias</th>
                <th scope="col" className="num">Jam libur di dalamnya</th>
              </tr>
            </thead>
            <tbody>
              {e.worst_origins.map((w) => (
                <tr key={w.origin}>
                  <td>{plainDate(w.origin)}</td>
                  <td className="num">{num0(w.mae)} MW</td>
                  <td className="num">{signedMw(w.bias)}</td>
                  <td className="num">{w.special_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="help">
          Bias positif berarti prakiraan terlalu tinggi. Origin yang berdekatan biasanya muncul bersama karena minggu
          prakiraannya tumpang tindih.
        </p>
      </Section>

      <Section title="Bias menurut jam (waktu lokal Jerman)" id="judul-bias-jam">
        <Plot
          data={[
            {
              x: hours,
              y: e.bias_by_local_hour,
              type: "bar",
              marker: { color },
              hovertemplate: "%{y:,.0f} MW<extra>Bias</extra>",
            },
          ]}
          layout={barLayout("Bias (MW)")}
          height={260}
          theme={theme}
          label={`Grafik bias ${MODEL_LABEL[model]} per jam lokal`}
        />
      </Section>

      <Section title="Galat menurut hari" id="judul-hari">
        <Plot
          data={[
            {
              x: data.dow_labels,
              y: e.mae_by_dow,
              type: "bar",
              marker: { color },
              hovertemplate: "%{y:,.0f} MW<extra>MAE</extra>",
            },
          ]}
          layout={barLayout("MAE (MW)")}
          height={260}
          theme={theme}
          label={`Grafik MAE ${MODEL_LABEL[model]} per hari dalam seminggu`}
        />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Hari</th>
                {data.dow_labels.map((d) => (
                  <th scope="col" key={d} className="num">
                    {d}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">MAE</th>
                {e.mae_by_dow.map((v, i) => (
                  <td className="num" key={i}>
                    {num0(v)}
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row">Bias</th>
                {e.bias_by_dow.map((v, i) => (
                  <td className="num" key={i}>
                    {signedMw(v)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
