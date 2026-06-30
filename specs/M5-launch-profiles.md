# M5 — Launch profiles + onboarding

Status: **spec / not started**
Depends on: M0 (Result envelope), M1 (think-time + the verdict/band).

## Goal

Map the abstract verdict to a launch the user actually cares about. "Survives ~90
concurrent users" is hard to act on; **"would survive a Product Hunt #1 launch"**
is a decision. M5 adds named **launch profiles** that pick a realistic peak
concurrency + traffic shape and frame the verdict against it, plus onboarding
polish.

## Launch profiles

A profile is a reasonable approximation of the concurrency a named scenario tends
to produce — honest, not exact. Each sets the ramp's **peak users** and a
**think-time** (real users pause between requests, so it's a more open-loop shape),
and carries a human **label**.

| name | label | ~peak users | think-time |
|---|---|---|---|
| `steady-10k-dau` | steady traffic (~10k daily users) | 25 | 1.0s |
| `product-hunt` | a Product Hunt #1 launch | 100 | 0.5s |
| `reddit` | a top Reddit post spike | 300 | 0.3s |
| `hn-frontpage` | a Hacker News front-page hug | 300 | 0.3s |
| `black-friday` | sustained Black Friday load | 500 | 0.5s |

(Numbers are anchors, tunable; the point is a relatable frame, not false precision.)

## Surface

- `prescale run <url> --profile product-hunt` — sets the ramp's peak users and
  think-time from the profile, records it, and frames the verdict against it.
- `prescale profiles` — list the available profiles + descriptions.

`--profile` drives peak users and think-time for the scenario (it's the point of
the profile); pass neither `-u` nor `--think-time` alongside it.

## Verdict framing (additive; `schema_version` stays 1)

A `profile` block on the Result, so `show`/MCP reuse it:

```jsonc
"profile": {
  "name": "product-hunt",
  "label": "a Product Hunt #1 launch",
  "peak_users": 100,
  "would_survive": true            // survives_users >= peak_users
}
```

Terminal readiness panel gains a line:
`Launch  ✅ a Product Hunt #1 launch: likely holds (peaks ~100, you survive ~150).`
or `🛑 … unlikely (peaks ~100, breaks at ~90).` The HTML report shows the same in
the verdict sub-line.

## Structure
- `profiles.py` — the `Profile` registry + `lookup(name)` + `scenario_block(profile,
  survives_users)`. Pure → fully unit-testable.
- `commands/profiles.py` — `prescale profiles` (list).
- `run` — `--profile` applies peak/think-time, records `config.profile`, injects the
  `profile` block before persisting (like `investigate` injects `investigation`).
- `render_terminal` / `report.py` — the scenario line.

## Build sub-steps
1. **M5.1** — `profiles.py` registry + `scenario_block` (pure).
2. **M5.2** — `run --profile NAME` (apply + record + inject block); terminal +
   HTML scenario line.
3. **M5.3** — `prescale profiles` command.
4. **M5.4** — schema `profile` block + `config.profile`; README profiles section;
   tests.

## Tests
- registry: `lookup` known/unknown; profiles have sane fields.
- `scenario_block`: would_survive true/false around the peak boundary.
- `run --profile` applies peak/think-time and injects the block (via the
  `transport=` seam / a saved Result).
- `prescale profiles` lists the names.

## Decisions (override any)
1. **The profile set + rough peak magnitudes** above (anchors, not promises).
2. **`would_survive = survives_users >= peak_users`** (point estimate; the band is
   still shown).
3. **`--profile` drives peak users + think-time** (don't combine with `-u` /
   `--think-time`).
4. **Onboarding = README profiles section + `prescale profiles`**; the marketing
   landing page is the founder's separate Figma track.
