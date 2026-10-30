export type ModelName = "ensemble" | "lightgbm" | "mstl_ets" | "snaive168" | "snaive24";

export type PointBlock = { mae: number; mase: number; rmse: number; mape: number; bias: number };
export type WeekBlock = PointBlock & {
  mae_ci95: [number, number];
  mae_minus_snaive168: number;
  mae_minus_snaive168_ci95: [number, number];
  skill_vs_snaive168: number;
};
export type IntervalLevel = {
  coverage: number;
  coverage_day_ahead: number;
  mean_width: number;
  interval_score: number;
};
export type ModelMetrics = {
  day_ahead: PointBlock;
  week_ahead: WeekBlock & { mae_minus_lightgbm?: number; mae_minus_lightgbm_ci95?: [number, number] };
  interval: { n_origins_with_interval: number; "80": IntervalLevel; "95": IntervalLevel };
};
export type PeriodMetrics = { n_origins: number } & Record<ModelName, ModelMetrics>;
export type PeriodName = "validation" | "test" | "test_2019" | "test_2020";

export type MetricsFile = {
  metrics: Record<PeriodName, PeriodMetrics>;
  per_horizon_test: Record<ModelName, { mae: number[]; coverage80: number[]; coverage95: number[] }>;
  selection: {
    criterion_point: string;
    criterion_interval: string;
    mstl_ets: { params: Record<string, unknown>; val_mae_week_ahead: number }[];
    lightgbm: { params: Record<string, unknown>; val_mae_week_ahead: number }[];
    ensemble?: {
      day: number;
      weight_lightgbm: number;
      val_mae: number;
      val_mae_lightgbm_only: number;
      val_mae_mstl_only: number;
    }[];
    conformal_window: Record<
      ModelName,
      { window_days: number; mode?: "absolute" | "relative"; mean_interval_score: number }[]
    >;
  };
};

export type MetaFile = {
  dev_data: boolean;
  source: { id: string; name: string; license: string; url: string; sha256: Record<string, string> };
  data_quality: Record<string, number | string>;
  protocol: {
    horizon_h: number;
    day_ahead_h: number;
    warmup_origins: [string, string];
    validation_origins: [string, string];
    test_origins: [string, string];
    data_end_utc: string;
    mase_scale_mw: number;
    mase_scale_definition: string;
    interval_method: string;
    interval_levels: number[];
    version?: string;
    bootstrap: { resamples: number; block_days: number; seed: number };
  };
  models: Record<
    ModelName,
    {
      params: Record<string, unknown>;
      version: string;
      conformal_window_days: number;
      conformal_residual?: "absolute" | "relative";
    }
  >;
  environment: Record<string, string>;
  export_date: string;
};

export type PlanningFile = {
  origin_utc: string;
  hours_utc: string[];
  quantile_probs: number[];
  history_utc_start: string;
  history_mw: number[];
  models: Record<ModelName, { point_mw: number[]; quantiles_mw: number[][] }>;
};

export type ReplayFile = {
  origins_utc: string[];
  actual_mw: number[][];
  levels: number[];
  models: Record<ModelName, { point_mw: number[][]; bounds_mw: number[][][] }>;
};

export type WorstOrigin = {
  origin: string;
  mae: number;
  bias: number;
  holiday_hours: number;
  special_hours: number;
};
export type ErrorsFile = {
  by_model: Record<
    ModelName,
    {
      worst_origins: WorstOrigin[];
      mae_holiday_hours: number | null;
      mae_normal_hours: number;
      mae_special_hours: number | null;
      bias_by_local_hour: number[];
      mae_by_local_hour: number[];
      bias_by_dow: number[];
      mae_by_dow: number[];
    }
  >;
  weekly_mae: { week_start: string[] } & Record<ModelName, number[]>;
  dow_labels: string[];
};

export const MODEL_ORDER: ModelName[] = ["ensemble", "lightgbm", "mstl_ets", "snaive168", "snaive24"];

/** Model yang ada di berkas data (hasil v1 tidak punya model gabungan). */
export function modelsIn(rec: object): ModelName[] {
  return MODEL_ORDER.filter((m) => m in rec);
}

/**
 * Model untuk grafik banyak garis. Bila ada model gabungan, LightGBM (komponennya) tidak
 * digambar bersamanya: kurvanya hampir berimpit dan warna biru-ungu sulit dibedakan.
 * Angka LightGBM tetap ada di tabel.
 */
export function chartModels(rec: object): ModelName[] {
  const all = modelsIn(rec);
  return all.includes("ensemble") ? all.filter((m) => m !== "lightgbm") : all;
}

/** Model utama: gabungan bila tersedia, selain itu LightGBM. */
export function headlineModel(rec: object): ModelName {
  return "ensemble" in rec ? "ensemble" : "lightgbm";
}

export const MODEL_LABEL: Record<ModelName, string> = {
  ensemble: "Gabungan",
  lightgbm: "LightGBM",
  mstl_ets: "MSTL + ETS",
  snaive168: "Naive mingguan",
  snaive24: "Naive harian",
};

export const MODEL_KIND: Record<ModelName, string> = {
  ensemble: "LightGBM + MSTL + ETS, bobot per hari",
  lightgbm: "Machine learning",
  mstl_ets: "Statistik (statsmodels)",
  snaive168: "Baseline: minggu lalu, jam yang sama",
  snaive24: "Baseline: kemarin, jam yang sama",
};
