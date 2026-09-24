# build_installer.ps1
# KyteView 一鍵打包與安裝程式編譯腳本

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   KyteView 自動化編譯與安裝檔封裝程序   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 0. 確認 Python 與 PyInstaller 環境
$venvPy = ".\.venv\Scripts\python.exe"
$venvPyInstaller = ".\.venv\Scripts\pyinstaller.exe"

$pyCmd = "python"
$pyinstallerCmd = "pyinstaller"

if (Test-Path $venvPy) {
    Write-Host "`n>>> [0/3] 偵測到專案虛擬環境 (.venv)，優先使用... " -ForegroundColor Green
    $pyCmd = $venvPy
    if (-not (Test-Path $venvPyInstaller)) {
        Write-Host "虛擬環境中尚未安裝 PyInstaller，正在自動安裝... " -ForegroundColor Yellow
        & $venvPy -m pip install --upgrade pyinstaller
    }
    $pyinstallerCmd = $venvPyInstaller
}

# 1. 清理過往建置產物
Write-Host "`n>>> [1/3] 正在清理過往建置目錄... " -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 2. PyInstaller 打包
Write-Host "`n>>> [2/3] 正在執行 PyInstaller 編譯 (無黑窗、獨立目錄模式)... " -ForegroundColor Yellow
& $pyinstallerCmd --noconfirm --onedir --windowed `
    --name "KyteView" `
    --icon "assets/icon.ico" `
    --add-data "assets;assets" `
    --collect-all "pygments" `
    --hidden-import "py7zr" `
    --hidden-import "mammoth" `
    --hidden-import "pptx" `
    --hidden-import "fitz" `
    --hidden-import "pymupdf" `
    --hidden-import "miniaudio" `
    --hidden-import "calamine" `
    --hidden-import "python_calamine" `
    --hidden-import "markdown_it" `
    --hidden-import "win32timezone" `
    --hidden-import "PySide6.QtSvg" `
    --hidden-import "PySide6.QtSvgWidgets" `
    --hidden-import "PySide6.QtMultimedia" `
    --hidden-import "PySide6.QtMultimediaWidgets" `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] PyInstaller 編譯失敗，請檢查上方輸出訊息！ " -ForegroundColor Red
    exit 1
}

# 3. Inno Setup 封裝
Write-Host "`n>>> [3/3] 正在使用 Inno Setup 封裝安裝精靈... " -ForegroundColor Yellow
$isccCandidates = @(
    "C:\Program Files\Inno Setup 7\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
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
    Write-Host "使用編譯器：$foundIscc " -ForegroundColor DarkCyan
    & $foundIscc setup.iss

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=============================================" -ForegroundColor Green
        Write-Host " [SUCCESS] 安裝精靈打包成功！ " -ForegroundColor Green
        Write-Host " 安裝檔位置：dist\KyteView_Setup_1.0.0.exe " -ForegroundColor Green
        Write-Host "=============================================" -ForegroundColor Green
    } else {
        Write-Host "`n[ERROR] Inno Setup 封裝失敗，請檢查 setup.iss 設定！ " -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n[WARNING] 未偵測到 Inno Setup 編譯器 (ISCC.exe)。 " -ForegroundColor Yellow
    Write-Host "已為您完成 dist\KyteView 免安裝獨立目錄版。 " -ForegroundColor Yellow
    Write-Host "安裝 Inno Setup 後再次執行本腳本即可產生安裝檔。 " -ForegroundColor Yellow
}