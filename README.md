# Energy Forecast Studio

Studio perencanaan beban listrik: prakiraan beban Jerman per jam untuk 24 jam sampai 7 hari ke depan,
dengan interval prediksi, skenario permintaan, dan peluang beban melewati batas kapasitas.
Yang diuji bukan tampilannya, melainkan apakah model benar-benar lebih baik daripada tebakan
paling sederhana.

> **Status:** hasil resmi pada data Open Power System Data sudah ada (workflow Evaluasi OPSD,
> run 41080532889). Website live dan notebook Kaggle belum terverifikasi. Lihat [Hasil](#hasil).

## Masalah

Operator jaringan dan perencana energi butuh prakiraan beban per jam untuk beberapa hari ke depan,
lengkap dengan seberapa yakin prakiraan itu. Pertanyaan proyek ini:

1. Apakah model statistik (MSTL + ETS) dan model machine learning (LightGBM) mengalahkan
   *seasonal naive* (nilai jam yang sama kemarin atau minggu lalu)?
2. Apakah interval prediksi 80% dan 95% benar-benar memuat beban aktual sesering yang dijanjikan?

## Data

| | |
|---|---|
| Sumber | [Open Power System Data, Time series 2020-10-06](https://doi.org/10.25832/time_series/2020-10-06) |
| Kolom | `DE_load_actual_entsoe_transparency` (MW, per jam, UTC), berasal dari ENTSO-E Transparency Platform |
| Lisensi | CC BY 4.0 (atribusi: Open Power System Data. 2020. Data Package Time series. Version 2020-10-06) |
| Rentang | 2015-01-01 sampai 2020-09-30 |
| Integritas | SHA-256 dikunci di `data/manifest.json` setelah unduhan pertama; ketidakcocokan menghentikan pipeline |

Kartu data lengkap: [docs/kartu-data.md](docs/kartu-data.md).

## Protokol

- **Origin bergulir**: setiap hari pukul 00:00 UTC model membuat prakiraan 168 jam hanya dari data
  sebelum origin. Tes otomatis meracuni data sesudah origin dan memastikan prakiraan tidak berubah.
- **Pembagian waktu**: latih awal 2015 sampai 2017, pemanasan Okt sampai Des 2017 (hanya residual
  untuk interval), **validasi 2018** (satu-satunya tempat memilih konfigurasi), **uji 1 Jan 2019
  sampai 24 Sep 2020** (dijalankan sekali).
- **Model**: naive harian (m=24), naive mingguan (m=168), MSTL + ETS teredam (statsmodels, dicocokkan
  ulang di setiap origin), LightGBM multi-horizon langsung (fitur lag 168/336/504 jam, level terakhir,
  kalender, libur nasional Jerman; dilatih ulang setiap Senin).
- **Interval**: konformal bergulir per horizon dari residual model yang sama pada origin yang hasilnya
  sudah diketahui. Lebar jendela dipilih di validasi. Coverage diukur, tidak diasumsikan.
- **Metrik**: MAE, MASE (skala = MAE naive mingguan in-sample 2015 sampai 2017), RMSE, MAPE, bias,
  coverage 80% dan 95%, lebar interval, interval score. Interval kepercayaan 95% dengan bootstrap
  blok 7 hari.

Detail: [docs/laporan-evaluasi.md](docs/laporan-evaluasi.md) dan [docs/kartu-model.md](docs/kartu-model.md).

## Hasil

Periode uji 1 Jan 2019 sampai 24 Sep 2020 (633 origin harian, horizon 7 hari), data OPSD dengan
SHA-256 `6a7f2bc5…04c8`. MAE dalam MW; selisih negatif berarti lebih akurat daripada naive mingguan.

| Model | MAE 24 jam | MAE 7 hari | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% / 95% |
|---|---:|---:|---:|---:|---:|
| LightGBM | 1.191 | 1.341 | 0,59 | −1.060 (−1.354 s.d. −732) | 78,3% / 93,2% |
| MSTL + ETS | 1.959 | 2.541 | 1,12 | +140 (+3 s.d. +296) | 80,8% / 92,8% |
| Naive mingguan | 2.422 | 2.401 | 1,05 | acuan | 79,1% / 92,1% |
| Naive harian | 4.341 | 5.943 | 2,61 | +3.543 (+3.259 s.d. +3.851) | 81,4% / 96,1% |

- **LightGBM** mengalahkan naive mingguan dengan selang kepercayaan seluruhnya di bawah nol, juga
  pada validasi 2018 (dipilih di sana: num_leaves 127, objektif l2).
- **MSTL + ETS tidak mengalahkan naive mingguan untuk 7 hari** (selisih +140 MW, CI di atas nol).
  Untuk 24 jam ke depan ia lebih baik (1.959 vs 2.422 MW). Ini dilaporkan apa adanya.
- **Coverage**: interval 80% mendekati nominal; interval 95% sedikit di bawah nominal (92% sampai 93%)
  untuk semua model kecuali naive harian.
- **Kegagalan**: minggu terburuk LightGBM adalah awal April 2020 (Paskah bersamaan dengan pembatasan
  COVID). MSTL + ETS dan naive mingguan paling buruk di libur nasional (MAE jam libur sekitar
  11.600 sampai 12.600 MW vs sekitar 2.200 MW di jam biasa), karena keduanya tidak tahu kalender libur.

Laporan lengkap (validasi, uji 2019 dan 2020 terpisah, seleksi, analisis kegagalan):
[docs/laporan-evaluasi.md](docs/laporan-evaluasi.md). Hasil ini dibuat oleh workflow GitHub Actions
**Evaluasi OPSD** (`.github/workflows/evaluate.yml`) dan diperiksa ulang secara independen oleh
`tools/verify_published.py`.

### Catatan kejujuran tentang periode uji

Lingkungan pengembangan tidak bisa menjangkau host OPSD, jadi pipeline lengkap (termasuk periode
uji) diuji pada salinan ENTSO-E Jerman di HuggingFace, yang berasal dari sumber primer yang sama
dengan kolom OPSD. Artinya angka uji perkiraan sudah terlihat selama pengembangan. Untuk membatasi
dampaknya:

- Grid kandidat, fitur, jendela interval, dan pembagian waktu dikunci di commit pertama, sebelum
  pipeline pertama kali selesai berjalan.
- Satu-satunya perubahan sesudah itu adalah perbaikan bug satuan waktu (pandas 3) yang membuat
  semua interval kosong; tidak ada penyetelan model berdasarkan angka uji.
- Hasil dari salinan disimpan di `reports/dev/` (tidak di-commit) dan ditolak oleh `export-web`.

## Website

React + TypeScript + Plotly, statis di Cloudflare Pages (tanpa server, tanpa tidur saat idle).
Website hanya membaca prakiraan dan metrik tersimpan di `web/public/data/`; tidak ada model yang
dijalankan di browser.

- **Studio**: prakiraan 7 hari dari data terakhir, pilihan model, horizon, level interval, skenario
  permintaan (beban × (1 + s)), dan peluang melewati batas kapasitas per jam dari kuantil tersimpan.
- **Uji mundur**: prakiraan setiap Senin di periode uji dibandingkan dengan beban aktual.
- **Kinerja**, **Kesalahan**, **Metode & data**.

Skenario adalah transformasi what-if atas prakiraan tersimpan, bukan simulasi sebab-akibat.

## Reproduksi

```bash
make install            # Python >= 3.11
make data               # unduh OPSD + cek SHA-256
make run                # seleksi validasi, uji, prakiraan perencanaan (sekitar 40 menit, CPU)
make web-data verify    # ekspor JSON web + pemeriksaan independen angka
make test lint
make web-install web-test web-build
```

Tanpa mesin lokal: buka tab **Actions → Evaluasi OPSD → Run workflow**. Agar workflow bisa
membuka pull request, aktifkan *Settings → Actions → General → Allow GitHub Actions to create and
approve pull requests*. PR yang dibuat oleh workflow tidak memicu CI otomatis; tutup lalu buka lagi
PR itu, atau dorong commit kecil, untuk menjalankan CI.

Notebook Kaggle yang menjalankan langkah yang sama: [notebooks/kaggle_backtest.ipynb](notebooks/kaggle_backtest.ipynb).

## Batas klaim

- Satu negara, satu variabel, tanpa data cuaca. Hasil tidak otomatis berlaku untuk jaringan lain.
- Data berhenti 30 September 2020; situs tidak memprakirakan beban hari ini.
- Interval konformal untuk deret waktu tidak punya jaminan coverage; angka coverage dilaporkan apa adanya.

## Lisensi

Kode: MIT. Data: CC BY 4.0, Open Power System Data / ENTSO-E.
