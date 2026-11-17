# Murmur installer / Installations-Skript  (per user, no administrator rights needed)
#   Double-click Install-Murmur.cmd.   Optional: -Zip <path to Murmur-Windows*.zip>  -Target <folder>  -NoPause
param(
  [string]$Zip = "",
  [string]$Target = (Join-Path $env:LOCALAPPDATA "Programs\Murmur"),
  [switch]$NoPause,
  [switch]$NoLaunch
)
$ErrorActionPreference = "Stop"
$de = (Get-Culture).TwoLetterISOLanguageName -eq "de"
function T($en, $deText) { if ($de) { $deText } else { $en } }
function Say($en, $deText) { Write-Host (T $en $deText) }

try {
  if (-not $Zip) {
    $z = Get-ChildItem -Path $PSScriptRoot -Filter "Murmur-Windows*.zip" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $z) { throw (T "Murmur-Windows*.zip not found next to this script." "Murmur-Windows*.zip wurde neben diesem Skript nicht gefunden.") }
    $Zip = $z.FullName
  }
  if (-not (Test-Path $Zip)) { throw (T "Zip file not found: $Zip" "Zip-Datei nicht gefunden: $Zip") }

  Say "Installing Murmur from: $Zip" "Installiere Murmur aus: $Zip"
  Say "Target folder:          $Target" "Zielordner:               $Target"

  $running = Get-Process -Name Murmur -ErrorAction SilentlyContinue
  if ($running) {
    Say "Murmur is running; closing it first (your recordings and settings are kept)..." "Murmur läuft noch und wird zuerst beendet (Aufnahmen und Einstellungen bleiben erhalten)..."
    $running | ForEach-Object { try { [void]$_.CloseMainWindow() } catch {} }
    Start-Sleep -Seconds 2
    Get-Process -Name Murmur -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
  }

  $tmp = Join-Path $env:TEMP ("murmur-install-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
  New-Item -ItemType Directory -Force $tmp | Out-Null
  Say "Unpacking..." "Entpacke..."
  Expand-Archive -Path $Zip -DestinationPath $tmp -Force
  $src = Join-Path $tmp "Murmur"
  if (-not (Test-Path (Join-Path $src "Murmur.exe"))) { throw (T "The zip does not contain Murmur\Murmur.exe." "Die Zip-Datei enthält kein Murmur\Murmur.exe.") }

  New-Item -ItemType Directory -Force $Target | Out-Null
  & robocopy $src $Target /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw (T "Copying files failed (robocopy code $LASTEXITCODE)." "Kopieren fehlgeschlagen (robocopy-Code $LASTEXITCODE).") }
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
  Get-ChildItem $Target -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

  $exe = Join-Path $Target "Murmur.exe"
  $lnkDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
  $sh = New-Object -ComObject WScript.Shell
  $lnk = $sh.CreateShortcut((Join-Path $lnkDir "Murmur.lnk"))
  $lnk.TargetPath = $exe; $lnk.WorkingDirectory = $Target; $lnk.IconLocation = "$exe,0"; $lnk.Description = "Murmur voice typing"
  $lnk.Save()

  Say "Done. Starting Murmur (look for the little bird in the system tray, bottom right)." "Fertig. Murmur startet (such den kleinen Vogel im Infobereich unten rechts)."
  if (-not $NoLaunch) { Start-Process -FilePath $exe -ArgumentList "--show" -WorkingDirectory $Target }
  Say "Tip: first time? Pick a speech model on the Home screen (or import one from the stick: Settings > Offline / office mode)." "Tipp: Erster Start? Wähle auf der Startseite ein Sprachmodell (oder importiere eins vom Stick: Einstellungen > Offline-/Kanzlei-Modus)."
  $code = 0
} catch {
  Write-Host ""
  Write-Host ((T "INSTALL FAILED: " "INSTALLATION FEHLGESCHLAGEN: ") + $_.Exception.Message) -ForegroundColor Red
  $code = 1
}
if (-not $NoPause) { Write-Host ""; [void](Read-Host (T "Press Enter to close" "Zum Schließen Enter drücken")) }
exit $code
