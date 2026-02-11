$baseUrl = "http://localhost:8001"

Write-Host "1. Checking initial status..."
$status = Invoke-RestMethod -Uri "$baseUrl/api/retrain/status" -Method Get
Write-Host "   Status: $($status.running)"
Write-Host "   Last Run: $($status.last_run.status)"

Write-Host "`n2. Triggering retrain (Wait 5s)..."
$trigger = Invoke-RestMethod -Uri "$baseUrl/api/retrain/trigger" -Method Post -Body (@{hours=24} | ConvertTo-Json) -ContentType "application/json"
Write-Host "   Triggered. Run Status: $($trigger.status)"

Write-Host "`n3. Monitoring status..."
for ($i=0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 2
    $status = Invoke-RestMethod -Uri "$baseUrl/api/retrain/status" -Method Get
    Write-Host "   [$i] Status: $($status.last_run.status) | running: $($status.running)"
    if ($status.last_run.status -ne "running" -and $status.last_run.status -ne "pending") {
        break
    }
}

Write-Host "`n4. Final History..."
$history = Invoke-RestMethod -Uri "$baseUrl/api/retrain/history" -Method Get
$last = $history.history[0]
Write-Host "   Latest Run: $($last.status)"
Write-Host "   Data Points: $($last.data_points)"
Write-Host "   Error: $($last.error)"
Write-Host "   Deployed: $($last.deployed)"
