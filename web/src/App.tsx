import { useEffect, useState } from "react";
import { Loading } from "./components/ui";
import { loadMeta } from "./lib/data";
import { utcDate } from "./lib/format";
import { useTheme, type ThemeChoice } from "./lib/theme";
import { useAsync } from "./lib/useAsync";
import { Errors } from "./views/Errors";
import { Method } from "./views/Method";
import { Performance } from "./views/Performance";
import { Replay } from "./views/Replay";
import { Studio } from "./views/Studio";

const TABS = [
  { id: "studio", label: "Studio" },
  { id: "uji-mundur", label: "Uji mundur" },
  { id: "kinerja", label: "Kinerja" },
  { id: "kesalahan", label: "Kesalahan" },
  { id: "metode", label: "Metode & data" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const PAGE_TITLE: Record<TabId, string> = {
  studio: "Studio perencanaan beban",
  "uji-mundur": "Uji mundur",
  kinerja: "Kinerja model",
  kesalahan: "Analisis kesalahan",
  metode: "Metode dan data",
};

function tabFromHash(): TabId {
  const h = window.location.hash.replace("#", "");
  return (TABS.find((t) => t.id === h)?.id ?? "studio") as TabId;
}

function Mark() {
  return (
    <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" className="mark">
      <rect width="32" height="32" rx="7" className="mark-bg" />
      <path d="M5 22 L11 16 L15 19 L21 11" className="mark-line" />
      <path d="M21 11 L27 8" className="mark-dash" />
      <circle cx="21" cy="11" r="2.6" className="mark-dot" />
    </svg>
  );
}

export function App() {
  const { data: meta, error } = useAsync(loadMeta);
  const { choice, setChoice, resolved } = useTheme();
  const [tab, setTab] = useState<TabId>(tabFromHash);

  useEffect(() => {
    const on = () => setTab(tabFromHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const go = (id: TabId) => {
    if (window.location.hash !== `#${id}`) window.history.pushState(null, "", `#${id}`);
    setTab(id);
  };

  const nextTheme: Record<ThemeChoice, ThemeChoice> = { system: "dark", dark: "light", light: "system" };
  const themeLabel: Record<ThemeChoice, string> = { system: "Tema: sistem", dark: "Tema: gelap", light: "Tema: terang" };

  return (
    <>
      <a className="skip" href="#isi">
        Lompat ke isi
      </a>
      <header className="topbar">
        <div className="brand">
          <Mark />
          <div>
            <div className="brand-name">Energy Forecast Studio</div>
            <div className="brand-sub">Prakiraan beban listrik Jerman per jam</div>
          </div>
        </div>
        <nav aria-label="Bagian situs">
          <ul className="tabs">
            {TABS.map((t) => (
              <li key={t.id}>
                <a
                  href={`#${t.id}`}
                  aria-current={tab === t.id ? "page" : undefined}
                  onClick={(e) => {
                    e.preventDefault();
                    go(t.id);
                  }}
                >
                  {t.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <button type="button" className="btn-ghost theme-btn" onClick={() => setChoice(nextTheme[choice])}>
          {themeLabel[choice]}
        </button>
      </header>

      {meta?.dev_data ? (
        <div className="dev-banner" role="note">
          Data uji coba: angka di halaman ini berasal dari salinan data pengembangan, bukan hasil resmi Open Power System
          Data.
        </div>
      ) : null}

      <main id="isi" tabIndex={-1}>
        {!meta ? (
          <Loading error={error} />
        ) : (
          <>
            <div className="page-head">
              <h1>{PAGE_TITLE[tab]}</h1>
              <p className="mode-label">
                Mode demo: prakiraan batch tersimpan · data sampai {utcDate(meta.protocol.data_end_utc)} (UTC) · diekspor{" "}
                {meta.export_date}
              </p>
            </div>
            {tab === "studio" && <Studio meta={meta} theme={resolved} />}
            {tab === "uji-mundur" && <Replay theme={resolved} />}
            {tab === "kinerja" && <Performance meta={meta} theme={resolved} />}
            {tab === "kesalahan" && <Errors theme={resolved} />}
            {tab === "metode" && <Method meta={meta} />}
          </>
        )}
      </main>
      <footer className="footer">
        <p>
          Data: Open Power System Data (CC BY 4.0), berasal dari ENTSO-E. Kode MIT.{" "}
          <a href="https://github.com/muhshandy-dev/energy-forecast-studio">GitHub</a>
        </p>
      </footer>
    </>
  );
}
