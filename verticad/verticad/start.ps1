# Runs the VERTICAD backend (:8000) and frontend (:5173) together. Ctrl+C stops both.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
if (-not (Test-Path ".venv")) { & $py -m venv .venv }
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
& $venvPy -m pip install -q -r pipeline/src/Schependomlaan/requirements.txt -r backend/requirements.txt

Push-Location web
npm install
Pop-Location

$backend = Start-Process -FilePath $venvPy `
  -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" `
  -WorkingDirectory (Join-Path $root "backend") -NoNewWindow -PassThru
try {
  Write-Host "Open http://localhost:5173" -ForegroundColor Cyan
  Set-Location (Join-Path $root "web")
  npm run dev
} finally {
  Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}
