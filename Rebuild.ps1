$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$gameExe=Join-Path $projectRoot 'EarthBound Companion\Game\earthbound.exe'
if(Get-Process -Name earthbound -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $gameExe}){throw 'Close EarthBound before rebuilding.'}
Push-Location $projectRoot
$taskOriginalPath=$env:PATH
try {
 $env:PATH="$projectRoot\tools\mingw64\bin;$projectRoot\native-source\.venv\Scripts;$env:PATH"
 $env:PYTHONUTF8='1'
 & native-source\.venv\Scripts\python.exe tools\create_fixture.py
 if($LASTEXITCODE -ne 0){throw 'Fixture preparation failed.'}
 & native-source\.venv\Scripts\cmake.exe -S native-source\port\unix -B build\companion -G Ninja -DCMAKE_BUILD_TYPE=Release -DEB_RUNTIME_ASSETS=ON -DEB_ENABLE_VERIFY=OFF -DEB_ENABLE_AUDIO=ON "-DSDL2_DIR=$projectRoot/tools/SDL2-2.32.10/x86_64-w64-mingw32/lib/cmake/SDL2"
 if($LASTEXITCODE -ne 0){throw 'Native configuration failed.'}
 & native-source\.venv\Scripts\cmake.exe --build build\companion --parallel 8
 if($LASTEXITCODE -ne 0){throw 'Native build failed.'}
 & native-source\.venv\Scripts\python.exe tools\export_randomizer_layout.py
 if($LASTEXITCODE -ne 0){throw 'Randomizer asset registry export failed.'}
 & native-source\.venv\Scripts\python.exe tools\audit_progression.py
 if($LASTEXITCODE -ne 0){throw 'Progression protection audit failed.'}
 & dotnet publish Companion\Companion.csproj -c Release -o 'EarthBound Companion'
 if($LASTEXITCODE -ne 0){throw 'Companion build failed.'}
 Copy-Item build\companion\earthbound.exe $gameExe -Force
 Copy-Item tools\SDL2-2.32.10\x86_64-w64-mingw32\bin\SDL2.dll 'EarthBound Companion\Game\SDL2.dll' -Force
 Write-Output 'Built EarthBound Companion. Saves and preferences were retained.'
} finally {$env:PATH=$taskOriginalPath;Pop-Location}
