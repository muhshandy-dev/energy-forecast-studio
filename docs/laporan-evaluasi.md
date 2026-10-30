# Laporan evaluasi

Dibuat otomatis oleh `tools/write_report.py` dari `reports/results.json`. Jangan diedit tangan.

- Sumber data: Open Power System Data, Time series 2020-10-06 (CC BY 4.0)
- SHA-256: `time_series_60min_singleindex.csv` `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`
- Origin validasi: 2018-01-01 s.d. 2018-12-31; origin uji: 2019-01-01 s.d. 2020-09-24 (harian, 00:00 UTC, horizon 168 jam)
- Skala MASE: 2.276 MW (MAE in-sample seasonal naive m=168, 2015-01-01..2017-12-31 UTC)
- Interval: rolling split-conformal per horizon, pool +-3 h; CI: bootstrap blok 7 hari, 2000 ulangan, seed 20261029

MAE dan lebar dalam MW. Selisih negatif berarti lebih akurat daripada naive mingguan.

## Validasi 2018 (365 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LightGBM | 1.247 | 1.412 (1.273–1.548) | 0,62 | −1.134 (−1.503 s.d. −693) | 77,5% | 92,5% | 4.470 |
| MSTL + ETS | 1.959 | 2.554 (2.112–2.901) | 1,12 | +8 (−159 s.d. +190) | 77,5% | 92,0% | 7.746 |
| Naive mingguan | 2.556 | 2.546 (2.067–2.935) | 1,12 | acuan | 76,6% | 91,9% | 7.194 |
| Naive harian | 4.608 | 6.241 (6.004–6.466) | 2,74 | +3.695 (+3.368 s.d. +4.053) | 80,8% | 95,9% | 22.095 |

## Uji 2019 s.d. Sep 2020 (633 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LightGBM | 1.191 | 1.341 (1.243–1.445) | 0,59 | −1.060 (−1.354 s.d. −732) | 78,3% | 93,2% | 4.220 |
| MSTL + ETS | 1.959 | 2.541 (2.223–2.849) | 1,12 | +140 (+3 s.d. +296) | 80,8% | 92,8% | 8.115 |
| Naive mingguan | 2.422 | 2.401 (2.034–2.736) | 1,05 | acuan | 79,1% | 92,1% | 6.988 |
| Naive harian | 4.341 | 5.943 (5.765–6.130) | 2,61 | +3.543 (+3.259 s.d. +3.851) | 81,4% | 96,1% | 21.021 |

## Uji 2019 (365 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LightGBM | 1.180 | 1.333 (1.237–1.432) | 0,59 | −1.223 (−1.616 s.d. −760) | 78,6% | 93,6% | 4.116 |
| MSTL + ETS | 2.038 | 2.688 (2.243–3.092) | 1,18 | +133 (−32 s.d. +317) | 78,9% | 91,2% | 8.079 |
| Naive mingguan | 2.558 | 2.556 (2.056–2.990) | 1,12 | acuan | 78,5% | 91,2% | 6.876 |
| Naive harian | 4.558 | 6.197 (5.942–6.459) | 2,72 | +3.641 (+3.289 s.d. +4.037) | 81,1% | 95,8% | 21.901 |

## Uji 2020 (Jan s.d. Sep) (268 origin)

| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) | Coverage 80% | Coverage 95% | Lebar 80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LightGBM | 1.207 | 1.352 (1.162–1.578) | 0,59 | −838 (−1.160 s.d. −434) | 77,9% | 92,6% | 4.363 |
| MSTL + ETS | 1.852 | 2.340 (1.933–2.649) | 1,03 | +150 (−59 s.d. +388) | 83,4% | 95,0% | 8.164 |
| Naive mingguan | 2.235 | 2.189 (1.721–2.567) | 0,96 | acuan | 80,0% | 93,4% | 7.140 |
| Naive harian | 4.045 | 5.598 (5.387–5.772) | 2,46 | +3.409 (+3.040 s.d. +3.857) | 81,7% | 96,5% | 19.822 |

## Seleksi di validasi

| Kandidat | MAE 7 hari validasi |
|---|---:|
| MSTL + ETS window_weeks=4, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.763 |
| MSTL + ETS window_weeks=8, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.612 |
| MSTL + ETS window_weeks=12, periods=[24, 168], robust_stl=False, ets=A,Ad,N | 2.554 |
| LightGBM num_leaves=31, objective=l2, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.443 |
| LightGBM num_leaves=31, objective=l1, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.477 |
| LightGBM num_leaves=127, objective=l2, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.412 |
| LightGBM num_leaves=127, objective=l1, n_estimators=600, learning_rate=0.05, min_child_samples=100 | 1.429 |

| Model | Jendela interval terpilih (hari) |
|---|---:|
| Naive harian | 91 |
| Naive mingguan | 91 |
| MSTL + ETS | 91 |
| LightGBM | 91 |

## Analisis kegagalan (uji)

- **LightGBM**: MAE jam biasa 1.337, jam libur nasional 1.425, libur + 24–31 Des 1.446. Origin terburuk: 2020-04-06 (4.411), 2020-04-08 (4.251), 2020-04-09 (4.051), 2020-04-07 (3.819), 2020-04-05 (3.535).
- **MSTL + ETS**: MAE jam biasa 2.291, jam libur nasional 11.595, libur + 24–31 Des 10.151. Origin terburuk: 2019-04-23 (12.395), 2019-05-02 (10.784), 2019-12-22 (10.373), 2020-01-02 (10.225), 2019-06-11 (10.181).
- **Naive mingguan**: MAE jam biasa 2.139, jam libur nasional 12.574, libur + 24–31 Des 10.366. Origin terburuk: 2019-12-21 (10.685), 2019-12-20 (10.628), 2019-12-22 (10.450), 2019-12-23 (10.333), 2019-01-02 (9.708).

## Lingkungan

python 3.12.15, numpy 2.5.4, pandas 3.0.6, statsmodels 0.15.0, lightgbm 4.7.0
