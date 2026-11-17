# Builds Murmur-Windows.zip (a portable folder containing Murmur.exe).
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
# Requires a Python venv with the packages from requirements.txt + pyinstaller.
param([string]$Python = "python",
      [string]$Work = "C:\murmur-build")   # keep this path short (Windows path-length limits)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
New-Item -ItemType Directory -Force "$Work\assets" | Out-Null
& $Python -c "import sys; sys.path.insert(0, r'$root'); from murmur import mascot; mascot.save_ico(r'$Work\assets\murmur.ico')"
& $Python -m PyInstaller --noconfirm --clean --windowed --name Murmur `
  --icon "$Work\assets\murmur.ico" `
  --workpath "$Work\build" --distpath "$Work\dist" --specpath "$Work" `
  --paths "$root" `
  --add-data "$root\murmur\ui;murmur\ui" `
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime `
  --collect-all tokenizers --collect-all av --collect-all webview `
  --hidden-import pystray._win32 `
  "$root\murmur\__main__.py"
if (Test-Path "$Work\Murmur-Windows.zip") { Remove-Item "$Work\Murmur-Windows.zip" }
Compress-Archive -Path "$Work\dist\Murmur" -DestinationPath "$Work\Murmur-Windows.zip"
Write-Host "Done: $Work\Murmur-Windows.zip"
# Optional: also create the signed USB-stick update package (needs the private key from tools\keygen.py).
$key = Join-Path $env:USERPROFILE ".murmur-signing\update-private.pem"
if (Test-Path $key) {
  $ver = (Select-String -Path "$root\murmur\__init__.py" -Pattern '"(.+)"').Matches[0].Groups[1].Value
  & $Python "$root\tools\make_update.py" --payload "$Work\dist\Murmur" --version $ver --out $Work
} else { Write-Host "No signing key found; skipped the .murmurupdate package (run tools\keygen.py once to enable)." }
