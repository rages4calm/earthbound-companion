param([string]$RomPath=(Join-Path $PSScriptRoot 'ROM\EarthBound (USA).sfc'),[string]$OutputPath=(Join-Path $PSScriptRoot 'EarthBound Companion\Game\assets.pak'))
$ErrorActionPreference='Stop'
if(!(Test-Path -LiteralPath $RomPath)){throw 'Donor ROM not found.'}
if(Get-Process -Name earthbound -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq (Join-Path $PSScriptRoot 'EarthBound Companion\Game\earthbound.exe')}){throw 'Close EarthBound before replacing assets.'}
$RomPath=(Resolve-Path -LiteralPath $RomPath).Path
$OutputPath=[IO.Path]::GetFullPath($OutputPath)
if(Test-Path -LiteralPath $OutputPath){Copy-Item -LiteralPath $OutputPath -Destination ($OutputPath+'.backup') -Force}
Push-Location (Join-Path $PSScriptRoot 'native-source')
try {
 $env:PYTHONUTF8='1'
 & .venv\Scripts\ebtools.exe setup $RomPath --out $OutputPath
 if($LASTEXITCODE -ne 0){throw 'Asset extraction failed. Previous pack is retained as .backup.'}
} finally {Pop-Location}
