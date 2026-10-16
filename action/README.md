# PreScale capacity check (GitHub Action)

Load-tests every preview deploy, uploads the verdict to your PreScale
dashboard, and keeps one comment on the PR with the capacity change vs your
baseline branch, the route that breaks first, why, and the fix.

```yaml
# .github/workflows/capacity.yml
name: Capacity
on: deployment_status

jobs:
  capacity:
    # Vercel, Netlify and others report preview deploys as deployment statuses.
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    permissions:
      contents: read         # find the PR for the deployed commit
      pull-requests: write   # the capacity comment
    steps:
      - uses: pyjeebz/prescale/action@v1
        with:
          token: ${{ secrets.PRESCALE_TOKEN }}
          target: staging.myapp.com
          paths: |
            /api/search
            /checkout
          # Vercel Deployment Protection: Settings → Deployment Protection →
          # Protection Bypass for Automation.
          headers: |
            x-vercel-protection-bypass: ${{ secrets.VERCEL_AUTOMATION_BYPASS_SECRET }}
          fail-on-regression: true
```

## How it works

1. A preview deploy finishes; GitHub sends `deployment_status`.
2. `prescale ci` ramps load against the preview URL and diagnoses the first
   route to break (`prescale investigate`).
3. The Result is uploaded to PreScale and attached to `target`. PreScale
   compares it with the latest run on the target's baseline branch (`main` by
   default), using the same rule as the dashboard: a change of more than 20%,
   confident when the confidence bands don't overlap.
4. The PR gets one comment, updated on every push.

**Baseline.** PRs compare against runs on your baseline branch. Give PreScale
one by running the action (or `prescale ci <staging-url>`) on pushes to `main`
against a staging URL. Until then, each push compares with the previous run on
the same PR.

**Safety.** Production deploys are skipped unless `allow-production: true`.
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
| `max-users` | `200` | Peak virtual users |
| `stage-seconds` | `5` | Seconds per load level |
| `fail-on-regression` | `false` | Fail on a confident regression |
| `comment` | `true` | Post/update the PR comment |
| `allow-production` | `false` | Also test production deploys |
| `app-url` | `https://prescale.dev/dashboard` | Dashboard URL |
| `prescale-version` | latest | CLI version |
