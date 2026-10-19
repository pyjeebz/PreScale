/*
 * PreScale's own capacity run on prescale.dev, which draws the footer wordmark.
 * Written by `node scripts/dogfood.mjs <result.json> [report-url]` from a real
 * run; null until one exists, and the footer keeps its static wordmark.
 */
export type DogfoodRun = {
  host: string;
  measuredAt: string;
  report: string | null;
  stages: Array<{ users: number; p95: number }>;
};

export const DOGFOOD: DogfoodRun | null = null;
