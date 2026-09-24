# build_installer.ps1
# KyteView 一鍵打包與安裝程式編譯腳本

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   KyteView 自動化編譯與安裝檔封裝程序   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. 清理過往建置產物
Write-Host "`n>>> [1/3] 正在清理過往建置目錄..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 2. PyInstaller 打包
Write-Host "`n>>> [2/3] 正在執行 PyInstaller 編譯 (無黑窗、獨立目錄模式)..." -ForegroundColor Yellow
pyinstaller --noconfirm --onedir --windowed `
    --name "KyteView" `
    --icon "assets/icon.ico" `
    --add-data "assets;assets" `
    --hidden-import "py7zr" `
    --hidden-import "mammoth" `
    --hidden-import "pptx" `
    --hidden-import "fitz" `
    --hidden-import "pymupdf" `
    --hidden-import "miniaudio" `
    --hidden-import "calamine" `
    --hidden-import "python_calamine" `
    --hidden-import "pygments" `
    --hidden-import "markdown_it" `
    --hidden-import "win32timezone" `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] PyInstaller 編譯失敗，請檢查上方輸出訊息！" -ForegroundColor Red
    exit 1
}

# 3. Inno Setup 封裝
Write-Host "`n>>> [3/3] 正在使用 Inno Setup 封裝安裝精靈..." -ForegroundColor Yellow
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "ISCC.exe"
)

$foundIscc = $null
foreach ($cand in $isccCandidates) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        $foundIscc = $cand
        break
    }
    if (Test-Path $cand) {
        $foundIscc = $cand
        break
    }
}

if ($foundIscc) {
    & $foundIscc setup.iss
    Write-Host "`n=============================================" -ForegroundColor Green
    Write-Host " [SUCCESS] 安裝精靈打包成功！" -ForegroundColor Green
    Write-Host " 安裝檔位置：dist\KyteView_Setup_1.0.0.exe" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
} else {
    Write-Host "`n[WARNING] 未偵測到 Inno Setup 6 編譯器 (ISCC.exe)。" -ForegroundColor Yellow
    Write-Host "已為您完成 dist\KyteView 免安裝獨立目錄版。" -ForegroundColor Yellow
    Write-Host "安裝 Inno Setup 6 後再次執行本腳本即可產生安裝檔。" -ForegroundColor Yellow
}
