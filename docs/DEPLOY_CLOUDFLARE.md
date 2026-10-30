# Deploy ke Cloudflare Pages

Situs statis hasil build Vite. Tanpa Functions, Workers, atau D1, jadi tidak ada server yang tidur.

1. Cloudflare dashboard → Workers & Pages → Create → Pages → **Connect to Git** →
   pilih `muhshandy-dev/energy-forecast-studio`.
2. Pengaturan build:
   - Project name: `energy-forecast-studio`
   - Production branch: `main`
   - Framework preset: None
   - Root directory: `web`
   - Build command: `npm ci && npm run build`
   - Build output directory: `dist`
   - Environment variable: `NODE_VERSION` = `22`
3. Simpan dan deploy. Alamatnya `https://energy-forecast-studio.pages.dev/` bila nama itu tersedia.
4. Opsional: Settings → Builds → matikan preview deployments untuk cabang selain `main` agar kuota
   500 build/bulan (dibagi semua proyek) tidak cepat habis.

`web/public/_headers` ikut tersalin ke `dist/` dan memasang CSP, HSTS, serta cache. Data website ada
di `web/public/data/` dan hanya berubah lewat `energy-forecast export-web` yang menolak data uji coba.
