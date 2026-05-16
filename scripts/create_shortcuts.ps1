# Creates Desktop shortcuts for EyeCursor App, EyeCursor TestLab, and Horsin' Around.
# Each shortcut launches `wscript.exe scripts\launch_hidden.vbs <module>`, which
# spawns the venv's python.exe (NOT pythonw.exe) with a hidden console window.
# We avoid pythonw because mediapipe/TF Lite logging in the tracking app
# interacts badly with pythonw's null stdio, breaking the capture handshake.

$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent $PSScriptRoot
$assets  = Join-Path $root "assets"
$python  = Join-Path $root "venv\Scripts\python.exe"
$wscript = Join-Path $env:WINDIR "System32\wscript.exe"
$vbs     = Join-Path $root "scripts\launch_hidden.vbs"
$shell   = New-Object -ComObject WScript.Shell
$desktop = $shell.SpecialFolders("Desktop")

if (-not (Test-Path $python)) {
    throw "Missing $python -- run setup_windows.bat first."
}
if (-not (Test-Path $vbs)) {
    throw "Missing $vbs"
}

function Ensure-Icon {
    param([string]$Path, [string]$GeneratorScript)
    if (Test-Path $Path) { return }
    Write-Host "[shortcuts] $Path missing -- generating via $GeneratorScript ..." -ForegroundColor Yellow
    $venvPy = Join-Path $root "venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        & $venvPy (Join-Path $root $GeneratorScript)
    } else {
        $py = $null
        foreach ($v in @("3.12","3.11")) { & py -$v --version *> $null; if ($LASTEXITCODE -eq 0) { $py = $v; break } }
        if (-not $py) { throw "Need Python 3.11/3.12 (or the venv) to generate icons" }
        & py -$py (Join-Path $root $GeneratorScript)
    }
}

Ensure-Icon -Path (Join-Path $assets "eyecursor.ico")     -GeneratorScript "scripts\png_to_ico.py"
Ensure-Icon -Path (Join-Path $assets "testlab.ico")       -GeneratorScript "scripts\make_icons.py"
Ensure-Icon -Path (Join-Path $assets "horsin_around.ico") -GeneratorScript "scripts\make_icons.py"

$entries = @(
    @{ Name = "EyeCursor App";     Module = "src.app.main";       Icon = "eyecursor.ico";     Comment = "Launch EyeCursor main app" },
    @{ Name = "EyeCursor TestLab"; Module = "criteria.app.main";  Icon = "testlab.ico";       Comment = "Launch the EyeCursor TestLab" },
    @{ Name = "Horsin' Around";    Module = "game.app.main";      Icon = "horsin_around.ico"; Comment = "Launch the Horsin' Around game" }
)

# Names from earlier versions of this script that should be cleaned up.
$legacy = @("EyeCursor.lnk", "EyeCursor Criteria.lnk", "EyeCursor Game.lnk")
foreach ($leg in $legacy) {
    $p = Join-Path $desktop $leg
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Host "[shortcuts] removed legacy $leg" -ForegroundColor DarkGray
    }
}

foreach ($e in $entries) {
    $lnkPath = Join-Path $desktop ("{0}.lnk" -f $e.Name)
    $icon    = Join-Path $assets $e.Icon
    if (-not (Test-Path $icon)) { Write-Warning "Missing icon $icon -- skipping"; continue }

    $sc = $shell.CreateShortcut($lnkPath)
    $sc.TargetPath       = $wscript
    $sc.Arguments        = ('"{0}" {1}' -f $vbs, $e.Module)
    $sc.WorkingDirectory = $root
    $sc.IconLocation     = "$icon, 0"
    $sc.Description      = $e.Comment
    $sc.WindowStyle      = 1
    $sc.Save()

    Write-Host ("[shortcuts] {0} -> wscript launch_hidden.vbs {1}  (icon: {2})" -f $e.Name, $e.Module, $e.Icon) -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Shortcuts placed in: $desktop" -ForegroundColor Cyan
