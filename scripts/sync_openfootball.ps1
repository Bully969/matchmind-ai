$ErrorActionPreference = "Stop"
$dest = Join-Path $PSScriptRoot "..\data\openfootball"
if (Test-Path $dest) {
  Write-Host "Directory already exists: $dest"
  Write-Host "To refresh, delete it first, then rerun this script."
  exit 1
}
git clone --depth 1 https://github.com/openfootball/football.json.git $dest
Write-Host "OpenFootball CC0 JSON dataset cloned to $dest"
