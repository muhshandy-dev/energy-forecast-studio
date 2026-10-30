import { describe, expect, it } from "vitest";
import vectors from "./fixtures/scenario_vectors.json";
import {
  applyShift,
  exceedance,
  exceedanceByHour,
  expectedHoursAbove,
  intervalIndices,
  scaleFactor,
} from "../src/lib/scenario";

describe("skenario", () => {
  it("sama dengan implementasi Python pada vektor bersama", () => {
    for (const c of vectors.cases) {
      const f = scaleFactor(c.shift_pct);
      const r = exceedance(vectors.probs, c.quantiles.map((q) => q * f), c.capacity);
      expect(r.bound).toBe(c.bound);
      expect(r.p).toBeCloseTo(c.p, 12);
    }
  });

  it("interpolasi linear dan batas di luar grid", () => {
    const probs = [0.1, 0.5, 0.9];
    const q = [100, 200, 300];
    expect(exceedance(probs, q, 150).p).toBeCloseTo(0.7, 12);
    expect(exceedance(probs, q, 50)).toEqual({ p: 0.9, bound: "atLeast" });
    expect(exceedance(probs, q, 300).bound).toBe("atMost");
  });

  it("geser level mengalikan nilai dan menolak <= -100%", () => {
    expect(applyShift([100, 200], 5)).toEqual([105, 210]);
    expect(() => scaleFactor(-100)).toThrow();
  });

  it("perkiraan jam di atas batas berupa rentang bila ada batas", () => {
    const probs = [0.1, 0.5, 0.9];
    const grid = [
      [100, 100],
      [200, 200],
      [300, 300],
    ];
    const ex = exceedanceByHour(probs, grid, 150, 0, 2);
    expect(expectedHoursAbove(ex)).toEqual({ low: 1.4, high: 1.4 });
    const ex2 = exceedanceByHour(probs, grid, 50, 0, 2);
    expect(expectedHoursAbove(ex2)).toEqual({ low: 1.8, high: 2 });
  });

  it("indeks interval sentral", () => {
    const probs = [0.025, 0.05, 0.1, 0.5, 0.9, 0.95, 0.975];
    expect(intervalIndices(probs, 0.8)).toEqual([2, 4]);
    expect(intervalIndices(probs, 0.95)).toEqual([0, 6]);
    expect(() => intervalIndices(probs, 0.5)).toThrow();
  });
});
