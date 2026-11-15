# Meeting Organiser Agent — Backend Startup Script
# Run this from the project root whenever the server needs to start/restart.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Kill any existing process on port 8000
$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $procId = $existing.OwningProcess
    Write-Host "Stopping existing server (PID $procId)..."
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "Starting backend on http://0.0.0.0:8000 ..."
$env:PYTHONPATH = "backend"
& "$projectRoot\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload

