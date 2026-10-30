import type { Config, Layout, Trace } from "plotly.js-basic-dist-min";
import { useEffect, useRef, useState } from "react";
import { token } from "../lib/theme";

type Props = {
  data: Trace[];
  layout?: Layout;
  height?: number;
  /** Ringkasan teks untuk pembaca layar; grafik selalu punya tabel/teks pendamping. */
  label: string;
  theme: string;
};

let plotlyPromise: Promise<typeof import("plotly.js-basic-dist-min").default> | null = null;
const ID_LOCALE = {
  moduleType: "locale",
  name: "id",
  dictionary: {},
  format: {
    days: ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"],
    shortDays: ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"],
    months: [
      "Januari", "Februari", "Maret", "April", "Mei", "Juni",
      "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ],
    shortMonths: ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
    date: "%d/%m/%Y",
    decimal: ",",
    thousands: ".",
  },
};

const loadPlotly = () => {
  plotlyPromise ??= import("plotly.js-basic-dist-min").then((m) => {
    m.default.register(ID_LOCALE);
    return m.default;
  });
  return plotlyPromise;
};

export function baseLayout(height: number): Layout {
  const ink2 = token("--text-secondary");
  const muted = token("--text-muted");
  const grid = token("--grid");
  const axis = token("--axis");
  const font = getComputedStyle(document.body).fontFamily;
  return {
    height,
    margin: { l: 64, r: 16, t: 12, b: 44 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: font, size: 12, color: ink2 },
    hovermode: "x unified",
    hoverlabel: {
      bgcolor: token("--surface-raised"),
      bordercolor: token("--border-strong"),
      font: { family: font, size: 12, color: token("--text-primary") },
    },
    showlegend: true,
    legend: { orientation: "h", x: 0, y: 1.02, yanchor: "bottom", font: { size: 12, color: ink2 } },
    xaxis: {
      gridcolor: grid,
      linecolor: axis,
      tickcolor: axis,
      tickfont: { color: muted },
      zeroline: false,
      showspikes: true,
      spikemode: "across",
      spikethickness: 1,
      spikecolor: axis,
      spikedash: "solid",
    },
    yaxis: {
      gridcolor: grid,
      linecolor: axis,
      tickfont: { color: muted },
      zeroline: false,
      separatethousands: true,
      tickformat: ",.0f",
    },
    separators: ",.",
  };
}

const CONFIG: Config = { displayModeBar: false, responsive: true, locale: "id" };

export function Plot({ data, layout, height = 360, label, theme }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const el = ref.current;
    if (!el) return;
    loadPlotly()
      .then((Plotly) => {
        if (!alive) return;
        const base = baseLayout(height);
        const merged: Layout = {
          ...base,
          ...layout,
          xaxis: { ...(base.xaxis as object), ...((layout?.xaxis as object) ?? {}) },
          yaxis: { ...(base.yaxis as object), ...((layout?.yaxis as object) ?? {}) },
        };
        return Plotly.react(el, data, merged, CONFIG).then(() => {
          if (alive) el.dataset.plot = "ready";
        });
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [data, layout, height, theme]);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      loadPlotly().then((Plotly) => {
        if (el.isConnected && el.querySelector(".plot-container")) Plotly.Plots.resize(el);
      });
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      loadPlotly().then((Plotly) => Plotly.purge(el));
    };
  }, []);

  return (
    <figure className="plot" aria-label={label}>
      {failed ? (
        <p className="plot-fallback">Grafik gagal dimuat. Angka yang sama tersedia di tabel.</p>
      ) : (
        <div ref={ref} style={{ minHeight: height }} role="img" aria-label={label} />
      )}
    </figure>
  );
}
