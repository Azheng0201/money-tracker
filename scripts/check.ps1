# 强制控制台按 UTF-8 输出
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

Write-Host "🔍 [1/4] ruff check..." -ForegroundColor Cyan
ruff check .

Write-Host "`n🎨 [2/4] ruff format --check..." -ForegroundColor Cyan
ruff format --check .

Write-Host "`n🧪 [3/4] pytest with coverage..." -ForegroundColor Cyan
pytest --cov=. --cov-report=term-missing

Write-Host "`n✅ 全部通过！" -ForegroundColor Green