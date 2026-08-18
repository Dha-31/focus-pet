# tools/build_client.ps1 —— 一键生成客户端 + 安装包
# 用法: powershell -ExecutionPolicy Bypass -File tools\build_client.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

# 1) 构建精简版客户端（onedir，含 Electron 运行时 + 屏幕分析 OCR）
& $py (Join-Path $root "tools\build_exe.py")
if ($LASTEXITCODE -ne 0) { throw "build_exe.py 失败" }

# 2) 编译安装包（Inno Setup 6）
$iscc = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "未找到 Inno Setup，请先安装：https://jrsoftware.org/isdl.php" }
& $iscc (Join-Path $root "tools\installer.iss")
if ($LASTEXITCODE -ne 0) { throw "安装包编译失败" }

Write-Host "OK 安装包: $(Join-Path $root 'release\FocusPet-Setup-4.0.4.exe')"
