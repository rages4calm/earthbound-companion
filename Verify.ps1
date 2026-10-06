$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
Push-Location $projectRoot
try{
 & native-source\.venv\Scripts\python.exe scripts\create_fixture.py
 if($LASTEXITCODE -ne 0){throw 'Runtime fixture preparation failed.'}
 & native-source\.venv\Scripts\cmake.exe --build build\companion --target test_runtime_assets --parallel 4
 if($LASTEXITCODE -ne 0){throw 'Runtime loader test build failed.'}
}finally{Pop-Location}
$testDir=Join-Path $projectRoot 'validation\tests'
New-Item -ItemType Directory -Force $testDir | Out-Null
Copy-Item (Join-Path $projectRoot 'EarthBound Companion\Game\earthbound.exe') $testDir -Force
Copy-Item (Join-Path $projectRoot 'EarthBound Companion\Game\SDL2.dll') $testDir -Force
$pak=Join-Path $projectRoot 'EarthBound Companion\Game\assets.pak'
$results=@()
foreach($name in @('pc','savestate','keyitems','joinlevel')) {
 $log=Join-Path $testDir "$name.log"
 $testArg='--assets "'+$pak+'" --selftest-'+$name
 $p=Start-Process -FilePath (Join-Path $testDir 'earthbound.exe') -ArgumentList $testArg -Wait -PassThru -WindowStyle Hidden -RedirectStandardError $log -RedirectStandardOutput ($log+'.out')
 Get-Content $log
 $results+=@{test=$name;exit_code=$p.ExitCode}
 if($p.ExitCode -ne 0){throw "$name failed. See $log"}
}
$p=Start-Process -FilePath (Join-Path $projectRoot 'EarthBound Companion\EarthBound Companion.exe') -ArgumentList '--selftest' -Wait -PassThru -WindowStyle Hidden -RedirectStandardError (Join-Path $testDir 'companion-error.log')
if($p.ExitCode -ne 0){throw 'Companion selftest failed.'}
Copy-Item (Join-Path $projectRoot 'EarthBound Companion\companion-selftest.txt') (Join-Path $testDir 'companion.log') -Force
Get-Content (Join-Path $testDir 'companion.log')
$results+=@{test='companion';exit_code=$p.ExitCode}
$shuffleTestDir=Join-Path $projectRoot 'validation\randomizer'
New-Item -ItemType Directory -Force $shuffleTestDir | Out-Null
$p=Start-Process -FilePath (Join-Path $projectRoot 'EarthBound Companion\EarthBound Companion.exe') -ArgumentList ('--randomizer-test "'+$shuffleTestDir+'"') -Wait -PassThru -WindowStyle Hidden -RedirectStandardError (Join-Path $shuffleTestDir 'error.log')
if($p.ExitCode -ne 0){throw 'Randomizer tests failed.'}
Get-Content (Join-Path $shuffleTestDir 'tests.txt')
$results+=@{test='randomizer';exit_code=$p.ExitCode}
$fixturePak=Join-Path $projectRoot 'build\companion\game_lib\runtime_assets_test\assets_test.pak'
$fixtureScratch=Join-Path $projectRoot 'build\companion\game_lib\runtime_assets_test\scratch'
$p=Start-Process -FilePath (Join-Path $projectRoot 'build\companion\game_lib\test_runtime_assets.exe') -ArgumentList ('"'+$fixturePak+'" "'+$fixtureScratch+'"') -Wait -PassThru -WindowStyle Hidden -RedirectStandardError (Join-Path $testDir 'assets-error.log') -RedirectStandardOutput (Join-Path $testDir 'assets.log')
if($p.ExitCode -ne 0){throw 'Runtime asset loader test failed.'}
Get-Content (Join-Path $testDir 'assets.log')
$results+=@{test='runtime-assets';exit_code=$p.ExitCode}
Push-Location $projectRoot
try{& native-source\.venv\Scripts\python.exe scripts\validate_msu.py;if($LASTEXITCODE -ne 0){throw 'MSU validation failed.'}}finally{Pop-Location}
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $testDir 'results.json') -Encoding UTF8
Write-Output 'All checks passed. Full-game playthrough remains unverified.'
