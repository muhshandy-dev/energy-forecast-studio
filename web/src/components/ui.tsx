import type { ReactNode } from "react";

export function Segmented<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="segmented">
      <legend>{label}</legend>
      <div className="segmented-row">
        {options.map((o) => (
          <label key={String(o.value)} className={o.value === value ? "on" : ""}>
            <input
              type="radio"
              name={label}
              checked={o.value === value}
              onChange={() => onChange(o.value)}
            />
            <span>{o.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function Stat({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note ? <div className="stat-note">{note}</div> : null}
    </div>
  );
}

export function Section({
  title,
  lead,
  children,
  id,
}: {
  title: string;
  lead?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section className="card" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {lead ? <p className="lead">{lead}</p> : null}
      {children}
    </section>
  );
}

export function Loading({ error }: { error?: string }) {
  if (error)
    return (
      <p className="notice notice-error" role="alert">
        Data gagal dimuat: {error}. Muat ulang halaman; jika tetap gagal, angka resmi ada di repositori
        GitHub (reports/results.json).
      </p>
    );
  return (
    <p className="loading" aria-live="polite">
      Memuat data…
    </p>
  );
}

export function SwatchLine({ color, dash }: { color: string; dash?: string }) {
  return (
    <svg width="22" height="10" aria-hidden="true" className="swatch">
      <line
        x1="1"
        y1="5"
        x2="21"
        y2="5"
        stroke={color}
        strokeWidth="2.5"
        strokeDasharray={dash === "dash" ? "6 3" : dash === "dot" ? "2 3" : undefined}
        strokeLinecap="round"
      />
    </svg>
  );
}
