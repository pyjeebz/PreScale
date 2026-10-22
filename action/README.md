# PreScale capacity check (GitHub Action)

Load-tests every pull request, uploads the verdict to your PreScale dashboard,
and keeps one comment on the PR with the capacity change vs your baseline
branch, the route that breaks first, why, and the fix.

## Replica mode (recommended): no deploy, no host

The action builds the pull request in the job, starts it, tests it on localhost,
and stops it. No host is involved, so no host's load-testing rules apply and no
CDN shapes the result.

```yaml
# .github/workflows/capacity.yml
name: Capacity
on:
  pull_request:
  push:
    branches: [main]          # the baseline PRs compare against

jobs:
  capacity:
    runs-on: ubuntu-latest
    permissions:
      contents: read          # find the PR for the commit
      pull-requests: write    # the capacity comment
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - uses: pyjeebz/prescale/action@v1
        with:
          token: ${{ secrets.PRESCALE_TOKEN }}
          target: myapp.com
          app: npm run build && npm start      # tested at http://localhost:3000
          fail-on-regression: true
        env:
          # The app runs with these: point them at dev or staging, never production.
          DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}
```

Results say they were measured on a replica (no serverless cold starts). The
`app` command is never saved or uploaded.

## Testing a deployed staging URL

**Your host's rules come first.** Vercel only permits load testing on Enterprise
plans with prior notice, Netlify needs its express permission, and Cloudflare
blocks load tests unless arranged. On their deploys the action skips, says why on
the PR, and passes, unless you set `host-permission: true` because you have that
permission. Use it on staging you're allowed to load: your own servers, or a
host that permits load testing.

```yaml
on: deployment_status

jobs:
  capacity:
    # Most deploy platforms report deploys to GitHub as deployment statuses.
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: pyjeebz/prescale/action@v1
        with:
          token: ${{ secrets.PRESCALE_TOKEN }}
          target: staging.myapp.com
          paths: |
            /api/search
            /checkout
          # Logged-in or protected routes: headers go to your site only.
          headers: |
            authorization: Bearer ${{ secrets.STAGING_TOKEN }}
          fail-on-regression: true
```

## How it works

1. A pull request is pushed (replica mode) or a deploy finishes (`deployment_status`).
2. `prescale ci` ramps load against the app (the replica on localhost, or the
   deploy URL) and diagnoses the first route to break (`prescale investigate`).
3. The Result is uploaded to PreScale and attached to `target`. PreScale
   compares it with the latest run on the target's baseline branch (`main` by
   default), using the same rule as the dashboard: a change of more than 20%,
   confident when the confidence bands don't overlap.
4. The PR gets one comment, updated on every push.

**Baseline.** PRs compare against runs on your baseline branch. Give PreScale
one by running the action (or `prescale ci <staging-url>`) on pushes to `main`
against a staging URL. Until then, each push compares with the previous run on
the same PR.

**Safety.** Production deploys are skipped unless `allow-production: true`,
and deploys on hosts that restrict load testing unless `host-permission: true`.
Previews often point at the same database as production; if yours do, the load
reaches it too, so check before turning this on. On serverless every request is a
billed invocation; the default of 100 users keeps each check small, and the job
log says how many requests it sent.
Headers go to your site only; they're never saved or uploaded. The only thing
uploaded is the run's Result file, which you can inspect with
`prescale upload --dry-run`.

## Inputs

| Input | Default | |
|---|---|---|
| `token` | — | PreScale API token (required) |
| `target` | — | PreScale target hostname the deploy belongs to (required) |
| `url` | deploy URL | URL to test |
| `paths` | — | Extra routes, one per line |
| `headers` | — | `Name: value` per line, sent to your site only |
| `max-users` | `100` | Peak virtual users (gentle enough for every PR) |
| `stage-seconds` | `5` | Seconds per load level |
| `fail-on-regression` | `false` | Fail on a confident regression |
| `comment` | `true` | Post/update the PR comment |
| `allow-production` | `false` | Also test production deploys |
| `host-permission` | `false` | You have the host's permission to load-test (Vercel, Netlify, Cloudflare restrict it; otherwise the action skips) |
| `app` | — | Replica mode: build-and-start command, tested at `url` (default `http://localhost:3000`) |
| `app-timeout` | `600` | Seconds to wait for the app to answer |
| `working-directory` | `.` | Where to run `app` (monorepos) |
| `app-url` | `https://prescale.dev/dashboard` | Dashboard URL |
| `prescale-version` | latest | CLI version |
