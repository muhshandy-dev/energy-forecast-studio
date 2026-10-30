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
| MSTL + ETS | statistik (statsmodels) | MSTL (musim 24 dan 168 jam) pada jendela N minggu terakhir; pola musim diulang; tren + sisa diprakirakan ETS(A, Ad, N) | setiap origin |
| LightGBM | machine learning | satu model multi-horizon langsung; target = beban / rata-rata 168 jam terakhir; fitur: h, jam/hari lokal, libur nasional, hari kejepit, 24–31 Des, musim (sin/cos), lag 168/336/504 jam, naive harian, nilai terakhir, rata-rata 24 jam, level 168 jam | setiap Senin, jendela melebar |

Konfigurasi dipilih hanya dengan MAE 7 hari di validasi 2018:
MSTL + ETS jendela {4, 8, 12} minggu; LightGBM `num_leaves` {31, 127} × objektif {L2, L1}
(600 pohon, laju belajar 0,05, `min_child_samples` 100, seed tetap, `deterministic=True`).
Pilihan akhir tercatat di `reports/results.json` (`models`, `selection`) dan di
[laporan-evaluasi.md](laporan-evaluasi.md).

## Interval prediksi

Konformal bergulir per horizon: batas = prakiraan + kuantil residual model yang sama dari origin
dalam W hari terakhir yang 168 jam aktualnya sudah teramati saat origin. Residual horizon h±3 jam
digabung. W ∈ {28, 56, 91} hari dipilih per model dengan rerata interval score 80% dan 95% di validasi.
Deret waktu tidak dapat dipertukarkan, jadi tidak ada jaminan coverage; coverage uji dilaporkan apa adanya.

## Evaluasi

Lihat [laporan-evaluasi.md](laporan-evaluasi.md) (dibuat otomatis dari hasil). Ringkasnya, laporan
memuat MAE 24 jam dan 7 hari, MASE, selisih terhadap naive mingguan dengan CI bootstrap blok, coverage
dan lebar interval, per periode (validasi, uji gabungan, uji 2019, uji 2020) serta analisis kegagalan.

## Penggunaan yang tidak dianjurkan

- Menganggap skenario geser level sebagai simulasi kebijakan atau dampak cuaca.
- Memakai model untuk negara lain tanpa melatih ulang dan mengevaluasi ulang.
- Mengklaim coverage terjamin.

## Versi

`versi = <versi paket>+<8 karakter SHA-256 parameter>` per model, tercantum di situs (Studio dan
Metode) dan di `web/public/data/meta.json` bersama tanggal ekspor.
