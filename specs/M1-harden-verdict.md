# M1 — Harden the verdict

Status: **spec / not started**
Depends on: M0 (the Result envelope carries the new confidence fields — additive,
so `schema_version` stays 1).

## Goal

Make the verdict **trustworthy**: reproducible, honest about uncertainty, and
based on realistic traffic. Today a single ~5s stage per level decides the
answer, so cold caches, JIT warmup, connection setup, and run-to-run noise can
swing it. A tool that draws conclusions is only worth anything if the
conclusions hold up — and M2 (MCP) and M3 (investigate) both broadcast this
verdict, so it has to be solid first.

## In scope

- A **warmup** (discarded) stage before measurement.
- A **confidence band** on the verdict, derived from the data: "survives ~90 (80–100)".
- Optional **run-to-run robustness** (`--repeat N`).
- Optional **think-time** for a more realistic (open-loop) arrival pattern.
- A **repeatability** guarantee: same target twice → consistent verdict.

## Out of scope (deferred)

- Weighted route mix → **M5** (pairs naturally with launch profiles).
- Distributed load / higher scale → non-goal.

## Schema (additive; `schema_version` stays 1)

- `verdict.confidence` — `{ "survives_low": int, "survives_high": int, "stable": bool }`:
  the band around `survives_users`, and whether the verdict is statistically stable.
- `config` gains `warmup` (bool), `repeat` (int), `think_time_s` (number).
- `stages[].samples` — optional, set when `--repeat > 1`.

Old consumers ignore unknown fields, so the version is unchanged.

## Design

### M1.1 — Warmup
A short discarded stage (default ~2s at a low level, e.g. 5 VUs) before the
measured ramp, so cold-start latency doesn't pollute the first measured level.
On by default; `--no-warmup` to skip. ~2s cost.

### M1.2 — Confidence band (within-run bootstrap, no extra wall-time)
The onset level is where p95 crosses the latency wall or the error rate crosses
the threshold — both estimated from the per-request samples already collected at
each level. Bootstrap-resample those samples to get a confidence interval on
p95 / error-rate per level, then propagate to the band of levels where the
crossing is uncertain → `survives_users (low–high)`. **Zero added runtime**; the
band reflects within-run sampling noise. A wide band flags the verdict as
not-`stable`, and the render says so instead of implying false precision.

### M1.3 — Optional run-to-run robustness
`--repeat N` (default 1) runs the whole ramp N times and folds run-to-run
variance (GC pauses, noisy neighbors, cache state) into the band. N× slower, so
opt-in — the default stays a single fast pass.

### M1.4 — Think-time
`--think-time SECONDS` (default 0) inserts a pause between each VU's requests,
modeling real users (a more open-loop arrival pattern) instead of the current
back-to-back closed loop. Default 0 = today's behavior; opt-in realism.

### M1.5 — Repeatability + docs
A test asserts the verdict is stable across two runs of the same synthetic
target (within the band). README/docs for the new flags.

## Render
`Scale readiness: ⚠️ Survives ~90 (80–100) concurrent users`, with the band shown
only when meaningful and a "verdict is stable / uncertain" note. The HTML report
shows the band on the Survives stat.

## Build sub-steps
1. **M1.1** warmup + `--no-warmup`
2. **M1.2** confidence band (bootstrap) → verdict + render + schema
3. **M1.3** `--repeat N`
4. **M1.4** `--think-time`
5. **M1.5** repeatability test + docs

## Decisions (override any)
1. **Confidence = within-run bootstrap by default** (keeps runs fast/zero-config);
   `--repeat N` adds run-to-run robustness for those who want it. (Alternative:
   always repeat the ramp — more robust but several-× slower for everyone.)
2. **Warmup on by default** (~2s), `--no-warmup` to skip.
3. **Weighted route mix deferred to M5;** M1's traffic realism is think-time only.
