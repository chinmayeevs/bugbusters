# start.ps1 - Production Launcher for AIOps Alert Shield (Windows PowerShell)

Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  AIOPS ALERT SHIELD // ORCHESTRATED ALERT VERIFICATION PLATFORM" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green

# 1. Environment Check
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path "$Root\.env")) {
    if (Test-Path "$Root\.env.example") {
        Write-Host "[INIT] Copying .env.example to .env..." -ForegroundColor Yellow
        Copy-Item "$Root\.env.example" "$Root\.env"
    } else {
        Write-Host "[INIT] Creating default .env configuration..." -ForegroundColor Yellow
        Set-Content -Path "$Root\.env" -Value "MOCK_LLM=true`nLLM_PROVIDER=gemini`nLLM_MODEL=gemini/gemini-2.5-flash`nLLM_TIMEOUT_SECONDS=25`nLLM_MAX_TOKENS=1200"
    }
}

# 2. Set PYTHONPATH
$env:PYTHONPATH = $Root

# 3. Check / Start Backend API (FastAPI on Port 8000)
Write-Host "[1/3] Checking backend API on port 8000..." -ForegroundColor Cyan
$BackendRunning = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
    if ($resp.status -eq "ok") {
        $BackendRunning = $true
        Write-Host "  Backend already active at http://127.0.0.1:8000" -ForegroundColor Green
    }
} catch {
    $BackendRunning = $false
}

if (-not $BackendRunning) {
    Write-Host "  Starting FastAPI backend daemon on port 8000..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000" -WindowStyle Minimized

    # Poll /health until online
    $retries = 20
    while ($retries -gt 0) {
        Start-Sleep -Milliseconds 800
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
            if ($resp.status -eq "ok") {
                Write-Host "  Backend successfully initialized at http://127.0.0.1:8000" -ForegroundColor Green
                $BackendRunning = $true
                break
            }
        } catch {
            $retries--
        }
    }
    if (-not $BackendRunning) {
        Write-Host "[ERROR] Backend failed to start within timeout. Check python dependencies." -ForegroundColor Red
        exit 1
    }
}

# 4. Check Frontend (Next.js on Port 3000)
Write-Host "[2/3] Checking Next.js operational console on port 3000..." -ForegroundColor Cyan
$FrontendRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 3000)
    $FrontendRunning = $true
    $tcp.Close()
    Write-Host "  Frontend console already listening on http://localhost:3000" -ForegroundColor Green
} catch {
    $FrontendRunning = $false
}

if (-not $FrontendRunning) {
    Write-Host "  Starting Next.js frontend production server on port 3000..." -ForegroundColor Yellow
    Set-Location "$Root\frontend"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm start -- -p 3000" -WindowStyle Minimized
    Set-Location $Root
    Start-Sleep -Seconds 2
}

# 5. Ready Banner & Useful Commands
Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "  AIOPS ALERT SHIELD PLATFORM READY" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  Operational Web Console:   http://localhost:3000" -ForegroundColor White
Write-Host "  GraphQL Playground:        http://localhost:8000/graphql" -ForegroundColor White
Write-Host "  System Health Check:       http://localhost:8000/health" -ForegroundColor White
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Evaluation Benchmark CLI:  python scripts/evaluate_system.py" -ForegroundColor Cyan
Write-Host "  Live Stream Replay CLI:    python scripts/replay_stream.py --speed 5.0" -ForegroundColor Cyan
Write-Host "  Run Pytest Test Suite:     python -m pytest tests -v" -ForegroundColor Cyan
Write-Host "================================================================================`n" -ForegroundColor Green
