# Laporan evaluasi

Dibuat otomatis oleh `tools/write_report.py` dari `reports/results.json`. Jangan diedit tangan.

- Protokol: v2
- Sumber data: Open Power System Data, Time series 2020-10-06 (CC BY 4.0)
- SHA-256: `time_series_60min_singleindex.csv` `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`
- Origin validasi: 2018-01-01 s.d. 2018-12-31; origin uji: 2019-01-01 s.d. 2020-09-24 (harian, 00:00 UTC, horizon 168 jam)
- Skala MASE: 2.276 MW (MAE in-sample seasonal naive m=168, 2015-01-01..2017-12-31 UTC)
- Interval: rolling split-conformal per horizon, pool +-3 h, residual absolut atau relatif; CI: bootstrap blok 7 hari, 2000 ulangan, seed 20261029

MAE dan lebar dalam MW. Selisih negatif berarti lebih akurat daripada naive mingguan.

## Validasi 2018 (365 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gabungan | 1.092 | 1.353 (1.228–1.477) | 0,59 | −1.193 (−1.551 s.d. −754) | 77,7% | 94,9% | 3.998 |
| LightGBM | 1.231 | 1.397 (1.261–1.532) | 0,61 | −1.149 (−1.518 s.d. −702) | 77,4% | 94,7% | 4.125 |
| MSTL + ETS | 1.352 | 1.841 (1.601–2.043) | 0,81 | −705 (−1.009 s.d. −366) | 76,9% | 93,6% | 5.244 |
| Naive mingguan | 2.556 | 2.546 (2.067–2.935) | 1,12 | acuan | 78,1% | 94,9% | 6.483 |
| Naive harian | 4.608 | 6.241 (6.004–6.466) | 2,74 | +3.695 (+3.368 s.d. +4.053) | 80,7% | 96,5% | 22.095 |

## Uji 2019 s.d. Sep 2020 (633 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gabungan | 1.072 | 1.308 (1.219–1.404) | 0,57 | −1.093 (−1.378 s.d. −771) | 79,6% | 94,3% | 4.013 |
| LightGBM | 1.189 | 1.350 (1.251–1.453) | 0,59 | −1.051 (−1.342 s.d. −721) | 79,5% | 94,1% | 4.125 |
| MSTL + ETS | 1.348 | 1.768 (1.609–1.928) | 0,78 | −632 (−880 s.d. −353) | 81,1% | 95,6% | 5.619 |
| Naive mingguan | 2.422 | 2.401 (2.034–2.736) | 1,05 | acuan | 80,9% | 95,1% | 6.497 |
| Naive harian | 4.341 | 5.943 (5.765–6.130) | 2,61 | +3.543 (+3.259 s.d. +3.851) | 83,1% | 97,2% | 21.562 |

## Uji 2019 (365 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gabungan | 1.074 | 1.305 (1.206–1.407) | 0,57 | −1.251 (−1.647 s.d. −795) | 80,1% | 94,7% | 4.051 |
| LightGBM | 1.178 | 1.338 (1.242–1.440) | 0,59 | −1.218 (−1.607 s.d. −755) | 80,3% | 94,8% | 4.203 |
| MSTL + ETS | 1.368 | 1.828 (1.590–2.034) | 0,80 | −728 (−1.072 s.d. −371) | 79,8% | 94,5% | 5.558 |
| Naive mingguan | 2.558 | 2.556 (2.056–2.990) | 1,12 | acuan | 79,9% | 94,1% | 6.497 |
| Naive harian | 4.558 | 6.197 (5.942–6.459) | 2,72 | +3.641 (+3.289 s.d. +4.037) | 81,2% | 96,5% | 21.956 |

## Uji 2020 (Jan s.d. Sep) (268 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gabungan | 1.070 | 1.312 (1.143–1.503) | 0,58 | −878 (−1.192 s.d. −476) | 79,0% | 93,6% | 3.962 |
| LightGBM | 1.205 | 1.366 (1.180–1.583) | 0,60 | −823 (−1.143 s.d. −417) | 78,4% | 93,2% | 4.018 |
| MSTL + ETS | 1.321 | 1.687 (1.482–1.848) | 0,74 | −503 (−829 s.d. −132) | 82,7% | 97,2% | 5.702 |
| Naive mingguan | 2.235 | 2.189 (1.721–2.567) | 0,96 | acuan | 82,2% | 96,5% | 6.497 |
| Naive harian | 4.045 | 5.598 (5.387–5.772) | 2,46 | +3.409 (+3.040 s.d. +3.857) | 85,7% | 98,3% | 21.025 |

## Perbandingan dengan v1 (uji 2019 s.d. Sep 2020)

v1 adalah hasil resmi pertama dengan protokol yang dikunci sebelum uji pernah dilihat. v2 dirancang **sesudah** hasil uji v1 terlihat (terutama kegagalan MSTL + ETS di hari libur), walaupun semua pilihan v2 tetap diambil hanya dari validasi 2018. Karena itu kenaikan v2 di periode uji bukan estimasi holdout buta; angka validasi v2 di atas adalah pembanding yang lebih adil.

| Model | Versi | MAE 24 jam | MAE 7 hari | MASE 7 hari | Coverage 80% | Coverage 95% |
|---|---|---:|---:|---:|---:|---:|
| Gabungan | v2 | 1.072 | 1.308 | 0,57 | 79,6% | 94,3% |
| LightGBM | v1 | 1.191 | 1.341 | 0,59 | 78,3% | 93,2% |
| LightGBM | v2 | 1.189 | 1.350 | 0,59 | 79,5% | 94,1% |
| MSTL + ETS | v1 | 1.959 | 2.541 | 1,12 | 80,8% | 92,8% |
| MSTL + ETS | v2 | 1.348 | 1.768 | 0,78 | 81,1% | 95,6% |
| Naive mingguan | v1 | 2.422 | 2.401 | 1,05 | 79,1% | 92,1% |
| Naive mingguan | v2 | 2.422 | 2.401 | 1,05 | 80,9% | 95,1% |
| Naive harian | v1 | 4.341 | 5.943 | 2,61 | 81,4% | 96,1% |
| Naive harian | v2 | 4.341 | 5.943 | 2,61 | 83,1% | 97,2% |

## Seleksi di validasi

| Kandidat | MAE 7 hari validasi |
|---|---:|
| MSTL + ETS window_weeks=4, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.763 |
| MSTL + ETS window_weeks=8, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.612 |
| MSTL + ETS window_weeks=12, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.554 |
| MSTL + ETS window_weeks=4, periods=[24, 168], robust_stl=False, ets=A,N,N | 2.753 |
| MSTL + ETS window_weeks=8, periods=[24, 168], robust_stl=False, ets=A,N,N | 2.586 |
| MSTL + ETS window_weeks=12, periods=[24, 168], robust_stl=False, ets=A,N,N | 2.528 |
| MSTL + ETS window_weeks=4, periods=[24, 168], robust_stl=False, ets=A,Ad,N, calendar_adjust=True | 1.960 |
| MSTL + ETS window_weeks=8, periods=[24, 168], robust_stl=False, ets=A,Ad,N, calendar_adjust=True | 1.866 |
| MSTL + ETS window_weeks=12, periods=[24, 168], robust_stl=False, ets=A,Ad,N, calendar_adjust=True | 1.842 |
| MSTL + ETS window_weeks=4, periods=[24, 168], robust_stl=False, ets=A,N,N, calendar_adjust=True | 1.958 |
| MSTL + ETS window_weeks=8, periods=[24, 168], robust_stl=False, ets=A,N,N, calendar_adjust=True | 1.864 |
| MSTL + ETS window_weeks=12, periods=[24, 168], robust_stl=False, ets=A,N,N, calendar_adjust=True | 1.841 |
| LightGBM num_leaves=31, objective=l2, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.443 |
| LightGBM num_leaves=31, objective=l1, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.477 |
| LightGBM num_leaves=127, objective=l2, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.412 |
| LightGBM num_leaves=127, objective=l1, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.429 |
| LightGBM num_leaves=255, objective=l2, n_estimators=600, learning_rate=0.05, min_child_samples=50 | 1.397 |
| LightGBM num_leaves=127, objective=l2, n_estimators=1200, learning_rate=0.03, min_child_samples=100 | 1.404 |

Bobot gabungan per hari horizon (porsi LightGBM; sisanya MSTL + ETS), dipilih di validasi:

| Hari | Bobot LightGBM | MAE validasi gabungan | Hanya LightGBM | Hanya MSTL + ETS |
|---:|---:|---:|---:|---:|
| 1 | 0,60 | 1.092 | 1.231 | 1.352 |
| 2 | 0,75 | 1.281 | 1.346 | 1.715 |
| 3 | 0,80 | 1.365 | 1.403 | 1.890 |
| 4 | 0,85 | 1.399 | 1.425 | 1.934 |
| 5 | 0,90 | 1.419 | 1.437 | 1.993 |
| 6 | 0,90 | 1.456 | 1.470 | 2.011 |
| 7 | 0,90 | 1.459 | 1.471 | 1.997 |

Uji: selisih MAE 7 hari gabungan dikurangi LightGBM −42 MW (CI 95% −64 s.d. −22).

| Model | Jendela interval terpilih (hari) | Jenis residual |
|---|---:|---|
| Naive harian | 364 | absolut |
| Naive mingguan | 364 | absolut |
| MSTL + ETS | 364 | absolut |
| LightGBM | 364 | relatif |
| Gabungan | 364 | relatif |

## Analisis kegagalan (uji)

- **Gabungan**: MAE jam biasa 1.301, jam libur nasional 1.451, libur + 24–31 Des 1.506. Origin terburuk: 2020-04-06 (3.987), 2020-04-08 (3.655), 2020-04-09 (3.470), 2020-04-05 (3.367), 2020-04-07 (3.329).
- **LightGBM**: MAE jam biasa 1.345, jam libur nasional 1.479, libur + 24–31 Des 1.479. Origin terburuk: 2020-04-06 (4.474), 2020-04-08 (4.209), 2020-04-09 (3.974), 2020-04-07 (3.812), 2020-04-11 (3.729).
- **MSTL + ETS**: MAE jam biasa 1.722, jam libur nasional 2.547, libur + 24–31 Des 3.170. Origin terburuk: 2019-11-02 (6.515), 2019-01-07 (5.911), 2019-06-21 (5.747), 2019-12-27 (5.230), 2019-12-28 (5.182).
- **Naive mingguan**: MAE jam biasa 2.139, jam libur nasional 12.574, libur + 24–31 Des 10.366. Origin terburuk: 2019-12-21 (10.685), 2019-12-20 (10.628), 2019-12-22 (10.450), 2019-12-23 (10.333), 2019-01-02 (9.708).

## Lingkungan

python 3.12.15, numpy 2.5.4, pandas 3.0.6, statsmodels 0.15.0, lightgbm 4.7.0
