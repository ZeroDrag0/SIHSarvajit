Write-Host "Starting VERTICAD SIH demo..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$PSScriptRoot\backend'; py -m uvicorn main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$PSScriptRoot\viewer'; npm run dev -- --port 5174"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$PSScriptRoot\landing'; npm run dev -- --port 5173"
Write-Host "Landing: http://localhost:5173"
Write-Host "Viewer : http://localhost:5174"
Write-Host "API    : http://localhost:8000/docs"
