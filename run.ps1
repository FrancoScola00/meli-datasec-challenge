# MeLi DataSec Challenge — task runner (Windows PowerShell).
# Usage:  .\run.ps1 <target> [args]
# Targets: install | test | c1 | c2 | c3-verify | c4-demo
param(
    [Parameter(Position = 0)][string]$Target = "help",
    [Parameter(ValueFromRemainingArguments = $true)]$Rest
)
$ErrorActionPreference = "Stop"
$Py = ".\.venv\Scripts\python.exe"

switch ($Target) {
    "install" {
        & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
        & $Py -m pip install --upgrade pip
        & $Py -m pip install -r requirements.txt
    }
    "test"      { & $Py -m pytest -v }
    "c1"        { & $Py solution_minesweeper.py }
    "c2"        { if ($Rest) { & $Py solution_best_in_genre.py @Rest } else { & $Py solution_best_in_genre.py Action } }
    "c3-verify" { & "$PSScriptRoot\tests\verify_c3.ps1" }
    "c4-demo"   { if ($Rest) { & $Py challenge4\demo_live.py @Rest } else { & $Py challenge4\demo_live.py --text "Please email me at jane.doe@example.com or call 11-5555-1234" } }
    default     { Write-Output "Targets: install | test | c1 | c2 | c3-verify | c4-demo" }
}
