declare module "plotly.js-basic-dist-min" {
  // Hanya bagian API yang dipakai situs ini.
  export type Datum = string | number | null;
  export type Trace = Record<string, unknown>;
  export type Layout = Record<string, unknown>;
  export type Config = Record<string, unknown>;
  const Plotly: {
    react(el: HTMLElement, data: Trace[], layout: Layout, config: Config): Promise<unknown>;
    purge(el: HTMLElement): void;
    Plots: { resize(el: HTMLElement): void };
  };
  export default Plotly;
}
