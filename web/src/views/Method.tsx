import { Loading, Section } from "../components/ui";
import { loadMetrics } from "../lib/data";
import { num0, plainDate } from "../lib/format";
import { MODEL_KIND, MODEL_LABEL, MODEL_ORDER, type MetaFile } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const REPO = "https://github.com/muhshandy-dev/energy-forecast-studio";

function params(p: Record<string, unknown>): string {
  return Object.entries(p)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("/") : String(v)}`)
    .join(", ");
}

export function Method({ meta }: { meta: MetaFile }) {
  const { data, error } = useAsync(loadMetrics);
  const pr = meta.protocol;
  const q = meta.data_quality;
  return (
    <div className="stack">
      <Section title="Data" id="judul-data">
        <dl className="facts">
          <dt>Sumber</dt>
          <dd>
            {meta.source.name}
            {meta.dev_data ? " (data uji coba, bukan hasil resmi)" : ""}
          </dd>
          <dt>Variabel</dt>
          <dd>Beban listrik aktual Jerman per jam (MW), dilaporkan ENTSO-E Transparency Platform.</dd>
          <dt>Lisensi</dt>
          <dd>{meta.source.license}. Atribusi: Open Power System Data (2020), Data Package Time series.</dd>
          <dt>Rentang</dt>
          <dd>
            {q.start_utc} sampai {pr.data_end_utc} (UTC), {num0(Number(q.n_hours))} jam
          </dd>
          <dt>Kualitas</dt>
          <dd>
            {q.n_missing_raw} jam kosong di data mentah, {q.n_interpolated} diisi interpolasi linear (celah maksimal{" "}
            {q.max_interpolated_gap_h} jam), {q.n_duplicates_dropped} duplikat dibuang. Celah lebih panjang akan
            menghentikan pipeline.
          </dd>
          <dt>Sidik jari berkas</dt>
          <dd>
            {Object.entries(meta.source.sha256).map(([k, v]) => (
              <div key={k}>
                <code>{k}</code> SHA-256 <code className="hash">{v}</code>
              </div>
            ))}
          </dd>
        </dl>
      </Section>

      <Section title="Protokol evaluasi" id="judul-protokol">
        <ol className="timeline">
          <li>
            <strong>Latih awal</strong> 2015–2017. Juga dipakai untuk skala MASE: {num0(pr.mase_scale_mw)} MW.
          </li>
          <li>
            <strong>Pemanasan</strong> {plainDate(pr.warmup_origins[0])} – {plainDate(pr.warmup_origins[1])}: hanya
            mengumpulkan residual untuk interval, tidak dinilai.
          </li>
          <li>
            <strong>Validasi</strong> {plainDate(pr.validation_origins[0])} – {plainDate(pr.validation_origins[1])}:
            satu-satunya periode untuk memilih konfigurasi model dan jendela interval.
          </li>
          <li>
            <strong>Uji</strong> {plainDate(pr.test_origins[0])} – {plainDate(pr.test_origins[1])}: dijalankan sekali
            dengan konfigurasi yang sudah dikunci.
          </li>
        </ol>
        <p>
          Setiap hari pukul 00:00 UTC (origin), model membuat prakiraan {pr.horizon_h} jam ke depan hanya dari data
          sebelum origin (rolling origin, jendela melebar). Model statistik dicocokkan ulang di setiap origin; LightGBM
          dilatih ulang setiap Senin. Tes otomatis memastikan mengubah data sesudah origin tidak mengubah prakiraan.
        </p>
      </Section>

      <Section title="Model" id="judul-model">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">Jenis</th>
                <th scope="col">Konfigurasi terpilih</th>
                <th scope="col">Versi</th>
              </tr>
            </thead>
            <tbody>
              {MODEL_ORDER.map((m) => (
                <tr key={m}>
                  <th scope="row">{MODEL_LABEL[m]}</th>
                  <td>{MODEL_KIND[m]}</td>
                  <td>
                    <code>{params(meta.models[m].params)}</code>, jendela interval {meta.models[m].conformal_window_days}{" "}
                    hari
                  </td>
                  <td>
                    <code>{meta.models[m].version}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="plain">
          <li>
            <strong>Naive harian / mingguan:</strong> nilai jam yang sama kemarin atau minggu lalu. Baseline wajib; model
            lain baru berguna bila mengalahkannya.
          </li>
          <li>
            <strong>MSTL + ETS (statsmodels):</strong> deret beberapa minggu terakhir dipecah menjadi pola harian, pola
            mingguan, dan sisa. Pola diulang ke depan; tren + sisa diprakirakan dengan ETS teredam.
          </li>
          <li>
            <strong>LightGBM:</strong> satu model untuk semua horizon dengan fitur lag 168/336/504 jam, level 24 dan 168
            jam terakhir, jam, hari, libur nasional, hari kejepit, dan musim. Target dinormalkan terhadap rata-rata 7
            hari terakhir agar tahan terhadap perubahan level.
          </li>
        </ul>
        {data ? (
          <details className="table-toggle">
            <summary>Hasil seleksi di validasi 2018</summary>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Kandidat</th>
                    <th scope="col" className="num">MAE 7 hari validasi</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.selection.mstl_ets.map((r) => ["MSTL + ETS", r] as const), ...data.selection.lightgbm.map((r) => ["LightGBM", r] as const)].map(
                    ([name, r], i) => (
                      <tr key={i}>
                        <td>
                          {name} <code>{params(r.params)}</code>
                        </td>
                        <td className="num">{num0(r.val_mae_week_ahead)} MW</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </details>
        ) : (
          <Loading error={error} />
        )}
      </Section>

      <Section title="Interval dan metrik" id="judul-metrik">
        <ul className="plain">
          <li>
            <strong>Interval konformal bergulir:</strong> untuk setiap jam ke depan, batas diambil dari kuantil galat model
            yang sama pada origin-origin terakhir yang hasilnya sudah diketahui. Lebar jendela dipilih di validasi. Cara
            ini tidak menjamin coverage untuk deret waktu, jadi coverage diukur, bukan diasumsikan.
          </li>
          <li>
            <strong>MAE:</strong> rata-rata selisih absolut (MW). <strong>MASE:</strong> MAE dibagi galat naive mingguan
            di data latih; di bawah 1 berarti lebih baik dari skala itu.
          </li>
          <li>
            <strong>Coverage:</strong> persentase jam ketika beban aktual ada di dalam interval.{" "}
            <strong>Interval score</strong> menghukum interval yang lebar dan yang meleset.
          </li>
          <li>
            <strong>Interval kepercayaan:</strong> bootstrap blok {pr.bootstrap.block_days} hari, {num0(pr.bootstrap.resamples)} ulangan,
            seed {pr.bootstrap.seed}.
          </li>
        </ul>
      </Section>

      <Section title="Batas klaim" id="judul-batas">
        <ul className="plain">
          <li>Satu negara (Jerman), satu variabel; hasil tidak otomatis berlaku untuk jaringan lain, termasuk Indonesia.</li>
          <li>Tanpa data cuaca. Skenario suhu sengaja tidak dibuat karena tidak ada model yang mendukungnya.</li>
          <li>Skenario di situs ini adalah transformasi what-if atas prakiraan tersimpan, bukan simulasi sebab-akibat.</li>
          <li>Data OPSD berhenti 30 September 2020; situs ini tidak memprakirakan beban hari ini.</li>
          <li>Model tidak dijalankan di browser. Semua angka dihitung offline lalu disimpan sebagai berkas statis.</li>
        </ul>
        <p>
          Kode, tes, dan cara reproduksi: <a href={REPO}>{REPO.replace("https://", "")}</a>. Lingkungan:{" "}
          {Object.entries(meta.environment)
            .map(([k, v]) => `${k} ${v}`)
            .join(", ")}
          .
        </p>
      </Section>
    </div>
  );
}
