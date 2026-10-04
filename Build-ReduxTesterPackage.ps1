param([string]$Version='0.5.0-redux-dev.1')
$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$releaseRoot=Join-Path $projectRoot 'release'
$stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$staging=Join-Path $releaseRoot ('.redux-staging-'+$stamp)
$app=Join-Path $staging 'EarthBound Companion'
$docs=Join-Path $projectRoot 'github-repo'
if(!(Test-Path -LiteralPath $docs)){$docs=$projectRoot}
$native=Join-Path $projectRoot 'build\companion\earthbound.exe'
$helper=Join-Path $projectRoot '_BuildScratch\redux-setup-dist\redux-setup.exe'
$originalHelper=Join-Path $projectRoot 'native-source\dist\ebtools-setup.exe'
foreach($input in @($native,$helper,$originalHelper)){if(!(Test-Path -LiteralPath $input -PathType Leaf)){throw "Missing build input: $input"}}
New-Item -ItemType Directory -Path $app -Force | Out-Null
foreach($folder in @('Game','msu','UserData','Profiles','Mods','Licenses')){New-Item -ItemType Directory -Path (Join-Path $app $folder) -Force | Out-Null}
& dotnet publish (Join-Path $projectRoot 'Companion\Companion.csproj') -c Release -o (Join-Path $staging 'publish') *> (Join-Path $staging 'publish.log')
if($LASTEXITCODE -ne 0){throw 'Companion publish failed. See the staging publish.log.'}
Copy-Item -LiteralPath (Join-Path $staging 'publish\EarthBound Companion.exe') -Destination $app
Copy-Item -LiteralPath $native -Destination (Join-Path $app 'Game\earthbound.exe')
Copy-Item -LiteralPath $helper -Destination (Join-Path $app 'Game\redux-setup.exe')
Copy-Item -LiteralPath $originalHelper -Destination (Join-Path $app 'Game\ebtools-setup.exe')
Copy-Item -LiteralPath (Join-Path $projectRoot 'tools\SDL2-2.32.10\x86_64-w64-mingw32\bin\SDL2.dll') -Destination (Join-Path $app 'Game\SDL2.dll')
foreach($name in @('README.md','RANDOMIZER.md','CREDITS.md','LEGAL.md','MATERNALBOUND-NATIVE.md')){Copy-Item -LiteralPath (Join-Path $docs $name) -Destination $app}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $docs 'Mods') -File){Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $app 'Mods')}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $projectRoot 'EarthBound Companion\Licenses') -File){Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $app 'Licenses')}
Copy-Item -LiteralPath (Join-Path $projectRoot '_BuildScratch\CoilSnake\LICENSE') -Destination (Join-Path $app 'Licenses\CoilSnake-LICENSE')
Copy-Item -LiteralPath (Join-Path $projectRoot '_BuildScratch\CoilSnake\coilsnake\util\eb\exhal\COPYING.txt') -Destination (Join-Path $app 'Licenses\Exhal-COPYING.txt')
@'
EarthBound Companion — Redux development edition

1. Extract this entire folder and run EarthBound Companion.exe.
2. Choose your clean EarthBound (USA) .sfc or .smc ROM.
3. Leave the complete MSU soundtrack selected for enhanced music.
4. Setup downloads the pinned Redux source and soundtrack, checks them,
   and builds the native game data locally. No Python installation is needed.
5. Play from Solo Play, or generate a Story Shuffle adventure.

This is an experimental native conversion. A complete story or randomized
playthrough remains unverified. Read MATERNALBOUND-NATIVE.md for coverage.
Redux Port lets you return to original EarthBound. Each edition and seed
keeps separate saves. Back up phone saves before moving between builds.

This ZIP contains no ROM, playable game asset pack, soundtrack or saves.
No game files are uploaded. MSU files download during setup; missing tracks
fall back to the converted SPC soundtrack.

F1 settings | F6 save | F7 load | F9 pause | F11 fullscreen
F12 screenshot | Tab fast-forward

Credits, source and development updates:
https://github.com/rages4calm/earthbound-companion
'@ | Set-Content -LiteralPath (Join-Path $app 'START HERE.txt') -Encoding utf8
$forbidden=@('.sfc','.smc','.fig','.swc','.rom','.pak','.pcm','.srm','.sav','.state','.bmp','.png','.replay')
$bad=Get-ChildItem -LiteralPath $app -File -Recurse | Where-Object {$_.Extension -in $forbidden -or $_.Name -match '^quicksave_'}
if($bad){throw 'Game-derived content entered the package staging folder.'}
$manifest=Get-ChildItem -LiteralPath $app -File -Recurse | Sort-Object FullName | ForEach-Object {
 [pscustomobject]@{Path=$_.FullName.Substring($app.Length+1).Replace('\','/');Bytes=$_.Length;SHA256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
}
@{Version=$Version;Status='development-only';FullPlaythroughVerified=$false;Files=$manifest} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $app 'PACKAGE-MANIFEST.json') -Encoding utf8
$zip=Join-Path $releaseRoot ("EarthBound-Companion-Redux-Tester-v$Version.zip")
if(Test-Path -LiteralPath $zip){$zip=Join-Path $releaseRoot ("EarthBound-Companion-Redux-Tester-v$Version-$stamp.zip")}
Compress-Archive -LiteralPath $app -DestinationPath $zip -CompressionLevel Optimal
$archive=[IO.Compression.ZipFile]::OpenRead($zip)
try{
 foreach($entry in $archive.Entries){if([IO.Path]::GetExtension($entry.Name) -in $forbidden -or $entry.Name -match '^quicksave_'){throw 'Forbidden game data entered the ZIP.'}}
}finally{$archive.Dispose()}
$result=[pscustomobject]@{Zip=$zip;Bytes=(Get-Item -LiteralPath $zip).Length;SHA256=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash;Staging=$app;FullPlaythroughVerified=$false}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $releaseRoot 'redux-development-package.json') -Encoding utf8
$result
