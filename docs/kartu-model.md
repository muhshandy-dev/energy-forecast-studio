# Kartu model

## Tujuan

Prakiraan beban listrik Jerman per jam, 1 sampai 168 jam ke depan, dengan interval prediksi 80% dan
95%, untuk mendukung perencanaan (berapa beban puncak, seberapa mungkin melewati batas kapasitas).
Bukan sistem operasional: tidak ada data cuaca, tidak ada pembaruan otomatis, data berhenti 2020.

## Model

| Model | Jenis | Ringkasan | Refit |
|---|---|---|---|
| Naive harian | baseline | nilai jam yang sama kemarin (m = 24) | tidak perlu |
| Naive mingguan | baseline, acuan | nilai jam yang sama minggu lalu (m = 168) | tidak perlu |
| MSTL + ETS | statistik (statsmodels) | MSTL (musim 24 dan 168 jam) pada jendela N minggu terakhir; pola musim diulang; tren + sisa diprakirakan ETS(A, Ad, N) atau ETS(A, N, N); opsi penyesuaian kalender (lihat bawah) | setiap origin |
| LightGBM | machine learning | satu model multi-horizon langsung; target = beban / rata-rata 168 jam terakhir; fitur: h, jam/hari lokal, libur nasional, hari kejepit, 24–31 Des, musim (sin/cos), lag 168/336/504 jam, naive harian, nilai terakhir, rata-rata 24 jam, level 168 jam | setiap Senin, jendela melebar |
| Gabungan (v2) | kombinasi | w_d × LightGBM + (1 − w_d) × MSTL + ETS, satu bobot w_d per hari horizon (hari ke-1 sampai ke-7) | mengikuti komponennya |

Konfigurasi dipilih hanya dengan MAE 7 hari di validasi 2018 (protokol v2):

- MSTL + ETS: jendela {4, 8, 12} minggu × tren ETS {teredam, tanpa tren} × penyesuaian kalender
  {tidak, ya} (12 kandidat; grid v1 termasuk di dalamnya).
- LightGBM: `num_leaves` {31, 127} × objektif {L2, L1} (600 pohon, laju 0,05, `min_child_samples`
  100) ditambah dua kandidat v2: 255 daun dengan `min_child_samples` 50, dan 127 daun dengan 1.200
  pohon laju 0,03. Seed tetap, `deterministic=True`.
- Gabungan: bobot per hari dari grid 0; 0,05; ...; 1 yang meminimalkan MAE validasi hari itu.

**Penyesuaian kalender MSTL + ETS.** Hari khusus = libur nasional, 24 sampai 31 Desember dan 1
Januari, serta hari kejepit. Sebelum MSTL, jam hari khusus di riwayat diganti nilai jam yang sama
seminggu sebelumnya (berantai bila minggu itu juga khusus), sehingga pola musim tidak tercemar
libur. Sesudah prakiraan, jam hari khusus dikalikan faktor = median (beban aktual / beban bersih)
per tipe hari dan jam lokal dari seluruh riwayat sebelum origin (minimal 3 contoh, selain itu 1).
Semuanya hanya membaca data sebelum origin dan diuji oleh tes kebocoran.

Fitur LightGBM "bersih libur" juga dicoba di validasi selama pengembangan dan tidak membantu
(MAE validasi sedikit lebih buruk), jadi tidak masuk grid.
Pilihan akhir tercatat di `reports/results.json` (`models`, `selection`) dan di
[laporan-evaluasi.md](laporan-evaluasi.md).

## Interval prediksi

Konformal bergulir per horizon: batas = prakiraan + kuantil residual model yang sama dari origin
dalam W hari terakhir yang 168 jam aktualnya sudah teramati saat origin. Residual horizon h±3 jam
digabung. Dua jenis residual: absolut (y − ŷ) atau relatif ((y − ŷ) / ŷ, lalu dikalikan prakiraan
origin target sehingga lebar mengikuti level beban). W ∈ {28, 56, 91, 182, 364} hari × jenis residual
dipilih per model dengan rerata interval score 80% dan 95% di validasi (v1: W ∈ {28, 56, 91}, absolut;
pilihan v1 jatuh di batas grid 91 hari, karena itu grid diperluas). Origin pemanasan untuk residual
diperpanjang ke 1 Jan sampai 31 Des 2017 agar jendela 364 hari punya cukup riwayat.
Deret waktu tidak dapat dipertukarkan, jadi tidak ada jaminan coverage; coverage uji dilaporkan apa adanya.

## Evaluasi

Lihat [laporan-evaluasi.md](laporan-evaluasi.md) (dibuat otomatis dari hasil). Ringkasnya, laporan
memuat MAE 24 jam dan 7 hari, MASE, selisih terhadap naive mingguan dengan CI bootstrap blok, coverage
dan lebar interval, per periode (validasi, uji gabungan, uji 2019, uji 2020) serta analisis kegagalan.

## Versi protokol

- **v1** (hasil resmi pertama, run 41080532889): protokol dikunci sebelum periode uji pernah dilihat.
  Arsip: `reports/v1/` dan [laporan-evaluasi-v1.md](laporan-evaluasi-v1.md).
- **v2**: dirancang sesudah hasil uji v1 terlihat, sebagai respons atas kegagalan MSTL + ETS di hari
  libur. Semua pilihan v2 diambil dari validasi 2018, tetapi angka uji v2 bukan holdout buta.
  Data cuaca tidak ditambahkan: data cuaca OPSD berhenti 2019 dan suhu aktual sebagai fitur akan
  membocorkan informasi masa depan (yang tersedia saat prakiraan hanya prakiraan cuaca).

## Penggunaan yang tidak dianjurkan

- Menganggap skenario geser level sebagai simulasi kebijakan atau dampak cuaca.
- Memakai model untuk negara lain tanpa melatih ulang dan mengevaluasi ulang.
- Mengklaim coverage terjamin.

## Versi

`versi = <versi paket>+<8 karakter SHA-256 parameter>` per model, tercantum di situs (Studio dan
Metode) dan di `web/public/data/meta.json` bersama tanggal ekspor.
