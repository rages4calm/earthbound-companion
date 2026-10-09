param([string]$ShaderRuntimePath='')
$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$gameExe=Join-Path $projectRoot 'EarthBound Companion\Game\earthbound.exe'
if(Get-Process -Name earthbound -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $gameExe}){throw 'Close EarthBound before rebuilding.'}
Push-Location $projectRoot
$taskOriginalPath=$env:PATH
try {
 $env:PATH="$projectRoot\tools\mingw64\bin;$projectRoot\native-source\.venv\Scripts;$env:PATH"
 $env:PYTHONUTF8='1'
 & native-source\.venv\Scripts\python.exe scripts\create_fixture.py
 if($LASTEXITCODE -ne 0){throw 'Fixture preparation failed.'}
 & native-source\.venv\Scripts\cmake.exe -S native-source\port\unix -B build\companion -G Ninja -DCMAKE_BUILD_TYPE=Release -DEB_RUNTIME_ASSETS=ON -DEB_ENABLE_VERIFY=OFF -DEB_ENABLE_AUDIO=ON "-DSDL2_DIR=$projectRoot/tools/SDL2-2.32.10/x86_64-w64-mingw32/lib/cmake/SDL2"
 if($LASTEXITCODE -ne 0){throw 'Native configuration failed.'}
 & native-source\.venv\Scripts\cmake.exe --build build\companion --parallel 8
 if($LASTEXITCODE -ne 0){throw 'Native build failed.'}
 & native-source\.venv\Scripts\python.exe scripts\export_randomizer_layout.py
 if($LASTEXITCODE -ne 0){throw 'Randomizer asset registry export failed.'}
 # Derive into build output and verify the checked-in policy. Rebuilding must
 # retain its exact audited hash aliases and existing seed compatibility.
 & native-source\.venv\Scripts\python.exe scripts\audit_progression.py --policy-output build\companion\derived-original-policy.json --report-output build\companion\derived-original-progression.json
 if($LASTEXITCODE -ne 0){throw 'Progression protection audit failed.'}
 $taskPolicy=Get-Content -LiteralPath 'Companion\progression-policy.json' -Raw | ConvertFrom-Json
 $taskDerived=Get-Content -LiteralPath 'build\companion\derived-original-policy.json' -Raw | ConvertFrom-Json
 foreach($property in @('ContentId','SaveStateVersion','SaveStateCrcPolynomial')){
  if($taskPolicy.$property -ne $taskDerived.$property){throw "Derived policy differs in $property"}
 }
 foreach($property in @('ProtectedItems','ProtectedEnemies')){
  if(($taskPolicy.$property -join ',') -ne ($taskDerived.$property -join ',')){throw "Derived protections differ in $property"}
 }
 if($taskDerived.BaseHash -notin (@($taskPolicy.BaseHash)+@($taskPolicy.CompatibleBaseHashes))){throw 'Pack hash is outside the audited policy registry.'}
 & dotnet publish Companion\Companion.csproj -c Release -o 'EarthBound Companion'
 if($LASTEXITCODE -ne 0){throw 'Companion build failed.'}
 Copy-Item build\companion\earthbound.exe $gameExe -Force
 Copy-Item tools\SDL2-2.32.10\x86_64-w64-mingw32\bin\SDL2.dll 'EarthBound Companion\Game\SDL2.dll' -Force
 Copy-Item -LiteralPath (Join-Path $projectRoot 'Shaders') -Destination (Join-Path $projectRoot 'EarthBound Companion') -Recurse -Force
 if($ShaderRuntimePath){Copy-Item -LiteralPath ([IO.Path]::GetFullPath($ShaderRuntimePath)) -Destination (Join-Path $projectRoot 'EarthBound Companion\Game\librashader.dll') -Force}
 Write-Output 'Built EarthBound Companion. Saves and preferences were retained.'
} finally {$env:PATH=$taskOriginalPath;Pop-Location}
