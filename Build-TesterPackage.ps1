$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$version='0.4.0'
$releaseRoot=Join-Path $projectRoot 'release'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$stagingParent=Join-Path $releaseRoot ('.staging-'+$stamp)
$app=Join-Path $stagingParent 'EarthBound Companion'
$zip=Join-Path $releaseRoot ("EarthBound-Companion-Tester-v$version.zip")

New-Item -ItemType Directory -Path $app -Force | Out-Null
foreach($folder in @('Game','msu','UserData','Mods','Licenses')){New-Item -ItemType Directory -Path (Join-Path $app $folder) -Force | Out-Null}

$publish=Join-Path $stagingParent 'publish'
& dotnet publish (Join-Path $projectRoot 'Companion\Companion.csproj') -c Release -o $publish
if($LASTEXITCODE -ne 0){throw 'Companion publish failed.'}

Copy-Item -LiteralPath (Join-Path $publish 'EarthBound Companion.exe') -Destination $app
Copy-Item -LiteralPath (Join-Path $projectRoot 'build\companion\earthbound.exe') -Destination (Join-Path $app 'Game\earthbound.exe')
Copy-Item -LiteralPath (Join-Path $projectRoot 'tools\SDL2-2.32.10\x86_64-w64-mingw32\bin\SDL2.dll') -Destination (Join-Path $app 'Game\SDL2.dll')
Copy-Item -LiteralPath (Join-Path $projectRoot 'native-source\dist\ebtools-setup.exe') -Destination (Join-Path $app 'Game\ebtools-setup.exe')
foreach($file in @('README.md','RANDOMIZER.md','RESEARCH.md','CREDITS.md')){Copy-Item -LiteralPath (Join-Path $projectRoot ('EarthBound Companion\'+$file)) -Destination $app}
Copy-Item -LiteralPath (Join-Path $projectRoot 'distribution\START HERE.txt') -Destination $app
Copy-Item -LiteralPath (Join-Path $projectRoot 'distribution\PACKAGE-NOTES.md') -Destination $app
Copy-Item -Path (Join-Path $projectRoot 'EarthBound Companion\Mods\*') -Destination (Join-Path $app 'Mods')
Copy-Item -Path (Join-Path $projectRoot 'EarthBound Companion\Licenses\*') -Destination (Join-Path $app 'Licenses')

$forbidden=Get-ChildItem -LiteralPath $app -File -Recurse | Where-Object {$_.Extension -in @('.sfc','.smc','.rom','.pak','.pcm','.srm','.bmp','.png','.state') -or $_.Name -match '^quicksave_'}
if($forbidden){throw ('Forbidden game-derived files entered staging: '+(($forbidden.FullName) -join ', '))}

$manifest=Get-ChildItem -LiteralPath $app -File -Recurse | Sort-Object FullName | ForEach-Object {
 [pscustomobject]@{Path=$_.FullName.Substring($app.Length+1).Replace('\','/');Bytes=$_.Length;SHA256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash}
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $app 'PACKAGE-MANIFEST.json') -Encoding utf8

if(Test-Path -LiteralPath $zip){$zip=Join-Path $releaseRoot ("EarthBound-Companion-Tester-v$version-$stamp.zip")}
Compress-Archive -LiteralPath $app -DestinationPath $zip -CompressionLevel Optimal

$zipEntries=[IO.Compression.ZipFile]::OpenRead($zip)
try {
 $bad=$zipEntries.Entries | Where-Object {$_.Name -match '\.(sfc|smc|rom|pak|pcm|srm|bmp|png|state)$' -or $_.Name -match '^quicksave_'}
 if($bad){throw ('Forbidden content found in ZIP: '+(($bad.FullName) -join ', '))}
} finally {$zipEntries.Dispose()}

[pscustomobject]@{Zip=$zip;Bytes=(Get-Item -LiteralPath $zip).Length;SHA256=(Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash;Staging=$app}
