param(
    [switch]$NoBrowser,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$appUrl = "http://127.0.0.1:8001"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "FundamentalIQ could not find its Python environment at $pythonPath"
}

$serverArguments = @(
    "-m", "uvicorn", "app.main:app",
    "--app-dir", "backend",
    "--host", "127.0.0.1",
    "--port", "8001"
)

Write-Host "Starting FundamentalIQ at $appUrl"
$server = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList $serverArguments `
    -WorkingDirectory $projectRoot `
    -NoNewWindow `
    -PassThru

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($server.HasExited) {
            throw "The FundamentalIQ server stopped during startup."
        }

        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $appUrl -TimeoutSec 1
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 300
        }
    }

    if (-not $ready) {
        throw "The FundamentalIQ server did not become ready at $appUrl"
    }

    Write-Host "FundamentalIQ is ready."
    if ($CheckOnly) {
        exit 0
    }

    if (-not $NoBrowser) {
        Start-Process $appUrl
    }

    Write-Host "Press Ctrl+C or close this window to stop the server."
    Wait-Process -Id $server.Id
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id
    }
}
