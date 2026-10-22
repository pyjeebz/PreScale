/*
 * PreScale's own capacity run, which draws the footer wordmark: on prescale.dev,
 * or (as Vercel doesn't allow load tests on our plan) a local build of the dashboard.
 * Written by `node scripts/dogfood.mjs <result.json> [report-url]` from a real
 * run; null until one exists, and the footer keeps its static wordmark.
 */
export type DogfoodRun = {
  host: string;
  measuredAt: string;
  report: string | null;
  stages: Array<{ users: number; p95: number }>;
};

export const DOGFOOD: DogfoodRun | null = {
  "host": "a local build of prescale.dev/dashboard",
  "measuredAt": "2026-10-22T17:30:13Z",
  "report": null,
  "stages": [
    {
      "users": 1,
      "p95": 15
    },
    {
      "users": 2,
      "p95": 24
    },
    {
      "users": 5,
      "p95": 58
    },
    {
      "users": 10,
      "p95": 168
    },
    {
      "users": 20,
      "p95": 474
    },
    {
      "users": 30,
      "p95": 681
    },
    {
      "users": 50,
      "p95": 1010
    },
    {
      "users": 75,
      "p95": 1737
    },
    {
      "users": 100,
      "p95": 2594
    }
  ]
};
