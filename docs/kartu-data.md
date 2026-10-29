# Kartu data

## Identitas

| | |
|---|---|
| Nama | Open Power System Data, Data Package Time series, versi 2020-10-06 |
| Berkas | `time_series_60min_singleindex.csv` |
| URL | https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv |
| DOI | https://doi.org/10.25832/time_series/2020-10-06 |
| Lisensi | CC BY 4.0 |
| Sumber asli | ENTSO-E Transparency Platform (actual total load) |
| Kolom yang dipakai | `utc_timestamp`, `DE_load_actual_entsoe_transparency` |
| Satuan | MW, rata-rata per jam |
| Rentang | 2015-01-01 sampai 2020-09-30 (UTC) |

Atribusi yang wajib dicantumkan: *Open Power System Data. 2020. Data Package Time series.
Version 2020-10-06. https://doi.org/10.25832/time_series/2020-10-06. (Primary data from various
sources, for a complete list see URL.)*

## Integritas

`energy-forecast data --source opsd --pin` menghitung SHA-256 berkas dan menyimpannya di
`data/manifest.json`. Unduhan berikutnya yang hash-nya berbeda menghentikan pipeline.

## Pembersihan

1. Baris diurutkan per `utc_timestamp`; duplikat stempel waktu dibuang (jumlahnya dicatat).
2. Deret disusun ulang ke grid per jam penuh di antara nilai valid pertama dan terakhir.
3. Celah sampai 3 jam diisi interpolasi linear waktu; celah lebih panjang atau nilai <= 0
   menghentikan pipeline. Jumlah jam kosong dan yang diinterpolasi tercatat di
   `reports/results.json` (`data_quality`) dan di halaman Metode.

## Batas dan risiko

- Satu wilayah (Jerman), beban total yang dilaporkan ke ENTSO-E; definisi beban ENTSO-E pernah
  berubah antarnegara dan antarperiode, sehingga level absolut tidak sepenuhnya sebanding lintas tahun.
- Tidak ada data cuaca. Model tidak tahu suhu, sehingga gelombang dingin atau panas hanya terlihat
  lewat lag beban.
- Periode uji mencakup guncangan permintaan musim semi 2020 (pembatasan COVID-19); periode itu
  dilaporkan terpisah (`test_2020`), bukan dibuang.
- Data berakhir 30 September 2020.

## Data pengembangan (tidak diterbitkan)

Selama host OPSD tidak bisa dijangkau dari lingkungan pengembangan, pipeline diuji dengan salinan
ENTSO-E Jerman di HuggingFace (`ken1711/DE_electricity_load-data`, tanpa lisensi tercantum). Hasilnya
disimpan di `reports/dev/` (diabaikan git) dan `energy-forecast export-web` menolak menerbitkannya.
