param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "Python launcher (py) not found. Install Python 3.10+ from python.org and enable the launcher." -ForegroundColor Red
  exit 1
}

py -m pip install -e .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Starting server on http://127.0.0.1:$Port/ui/?task=all" -ForegroundColor Green
Start-Process "http://127.0.0.1:$Port/ui/?task=all" | Out-Null

py -m server.app --port $Port

