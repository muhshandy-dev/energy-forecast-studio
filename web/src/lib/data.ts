import type { ErrorsFile, MetaFile, MetricsFile, PlanningFile, ReplayFile } from "./types";

const cache = new Map<string, Promise<unknown>>();

export function loadJson<T>(name: string): Promise<T> {
  if (!cache.has(name)) {
    const p = fetch(`data/${name}.json`, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`gagal memuat ${name}.json (${r.status})`);
      return r.json();
    });
    p.catch(() => cache.delete(name));
    cache.set(name, p);
  }
  return cache.get(name) as Promise<T>;
}

export const loadMeta = () => loadJson<MetaFile>("meta");
export const loadMetrics = () => loadJson<MetricsFile>("metrics");
export const loadPlanning = () => loadJson<PlanningFile>("planning");
export const loadReplay = () => loadJson<ReplayFile>("replay");
export const loadErrors = () => loadJson<ErrorsFile>("errors");
